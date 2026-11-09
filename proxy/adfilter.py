#!/usr/bin/env python3
"""选集广告过滤：识别“关注公众号/加微信/下载APP”等引流假选集。

只做名称判断（正则），不解析、不改写 m3u8；解析开销为零，误伤时保留正片结构。
"""
from __future__ import annotations

import re

# 命中即视为广告选集（非正片）。仅作用于选集【名称】，不碰正片名。
_EP_AD_PATTERNS = (
    r"关注(?:公众号|微信|官方|公众|抖音|快手)",
    r"(?:官方)?公众号",
    r"加(?:微信|群|VX|vx|V信|企微|客服)",
    r"(?:添加|联系)(?:微信|客服|QQ|qq)",
    r"扫码(?:关注|领取|添加)",
    r"微信[:：]?\s*[A-Za-z0-9_\-]{4,}",
    r"(?:QQ|qq)群?\s*[:：]?\s*\d{5,}",
    r"(?:VX|vx|v信|薇信)\s*[:：]?\s*[A-Za-z0-9_\-]{4,}",
    r"领(?:取|红包)(?:福利|资源|大片|影视)",
    r"(?:永久|免费)(?:网址|地址|入口|官网|看片)",
    r"(?:更多|精彩)(?:资源|影片|大片)?(?:请|前往|访问|关注)",
    r"(?:复制|打开)(?:浏览器|链接).{0,12}(?:搜索|访问|打开|下载)",
    r"www\.[A-Za-z0-9.\-]+\.(?:com|net|cn|cc|xyz|top|vip|tv|me|app)",
    r"[A-Za-z0-9.\-]+\.(?:com|net|cn|cc|xyz|top|vip|tv)\s*$",
    r"下载\s*(?:APP|app|应用|客户端)",
    r"(?:广告|推广|宣发|引流)(?:位|片|视频|选集)?$",
    r"本(?:集|片|视频)由.{0,20}(?:赞助|提供|广告)",
)
_EP_AD_RE = [re.compile(p, re.I) for p in _EP_AD_PATTERNS]

# 白名单：选集名里出现这些正片信号时，即使含“加/关注”等也不轻易删。
_EP_REAL = re.compile(
    r"(?:第?\s*\d{1,4}\s*[集期话]|^\s*\d{1,4}\s*$|正片|预告|花絮|彩蛋|"
    r"HD|BD|TC|TS|清晰|国语|粤语|中英|字幕|线路|CD\d|完结|大结局|"
    r"上$|下$|中$|前$|后$)")


def is_ad_episode(name: str) -> bool:
    """选集名是否为引流广告（公众号/微信/加群/网址/下载APP 等）。"""
    n = (name or "").strip()
    if not n or len(n) > 60:
        return False
    if _EP_REAL.search(n):
        return False
    return any(rx.search(n) for rx in _EP_AD_RE)
