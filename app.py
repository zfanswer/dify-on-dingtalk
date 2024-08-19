#!/usr/bin/env python
# -*- coding: utf-8 -*-
# __author__ = 'zfanswer'
import sys
from concurrent.futures import ThreadPoolExecutor

import dingtalk_stream
from dingtalk_stream import CallbackHandler
from loguru import logger

from configs import DIFY_OPEN_API_URL, LOG_LEVEL, load_bots_config, DEFAULT_MAX_WORKERS
from core.dify_client import ChatClient, CompletionClient, WorkflowClient
from core.handlers import HandlerFactory

logger.remove()
logger.add(sys.stdout, level=LOG_LEVEL)


def start_dingtalk_stream_client(app_client_id: str, app_client_secret: str, callback_handler: CallbackHandler):
    credential = dingtalk_stream.Credential(app_client_id, app_client_secret)
    client = dingtalk_stream.DingTalkStreamClient(credential, logger)
    # client.register_all_event_handler(event_handler())
    client.register_callback_handler(dingtalk_stream.ChatbotMessage.TOPIC, callback_handler)
    client.start_forever()


def run():
    bots_conf = load_bots_config()
    bots_cnt = len(bots_conf["bots"])
    max_workers_num = 0
    for bot in bots_conf["bots"]:
        max_workers_num += bot.get("max_workers", DEFAULT_MAX_WORKERS)
    logger.info(f"待启动机器人数量：{bots_cnt}, 预计使用最大线程数：{max_workers_num}")
    with ThreadPoolExecutor(max_workers=max_workers_num) as executor:
        futures = []
        for i, bot in enumerate(bots_conf["bots"]):
            logger.info(f"启动第{i+1}个机器人：{bot['name']}")
            logger.debug(bot)
            bot_worker_num = bot.get("max_workers", DEFAULT_MAX_WORKERS)
            bot_app_client_id = bot["dingtalk_app_client_id"]
            bot_app_client_secret = bot["dingtalk_app_client_secret"]
            # 根据app类型，使用不同的dify api client
            if bot["dify_app_type"].lower() == "chatbot":
                bot_dify_client = ChatClient(api_key=bot["dify_app_api_key"], base_url=DIFY_OPEN_API_URL)
            elif bot["dify_app_type"].lower() == "completion":
                bot_dify_client = CompletionClient(api_key=bot["dify_app_api_key"], base_url=DIFY_OPEN_API_URL)
            elif bot["dify_app_type"].lower() == "workflow":
                bot_dify_client = WorkflowClient(api_key=bot["dify_app_api_key"], base_url=DIFY_OPEN_API_URL)
            else:
                raise ValueError(f"不支持的机器人类型：{bot['dify_app_type']}")
            # bot_dify_client = ChatClient(api_key=bot["dify_app_api_key"], base_url=DIFY_OPEN_API_URL)
            handler_params = {"dify_api_client": bot_dify_client}
            bot_handler = HandlerFactory.create_handler(bot["handler"], **handler_params)
            for _ in range(bot_worker_num):
                futures.append(executor.submit(start_dingtalk_stream_client, bot_app_client_id, bot_app_client_secret, bot_handler))
        # 等待所有线程完成
        for future in futures:
            future.result()


if __name__ == "__main__":
    run()
