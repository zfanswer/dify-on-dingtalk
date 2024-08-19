#!/usr/bin/env python
# -*- coding: utf-8 -*-
# __author__ = 'zfanswer'
import unittest
from unittest.mock import patch
from core.dify_client import ChatClient


class TestChatClient(unittest.TestCase):

    def setUp(self):
        self.chat_client = ChatClient(api_key="app-r7P5q2Dl3opvJFewFD1OD7D9", base_url="http://192.168.250.64/v1")

    @patch("dify_client.ChatClient._send_request")
    def test_create_chat_message_blocking(self, mock_send_request):
        # 测试 blocking 模式
        inputs = {}
        query = "你好，介绍一下你自己吧。"
        user = "user"
        response_mode = "blocking"
        conversation_id = "conv_id"
        files = None

        self.chat_client.create_chat_message(inputs, query, user, response_mode, conversation_id, files)

        mock_send_request.assert_called_once_with(
            "POST",
            "/chat-messages",
            {
                "inputs": inputs,
                "query": query,
                "user": user,
                "response_mode": response_mode,
                "conversation_id": conversation_id,
                "files": files,
            },
            stream=False,
        )

    @patch("dify_client.ChatClient._send_request")
    def test_create_chat_message_streaming(self, mock_send_request):
        # 测试 streaming 模式
        inputs = {}
        query = "你好，介绍一下你自己吧。"
        user = "user"
        response_mode = "streaming"
        conversation_id = None
        files = None

        self.chat_client.create_chat_message(inputs, query, user, response_mode, conversation_id, files)

        mock_send_request.assert_called_once_with(
            "POST",
            "/chat-messages",
            {"inputs": inputs, "query": query, "user": user, "response_mode": response_mode, "files": files},
            stream=True,
        )

    # 可以添加更多的测试用例来覆盖不同的场景和参数组合


if __name__ == "__main__":
    unittest.main()
