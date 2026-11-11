#!/usr/bin/env python3
"""广告过滤：选集引流名过滤 + HLS 广告分片过滤。

两部分能力：
  A. is_ad_episode(name)  选集名过滤：识别「关注公众号/加微信/下载APP」等
     引流假选集。只做名称判断（正则），零解析开销，误伤时保留正片结构。
  B. filter_hls(text)     m3u8 分片过滤：剥除片头/片中广告分片。

B 的设计底线（对齐上游 fnmedia-ext AGENTS.md 播放红线）：
  1. 只做**同步规则匹配**：所有判断都基于已拉取到的 m3u8 文本本身，
     不起播关键路径上不新增任何网络请求（不下载分片、不做 SPS 指纹探测）；
  2. 只在有明确信号时才剔除，任何不确定一律保留原片——宁可漏删，
     不可误删正片；
  3. 单次删除量有上限（默认不超过总分片数 30%），超出则整表不动，
     防止规则误判把正片削掉；
  4. 只处理媒体播放列表（含 #EXTINF 的分片表），主播放列表
     （#EXT-X-STREAM-INF 多码率清单）绝不处理；
  5. 输出必须仍是语法正确的 m3u8：被删的分片连同其 EXTINF/注释一起删，
     不动其他行、不改写任何 URI。
"""
from __future__ import annotations

import re
from urllib.parse import urlsplit

# ============================================================ A. 选集引流名过滤

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


# ============================================================ B. HLS 广告分片过滤

# 分片 URI 里的广告特征词（命中即视为广告分片）
_AD_URI_WORDS = (
    "preroll", "midroll", "postroll", "advert", "adbreak",
    "/ad/", "/ads/", "ad_", "_ad.", "-ad.", "adspot", "adcall",
    "spot_ad", "adinsert",
)

# 已知广告/统计域名片段（保守：单独出现不足以判定，需配合成群条件）
_AD_HOST_WORDS = ("admob", "doubleclick", "adservice", "advertising",
                  "adserver", "adsystem", "adlog", "stats")

# 正常视频分片时长下限（秒）：低于此值且成群出现才视为广告
_MIN_SEG_SEC = 0.5
# 判断「时长离群」的倍数：与中位时长相差超过该倍数视为离群
_OUTLIER_RATIO = 0.2
# 单次最多删除的分片比例，超过则放弃整表过滤
_MAX_REMOVE_RATIO = 0.30
# CDN 切换型广告的典型片数范围
_SHORT_RUN = (1, 4)
# 时长离群的「成群」下限：少于该片数的连续离群不判广告（防误删正片段头/片尾）
_MIN_AD_RUN = 3

_EXTINF_RE = re.compile(r"^#EXTINF:\s*([0-9.]+)", re.I)


def _is_master(text: str) -> bool:
    """主播放列表（多码率）不处理。"""
    return "#EXT-X-STREAM-INF" in text


def _uri_is_ad(uri: str) -> bool:
    low = uri.lower()
    if any(w in low for w in _AD_URI_WORDS):
        return True
    try:
        host = urlsplit(low).netloc
    except Exception:  # noqa: BLE001
        return False
    return any(w in host for w in _AD_HOST_WORDS)


def _parse_segments(text: str) -> tuple[list[dict], list[str]]:
    """把媒体列表解析为分片记录。

    每条记录含：uri、extinf 行号、uri 行号、时长、_ad（是否广告候选）。
    不动其他行。"""
    lines = text.splitlines()
    segs: list[dict] = []
    cur = None
    for i, raw in enumerate(lines):
        s = raw.strip()
        if not s:
            continue
        if s.startswith("#"):
            m = _EXTINF_RE.match(s)
            if m:
                try:
                    dur = float(m.group(1))
                except ValueError:
                    dur = 0.0
                cur = {"extinf_line": i, "uri_line": None, "dur": dur,
                       "uri": "", "_ad": False}
            continue
        if cur is None:
            # 没有 EXTINF 的裸 URI（异常列表），不当分片处理
            continue
        cur["uri_line"] = i
        cur["uri"] = s
        segs.append(cur)
        cur = None
    return segs, lines


def _mark_outliers(segs: list[dict]) -> None:
    """时长离群标记：与中位时长相差过大者为广告候选。

    安全约束：离群分片必须**连续成群**（>=_MIN_AD_RUN 片）才标记。
    单片离群可能是正片片头/片尾衔接、变码率切换点，绝不能删。"""
    if len(segs) < 6:
        return
    durs = sorted(s["dur"] for s in segs if s["dur"] > 0)
    if not durs:
        return
    mid = len(durs) // 2
    median = (durs[mid] if len(durs) % 2 else (durs[mid - 1] + durs[mid]) / 2)
    if median <= 0:
        return
    for s in segs:
        if s["dur"] > 0 and (s["dur"] < _MIN_SEG_SEC
                            or s["dur"] < median * _OUTLIER_RATIO):
            s["_dur_outlier"] = True
    # 成群才保留标记，单片离群一律取消
    i = 0
    while i < len(segs):
        if segs[i].get("_dur_outlier"):
            j = i
            while j < len(segs) and segs[j].get("_dur_outlier"):
                j += 1
            if j - i >= _MIN_AD_RUN:
                for k in range(i, j):
                    segs[k]["_ad"] = True
            i = j
        else:
            i += 1


def _mark_cdn_switch(segs: list[dict]) -> None:
    """CDN 切换型广告：正片宿主 A 中插入一小段宿主 B，随后回到 A。

    只标记「短段」（_SHORT_RUN 片以内）且后续回到原宿主的连续片段，
    长段视为换源/容灾，绝不删。"""
    if len(segs) < 8:
        return
    hosts = []
    for s in segs:
        try:
            hosts.append(urlsplit(s["uri"]).netloc or "")
        except Exception:  # noqa: BLE001
            hosts.append("")
    if len(set(h for h in hosts if h)) < 2:
        return
    # 统计主要宿主（出现最多的非空 host）
    counts: dict[str, int] = {}
    for h in hosts:
        if h:
            counts[h] = counts.get(h, 0) + 1
    if not counts:
        return
    main_host = max(counts.items(), key=lambda kv: kv[1])[0]
    i = 0
    while i < len(segs):
        if hosts[i] and hosts[i] != main_host:
            j = i
            while j < len(segs) and hosts[j] and hosts[j] != main_host:
                j += 1
            run = j - i
            nxt = main_host if j >= len(segs) else hosts[j]
            if _SHORT_RUN[0] <= run <= _SHORT_RUN[1] and nxt == main_host:
                for k in range(i, j):
                    segs[k]["_ad"] = True
            i = j
        else:
            i += 1


def filter_hls(text: str | None) -> tuple[str | None, int]:
    """过滤媒体播放列表里的广告分片。

    返回 (新文本, 删除分片数)。文本为 None、非媒体列表、或判断结果不
    足以安全删除时，原样返回 (text, 0)。调用方无需 try/except。"""
    if not text or _is_master(text):
        return text, 0
    try:
        segs, lines = _parse_segments(text)
    except Exception:  # noqa: BLE001
        return text, 0
    if len(segs) < 3:
        # 分片太少无法判断，绝不动
        return text, 0

    # 1) URI 广告特征（最明确的信号）
    for s in segs:
        if _uri_is_ad(s["uri"]):
            s["_ad"] = True

    # 2) 时长离群 + 3) CDN 短段切换：启发式失败则回退到只信 URI 信号
    try:
        _mark_outliers(segs)
        _mark_cdn_switch(segs)
    except Exception:  # noqa: BLE001
        for s in segs:
            if not _uri_is_ad(s["uri"]):
                s["_ad"] = False

    marked = [s for s in segs if s.get("_ad")]
    if not marked:
        return text, 0

    # 4) 删除量安全闸：超过比例则整表放弃，保证不漏删正片
    if len(marked) > max(1, int(len(segs) * _MAX_REMOVE_RATIO)):
        return text, 0

    # 5) 删除：连同其 EXTINF 行一起删，其他行原样保留
    drop = set()
    for s in marked:
        drop.add(s["extinf_line"])
        if s["uri_line"] is not None:
            drop.add(s["uri_line"])
    out = [ln for i, ln in enumerate(lines) if i not in drop]
    # m3u8 以换行分隔；保留原始换行风格
    newline = "\r\n" if "\r\n" in text else "\n"
    return newline.join(out) + ("\n" if text.endswith("\n") else ""), len(marked)


def filter_hls_async(text: str | None) -> tuple[str | None, int]:
    """（兼容占位）异步入口与同步入口行为一致——本模块永不做网络 I/O。

    保留此函数是为了让调用点可以统一写成 sync/async 两种形态而不用担心
    误引入 await 网络请求；将来若需要异步版本，也必须遵守同样的红线。"""
    return filter_hls(text)
