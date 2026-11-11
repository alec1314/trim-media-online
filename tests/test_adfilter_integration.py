"""adfilter 集成测试：过滤必须安全地嵌在播放列表构建链路里。

验证红线：
  1. 开关关闭时完全不介入（默认行为不变）；
  2. 开启时才剥离广告分片，且输出仍是合法 m3u8；
  3. 过滤抛异常绝不能影响播放（异常被吞、正片仍返回）。
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from starlette.requests import Request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "proxy"))

import adfilter  # noqa: E402
import app as appmod  # noqa: E402


def _req():
    return Request({"type": "http", "method": "GET",
                    "path": "/v/media/online/mg/main.m3u8",
                    "query_string": b"", "headers": [], "app": appmod.app})


def _picked():
    return {"online_guid": "og", "line": "l1", "index": 0,
            "url": "https://media.test/list.m3u8",
            "headers": {}, "title": "测试片"}


def _playlist(n_ads: int = 0) -> str:
    segs = [("https://cdn.test/main%d.ts" % i, 5.0) for i in range(20)]
    for i in range(n_ads):
        segs.insert(10 + i, ("https://ads.test/preroll%d.ts" % i, 5.0))
    out = ["#EXTM3U", "#EXT-X-TARGETDURATION:10",
           "#EXT-X-MEDIA-SEQUENCE:0"]
    for uri, dur in segs:
        out.append(f"#EXTINF:{dur},")
        out.append(uri)
    out.append("#EXT-X-ENDLIST")
    return "\n".join(out)


def _count_segs(body: str) -> int:
    return body.count("#EXTINF:")


class AdFilterIntegrationTests(unittest.IsolatedAsyncioTestCase):

    async def test_disabled_by_default_touches_nothing(self):
        with patch.object(appmod, "_resolve_if_needed", new=AsyncMock()), \
             patch.object(appmod, "_fetch_playlist",
                          new=AsyncMock(return_value=(_playlist(0),
                                                     "https://media.test/"))), \
             patch.object(appmod.config, "get", return_value={}):
            body, _base = await appmod._build_playlist_body("mg", _picked(),
                                                            _req())
        self.assertIsNotNone(body)
        self.assertEqual(_count_segs(body), 20)
        with patch.object(adfilter, "filter_hls",
                          wraps=adfilter.filter_hls) as spy, \
             patch.object(appmod, "_resolve_if_needed", new=AsyncMock()), \
             patch.object(appmod, "_fetch_playlist",
                          new=AsyncMock(return_value=(_playlist(0),
                                                     "https://media.test/"))), \
             patch.object(appmod.config, "get", return_value={}):
            await appmod._build_playlist_body("mg", _picked(), _req())
        spy.assert_not_called()

    async def test_enabled_strips_ad_segments(self):
        self.assertEqual(_count_segs(_playlist(3)), 23)
        with patch.object(appmod, "_resolve_if_needed", new=AsyncMock()), \
             patch.object(appmod, "_fetch_playlist",
                          new=AsyncMock(return_value=(_playlist(3),
                                                     "https://media.test/"))), \
             patch.object(appmod.config, "get",
                          return_value={"ad_filter_enabled": True}):
            body, _base = await appmod._build_playlist_body("mg", _picked(),
                                                            _req())
        self.assertIsNotNone(body)
        self.assertEqual(_count_segs(body), 20)   # 3 条广告被剥掉
        self.assertIn("#EXT-X-ENDLIST", body)     # 输出仍是合法 m3u8

    async def test_filter_exception_never_breaks_playback(self):
        with patch.object(appmod, "_resolve_if_needed", new=AsyncMock()), \
             patch.object(appmod, "_fetch_playlist",
                          new=AsyncMock(return_value=(_playlist(3),
                                                     "https://media.test/"))), \
             patch.object(appmod.config, "get",
                          return_value={"ad_filter_enabled": True}), \
             patch.object(adfilter, "filter_hls",
                          side_effect=RuntimeError("boom")):
            body, _base = await appmod._build_playlist_body("mg", _picked(),
                                                            _req())
        # 异常被吞：广告分片仍在（未过滤），但播放链路完整返回
        self.assertIsNotNone(body)
        self.assertEqual(_count_segs(body), 23)
        self.assertIn("#EXT-X-ENDLIST", body)


if __name__ == "__main__":
    unittest.main()
