"""adfilter 单元测试：广告分片过滤的安全边界。

重点验证「红线」：
  - 起播路径零网络 I/O（纯同步函数）
  - 不确定一律保留原片
  - 主播放列表绝不处理
  - 删除量超闸时整表放弃
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "proxy"))

import adfilter  # noqa: E402


def _playlist(segments) -> str:
    """segments: [(uri, dur)] → m3u8 文本"""
    out = ["#EXTM3U", "#EXT-X-TARGETDURATION:10",
           "#EXT-X-MEDIA-SEQUENCE:0"]
    for uri, dur in segments:
        out.append(f"#EXTINF:{dur},")
        out.append(uri)
    out.append("#EXT-X-ENDLIST")
    return "\n".join(out)


class AdFilterSafetyTests(unittest.TestCase):

    # ---------- 绝对不能动的情况 ----------

    def test_master_playlist_untouched(self):
        master = ("#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1000\n"
                  "low.m3u8\n#EXT-X-STREAM-INF:BANDWIDTH=2000\n"
                  "high.m3u8\n")
        text, n = adfilter.filter_hls(master)
        self.assertEqual(text, master)
        self.assertEqual(n, 0)

    def test_too_few_segments_untouched(self):
        text_in = _playlist([("a.ts", 4), ("b.ts", 4)])
        text, n = adfilter.filter_hls(text_in)
        self.assertEqual(text, text_in)
        self.assertEqual(n, 0)

    def test_none_input_safe(self):
        self.assertEqual(adfilter.filter_hls(None), (None, 0))

    def test_no_ads_unchanged(self):
        segs = [(f"/cdn/{i}.ts", 4.0) for i in range(30)]
        text_in = _playlist(segs)
        text, n = adfilter.filter_hls(text_in)
        self.assertEqual(text, text_in)
        self.assertEqual(n, 0)

    # ---------- 明确广告必须删 ----------

    def test_uri_ad_word_removed(self):
        segs = [("/cdn/0.ts", 4.0)] * 20
        segs[5] = ("/ads/preroll-1.ts", 4.0)
        segs[6] = ("/ads/preroll-2.ts", 4.0)
        text_in = _playlist(segs)
        text, n = adfilter.filter_hls(text_in)
        self.assertEqual(n, 2)
        self.assertNotIn("/ads/preroll", text)
        self.assertIn("/cdn/0.ts", text)
        # 语法仍合法：EXTINF 与 URI 行数一致
        self._assert_valid_m3u8(text)

    def test_short_ad_segments_removed(self):
        """成群出现的超短分片（<0.5s）视为片头广告。"""
        segs = [("/cdn/main.ts", 5.0)] * 24
        segs[2:6] = [("/v/ad%d.ts" % i, 0.2) for i in range(4)]
        text_in = _playlist(segs)
        text, n = adfilter.filter_hls(text_in)
        self.assertGreaterEqual(n, 4)
        self.assertNotIn("/v/ad0.ts", text)
        self._assert_valid_m3u8(text)

    # ---------- 安全闸 ----------

    def test_over_ratio_abandons_whole_table(self):
        """删除量超 30% 时整表放弃，保证不漏删正片。"""
        segs = [("/ads/a%d.ts" % i, 4.0) for i in range(20)]
        segs += [("/cdn/main%d.ts" % i, 5.0) for i in range(10)]
        text_in = _playlist(segs)
        text, n = adfilter.filter_hls(text_in)
        self.assertEqual(n, 0)
        self.assertEqual(text, text_in)

    def test_single_short_segment_kept(self):
        """只删 1 片的极短分片不构成「成群」，时长信号不成立时不删。"""
        segs = [("/cdn/main.ts", 5.0)] * 20
        segs[10] = ("/cdn/short.ts", 0.2)
        text_in = _playlist(segs)
        text, n = adfilter.filter_hls(text_in)
        # URI 非广告 + 单片离群不足以判定 → 保留
        self.assertEqual(n, 0)
        self.assertEqual(text, text_in)

    # ---------- CDN 切换型 ----------

    def test_cdn_switch_short_run_removed(self):
        segs = [("https://cdn-a.com/%d.ts" % i, 5.0) for i in range(20)]
        segs.insert(10, ("https://cdn-b.com/x.ts", 5.0))
        segs.insert(11, ("https://cdn-b.com/y.ts", 5.0))
        text_in = _playlist(segs)
        text, n = adfilter.filter_hls(text_in)
        self.assertEqual(n, 2)
        self.assertNotIn("cdn-b.com", text)
        self._assert_valid_m3u8(text)

    def test_cdn_switch_long_run_kept(self):
        """长段切换视为换源/容灾，绝不做广告删。"""
        segs = [("https://cdn-a.com/%d.ts" % i, 5.0) for i in range(20)]
        for j in range(10):
            segs.insert(10 + j, ("https://cdn-b.com/y%d.ts" % j, 5.0))
        text_in = _playlist(segs)
        text, n = adfilter.filter_hls(text_in)
        self.assertEqual(n, 0)
        self.assertEqual(text, text_in)

    # ---------- 输出必须是合法 m3u8 ----------

    def _assert_valid_m3u8(self, text: str):
        self.assertTrue(text.startswith("#EXTM3U"))
        # 每个 URI 行前面必须紧跟一个 EXTINF 行
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        for i, ln in enumerate(lines):
            if ln.startswith("#") or not ln:
                continue
            if ln == "#EXT-X-ENDLIST":
                continue
            self.assertGreater(i, 0, "URI 行前没有 EXTINF")
            self.assertTrue(lines[i - 1].startswith("#EXTINF"),
                            f"URI 行前不是 EXTINF: {lines[i - 1]}")


if __name__ == "__main__":
    unittest.main()
