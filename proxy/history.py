#!/usr/bin/env python3
"""在线播放进度（继续观看）。state/history.json。

记录由前端高频 POST /play/record 驱动，内存更新 + 限频落盘；
GET /play/list 时与官方本地历史合并，让在线条目出现在「继续观看」。

进度按飞牛影视用户分桶（user_guid 来自 userctx）。官方后端自己也是按
(user_guid, item_guid) 存的，扩展早期只有一份全局记录，导致 A 用户的进度
出现在 B 用户的「继续观看」里。
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import userctx

_STATE = Path(__file__).resolve().parent.parent / "state" / "history.json"
_LOCK = threading.RLock()
_FLUSH_INTERVAL = 3.0
_MAX = 500
# 客户端进入播放页会先报 ts=0，随后从 0 起播、续播 seek 才落地；这段窗口里
# 上报的极小 ts 是起播抖动，不能覆盖已存进度（否则快速退出就丢进度）。
_ENTRY_WINDOW = 90.0


class History:
    def __init__(self):
        # {user_guid: {item_guid: record}}；"" 为无令牌请求的匿名桶
        self._rec: dict[str, dict[str, dict]] = {}
        self._zero_at: dict[tuple[str, str], float] = {}
        self._last_flush = 0.0
        self._dirty = False
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
            self._rec = {
                str(u): (v.get("records") or {})
                for u, v in users.items() if isinstance(v, dict)
            }
            return
        # 旧格式：全局 records。这些记录分不清是谁的，归到管理员名下，
        # 其余用户的「继续观看」从干净状态开始。
        legacy = j.get("records") or {}
        if isinstance(legacy, dict) and legacy:
            self._rec = {userctx.admin_user() or "": legacy}
            self._dirty = True
            self._flush_locked(force=True)

    @staticmethod
    def _owner(uid: str | None) -> str:
        return userctx.current() if uid is None else (uid or "")

    def _recs(self, uid: str | None) -> dict[str, dict]:
        return self._rec.setdefault(self._owner(uid), {})

    def _flush_locked(self, force: bool = False):
        now = time.time()
        if not self._dirty:
            return
        if not force and now - self._last_flush < _FLUSH_INTERVAL:
            return
        try:
            _STATE.parent.mkdir(parents=True, exist_ok=True)
            users = {}
            for uid, recs in self._rec.items():
                if len(recs) > _MAX:
                    keep = sorted(recs.values(),
                                  key=lambda r: r.get("updated_at", 0),
                                  reverse=True)[:_MAX]
                    recs = {r["item_guid"]: r for r in keep}
                    self._rec[uid] = recs
                if recs:
                    users[uid] = {"records": recs}
            self._rec = {u: v["records"] for u, v in users.items()}
            tmp = _STATE.with_suffix(".tmp")
            tmp.write_text(json.dumps({"users": users}, ensure_ascii=False))
            tmp.replace(_STATE)
            self._dirty = False
            self._last_flush = now
        except Exception:
            pass

    def flush(self):
        with _LOCK:
            self._flush_locked(force=True)

    def record(self, body: dict, uid: str | None = None) -> bool:
        """处理一次 play/record 上报，返回是否为我们的在线条目。"""
        ig = body.get("item_guid", "")
        if not ig:
            return False
        owner = self._owner(uid)
        with _LOCK:
            recs = self._recs(owner)
            prev = recs.get(ig, {})
            now = time.time()
            ts = max(0, int(float(body.get("ts", 0) or 0)))
            prev_ts = int(prev.get("ts", 0) or 0)
            reset = bool(body.get("reset"))
            zkey = (owner, ig)
            if ts == 0:
                self._zero_at[zkey] = now  # 进入播放页（先报 ts=0）
            # 播放器每次进入播放页会先上报 ts=0，不能把已看进度清零；除此之外
            # 以最后一次上报为准（包括用户向前拖动后的回退），跨端续播才准确。
            if ts == 0 and prev_ts >= 30 and not reset:
                ts = prev_ts
            elif ts < prev_ts and not reset:
                # 进入播放页后的窗口期内，播放器从 0 起播、续播 seek 尚未落地，
                # 此间上报的小 ts 是起播抖动，保持已存进度不被覆盖。
                if now - self._zero_at.get(zkey, 0.0) < _ENTRY_WINDOW:
                    ts = prev_ts
            duration = int(float(body.get("duration", 0) or 0))
            rec = {
                "item_guid": ig,
                "media_guid": body.get("media_guid", prev.get("media_guid", "")),
                "video_guid": body.get("video_guid", prev.get("video_guid", "")),
                "audio_guid": body.get("audio_guid", prev.get("audio_guid", "")),
                "subtitle_guid": body.get("subtitle_guid",
                                          prev.get("subtitle_guid", "")),
                "resolution": body.get("resolution", prev.get("resolution", "")),
                "ts": ts,
                "duration": duration or int(prev.get("duration", 0)),
                "updated_at": time.time(),
            }
            recs[ig] = rec
            self._dirty = True
            self._flush_locked()
        return True

    def set_duration(self, item_guid: str, duration: int, uid: str | None = None):
        """补齐总时长（清单 EXTINF 算出后回填），不改变 last-watched 排序。"""
        duration = int(duration or 0)
        if not duration:
            return
        with _LOCK:
            recs = self._recs(uid)
            rec = recs.get(item_guid)
            if not rec or int(rec.get("duration", 0) or 0) == duration:
                return
            rec["duration"] = duration
            self._dirty = True
            self._flush_locked(force=True)

    def set_position(self, item_guid: str, ts: int, duration: int = 0,
                     uid: str | None = None):
        with _LOCK:
            recs = self._recs(uid)
            prev = recs.get(item_guid, {})
            prev.update({"item_guid": item_guid, "ts": int(ts),
                         "updated_at": time.time()})
            if duration:
                prev["duration"] = int(duration)
            recs[item_guid] = prev
            self._dirty = True
            self._flush_locked(force=True)

    def get(self, item_guid: str, uid: str | None = None) -> dict | None:
        with _LOCK:
            rec = self._recs(uid).get(item_guid)
            return dict(rec) if rec else None

    def all(self, uid: str | None = None) -> list[dict]:
        with _LOCK:
            self._flush_locked(force=True)
            return [dict(r) for r in self._recs(uid).values()]

    def resume_episode(self, ep_guids: list[str],
                       uid: str | None = None) -> tuple[str | None, int]:
        """给定一部剧按顺序的全部集 guid，决定"该播哪一集"。

        - 从没看过 → 第一集（ts=0）
        - 有未看完的集（进度<95%）→ 最近在看的那一集，带回 ts 续播
        - 看过的都看完了 → 下一集（ts=0）；全看完 → 最后一集
        返回 (ep_guid 或 None 表示无记录, ts)。
        """
        with _LOCK:
            recs = self._recs(uid)
            # 有序地只保留有记录的集
            watched = [(i, recs[g]) for i, g in enumerate(ep_guids)
                       if g in recs]
            if not watched:
                return (ep_guids[0] if ep_guids else None), 0
            # 找未看完的，取集序最大（最近在追）的一集
            unfinished = [(i, r) for i, r in watched
                          if not self._finished(r)]
            if unfinished:
                i, r = max(unfinished, key=lambda x: x[0])
                return ep_guids[i], int(r.get("ts", 0) or 0)
            # 都看完了 → 下一集
            last_i = max(i for i, _ in watched)
            nxt = min(last_i + 1, len(ep_guids) - 1)
            return ep_guids[nxt], 0

    @staticmethod
    def _finished(r: dict) -> bool:
        ts = int(r.get("ts", 0) or 0)
        dur = int(r.get("duration", 0) or 0)
        return bool(dur) and ts >= dur * 0.95

    def delete(self, item_guids, uid: str | None = None) -> int:
        ids = item_guids if isinstance(item_guids, (list, tuple)) else [item_guids]
        n = 0
        with _LOCK:
            recs = self._recs(uid)
            for g in ids:
                if g in recs:
                    del recs[g]
                    n += 1
            if n:
                self._dirty = True
                self._flush_locked(force=True)
        return n


history = History()
