#!/usr/bin/env python3
"""LunaTV / MoonTV 配置订阅：拉取与解析。

LunaTV-config（hafrey1/LunaTV-config）提供三种现成配置：

  jin18.json          精简版（仅普通内容）
  jingjian.json       精简+（含成人源）
  LunaTV-config.json  完整版

结构为 MoonTV 的 ``{"cache_time": ..., "api_site": {...}}``；每个站点形如
``{"name": "...", "api": "https://.../api.php/provide/vod", "detail": "..."}``。
仓库另提供 Base58 编码的同内容 ``.txt`` 订阅，这里一并兼容（也兼容 Base64）。

本模块只负责「取回 + 解析成 [{name, api}]」，不直接改配置；导入策略
（去重、测活、落盘）由调用方决定。抓取走 subfetch 的「订阅代理」，
与播放/搜索流量隔离。
"""
from __future__ import annotations

import json
import re
from urllib.parse import urlparse

import subfetch

RAW_BASE = "https://raw.githubusercontent.com/hafrey1/LunaTV-config/main"

# key -> (文件名, 展示名, 说明)
PRESETS: dict[str, tuple[str, str, str]] = {
    "jin18": ("jin18.json", "精简版", "仅普通内容，源少而精"),
    "jingjian": ("jingjian.json", "精简+", "在精简版基础上补充更多可用源"),
    "full": ("LunaTV-config.json", "完整版", "仓库当前全部源（含部分小众/成人源）"),
}

_B58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_B58_INDEX = {c: i for i, c in enumerate(_B58_ALPHABET)}
_API_RE = re.compile(r"^https?://", re.I)


class LunaError(Exception):
    """拉取或解析失败（消息可直接展示给用户）。"""


def b58decode(s: str) -> bytes:
    """Bitcoin Base58 解码（无校验位）。"""
    s = "".join(s.split())
    n = 0
    for ch in s:
        try:
            n = n * 58 + _B58_INDEX[ch]
        except KeyError as exc:
            raise LunaError("Base58 内容包含非法字符") from exc
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big") if n else b""
    pad = len(s) - len(s.lstrip("1"))
    return b"\x00" * pad + raw


def decode_config(blob: bytes | str) -> dict:
    """把 JSON / Base58 / Base64 文本解成配置 dict。"""
    if isinstance(blob, bytes):
        try:
            text = blob.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise LunaError("配置不是 UTF-8 文本") from exc
    else:
        text = blob.lstrip("\ufeff")
    text = text.strip()
    if not text:
        raise LunaError("配置内容为空")
    if text[0] in "{[":
        candidates = [text]
    else:
        candidates = []
        try:
            candidates.append(b58decode(text).decode("utf-8-sig"))
        except Exception:
            pass
        try:
            import base64
            candidates.append(base64.b64decode(text, validate=False)
                              .decode("utf-8-sig"))
        except Exception:
            pass
        if not candidates:
            raise LunaError("无法识别配置编码（需为 JSON、Base58 或 Base64）")
    for raw in candidates:
        raw = raw.strip()
        if not raw.startswith(("{", "[")):
            continue
        try:
            cfg = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(cfg, dict):
            return cfg
    raise LunaError("配置不是有效的 JSON 对象")


def _clean_name(name: str, api: str) -> str:
    name = re.sub(r"[\x00-\x1f\x7f]", "", str(name or "")).strip()
    if not name:
        try:
            name = urlparse(api).netloc or api
        except Exception:
            name = api
    return name[:40]


def parse_sites(cfg: dict) -> list[dict]:
    """从 MoonTV/LunaTV 配置中提取 [{name, api, detail}]，按 api 去重。"""
    api_site = cfg.get("api_site")
    if not isinstance(api_site, dict):
        raise LunaError("配置缺少 api_site 字段（不是 LunaTV/MoonTV 配置）")
    out: list[dict] = []
    seen: set[str] = set()
    for key, site in api_site.items():
        if not isinstance(site, dict):
            continue
        api = str(site.get("api") or "").strip()
        if not _API_RE.match(api):
            continue
        norm = api.rstrip("/").lower()
        if norm in seen:
            continue
        seen.add(norm)
        out.append({
            "name": _clean_name(site.get("name") or key, api),
            "api": api,
            "detail": str(site.get("detail") or "").strip(),
        })
    return out


def preset_url(name: str) -> str:
    if name not in PRESETS:
        raise LunaError(f"未知预设：{name}")
    return f"{RAW_BASE}/{PRESETS[name][0]}"


def _url_candidates(url: str) -> list[str]:
    """优先原地址，GitHub raw 再尝试国内镜像。"""
    return subfetch.github_mirror_candidates(url)


async def fetch_config(*, preset: str = "", url: str = "") -> tuple[dict, str]:
    """按预设或自定义地址拉取配置。返回 (cfg, 实际命中地址)。"""
    target = (url or "").strip() or preset_url(preset or "jin18")
    if not _API_RE.match(target):
        raise LunaError("地址需以 http(s):// 开头")
    last = ""
    async with subfetch.async_sub_client() as client:
        for candidate in _url_candidates(target):
            try:
                r = await client.get(candidate, timeout=12,
                                     headers={"User-Agent": "Mozilla/5.0"})
                if r.status_code != 200:
                    last = f"HTTP {r.status_code} @ {candidate}"
                    continue
                cfg = decode_config(r.content)
                sites = parse_sites(cfg)
                if not sites:
                    last = f"配置中没有可用源 @ {candidate}"
                    continue
                return cfg, candidate
            except Exception as exc:  # noqa: BLE001
                last = f"{type(exc).__name__}: {str(exc)[:80]} @ {candidate}"
                continue
    raise LunaError(f"拉取失败：{last or '无可用地址'}")
