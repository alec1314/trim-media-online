"""trim-media-online 冒烟测试：改完代码后跑一遍，拦住低级故障。

历史教训（本测试每条都对应一次真实故障）：
  1. import app 失败            → v1.5.0 语法错误，接管服务启动失败
  2. 管理 API 返回 HTML         → v1.6.0 应用中心入口前缀未剥，Unexpected token '<'
  3. JS 双重 apiUrl 包裹         → v1.6.0 之前，管理台全 API 404
  4. 起播链路被改动             → 每次改 app.py 都要回归

运行：.venv/bin/python -m unittest tests.test_smoke -v
不依赖外网、不依赖官方 upstream（透传类接口单独标注）。
"""
from __future__ import annotations

import inspect
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "proxy"))


class ImportSmokeTests(unittest.TestCase):
    """故障 1：模块导入 + 语法。v1.5.0 app.py 语法错误让接管服务起不来。"""

    def test_core_modules_import(self):
        import app as appmod  # noqa: F401
        import adfilter  # noqa: F401
        import config as cfgmod  # noqa: F401
        import webui_gateway  # noqa: F401
        self.assertTrue(len(appmod.app.routes) > 50)

    def test_admin_ui_html_is_valid_python_string(self):
        from admin_ui import ADMIN_HTML
        self.assertIn("</html>", ADMIN_HTML)
        # 占位符必须存在（运行时由 app.py 注入版本号）
        self.assertIn("__TMO_VERSION__", ADMIN_HTML)


class AdminApiSmokeTests(unittest.TestCase):
    """故障 2/3：管理 API 必须返回 JSON，且带应用中心前缀时也要返回 JSON。"""

    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        import app as appmod
        cls.client = TestClient(appmod.app)

    def test_management_apis_return_json(self):
        from app import app  # noqa: F401
        paths = [
            "/_ext/healthz",
            "/v/api/ext/status",
            "/v/api/ext/whoami",
            "/v/api/ext/libs",
            "/v/api/ext/online",
            "/v/api/ext/source-health",
            "/v/api/ext/lunatv/status",
        ]
        for p in paths:
            r = self.client.get(p)
            self.assertIn(r.status_code, (200, 304), p)
            ct = r.headers.get("content-type", "")
            self.assertIn("application/json", ct,
                          f"{p} 返回了 {ct}（应为 JSON）")

    def test_app_center_prefixed_apis_return_json(self):
        """带 /app/trim-media-online 前缀也必须返回 JSON（1.6.0 病因）。"""
        prefix = "/app/trim-media-online"
        r = self.client.get(f"{prefix}/v/api/ext/status")
        self.assertEqual(r.status_code, 200)
        self.assertIn("application/json", r.headers.get("content-type", ""))
        body = r.json()
        self.assertTrue(body.get("ok"))
        self.assertIn("version", body)

    def test_config_roundtrip_safe(self):
        r = self.client.post("/v/api/ext/config",
                             json={"ad_filter_enabled": False})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json().get("code"), 0)


class GatewaySmokeTests(unittest.TestCase):
    """故障 2：网关剥前缀。相对 / 绝对 URI / 带查询串都要正确。"""

    def test_rewrite_handles_all_target_forms(self):
        from webui_gateway import _rewrite_request
        cases = {
            b"GET /app/trim-media-online/v/api/ext/status HTTP/1.1\r\nHost: h\r\n\r\n":
                "GET /v/api/ext/status HTTP/1.1",
            b"GET http://h/app/trim-media-online/v/api/ext/status HTTP/1.1\r\nHost: h\r\n\r\n":
                "GET /v/api/ext/status HTTP/1.1",
            b"GET /app/trim-media-online/v/api/ext/online?limit=5&q=a HTTP/1.1\r\nHost: h\r\n\r\n":
                "GET /v/api/ext/online?limit=5&q=a HTTP/1.1",
            b"GET http://h/app/trim-media-online/ HTTP/1.1\r\nHost: h\r\n\r\n":
                "GET /v/online-admin HTTP/1.1",
            b"GET /v/api/ext/status HTTP/1.1\r\nHost: h\r\n\r\n":
                "GET /v/api/ext/status HTTP/1.1",
        }
        for raw, expect in cases.items():
            got = _rewrite_request(raw).split(b"\r\n", 1)[0].decode()
            self.assertEqual(got, expect, f"输入 {raw!r}")


class AdminUiJsSmokeTests(unittest.TestCase):
    """故障 3：管理台 JS 不能出现 apiUrl 双重包裹（拦截 1.6.0 之前的 bug）。"""

    def test_no_double_apiurl_wrapping(self):
        src = (ROOT / "proxy" / "admin_ui.py").read_text(encoding="utf-8")
        self.assertNotIn("jget(apiUrl(", src)
        self.assertNotIn("jpost(apiUrl(", src)

    def test_jget_jpost_are_bare_paths(self):
        src = (ROOT / "proxy" / "admin_ui.py").read_text(encoding="utf-8")
        n = len(re.findall(r'j(get|post)\("/v/api/', src))
        self.assertGreaterEqual(n, 20, "管理 API 调用数量异常减少")

    def test_no_leftover_placeholder(self):
        src = (ROOT / "proxy" / "admin_ui.py").read_text(encoding="utf-8")
        self.assertNotIn("__PROTECTED_LINE_", src)


class PlaybackRegressionSmokeTests(unittest.TestCase):
    """故障 4：起播链路每次都要回归（去广告等改动不得侵入关键路径）。"""

    def test_adfilter_never_touches_master_playlist(self):
        import adfilter
        master = ("#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1\n"
                  "low.m3u8\n#EXT-X-STREAM-INF:BANDWIDTH=2\nhi.m3u8\n")
        self.assertEqual(adfilter.filter_hls(master), (master, 0))

    def test_adfilter_is_pure_sync_no_network(self):
        """用 AST 检查模块内无 await / 网络库调用（比文本匹配严谨）。"""
        import ast
        import adfilter
        src = inspect.getsource(adfilter)
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Await):
                self.fail("adfilter 出现 await：不得在起播路径引入异步网络 I/O")
            if isinstance(node, ast.Import):
                for a in node.names:
                    self.assertNotIn(a.name,
                                     ("httpx", "requests", "socket", "aiohttp"),
                                     f"adfilter 不得依赖网络库: {a.name}")
            if isinstance(node, ast.ImportFrom):
                self.assertNotIn(getattr(node, "module", ""),
                                 ("httpx", "requests", "socket", "aiohttp"))

    def test_adfilter_async_alias_behaves_same(self):
        """异步占位入口必须与同步入口行为完全一致。"""
        import adfilter
        sample = ("#EXTM3U\n#EXTINF:5,\n/a.ts\n#EXTINF:0.2,\n/ad.ts\n"
                  "#EXTINF:5,\n/b.ts\n")
        self.assertEqual(adfilter.filter_hls_async(sample),
                         adfilter.filter_hls(sample))

    def test_config_validate_never_raises(self):
        from config import config
        ok, warnings = config.validate()
        self.assertTrue(ok)
        self.assertIsInstance(warnings, list)


if __name__ == "__main__":
    unittest.main()
