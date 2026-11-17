"""按用户隔离「继续观看」的回归测试。

对应真实故障：所有用户的在线播放进度共用一份 history.json，A 用户最近看的
条目会出现在 B 用户的继续观看里。
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

import history as histmod  # noqa: E402
import userctx  # noqa: E402


class HistoryUserScopeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = Path(self.tmp.name) / "history.json"
        self._old = histmod._STATE
        histmod._STATE = self.state

    def tearDown(self):
        histmod._STATE = self._old
        self.tmp.cleanup()

    def _new(self) -> histmod.History:
        return histmod.History()

    def test_same_item_isolated_between_users(self):
        h = self._new()
        body = {"item_guid": "ep1", "media_guid": "mg1", "duration": 1000}
        h.record(dict(body, ts=120), uid="alice")
        h.record(dict(body, ts=480), uid="bob")
        self.assertEqual(h.get("ep1", uid="alice")["ts"], 120)
        self.assertEqual(h.get("ep1", uid="bob")["ts"], 480)
        self.assertEqual(len(h.all(uid="alice")), 1)
        self.assertIsNone(h.get("ep1", uid="carol"))

    def test_current_user_from_context(self):
        h = self._new()
        body = {"item_guid": "ep2", "duration": 600}
        tok = userctx.set_current("alice")
        try:
            h.record(dict(body, ts=60))
            self.assertEqual(h.get("ep2")["ts"], 60)
        finally:
            userctx.reset(tok)
        tok = userctx.set_current("bob")
        try:
            self.assertIsNone(h.get("ep2"))
            self.assertEqual(h.all(), [])
        finally:
            userctx.reset(tok)

    def test_anonymous_bucket_does_not_leak(self):
        h = self._new()
        h.record({"item_guid": "ep3", "ts": 30, "duration": 300})  # 无身份
        self.assertEqual(len(h.all(uid="")), 1)
        self.assertEqual(h.all(uid="alice"), [])

    def test_legacy_records_migrate_to_admin(self):
        self.state.write_text(json.dumps({"records": {
            "old1": {"item_guid": "old1", "ts": 77, "duration": 200,
                     "updated_at": 1}}}))
        with patch.object(userctx, "admin_user", return_value="admin-guid"):
            h = self._new()
        self.assertEqual(h.get("old1", uid="admin-guid")["ts"], 77)
        self.assertEqual(h.all(uid="someone-else"), [])
        saved = json.loads(self.state.read_text())
        self.assertIn("users", saved)
        self.assertNotIn("records", saved)

    def test_persist_and_reload_per_user(self):
        h = self._new()
        h.record({"item_guid": "ep4", "ts": 10, "duration": 100}, uid="alice")
        h.record({"item_guid": "ep4", "ts": 90, "duration": 100}, uid="bob")
        h.flush()
        h2 = self._new()
        self.assertEqual(h2.get("ep4", uid="alice")["ts"], 10)
        self.assertEqual(h2.get("ep4", uid="bob")["ts"], 90)

    def test_delete_only_current_user(self):
        h = self._new()
        h.record({"item_guid": "ep5", "ts": 5, "duration": 100}, uid="alice")
        h.record({"item_guid": "ep5", "ts": 6, "duration": 100}, uid="bob")
        self.assertEqual(h.delete(["ep5"], uid="alice"), 1)
        self.assertIsNone(h.get("ep5", uid="alice"))
        self.assertEqual(h.get("ep5", uid="bob")["ts"], 6)


class UserResolveTests(unittest.TestCase):
    def test_token_normalisation(self):
        self.assertEqual(userctx._norm_token("Bearer abc"), "abc")
        self.assertEqual(userctx._norm_token("  abc  "), "abc")
        self.assertEqual(userctx._norm_token(""), "")

    def test_unknown_token_is_empty(self):
        self.assertEqual(userctx.token_user("definitely-not-a-token"), "")


if __name__ == "__main__":
    unittest.main()
