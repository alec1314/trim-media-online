"""按用户隔离收藏 / 「已看」标记的回归测试。

对应真实故障：所有用户的在线收藏与已看标记共用一份 marks.json，A 用户收藏
的条目会出现在 B 用户的收藏夹里。
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "proxy"))

import marks as marksmod  # noqa: E402
import userctx  # noqa: E402


class MarksUserScopeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = Path(self.tmp.name) / "marks.json"
        self._old = marksmod._STATE
        marksmod._STATE = self.state

    def tearDown(self):
        marksmod._STATE = self._old
        self.tmp.cleanup()

    def _new(self) -> marksmod.Marks:
        return marksmod.Marks()

    def test_favorite_isolated_between_users(self):
        m = self._new()
        m.add_favorite("g1", {"title": "A"}, uid="alice")
        self.assertTrue(m.is_favorite("g1", uid="alice"))
        self.assertFalse(m.is_favorite("g1", uid="bob"))
        self.assertEqual(m.favorite_guids(uid="bob"), set())
        self.assertEqual([r["guid"] for r in m.favorite_records(uid="alice")],
                         ["g1"])

    def test_watched_isolated_between_users(self):
        m = self._new()
        m.set_watched("g2", {"title": "B"}, uid="alice")
        self.assertTrue(m.is_watched("g2", uid="alice"))
        self.assertFalse(m.is_watched("g2", uid="bob"))
        self.assertGreater(m.watched_ts("g2", uid="alice"), 0)
        self.assertEqual(m.watched_ts("g2", uid="bob"), 0)
        self.assertEqual(m.watched_guids(uid="bob"), set())

    def test_remove_only_affects_current_user(self):
        m = self._new()
        m.add_favorite("g3", uid="alice")
        m.add_favorite("g3", uid="bob")
        m.remove_favorite("g3", uid="alice")
        self.assertFalse(m.is_favorite("g3", uid="alice"))
        self.assertTrue(m.is_favorite("g3", uid="bob"))
        m.set_watched("g4", uid="alice")
        m.set_watched("g4", uid="bob")
        m.remove_watched("g4", uid="alice")
        self.assertFalse(m.is_watched("g4", uid="alice"))
        self.assertTrue(m.is_watched("g4", uid="bob"))

    def test_current_user_from_context(self):
        m = self._new()
        tok = userctx.set_current("alice")
        try:
            m.add_favorite("g5")
            m.set_watched("g6")
            self.assertTrue(m.is_favorite("g5"))
            self.assertTrue(m.is_watched("g6"))
        finally:
            userctx.reset(tok)
        tok = userctx.set_current("bob")
        try:
            self.assertFalse(m.is_favorite("g5"))
            self.assertFalse(m.is_watched("g6"))
            self.assertEqual(m.favorite_records(), [])
        finally:
            userctx.reset(tok)

    def test_anonymous_bucket_does_not_leak(self):
        m = self._new()
        m.add_favorite("g7")  # 无身份
        self.assertTrue(m.is_favorite("g7", uid=""))
        self.assertFalse(m.is_favorite("g7", uid="alice"))

    def test_legacy_marks_migrate_to_admin(self):
        self.state.write_text(json.dumps({
            "favorites": {"old1": {"guid": "old1", "ts": 1}},
            "watched": {"old2": {"guid": "old2", "ts": 2}},
        }))
        with patch.object(userctx, "admin_user", return_value="admin-guid"):
            m = self._new()
        self.assertTrue(m.is_favorite("old1", uid="admin-guid"))
        self.assertTrue(m.is_watched("old2", uid="admin-guid"))
        self.assertFalse(m.is_favorite("old1", uid="someone-else"))
        saved = json.loads(self.state.read_text())
        self.assertIn("users", saved)
        self.assertNotIn("favorites", saved)

    def test_persist_and_reload_per_user(self):
        m = self._new()
        m.add_favorite("g8", uid="alice")
        m.add_favorite("g9", uid="bob")
        m.set_watched("g10", uid="bob")
        m2 = self._new()
        self.assertEqual(m2.favorite_guids(uid="alice"), {"g8"})
        self.assertEqual(m2.favorite_guids(uid="bob"), {"g9"})
        self.assertTrue(m2.is_watched("g10", uid="bob"))
        self.assertFalse(m2.is_watched("g10", uid="alice"))

    def test_remember_meta_is_per_user(self):
        m = self._new()
        m.add_favorite("g11", uid="alice")
        m.remember_meta("g11", {"title": "标题"}, uid="alice")
        self.assertEqual(m.favorite_records(uid="alice")[0]["title"], "标题")
        self.assertEqual(m.favorite_records(uid="bob"), [])


if __name__ == "__main__":
    unittest.main()
