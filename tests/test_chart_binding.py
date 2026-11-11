"""榜单片绑定：严格同名匹配，宁可不显示也不串片。

背景（用户实测反馈）：豆瓣热门电影里的「每时每刻」「八仙！」点开无法
获取正确影视信息。根因是：
  1. 宽松兜底 `best = briefs[0]`：精确匹配搜不到时，把模糊搜索回来的
     第一部当成这一部 → 点开「每时每刻」却播成《时间倒数遇见你》；
  2. 包含匹配过宽：榜单片「八仙！」归一化成「八仙」，把 1990 年老剧
     《八仙过海》绑给 2026 年的新片。

对应上游 fnmedia-ext 的硬红线：
  - 「任意片名包含式榜单绑定，或把同名不同年份的影片合并」属永久禁止的负优化；
  - v1.0.0：「严格同名同年匹配，宁可不显示也不串到另一部同名作品」。
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "proxy"))

import app as appmod  # noqa: E402


class ChartTitleMatchTests(unittest.TestCase):
    """片名匹配规则：能绑的绑上，不能绑的一个都不许绑。"""

    def m(self, chart_title, result_title, year=None):
        return appmod._chart_title_match(chart_title, year, result_title)

    # ---------- 必须能绑 ----------

    def test_exact_equal(self):
        self.assertTrue(self.m("八仙过海", "八仙过海"))

    def test_punctuation_ignored(self):
        # 榜单片带感叹号，源站不带：归一化后相等
        self.assertTrue(self.m("八仙！", "八仙"))
        self.assertTrue(self.m("学生会也有洞！", "学生会也有洞"))

    def test_season_suffix_allowed(self):
        for suffix in [" 第一季", " 第2季", " S02", " 国语", " 粤语",
                       " 完结", " 上", " 大结局"]:
            self.assertTrue(self.m("某剧", "某剧" + suffix), suffix)

    # ---------- 绝不能绑（串片） ----------

    def test_contains_is_not_enough(self):
        """「八仙」绝不能绑给「八仙过海」——那是另一部老剧。"""
        self.assertFalse(self.m("八仙！", "八仙过海"))
        self.assertFalse(self.m("八仙", "八仙全传"))
        self.assertFalse(self.m("八仙", "八仙伏魔录"))

    def test_unrelated_never_binds(self):
        """源站没有这部新片时，模糊搜回来的别的片一律不绑。"""
        self.assertFalse(self.m("每时每刻", "时间倒数遇见你"))
        self.assertFalse(self.m("每时每刻", "O记实录国语第二部"))
        self.assertFalse(self.m("黑球", "黑镜"))

    def test_prefix_requires_season_modifier(self):
        """榜单名更长也不行：修饰续接必须是季/集/版本类。"""
        self.assertFalse(self.m("某剧番外篇", "某剧"))  # 番外篇不是合法修饰
        self.assertTrue(self.m("某剧第一季", "某剧"))

    def test_empty_inputs_safe(self):
        self.assertFalse(self.m("", "某片"))
        self.assertFalse(self.m("某片", ""))
        self.assertFalse(self.m(None, "某片"))
        self.assertFalse(self.m("某片", None))


class ResolveChartTests(unittest.IsolatedAsyncioTestCase):
    """端到端：绑定流程不得出现「搜不到就随便抓一部」。"""

    def setUp(self):
        # start_resolve_chart 用全局失败冷却表；固定 guid 会跨测试相互污染
        appmod._CHART_FAILED_TS.clear()
        appmod._chart_resolving.clear()
        appmod._PENDING_MEDIA_CHART.clear()

    async def _resolve(self, chart_item, briefs):
        guid = "chart-guid-xyz"
        with patch.object(appmod.chart_cache, "get_guid",
                          return_value=chart_item), \
             patch.object(appmod.store, "get_title_by_guid",
                          return_value=None), \
             patch.object(appmod, "_aggregate_briefs",
                          new=AsyncMock(return_value=briefs)), \
             patch.object(appmod.store, "remember_merged", new=Mock()):
            fut = appmod.start_resolve_chart(guid)
            if fut is None:
                return None
            return await fut

    async def test_no_source_returns_none_not_random_film(self):
        """源站没有这部片：必须返回 None（显示暂无片源），不能绑错片。"""
        chart = {"title": "每时每刻", "cat": "movie", "year": "2026"}
        briefs = [{"title": "时间倒数遇见你", "guid": "g1", "lines": {}},
                  {"title": "O记实录国语第二部", "guid": "g2", "lines": {}}]
        best = await self._resolve(chart, briefs)
        self.assertIsNone(best)

    async def test_same_title_binds(self):
        chart = {"title": "八仙过海", "cat": "tv", "year": ""}
        briefs = [{"title": "无关片子", "guid": "g0", "lines": {}},
                  {"title": "八仙过海", "guid": "g1", "lines": {}}]
        with patch.object(appmod.chart_cache, "get_guid",
                          return_value=chart), \
             patch.object(appmod.store, "get_title_by_guid",
                          return_value=None), \
             patch.object(appmod, "_aggregate_briefs",
                          new=AsyncMock(return_value=briefs)), \
             patch.object(appmod.store, "remember_merged", new=Mock()) as spy:
            fut = appmod.start_resolve_chart("chart-guid-xyz")
            best = await fut if fut else None
        self.assertIsNotNone(best)
        self.assertEqual(best["title"], "八仙过海")
        # 落库的身份必须换成榜单 guid，播放链才能挂到榜单卡片
        stored = spy.call_args.args[0][0]
        self.assertEqual(stored["guid"], "chart-guid-xyz")
        self.assertEqual(stored["chart"]["title"], "八仙过海")

    async def test_exclamation_variant_binds(self):
        chart = {"title": "八仙！", "cat": "movie", "year": "2026"}
        briefs = [{"title": "八仙过海", "guid": "g1", "lines": {}},
                  {"title": "八仙", "guid": "g2", "lines": {}}]
        best = await self._resolve(chart, briefs)
        self.assertIsNotNone(best)
        self.assertEqual(best["title"], "八仙")

    async def test_empty_briefs_safe(self):
        chart = {"title": "冷门片", "cat": "movie", "year": ""}
        best = await self._resolve(chart, [])
        self.assertIsNone(best)

    async def test_resolve_exception_safe(self):
        with patch.object(appmod.chart_cache, "get_guid",
                          return_value={"title": "x", "cat": "movie"}), \
             patch.object(appmod.store, "get_title_by_guid", return_value=None), \
             patch.object(appmod, "_aggregate_briefs",
                          new=AsyncMock(side_effect=RuntimeError("boom"))):
            fut = appmod.start_resolve_chart("g-err")
            result = await fut if fut else None
            self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
