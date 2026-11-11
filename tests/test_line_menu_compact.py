"""线路菜单压缩测试：TV / 手机原生端只拿单条线路，Web 端拿全部。

对应上游 fnmedia-ext v0.2.68 的修复：
「App 指定线路起播只回选中线单变体，避免原生播放器串行预取全部线路
累加等待；网页端多线路菜单保持不变。」

必须同时守住的红线：
  - Web 端行为完全不变（这是用户手动切线的主要入口）；
  - 压缩后其余线路仍被后台预热（切菜单时不能变慢）；
  - 预热必须异常安全、不阻塞响应。

实现备注：预热协程内部 `await _get_playlist_cached(...)`，patch 必须用
AsyncMock（普通 Mock 会让 await 抛 TypeError 被 except 静默吞掉，
造成「假通过」——这一条是本文件曾经的坑）。
"""
from __future__ import annotations

import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from starlette.requests import Request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "proxy"))

import app as appmod  # noqa: E402

# ---- 三种真实客户端画像（UA 样本取自 client.py 文档） ----
UA_TV = "1.4.2 (com.trim.tv; build:14209; Android 35) okHttp/4.9.0"
UA_IOS = "1.12.2 (com.trim.media.ios; build:1122011; iOS 27.2) Flutter/3.11.5"
UA_ANDROID = "Dalvik/2.1.0 (Linux; U; Android 15; V2203A) "
UA_WEB = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/120 Safari/537.36")

LINES = [{"line": "pA::m3u8", "label": "线路A", "url": "https://a.test/1.m3u8",
          "headers": {}, "kind": "movie"},
         {"line": "pB::m3u8", "label": "线路B", "url": "https://b.test/2.m3u8",
          "headers": {}, "kind": "movie"},
         {"line": "pC::m3u8", "label": "线路C", "url": "https://c.test/3.m3u8",
          "headers": {}, "kind": "movie"},
         {"line": "pD::m3u8", "label": "线路D", "url": "https://d.test/4.m3u8",
          "headers": {}, "kind": "movie"}]


def _req(ua: str, path: str = "/v/api/v1/stream",
         qs: bytes = b"") -> Request:
    return Request({"type": "http", "method": "POST", "path": path,
                    "query_string": qs,
                    "headers": [(b"user-agent", ua.encode())],
                    "app": appmod.app})


def _cfg(on=True):
    return {"line_menu_compact": on}


class CompactMenuTests(unittest.TestCase):

    def _qualities(self, ua, on=True):
        t = dict(LINES[0])
        with patch.object(appmod, "_line_choices",
                          return_value=[dict(x) for x in LINES]), \
             patch.object(appmod.config, "get", return_value=_cfg(on)):
            return appmod._qualities(t, _req(ua))

    # ---------- 原生端必须压缩 ----------

    def test_tv_gets_single_variant(self):
        q = self._qualities(UA_TV)
        self.assertEqual(len(q), 1)
        self.assertEqual(q[0]["resolution"], "线路A")  # 当前线路

    def test_ios_gets_single_variant(self):
        self.assertEqual(len(self._qualities(UA_IOS)), 1)

    def test_android_gets_single_variant(self):
        self.assertEqual(len(self._qualities(UA_ANDROID)), 1)

    # ---------- Web 端必须保持完整 ----------

    def test_web_gets_all_variants(self):
        q = self._qualities(UA_WEB)
        self.assertEqual(len(q), 4)
        self.assertEqual([x["resolution"] for x in q],
                         ["线路A", "线路B", "线路C", "线路D"])

    def test_no_request_keeps_all_variants(self):
        """request=None（内部调用）时按 Web 处理，不允许悄悄压缩。"""
        with patch.object(appmod, "_line_choices",
                          return_value=[dict(x) for x in LINES]), \
             patch.object(appmod.config, "get", return_value=_cfg()):
            q = appmod._qualities(dict(LINES[0]))
        self.assertEqual(len(q), 4)

    def test_unknown_client_keeps_all_variants(self):
        q = self._qualities("Mozilla/5.0 (未知客户端)")
        self.assertEqual(len(q), 4)

    # ---------- 配置开关 ----------

    def test_switch_off_disables_compression(self):
        self.assertEqual(len(self._qualities(UA_TV, on=False)), 4)

    def test_default_config_has_key(self):
        from config import DEFAULTS
        self.assertIn("line_menu_compact", DEFAULTS)
        self.assertTrue(DEFAULTS["line_menu_compact"])

    # ---------- 单线路目标 ----------

    def test_single_line_target_returns_empty(self):
        with patch.object(appmod, "_line_choices", return_value=[dict(LINES[0])]), \
             patch.object(appmod.config, "get", return_value=_cfg()):
            q = appmod._qualities(dict(LINES[0]), _req(UA_TV))
        self.assertEqual(q, [])


class WarmOtherLinesTests(unittest.IsolatedAsyncioTestCase):
    """后台预热：必须真实执行、只预热非当前线路、异常安全。"""

    async def _warm(self, ua, target_lines, on=True):
        calls = []

        async def fake(mg, picked, request):
            calls.append((mg, picked.get("line")))
            return "#EXTM3U\n"

        with patch.object(appmod, "_line_choices",
                          return_value=[dict(x) for x in target_lines]), \
             patch.object(appmod.config, "get", return_value=_cfg(on)), \
             patch.object(appmod, "_get_playlist_cached",
                          new=AsyncMock(side_effect=fake)):
            appmod._warm_other_lines("MG123", dict(target_lines[0]), _req(ua))
            # 让真实 create_task 的任务跑完
            for _ in range(40):
                await asyncio.sleep(0.05)
                if len(calls) >= max(0, len(target_lines) - 1):
                    break
        return calls

    async def test_native_warms_all_but_current(self):
        calls = await self._warm(UA_TV, LINES)
        self.assertEqual(len(calls), 3)
        self.assertEqual([c[1] for c in calls],
                         ["pB::m3u8", "pC::m3u8", "pD::m3u8"])
        self.assertTrue(all(c[0] == "MG123" for c in calls))

    async def test_ios_warms_others(self):
        calls = await self._warm(UA_IOS, LINES)
        self.assertEqual(len(calls), 3)

    async def test_web_warms_nothing(self):
        calls = await self._warm(UA_WEB, LINES)
        self.assertEqual(calls, [])

    async def test_switch_off_warms_nothing(self):
        calls = await self._warm(UA_TV, LINES, on=False)
        self.assertEqual(calls, [])

    async def test_skips_pan_and_special_sources(self):
        special = [dict(LINES[0]),
                   {"line": "pansou::x", "label": "网盘", "url": "u",
                    "headers": {}, "pan": True},
                   {"line": "pB::m3u8", "label": "B",
                    "url": "https://b/2.m3u8", "headers": {}, "kind": "movie"},
                   {"line": "pC::guard", "label": "加固",
                    "url": "https://c/3", "headers": {}, "kind": "movie"}]
        calls = await self._warm(UA_TV, special)
        # 只剩 pB（网盘与 guard 被跳过）
        self.assertEqual([c[1] for c in calls], ["pB::m3u8"])

    async def test_exception_inside_warm_never_propagates(self):
        """预热内部炸掉也不能影响请求。"""
        with patch.object(appmod, "_line_choices",
                          return_value=[dict(x) for x in LINES]), \
             patch.object(appmod.config, "get", return_value=_cfg()), \
             patch.object(appmod, "_get_playlist_cached",
                          new=AsyncMock(side_effect=RuntimeError("boom"))):
            appmod._warm_other_lines("MG", dict(LINES[0]), _req(UA_TV))
            await asyncio.sleep(0.2)
        # 不抛即通过

    async def test_bad_target_never_raises(self):
        for bad in (None, {}, {"line": None}, {"line": "x", "url": None}):
            appmod._warm_other_lines("MG", bad, _req(UA_TV))
            await asyncio.sleep(0.02)


if __name__ == "__main__":
    unittest.main()
