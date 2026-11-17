#!/usr/bin/env python3
"""在线条目的本地收藏 / 已看标记。state/marks.json。

官方后端不认识虚拟在线 guid：PUT /item/favorite 返回 -6、POST /item/watched
返回 -1。我们在本地接管这两类标记（卸载即清、零数据库污染），并在
item/list、item/{guid}、favorite/list 中回填，使收藏夹和「已看」筛选可用。

标记按飞牛影视用户分桶（user_guid 来自 userctx），与官方 favorite 表、
item_user_play 表的口径一致。早期只有一份全局记录，导致 A 用户收藏的在线
条目出现在 B 用户的收藏夹里。
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import userctx

_STATE = Path(__file__).resolve().parent.parent / "state" / "marks.json"
_LOCK = threading.RLock()
_MAX = 5000
_META_KEYS = ("title", "type", "poster", "year", "remarks",
              "ancestor_guid", "ancestor_name")


class Marks:
    def __init__(self):
        # {user_guid: {guid: record}}；"" 为无令牌请求的匿名桶
        self._fav: dict[str, dict[str, dict]] = {}
        self._watched: dict[str, dict[str, dict]] = {}
        self._load()

    def _load(self):
        try:
            j = json.loads(_STATE.read_text())
        except Exception:
            return
        if not isinstance(j, dict):
            return
        users = j.get("users")
        if isinstance(users, dict):
            for uid, v in users.items():
                if not isinstance(v, dict):
                    continue
                fav = v.get("favorites") or {}
                wat = v.get("watched") or {}
                if isinstance(fav, dict):
                    self._fav[str(uid)] = fav
                if isinstance(wat, dict):
                    self._watched[str(uid)] = wat
            return
        # 旧格式：全局 favorites / watched。分不清归属，整体归到管理员名下，
        # 其余用户从干净状态开始。
        fav = j.get("favorites") or {}
        wat = j.get("watched") or {}
        if (isinstance(fav, dict) and fav) or (isinstance(wat, dict) and wat):
            admin = userctx.admin_user() or ""
            self._fav = {admin: fav} if isinstance(fav, dict) and fav else {}
            self._watched = {admin: wat} if isinstance(wat, dict) and wat else {}
            self._persist_locked()

    @staticmethod
    def _owner(uid: str | None) -> str:
        return userctx.current() if uid is None else (uid or "")

    def _bucket(self, store: dict, uid: str | None) -> dict[str, dict]:
        owner = self._owner(uid)
        return store.setdefault(owner, {})

    @staticmethod
    def _trim(recs: dict[str, dict]) -> dict[str, dict]:
        if len(recs) <= _MAX:
            return recs
        keep = sorted(recs.values(), key=lambda r: r.get("ts", 0),
                      reverse=True)[:_MAX]
        return {r["guid"]: r for r in keep}

    def _persist_locked(self):
        try:
            _STATE.parent.mkdir(parents=True, exist_ok=True)
            users: dict[str, dict] = {}
            for store_name, store in (("favorites", self._fav),
                                      ("watched", self._watched)):
                for uid, recs in list(store.items()):
                    recs = self._trim(recs)
                    store[uid] = recs
                    if recs:
                        users.setdefault(uid, {})[store_name] = recs
            tmp = _STATE.with_suffix(".tmp")
            tmp.write_text(json.dumps({"users": users}, ensure_ascii=False))
            tmp.replace(_STATE)
        except Exception:
            pass

    # ---- 收藏 ----
    def add_favorite(self, guid: str, extra: dict | None = None,
                     uid: str | None = None) -> bool:
        if not guid:
            return False
        with _LOCK:
            fav = self._bucket(self._fav, uid)
            if guid in fav:
                return True
            rec = {"guid": guid, "ts": time.time()}
            if extra:
                for k in _META_KEYS:
                    if extra.get(k) not in (None, ""):
                        rec[k] = extra[k]
            fav[guid] = rec
            self._persist_locked()
            return True

    def remove_favorite(self, guid: str, uid: str | None = None) -> bool:
        if not guid:
            return False
        with _LOCK:
            fav = self._bucket(self._fav, uid)
            existed = fav.pop(guid, None) is not None
            if existed:
                self._persist_locked()
            return existed

    def is_favorite(self, guid: str, uid: str | None = None) -> bool:
        if not guid:
            return False
        with _LOCK:
            return guid in self._bucket(self._fav, uid)

    def favorite_guids(self, uid: str | None = None) -> set[str]:
        with _LOCK:
            return set(self._bucket(self._fav, uid).keys())

    def favorite_records(self, uid: str | None = None) -> list[dict]:
        with _LOCK:
            return [dict(r) for r in sorted(
                self._bucket(self._fav, uid).values(),
                key=lambda r: r.get("ts", 0), reverse=True)]

    # ---- 已看 ----
    def set_watched(self, guid: str, extra: dict | None = None,
                    uid: str | None = None) -> bool:
        if not guid:
            return False
        with _LOCK:
            wat = self._bucket(self._watched, uid)
            rec = wat.get(guid, {"guid": guid})
            rec["ts"] = time.time()
            if extra:
                for k in _META_KEYS:
                    if extra.get(k) not in (None, ""):
                        rec[k] = extra[k]
            wat[guid] = rec
            self._persist_locked()
            return True

    def remove_watched(self, guid: str, uid: str | None = None) -> bool:
        if not guid:
            return False
        with _LOCK:
            wat = self._bucket(self._watched, uid)
            existed = wat.pop(guid, None) is not None
            if existed:
                self._persist_locked()
            return existed

    def is_watched(self, guid: str, uid: str | None = None) -> bool:
        if not guid:
            return False
        with _LOCK:
            return guid in self._bucket(self._watched, uid)

    def watched_ts(self, guid: str, uid: str | None = None) -> int:
        with _LOCK:
            r = self._bucket(self._watched, uid).get(guid)
        return int(r.get("ts", 0)) if r else 0

    def watched_guids(self, uid: str | None = None) -> set[str]:
        with _LOCK:
            return set(self._bucket(self._watched, uid).keys())

    def remember_meta(self, guid: str, meta: dict, uid: str | None = None):
        """列表渲染时顺手补充元信息，供收藏夹在条目未被 store 记住时兜底。"""
        if not guid or not meta:
            return
        with _LOCK:
            changed = False
            for store in (self._fav, self._watched):
                rec = self._bucket(store, uid).get(guid)
                if not rec:
                    continue
                for k in _META_KEYS:
                    v = meta.get(k)
                    if v not in (None, "") and not rec.get(k):
                        rec[k] = v
                        changed = True
            if changed:
                self._persist_locked()


marks = Marks()
