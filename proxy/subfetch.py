#!/usr/bin/env python3
"""订阅 / API 抓取的共享低层工具。

支持两种「代理」形态（由 config 的 subscription_proxy_mode 决定，auto 自动识别）：

  - http  正向代理：http://user:pass@host:port（Clash 等），只有订阅资源走它；
  - relay URL 前缀中转：如 https://ac9.cc.cd/（CORSAPI / LunaTV 配套），
    请求会拼成 https://ac9.cc.cd/?url=<encode(目标URL)>。配置拉取、源测速、
    搜索与分类等 JSON API 都走它；媒体流（m3u8/mp4）仍直连。

客户端始终 trust_env=False，不读系统 Clash 环境变量；播放不经过本模块。
此模块无任何专有逻辑，可进入公开构建（未配置代理时退化为直连）。
"""
from __future__ import annotations

import asyncio
import time
from urllib.parse import quote, urlencode, urlparse

import httpx

# 抓取订阅资源用的超时（jar 可能数 MB，给宽一些）
SUB_TIMEOUT = httpx.Timeout(25.0, connect=10.0)
_UA = "Mozilla/5.0 (Linux; Android 11) AppleWebKit/537.36"


# ---------------- 浏览器指纹请求引擎（relay 中转必备） ----------------
# 多数公共中转站（如 ac9.cc.cd）架在 Cloudflare 后并开了 Bot 风控：
# Python httpx/urllib 的 OpenSSL TLS 指纹会被直接 RST（curl/浏览器能过）。
# relay 模式下改用 curl_cffi impersonate=chrome 发请求即可通过；
# 未安装 curl_cffi 时优雅降级回 httpx（但对开了风控的中转会失败）。


def _cffi():
    try:
        from curl_cffi import requests as _cr
        return _cr
    except Exception:  # noqa: BLE001
        return None


def _needs_cffi() -> bool:
    return proxy_mode() == "relay" and _cffi() is not None


def _tmo(t, default: float) -> float:
    """把 httpx.Timeout / 数字 / None 归一成秒数。"""
    if isinstance(t, (int, float)) and t > 0:
        return float(t)
    for attr in ("total", "read", "connect"):
        try:
            v = getattr(t, attr, None)
            if v and v > 0:
                return float(v)
        except Exception:  # noqa: BLE001
            pass
    return default


class _CffiClient:
    """同步客户端：模拟 httpx.Client 用到的子集（get / 上下文管理器）。"""

    def __init__(self, timeout=None):
        self._s = _cffi().Session(impersonate="chrome", verify=False)
        self._timeout = _tmo(timeout, 15.0)

    def get(self, url, headers=None, timeout=None, follow_redirects=True, **kw):
        tmo = _tmo(timeout, self._timeout)
        last = None
        for attempt in range(2):  # 中转站偶发抖动，重试一次
            try:
                return self._s.get(url, headers=headers, timeout=tmo,
                                   allow_redirects=follow_redirects)
            except Exception as exc:  # noqa: BLE001
                last = exc
                if attempt == 0:
                    time.sleep(0.4)
        raise last

    def close(self):
        try:
            self._s.close()
        except Exception:  # noqa: BLE001
            pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


class _CffiAsyncClient:
    """异步客户端：模拟 httpx.AsyncClient 用到的子集。"""

    def __init__(self, timeout=None):
        from curl_cffi.requests import AsyncSession
        self._s = AsyncSession(impersonate="chrome", verify=False)
        self._timeout = _tmo(timeout, 15.0)

    async def get(self, url, headers=None, timeout=None,
                  follow_redirects=True, **kw):
        tmo = _tmo(timeout, self._timeout)
        last = None
        for attempt in range(2):  # 中转站偶发抖动，重试一次
            try:
                return await self._s.get(url, headers=headers, timeout=tmo,
                                         allow_redirects=follow_redirects)
            except Exception as exc:  # noqa: BLE001
                last = exc
                if attempt == 0:
                    await asyncio.sleep(0.4)
        raise last

    async def close(self):
        try:
            await self._s.close()
        except Exception:  # noqa: BLE001
            pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        await self.close()


def async_api_client(timeout=None):
    """异步 API 客户端：走中转（wrap 后 URL）的请求统一用它。

    relay 模式 → curl_cffi 浏览器指纹；否则 httpx 直连（可带正向代理）。
    """
    if _needs_cffi():
        return _CffiAsyncClient(timeout)
    kw = {}
    px = subscription_proxy()
    if px:
        try:
            kw["proxy"] = px
        except TypeError:
            kw["proxies"] = px
    return httpx.AsyncClient(trust_env=False, verify=False, follow_redirects=True,
                             timeout=timeout or SUB_TIMEOUT, **kw)

# GitHub 原始 / 常见加速域名（这些域名在国内 NAS 上常 NXDOMAIN 或被墙）
_GH_HOSTS = ("raw.githubusercontent.com", "raw.kkgithub.com", "raw.bgithub.xyz",
             "raw.fastgit.org", "ghproxy.com")


def _settings() -> tuple[str, str]:
    """(代理/中转地址, 模式)。惰性读取 config，避免循环导入。"""
    try:
        import config
        cfg = config.config.get()
        return (str(cfg.get("subscription_proxy") or "").strip(),
                str(cfg.get("subscription_proxy_mode") or "auto").strip().lower())
    except Exception:  # noqa: BLE001
        return "", "auto"


def proxy_mode() -> str:
    """返回 "http" / "relay" / ""（直连）。"""
    px, mode = _settings()
    if not px:
        return ""
    if mode in ("http", "relay"):
        return mode
    # auto：socks/带端口/常见代理形态 → 正向代理；无端口或无路径的域名 → 中转
    u = urlparse(px)
    if u.scheme.startswith("socks"):
        return "http"
    if "{url}" in px or "url=" in (u.query or ""):
        return "relay"
    if u.port:
        return "http"
    return "relay"


def subscription_proxy() -> str:
    """正向代理 URL（relay 模式返回空串，让 httpx 直连到中转地址）。"""
    px, _ = _settings()
    return px if proxy_mode() == "http" else ""


def proxy_setting() -> str:
    """用户配置的原始地址（无论正向代理还是中转）。"""
    return _settings()[0]


def api_relay() -> str:
    """URL 前缀中转地址（forward 代理模式返回空串）。"""
    px, _ = _settings()
    return px if proxy_mode() == "relay" else ""


def build_url(url: str, params: dict | None = None) -> str:
    """把 query 参数拼到 URL 上（中转必须自己拼，httpx 的 params 无法放进 url=）。"""
    if not params:
        return url
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}{urlencode(params, doseq=True)}"


def wrap(url: str) -> str:
    """按中转模式把目标 URL 包成 <base>?url=<encoded>；非中转模式原样返回。"""
    base = api_relay()
    if not base:
        return url
    try:
        if urlparse(url).netloc == urlparse(base).netloc:
            return url  # 已是本中转的地址（如 /p/xxx?url=...），避免套娃
    except Exception:  # noqa: BLE001
        pass
    if "{url}" in base:
        return base.replace("{url}", quote(url, safe=""))
    if "?" not in base and urlparse(base).path in ("", "/"):
        base = base.rstrip("/") + "/"
    sep = "&" if "?" in base else "?"
    return f"{base}{sep}url={quote(url, safe='')}"


def sub_client() -> httpx.Client:
    """同步客户端：仅用于拉取订阅资源。trust_env=False（不读系统代理），
    但显式应用用户配置的订阅代理；relay 模式用浏览器指纹引擎。"""
    if _needs_cffi():
        return _CffiClient(SUB_TIMEOUT)
    px = subscription_proxy()
    try:
        return httpx.Client(trust_env=False, verify=False, follow_redirects=True,
                            timeout=SUB_TIMEOUT,
                            **({"proxy": px} if px else {}))
    except TypeError:
        # 极旧版 httpx 用 proxies=
        return httpx.Client(trust_env=False, verify=False, follow_redirects=True,
                            timeout=SUB_TIMEOUT,
                            **({"proxies": px} if px else {}))


def async_sub_client() -> httpx.AsyncClient:
    if _needs_cffi():
        return _CffiAsyncClient(SUB_TIMEOUT)
    px = subscription_proxy()
    try:
        return httpx.AsyncClient(trust_env=False, verify=False, follow_redirects=True,
                                 timeout=SUB_TIMEOUT,
                                 **({"proxy": px} if px else {}))
    except TypeError:
        return httpx.AsyncClient(trust_env=False, verify=False, follow_redirects=True,
                                 timeout=SUB_TIMEOUT,
                                 **({"proxies": px} if px else {}))


def connectivity_test() -> tuple[bool, str]:
    """实测「订阅 / API 抓取」链路（generate_204），失败自动重试一次。

    返回 (ok, 展示消息)。"""
    target = wrap("https://www.gstatic.com/generate_204")
    mode = proxy_mode() or "直连"
    errs = []
    for i in range(2):
        try:
            with sub_client() as cli:
                r = cli.get(target, timeout=12, headers={"User-Agent": _UA})
            if r.status_code in (200, 204):
                return True, f"HTTP {r.status_code}（{mode}）"
            errs.append(f"HTTP {r.status_code}")
        except Exception as exc:  # noqa: BLE001
            errs.append(f"{type(exc).__name__}: {str(exc)[:80]}")
        if i == 0:
            time.sleep(0.5)
    hint = ""
    if proxy_mode() == "relay" and _cffi() is None:
        hint = "（中转站有浏览器风控，需在 venv 安装 curl_cffi）"
    return False, f"连接失败（{mode}）：{'；'.join(errs)}{hint}"


def github_mirror_candidates(url: str) -> list[str]:
    """GitHub 原始/加速域名资源 → [原URL, 各国内镜像候选]；非 GitHub 只返回原 URL。"""
    out = [url]
    try:
        p = urlparse(url)
        host = (p.netloc or "").lower()
        parts = [seg for seg in p.path.split("/") if seg]
        if host in _GH_HOSTS and len(parts) >= 4:
            owner, repo, branch = parts[0], parts[1], parts[2]
            rest = "/".join(parts[3:])
            raw = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{rest}"
            for c in (
                f"https://ghproxy.net/{raw}",
                f"https://gh-proxy.com/{raw}",
                f"https://ghfast.top/{raw}",
                f"https://raw.gitmirror.com/{owner}/{repo}/{branch}/{rest}",
                f"https://cdn.jsdelivr.net/gh/{owner}/{repo}@{branch}/{rest}",
            ):
                if c not in out:
                    out.append(c)
    except Exception:  # noqa: BLE001
        pass
    return out


def fetch_first(urls, *, want_zip: bool = False, timeout: float | None = None):
    """用订阅代理按顺序尝试一组 URL。返回 (bytes, 命中URL)；全失败返回 (None, 错误)。

    want_zip=True 时额外校验 zip(jar/apk) 魔数 PK。
    """
    last = ""
    for u in urls:
        try:
            kw = {} if timeout is None else {"timeout": httpx.Timeout(timeout, connect=10.0)}
            target = wrap(u)
            with sub_client() as cli:
                r = cli.get(target, headers={"User-Agent": _UA}, **kw)
                if r.status_code >= 400:
                    last = f"HTTP {r.status_code} @ {u}"
                    continue
                blob = r.content
            if not blob:
                last = f"空响应 @ {u}"
                continue
            if want_zip and blob[:2] != b"PK":
                last = f"非有效 jar(zip) @ {u}"
                continue
            return blob, u
        except Exception as exc:  # noqa: BLE001
            last = f"{type(exc).__name__} @ {u}"
            continue
    return None, last
