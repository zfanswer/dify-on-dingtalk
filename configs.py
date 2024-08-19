#!/usr/bin/env python
# -*- coding: utf-8 -*-
# __author__ = 'zfanswer'

import os

import yaml
from dotenv import load_dotenv
from loguru import logger

load_dotenv(override=False, verbose=True)

try:
    # app config
    LOG_LEVEL = os.getenv("LOG_LEVEL", default="INFO")
    DEFAULT_MAX_WORKERS = int(os.getenv("DEFAULT_MAX_WORKERS", default=2))
    # dify service config
    DIFY_OPEN_API_URL = os.getenv("DIFY_OPEN_API_URL", default="https://api.dify.ai/v1")
except (TypeError, ValueError) as e:
    logger.error(f"Error converting environment variable: {e}")
    raise e


def load_bots_config():
    """
    load bots config from file
    :return:
    """
    with open(".bots.yaml", "r") as f:
        bots_conf = yaml.safe_load(f)
    return bots_conf


if __name__ == "__main__":
    # 使用示例
    print(os.getenv("DIFY_OPEN_API_URL"))
    print(type(DEFAULT_MAX_WORKERS))
