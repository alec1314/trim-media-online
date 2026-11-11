"""adfilter 选集名过滤测试。

这些用例守护的是项目里原有的能力（我在新增 m3u8 过滤时曾误覆盖整个
adfilter.py 导致它丢失，故补测试固化）。
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "proxy"))

import adfilter  # noqa: E402


class AdEpisodeNameTests(unittest.TestCase):

    def test_existing_ability_preserved(self):
        """原有能力必须保留（防文件被覆盖丢失）。"""
        self.assertTrue(callable(adfilter.is_ad_episode))

    # ---------- 必须识别为引流广告 ----------

    def test_wechat_and_public_account(self):
        for n in ["关注公众号", "微信公众号：abc", "加微信 abc1234",
                  "VX: myfilm", "QQ群 123456", "扫码关注", "下载APP",
                  "更多精彩资源请关注", "www.example.com", "本片由xx提供",
                  "永久网址入口", "广告位"]:
            self.assertTrue(adfilter.is_ad_episode(n), n)

    # ---------- 绝不能误判为正片 ----------

    def test_real_episodes_kept(self):
        for n in ["第1集", "01", "第12期", "正片", "预告", "花絮",
                  "HD国语", "大结局", "第3集 加长版", "上", "中",
                  "第2集 蓝光1080P", "25"]:
            self.assertFalse(adfilter.is_ad_episode(n), n)

    # ---------- 边界安全 ----------

    def test_empty_and_overlong_safe(self):
        self.assertFalse(adfilter.is_ad_episode(""))
        self.assertFalse(adfilter.is_ad_episode(None))
        self.assertFalse(adfilter.is_ad_episode("x" * 61))


if __name__ == "__main__":
    unittest.main()
