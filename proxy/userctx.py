#!/usr/bin/env python3
"""识别请求所属的飞牛影视用户。

官方后端把播放进度按 (user_guid, item_guid) 存（trimmedia.db 的
item_user_play 表），而扩展此前只有一份全局 history.json，于是所有用户共用
「继续观看」。客户端的身份载体是登录令牌（Authorization），令牌 → 用户在官方
的 trimactivity.db → user_token 表里；这里只读该表，拿 user_guid 做分桶键。

只读、只缓存，不写官方库。取不到身份（无令牌的局域网探测、旧客户端）时返回
空串，落到匿名桶，不会串到其他用户。
"""
from __future__ import annotations

import contextvars
import hashlib
import os
import sqlite3
import threading
import time

_APP_DATA = "/usr/local/apps/@appdata/trim.media/database"
_ACTIVITY_DB = os.environ.get("TMO_ACTIVITY_DB") or f"{_APP_DATA}/trimactivity.db"
_MEDIA_DB = os.environ.get("TMO_MEDIA_DB") or f"{_APP_DATA}/trimmedia.db"

_POS_TTL = 3600.0   # 令牌 → 用户：登录期间不会变，缓存久一点
_NEG_TTL = 60.0     # 查不到的令牌短暂缓存，避免每次请求都开库

_lock = threading.Lock()
_cache: dict[str, tuple[str, float]] = {}   # sha256(token) -> (user_guid, expires)
_admin_cache: tuple[str, float] = ("", 0.0)

_current: contextvars.ContextVar[str] = contextvars.ContextVar(
    "tmo_current_user", default="")


def _rows(sql: str, args: tuple = (), db: str = "") -> list[tuple]:
    try:
        conn = sqlite3.connect(f"file:{db or _ACTIVITY_DB}?mode=ro", uri=True,
                               timeout=1.0)
        try:
            return list(conn.execute(sql, args))
        finally:
            conn.close()
    except Exception:
        return []


def _norm_token(raw: str) -> str:
    tok = (raw or "").strip()
    if tok[:7].lower() == "bearer ":
        tok = tok[7:].strip()
    return tok


def _key(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8", "ignore")).hexdigest()


def token_user(token: str) -> str:
    """登录令牌 → user_guid；未知/失效令牌返回空串。"""
    token = _norm_token(token)
    if not token:
        return ""
    key = _key(token)
    now = time.time()
    with _lock:
        hit = _cache.get(key)
        if hit and hit[1] > now:
            return hit[0]
    rows = _rows("select user_guid from user_token where token = ? and status = 1",
                 (token,))
    uid = (rows[0][0] if rows else "") or ""
    with _lock:
        _cache[key] = (uid, now + (_POS_TTL if uid else _NEG_TTL))
        if len(_cache) > 4096:
            dead = [k for k, v in _cache.items() if v[1] <= now]
            for k in dead:
                _cache.pop(k, None)
    return uid


def admin_user() -> str:
    """首个启用的管理员 user_guid，用于旧全局历史的归属迁移。"""
    global _admin_cache
    now = time.time()
    with _lock:
        uid, exp = _admin_cache
        if exp > now:
            return uid
    rows = _rows("select guid from user where is_admin = 1 and status = 1 "
                 "order by create_time limit 1", db=_MEDIA_DB)
    uid = (rows[0][0] if rows else "") or ""
    with _lock:
        _admin_cache = (uid, now + 600.0)
    return uid


def resolve(request) -> str:
    """从请求头解析当前用户。"""
    return token_user(request.headers.get("authorization", ""))


def set_current(uid: str):
    return _current.set(uid or "")


def reset(token) -> None:
    try:
        _current.reset(token)
    except Exception:
        pass


def current() -> str:
    return _current.get()
