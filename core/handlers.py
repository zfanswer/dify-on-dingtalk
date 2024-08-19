#!/usr/bin/env python
# -*- coding: utf-8 -*-
# __author__ = 'zfanswer'
import json
import os
from typing import Callable

from dingtalk_stream import AckMessage, ChatbotHandler, CallbackHandler, CallbackMessage, ChatbotMessage, AICardReplier
from loguru import logger
from sseclient import SSEClient

from core.cache import Cache
from core.dify_client import ChatClient, DifyClient


class HandlerFactory(object):

    @staticmethod
    def create_handler(handler_type: str, **kwargs) -> CallbackHandler:
        if handler_type == "DifyAiCardBotHandler":
            return DifyAiCardBotHandler(**kwargs)
        else:
            raise ValueError(f"Unsupported handler type: {handler_type}")


class DifyAiCardBotHandler(ChatbotHandler):

    def __init__(self, dify_api_client: DifyClient):
        super().__init__()
        self.dify_api_client = dify_api_client
        self.cache = Cache(expiry_time=60 * int(os.getenv("DIFY_CONVERSATION_REMAIN_TIME")))  # 每个用户维持会话时间xx秒

    async def process(self, callback_msg: CallbackMessage):
        logger.debug(callback_msg)
        incoming_message = ChatbotMessage.from_dict(callback_msg.data)

        logger.info(f"收到用户消息：{incoming_message}")

        if incoming_message.message_type != "text":
            self.reply_text("对不起，我目前只看得懂文字喔~", incoming_message)
            return AckMessage.STATUS_OK, "OK"

        # 在企业开发者后台配置的卡片模版id https://open-dev.dingtalk.com/fe/card
        card_template_id = os.getenv("DINGTALK_AI_CARD_TEMPLATE_ID")
        content_key = "content"
        card_data = {content_key: ""}
        card_instance = AICardReplier(self.dingtalk_client, incoming_message)
        # 先投放卡片
        card_instance_id = card_instance.create_and_send_card(card_template_id, card_data, callback_type="STREAM")
        # 再流式更新卡片
        try:
            # full_content_value = await aio_call_with_stream(
            full_content_value = self._call_dify_with_stream(
                incoming_message,
                lambda content_value: card_instance.streaming(
                    card_instance_id,
                    content_key=content_key,
                    content_value=content_value,
                    append=False,
                    finished=False,
                    failed=False,
                ),
            )
            card_instance.streaming(
                card_instance_id,
                content_key=content_key,
                content_value=full_content_value,
                append=False,
                finished=True,
                failed=False,
            )
        except Exception as e:
            logger.exception(e)
            card_instance.streaming(
                card_instance_id,
                content_key=content_key,
                content_value=f"出现了异常: {e}",
                append=False,
                finished=False,
                failed=True,
            )

        return AckMessage.STATUS_OK, "OK"

    def _call_dify_with_stream(self, incoming_message: ChatbotMessage, callback: Callable[[str], None]):
        if incoming_message.message_type != "text":
            # TODO: 暂时只支持文本消息
            request_content = ""
        else:
            request_content = incoming_message.text.content
        conversation_id = self.cache.get(incoming_message.sender_staff_id)
        response = self.dify_api_client.query(
            inputs={},
            query=request_content,
            user=incoming_message.sender_nick,
            response_mode="streaming",
            files=None,
            conversation_id=conversation_id,  # 需要考虑下怎么让一个用户的回话保持自己的上下文
        )
        if response.status_code != 200:
            raise Exception(f"调用模型服务失败，返回码：{response.status_code}，返回内容：{response.text}")
        sse_client = SSEClient(response)
        full_content = ""  # with incrementally we need to merge output.
        length = 0
        for event in sse_client.events():
            r = json.loads(event.data)
            logger.debug(f"接收到模型服务返回：{r}")
            if r.get("event") in ["message", "agent_message"]:
                # basic chat mode, agent mode下的文本输出
                full_content += r.get("answer", "")
                full_content_length = len(full_content)
                if full_content_length - length > 10:
                    callback(full_content)
                    logger.debug(
                        f'调用流式接口更新内容：output={r.get("answer", "")}, current_length={length}, next_length={full_content_length}'
                    )
                    length = full_content_length
            elif r.get("event") in ["text_chunk"]:
                # completion模式文本输出
                full_content += r["data"].get("text", "")
                full_content_length = len(full_content)
                if full_content_length - length > 10:
                    callback(full_content)
                    logger.debug(
                        f'调用流式接口更新内容：output={r.get("answer", "")}, current_length={length}, next_length={full_content_length}'
                    )
                    length = full_content_length
            elif r.get("event") in ["agent_thought"]:
                # agent模式调用过程处理
                # 接收到模型服务返回：{'event': 'agent_thought', 'conversation_id': 'd881314b-5e75-45cb-8aac-16e2bed5a09c', 'message_id': '977bf584-5e11-4493-9b98-e56226d9e9a0', 'created_at': 1722310961, 'task_id': 'b3840f55-34b0-4479-8240-ad6b3af76401', 'id': 'c322cfa9-50cb-4f1b-9e2f-680e561291ea', 'position': 1, 'thought': '', 'observation': '', 'tool': 'gaode_weather', 'tool_labels': {'gaode_weather': {'zh_Hans': '天气预报', 'en_US': 'Weather Forecast', 'pt_BR': 'Previsão do tempo'}}, 'tool_input': '{"gaode_weather": {"city": "郑州"}}', 'message_files': []}
                # 接收到模型服务返回：{'event': 'agent_thought', 'conversation_id': 'd881314b-5e75-45cb-8aac-16e2bed5a09c', 'message_id': '977bf584-5e11-4493-9b98-e56226d9e9a0', 'created_at': 1722310961, 'task_id': 'b3840f55-34b0-4479-8240-ad6b3af76401', 'id': 'c322cfa9-50cb-4f1b-9e2f-680e561291ea', 'position': 1, 'thought': '', 'observation': '{"gaode_weather": "[{\\"date\\": \\"2024-07-30\\", \\"week\\": \\"2\\", \\"dayweather\\": \\"小雨\\", \\"daytemp_float\\": \\"33.0\\", \\"daywind\\": \\"南\\", \\"nightweather\\": \\"小雨\\", \\"nighttemp_float\\": \\"25.0\\"}, {\\"date\\": \\"2024-07-31\\", \\"week\\": \\"3\\", \\"dayweather\\": \\"小雨\\", \\"daytemp_float\\": \\"32.0\\", \\"daywind\\": \\"南\\", \\"nightweather\\": \\"阴\\", \\"nighttemp_float\\": \\"26.0\\"}, {\\"date\\": \\"2024-08-01\\", \\"week\\": \\"4\\", \\"dayweather\\": \\"多云\\", \\"daytemp_float\\": \\"35.0\\", \\"daywind\\": \\"南\\", \\"nightweather\\": \\"晴\\", \\"nighttemp_float\\": \\"26.0\\"}, {\\"date\\": \\"2024-08-02\\", \\"week\\": \\"5\\", \\"dayweather\\": \\"多云\\", \\"daytemp_float\\": \\"35.0\\", \\"daywind\\": \\"南\\", \\"nightweather\\": \\"多云\\", \\"nighttemp_float\\": \\"27.0\\"}]"}', 'tool': 'gaode_weather', 'tool_labels': {'gaode_weather': {'zh_Hans': '天气预报', 'en_US': 'Weather Forecast', 'pt_BR': 'Previsão do tempo'}}, 'tool_input': '{"gaode_weather": {"city": "郑州"}}', 'message_files': []}
                pass
            elif r.get("event") in ["message_file"]:
                # 生成文件处理
                # e.g. 接收到模型服务返回：{'event': 'message_file', 'conversation_id': '3b0f090e-82a1-4734-a178-16b113e39698', 'message_id': '5e7ba156-a78b-4da4-9e43-9101dcae25b1', 'created_at': 1722311020, 'task_id': 'a20270d4-0829-47ad-a509-da748bb791b1', 'id': 'b746560e-8e03-4e94-bd3f-8c2e42373ed7', 'type': 'image', 'belongs_to': 'assistant', 'url': '/files/tools/d5041a35-3e2a-4a7d-963a-52b094c8cf73.png?timestamp=1722311048&nonce=a1e57c297e933b0f643e2be04a1dc794&sign=kPAjh2r7oBbwvyIgmHKzKZY8z75Y_sDH1SkL0fmJxI0='}
                pass
            elif r.get("event") in ["workflow_started", "workflow_finished"]:
                pass
            elif r.get("event") in ["node_started", "node_finished"]:
                pass
            elif r.get("event") in ["message_end"]:
                # 对话结束消息处理
                # 接收到模型服务返回：{'event': 'message_end', 'conversation_id': 'd881314b-5e75-45cb-8aac-16e2bed5a09c', 'message_id': '977bf584-5e11-4493-9b98-e56226d9e9a0', 'created_at': 1722310961, 'task_id': 'b3840f55-34b0-4479-8240-ad6b3af76401', 'id': '977bf584-5e11-4493-9b98-e56226d9e9a0', 'metadata': {'usage': {'prompt_tokens': 1279, 'prompt_unit_price': '0.0005', 'prompt_price_unit': '0.001', 'prompt_price': '0.0006395', 'completion_tokens': 66, 'completion_unit_price': '0.0015', 'completion_price_unit': '0.001', 'completion_price': '0.0000990', 'total_tokens': 507, 'total_price': '0.0002605', 'currency': 'USD', 'latency': 1.715979496948421}}}
                self.cache.set(incoming_message.sender_staff_id, r.get("conversation_id"))
            else:
                # raise NotImplementedError(f"Event: {r.get('event')}, not implemented.")
                logger.exception(f"Event: {r.get('event')}, not implemented.")
        logger.info(
            {
                "request_content": request_content,
                "full_response": full_content,
                "full_response_length": len(full_content),
            }
        )
        return full_content
