#!/usr/bin/env python3
"""trim-media-online 运行配置（可热加载）。state/config.json。"""
from __future__ import annotations

import hashlib
import json
import re
import threading
from pathlib import Path

import features
from providers import DEFAULT_SOURCES

_STATE = Path(__file__).resolve().parent.parent / "state" / "config.json"
_LOCK = threading.RLock()

# 噪音关键词：标题或备注命中则不注入（电影解说、预告、花絮、AI 漫剧等）
JUNK_KEYWORDS = [
    "电影解说", "影视解说", "解说", "预告片", "预告", "花絮", "抢先", "枪版",
    "AI漫剧", "漫剧", "动态漫画", "彩蛋", "删减", "片场", "开机", "特辑",
]

DEFAULTS = {
    "sources": [dict(s) for s in DEFAULT_SOURCES],
    # 被删除的内置源 id（自定义源删除时直接从 sources 移除）
    "removed_ids": [],
    "max_per_keyword": 12,
    "filter_junk": True,
    "junk_keywords": JUNK_KEYWORDS,
    # 在线资源前排展示（在线片库更齐全，默认前排）
    "online_first": True,
    # 播放线路健康探测与自动换线：当前线路解析失败/文件不存在时，自动探测同集其他
    # 线路并切到首个可用线路；坏线短时记忆，起播自动跳过（关闭则保持纯手动选线）
    "line_autofail": True,
    # 完全自动选最快线：起播时并行竞速探测前若干条候选线路，选首字节延迟最低的线；
    # 最快线短时记忆，同一集后续/重放稳定用它（手动在播放器切线仍被尊重）
    "line_fastest": True,
    # 自动选最快线时最多参与竞速的候选线路数（控制起播开销）
    "line_fastest_max": 6,
    # 竞速超时预算（秒）：超时未响应的线路本轮判慢，不阻塞起播
    "line_fastest_timeout": 4.0,
    # 默认线（高质量源）领先优势（秒）：它在该优势内返回就算赢，避免无谓抖动
    "line_fastest_prefer": 0.25,
    # 虚拟“热门榜单”四库媒体库（豆瓣真实周榜/标签榜）
    "hot_library_enabled": True,
    # 置顶的虚拟媒体库 guid 集合（打开=在飞牛影视媒体库列表置顶，关闭=普通顺序）。
    "pinned_libs": [],
    "hot_library_title": "🌐在线热门",
    "hot_limit": 300,          # 四库合计保留条数上限
    "hot_per_source": 120,    # 每个资源站最多抓取的可播条目
    "hot_pages_per_source": 6,  # 每个资源站翻“最近更新”的页数（每页约20条）
    "hot_refresh_interval": 6 * 3600,
    # 源质量优先级：source_id -> 权重（越高越优先）。未列出的源取内省默认（见
    # providers.source_priority）。热门榜单点击搜源时按 (优先级, 直链数) 排序。
    "source_priority": {},
    # 热门资源解析是否优先高质量源（关闭则只按可播直链数）
    "prefer_quality_source": True,
    "admin_token": "",
    # 订阅 / API 抓取代理。两种形态（mode 决定，auto 自动识别）：
    #   http  = 正向代理 http://user:pass@host:port（Clash 等）
    #   relay = URL 前缀中转 https://ac9.cc.cd/（CORSAPI/LunaTV 配套，拼 ?url=）
    # 作用范围：拉取订阅配置 + 源测速/搜索/分类等 JSON API；媒体流仍直连。
    "subscription_proxy": "",
    "subscription_proxy_mode": "auto",
    # 最近一次 LunaTV 源订阅导入的报告（仅展示用，不参与运行逻辑）。
    "lunatv_last_sync": {},
    # LunaTV 定时抓源：开启后按间隔从 LunaTV-config 拉取源清单并测速。
    "lunatv_sync_enabled": False,
    "lunatv_sync_preset": "jin18",
    "lunatv_sync_url": "",
    "lunatv_sync_interval": 12,      # 小时
    "lunatv_auto_disable": True,     # 连续两轮测速失败自动禁用
    # 每源最近测速结果：id -> {ok, ms, fails, at}（供管理台展示与连续失败计数）
    "lunatv_sync_stats": {},
    # 弹幕：对接自建 danmu_api（弹弹play 兼容）。弹幕转 ASS 字幕轨，由播放器
    # 自带的外挂字幕渲染；不内置任何弹幕服务。
    "danmu_enabled": False,
    "danmu_api": "",
    "danmu_token": "",
    "danmu_auto": True,        # 打开播放页自动选中「弹幕」字幕
    "danmu_offset": 0.0,       # 时间偏移（秒），正值让弹幕更晚出现
    "danmu_limit": 800,        # 单集最多渲染条数（按时间均匀抽样）
    # 播放去广告：实时分析当前线路的 m3u8，剥除片头/片中广告分片。
    # 只用同步规则（URI 特征 / 时长离群成群 / CDN 短段切换），
    # 不在起播路径新增任何网络请求；判断不确定就保留原片，不影响播放。
    # 默认关闭：需要用户手动开启（先保证默认行为不变）。
    "ad_filter_enabled": False,
    # 线路菜单压缩：TV / 手机原生播放器拿到多线路清单后会【串行】预取每一条，
    # 慢线逐条累加等待，起播被拖慢（上游 fnmedia-ext v0.2.68 同款修复）。
    # 开启后：对这些端只下发当前线路一个变体，其余线路由服务端并发预热
    # （有界并发、单飞、复用播放列表缓存），切菜单时即时命中。
    # Web 端始终返回完整菜单，用户手动切线的行为不变。
    "line_menu_compact": True,
}

# 已废弃、需从旧配置里清除的键
_DEPRECATED = {"public_base", "strm_root"}
_BUILTIN_IDS = {s["id"] for s in DEFAULT_SOURCES}


class Config:
    def __init__(self):
        self._cfg: dict = {}
        self._mtime = 0
        self.load()


    def load(self):
        with _LOCK:
            try:
                j = json.loads(_STATE.read_text())
            except Exception:
                j = {}
            cfg = json.loads(json.dumps(DEFAULTS))  # deep copy
            cfg.update(j)
            for k in list(cfg.keys()):
                if k in _DEPRECATED:
                    cfg.pop(k, None)
            removed = set(cfg.get("removed_ids", []))

            # 源列表：以内置为底（跳过被删除的），保留用户的启用/改名/改地址，
            # 再追加用户自定义源。
            saved = j.get("sources") if isinstance(j.get("sources"), list) else []
            saved_by_id = {s.get("id"): s for s in saved if isinstance(s, dict)}
            merged = []
            for s in DEFAULT_SOURCES:
                if s["id"] in removed:
                    continue
                cur = saved_by_id.get(s["id"], {})
                m = dict(s)
                m.update({k: cur[k] for k in ("enabled", "name", "api") if k in cur})
                m["builtin"] = True
                m["standalone"] = bool(cur.get("standalone", False))
                m["loose_filter"] = bool(cur.get("loose_filter", False))
                m["origin"] = str(cur.get("origin") or "manual")
                m["auto_disabled"] = bool(cur.get("auto_disabled", False))
                merged.append(m)
            for sid, s in saved_by_id.items():
                if sid in _BUILTIN_IDS or sid in removed:
                    continue
                m = {k: s.get(k) for k in ("id", "name", "api", "enabled")}
                m["enabled"] = bool(s.get("enabled", True))
                m["standalone"] = bool(s.get("standalone", False))
                m["loose_filter"] = bool(s.get("loose_filter", False))
                m["builtin"] = bool(s.get("builtin", False))
                m["origin"] = str(s.get("origin") or "manual")
                m["auto_disabled"] = bool(s.get("auto_disabled", False))
                merged.append(m)
            cfg["sources"] = merged
            cfg["removed_ids"] = sorted(removed)
            # 旧版本（单库/小数量）保存过的热门参数自动升级到深度爬取规模；
            # 仅在检测到旧小值时迁移一次，用户之后自定义的大值不会被覆盖。
            migrated = False
            try:
                if int(cfg.get("hot_limit", 0)) <= 120 and int(DEFAULTS["hot_limit"]) > 120:
                    cfg["hot_limit"] = DEFAULTS["hot_limit"]; migrated = True
                if int(cfg.get("hot_per_source", 0)) <= 40:
                    cfg["hot_per_source"] = DEFAULTS["hot_per_source"]; migrated = True
                if not cfg.get("hot_pages_per_source"):
                    cfg["hot_pages_per_source"] = DEFAULTS["hot_pages_per_source"]; migrated = True
            except (TypeError, ValueError):
                pass
            if migrated:
                j.update({k: cfg[k] for k in
                          ("hot_limit", "hot_per_source", "hot_pages_per_source")})
                try:
                    _STATE.write_text(json.dumps(j, ensure_ascii=False, indent=2))
                except Exception:
                    pass
            if not cfg.get("admin_token"):
                import secrets
                cfg["admin_token"] = secrets.token_hex(8)
            self._cfg = cfg
            try:
                self._mtime = _STATE.stat().st_mtime
            except FileNotFoundError:
                self._mtime = 0

    def maybe_reload(self):
        try:
            mt = _STATE.stat().st_mtime
        except FileNotFoundError:
            return
        if mt != self._mtime:
            self.load()

    def get(self):
        with _LOCK:
            return json.loads(json.dumps(self._cfg))

    def enabled_sources(self):
        self.maybe_reload()
        with _LOCK:
            return [dict(s) for s in self._cfg["sources"] if s.get("enabled")]

    def all_sources(self):
        self.maybe_reload()
        with _LOCK:
            return [dict(s) for s in self._cfg["sources"]]

    def save(self, patch: dict):
        with _LOCK:
            cfg = self.get()
            for k, v in patch.items():
                if k in cfg:
                    cfg[k] = v
            self._persist(cfg)

    def _persist(self, cfg: dict):
        _STATE.parent.mkdir(parents=True, exist_ok=True)
        tmp = _STATE.with_suffix(".tmp")
        tmp.write_text(json.dumps(cfg, ensure_ascii=False, indent=2))
        tmp.replace(_STATE)
        self._cfg = cfg
        self._mtime = _STATE.stat().st_mtime

    @staticmethod
    def make_custom_id(api: str) -> str:
        return "custom_" + hashlib.md5(api.strip().encode()).hexdigest()[:10]

    def add_source(self, name: str, api: str, enabled: bool = True,
                   standalone: bool = False) -> tuple[bool, str]:
        with _LOCK:
            cfg = self.get()
            api = (api or "").strip()
            name = (name or "").strip()
            if not api.startswith(("http://", "https://")):
                return False, "API 地址需以 http(s):// 开头"
            if not name:
                name = api.split("/")[2]
            sid = self.make_custom_id(api)
            norm = api.rstrip("/").lower()
            if any(s["id"] == sid or s.get("api", "").rstrip("/").lower() == norm
                   for s in cfg["sources"]):
                return False, "该资源站地址已存在"
            cfg["sources"].append(
                {"id": sid, "name": name, "api": api,
                 "enabled": bool(enabled), "standalone": bool(standalone),
                 "builtin": False})
            self._persist(cfg)
            return True, sid

    def add_sources(self, items: list[dict], enabled: bool = True,
                    standalone: bool = False, origin: str = "manual") -> dict:
        """批量添加自定义源（单次落盘）；按 API 地址去重。

        items: [{"name": ..., "api": ...}]。origin 标记来源（manual/lunatv）。
        返回 {"added": [name...], "duplicate": n, "invalid": n}。
        """
        added: list[str] = []
        duplicate = invalid = 0
        with _LOCK:
            cfg = self.get()
            seen = {s.get("api", "").rstrip("/").lower()
                    for s in cfg["sources"]}
            ids = {s["id"] for s in cfg["sources"]}
            for it in items or []:
                api = str((it or {}).get("api") or "").strip()
                name = str((it or {}).get("name") or "").strip()
                if not api.startswith(("http://", "https://")):
                    invalid += 1
                    continue
                norm = api.rstrip("/").lower()
                sid = self.make_custom_id(api)
                if norm in seen or sid in ids:
                    duplicate += 1
                    continue
                if not name:
                    name = api.split("/")[2]
                cfg["sources"].append(
                    {"id": sid, "name": name[:40], "api": api,
                     "enabled": bool(enabled), "standalone": bool(standalone),
                     "builtin": False, "origin": str(origin or "manual"),
                     "auto_disabled": False})
                seen.add(norm)
                ids.add(sid)
                added.append(name[:40])
            if added:
                self._persist(cfg)
        return {"added": added, "duplicate": duplicate, "invalid": invalid}

    def source_priorities(self) -> dict:
        with _LOCK:
            return dict(self.get().get("source_priority") or {})


    def set_source_priority(self, mapping: dict) -> tuple[bool, str]:
        """整体保存源优先级（id -> 整数权重），忽略未知源与非法值。"""
        with _LOCK:
            cfg = self.get()
            valid = {s["id"] for s in cfg["sources"]}
            out = {}
            for k, v in (mapping or {}).items():
                if k in valid:
                    try:
                        out[k] = max(-100, min(100, int(v)))
                    except (TypeError, ValueError):
                        continue
            cfg["source_priority"] = out
            self._persist(cfg)
            return True, "ok"

    def set_subscription_proxy(self, proxy_url: str,
                               mode: str = "auto") -> tuple[bool, str]:
        """保存「订阅 / API 抓取」代理（空串=直连）。

        mode: auto 自动识别 / http 正向代理 / relay URL 前缀中转。
        正向代理接受 http(s)/socks5；中转接受 http(s) 基础地址或含 {url} 模板。
        """
        from urllib.parse import urlparse
        p = (proxy_url or "").strip()
        m = (mode or "auto").strip().lower()
        if m not in ("auto", "http", "relay"):
            return False, "代理方式应为 auto / http / relay"
        if p:
            u = urlparse(p)
            if u.scheme not in ("http", "https", "socks5", "socks5h") or not u.hostname:
                return False, "代理地址格式应为 http://user:pass@host:port 或 https://中转域名/"
            if m == "relay" and u.scheme not in ("http", "https"):
                return False, "URL 前缀中转仅支持 http(s) 地址"
        with _LOCK:
            cfg = self.get()
            cfg["subscription_proxy"] = p
            cfg["subscription_proxy_mode"] = m
            self._persist(cfg)
            return True, "ok"

    def set_standalone(self, sid: str, on: bool) -> tuple[bool, str]:
        with _LOCK:
            cfg = self.get()
            target = next((s for s in cfg["sources"] if s["id"] == sid), None)
            if not target:
                return False, "源不存在"
            target["standalone"] = bool(on)
            self._persist(cfg)
            return True, "ok"

    def pinned_lib_guids(self) -> set:
        with _LOCK:
            try:
                return set(self.get().get("pinned_libs") or [])
            except TypeError:
                return set()

    def set_lib_pinned(self, guid: str, on: bool) -> tuple[bool, str]:
        """置顶/取消置顶某个虚拟媒体库（guid）。"""
        if not isinstance(guid, str) or not guid:
            return False, "guid 非法"
        with _LOCK:
            cfg = self.get()
            cur = [g for g in (cfg.get("pinned_libs") or []) if isinstance(g, str)]
            if on:
                if guid not in cur:
                    cur.append(guid)
            else:
                cur = [g for g in cur if g != guid]
            cfg["pinned_libs"] = cur
            self._persist(cfg)
            return True, "ok"

    def set_loose_filter(self, sid: str, on: bool) -> tuple[bool, str]:
        """放宽正片（标题/备注噪音）过滤；分类层面的红线不受影响。"""
        with _LOCK:
            cfg = self.get()
            target = next((s for s in cfg["sources"] if s["id"] == sid), None)
            if not target:
                return False, "源不存在"
            target["loose_filter"] = bool(on)
            self._persist(cfg)
            return True, "ok"

    def set_source_enabled(self, sid: str, on: bool,
                           auto: bool = False) -> tuple[bool, str]:
        """启用/禁用源；auto=True 表示由测速自动禁用，可被后续测速恢复。"""
        with _LOCK:
            cfg = self.get()
            target = next((s for s in cfg["sources"] if s["id"] == sid), None)
            if not target:
                return False, "源不存在"
            target["enabled"] = bool(on)
            if on:
                target["auto_disabled"] = False
            elif auto:
                target["auto_disabled"] = True
            self._persist(cfg)
            return True, "ok"

    def apply_sync_result(self, stats: dict, report: dict,
                          disable_ids: list[str],
                          enable_ids: list[str]) -> None:
        """一次性落盘 LunaTV 同步结果（测速统计 + 报告 + 自动禁用/恢复）。"""
        with _LOCK:
            cfg = self.get()
            sid_map = {s["id"]: s for s in cfg["sources"]}
            for sid in disable_ids:
                s = sid_map.get(sid)
                if s is not None:
                    s["enabled"] = False
                    s["auto_disabled"] = True
            for sid in enable_ids:
                s = sid_map.get(sid)
                if s is not None:
                    s["enabled"] = True
                    s["auto_disabled"] = False
            cfg["lunatv_sync_stats"] = dict(stats or {})
            cfg["lunatv_last_sync"] = dict(report or {})
            self._persist(cfg)


    def remove_source(self, sid: str) -> tuple[bool, str]:
        with _LOCK:
            cfg = self.get()
            target = next((s for s in cfg["sources"] if s["id"] == sid), None)
            if not target:
                return False, "源不存在"
            if target.get("builtin"):
                # 内置源不物理删除，标记移除（可在重置时恢复）
                if sid not in cfg["removed_ids"]:
                    cfg["removed_ids"].append(sid)
            cfg["sources"] = [s for s in cfg["sources"] if s["id"] != sid]
            self._persist(cfg)
            return True, "ok"

    def restore_builtin(self) -> tuple[bool, str]:
        """本项目不内置任何源：此操作语义为「清空全部源」，回到初始状态。"""
        with _LOCK:
            cfg = self.get()
            cfg["removed_ids"] = []
            cfg["sources"] = []
            self._persist(cfg)
            self.load()
            return True, "ok"

    @staticmethod
    def normalize_keywords(raw) -> list[str]:
        """把逗号/换行/空白分隔的输入清洗成去重关键词列表。"""
        if isinstance(raw, str):
            parts = re.split(r"[,，、\n\r;；\s]+", raw)
        elif isinstance(raw, (list, tuple)):
            parts = []
            for item in raw:
                parts.extend(re.split(r"[,，、\n\r;；\s]+", str(item)))
        else:
            return []
        out, seen = [], set()
        for p in parts:
            k = p.strip()
            if k and k not in seen and len(k) <= 30:
                seen.add(k)
                out.append(k)
        return out

    def set_junk_keywords(self, raw) -> list[str]:
        kws = self.normalize_keywords(raw)
        self.save({"junk_keywords": kws})
        return kws

    def reset_junk_keywords(self) -> list[str]:
        self.save({"junk_keywords": list(JUNK_KEYWORDS)})
        return list(JUNK_KEYWORDS)

    def is_junk(self, title: str, remarks: str = "") -> bool:
        if not self._cfg.get("filter_junk", True):
            return False
        kws = self._cfg.get("junk_keywords", JUNK_KEYWORDS)
        hay = f"{title} {remarks}"
        return any(k and k in hay for k in kws)

    def validate(self) -> tuple[bool, list[str]]:
        """诊断性配置检查：自动纠正越界数值，仅报告无法自动修复的结构问题。

        返回 (是否有严重问题, 提示列表)。不用于阻塞服务启动——
        配置异常时纠正比拒绝启动更安全（服务起不来意味着飞牛影视回落官方）。"""
        warnings: list[str] = []
        try:
            sources = self._cfg.get("sources", [])
            if not isinstance(sources, list):
                return False, ["sources 不是列表（load 已兜底为默认值）"]

            for i, source in enumerate(sources):
                if not isinstance(source, dict) or not source.get("id"):
                    warnings.append(f"源 {i} 结构异常，已忽略")
                    continue

            # 越界数值直接夹取纠正
            for key, lo, hi in (("max_per_keyword", 1, 50),
                                ("line_fastest_max", 2, 12),
                                ("hot_limit", 60, 800)):
                if key in self._cfg:
                    try:
                        v = int(self._cfg[key])
                    except (TypeError, ValueError):
                        self._cfg[key] = DEFAULTS[key]
                        warnings.append(f"{key} 非法，已重置为默认 {DEFAULTS[key]}")
                        continue
                    if v < lo or v > hi:
                        self._cfg[key] = max(lo, min(hi, v))
                        warnings.append(f"{key}={v} 越界，已夹取为 {self._cfg[key]}")

            return True, warnings
        except Exception as e:  # noqa: BLE001
            return False, [f"配置检查异常: {type(e).__name__}: {e}"]


config = Config()
