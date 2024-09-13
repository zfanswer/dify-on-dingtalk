#!/usr/bin/env python
# -*- coding: utf-8 -*-
# __author__ = 'zfanswer'
import time


class Cache:
    def __init__(self, expiry_time=60):
        self.cache = {}  # 普通的字典来存储数据
        self.expiry_time = expiry_time

    def _is_expired(self, key):
        return time.time() - self.cache[key][1] > self.expiry_time

    def set(self, key, value):
        # 插入新的key-value，并存储当前时间戳
        self.cache[key] = (value, time.time())

    def get(self, key):
        item = self.cache.get(key)
        if item:
            if not self._is_expired(key):
                return item[0]  # 返回值
            else:
                del self.cache[key]  # 如果过期，删除该key
        return None

    def cleanup(self):
        # 清除过期的缓存
        keys_to_delete = [key for key in list(self.cache) if self._is_expired(key)]
        for key in keys_to_delete:
            del self.cache[key]

    def __str__(self):
        # 用于查看缓存内容
        return str({k: v[0] for k, v in self.cache.items()})


if __name__ == "__main__":
    # 使用示例
    cache = Cache(expiry_time=5)  # 设置过期时间为5秒

    cache.set("a", 1)
    cache.set("b", 2)

    time.sleep(3)
    print(cache.get("a"))  # 输出: 1

    time.sleep(3)
    print(cache.get("a"))  # 输出: None, 因为 "a" 已经过期
