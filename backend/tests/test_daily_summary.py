import json
import os
import unittest
from datetime import date
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch
from urllib.error import URLError
from backend.app import daily_summary as summary


class DailySummaryTests(unittest.TestCase):
    def setUp(self):
        summary._cache.clear()

    def test_counts_exclude_closed_and_future_from_today(self):
        events = [{"id": str(index), "due_date": day, "status": status} for index, (day, status) in enumerate([
            (date(2026, 10, 1), "planowany"), (date(2026, 9, 30), "planowany"),
            (date(2026, 9, 29), "wykonany"), (date(2026, 10, 1), "anulowany"),
            (date(2026, 10, 2), "planowany"), (None, "planowany")])]
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
            result = summary.build_overview(events, [SimpleNamespace(progress=value) for value in (0, 50, 100)], date(2026, 10, 1))
        self.assertEqual(result["stats"], {"today": 1, "overdue": 1, "tomorrow": 1, "active_services": 1, "unscheduled": 1})
        self.assertEqual(result["source"], "local")
        self.assertFalse(result["ai_configured"])
        self.assertEqual(len(result["today_events"]), 1)

    def test_empty_day_is_not_fabricated(self):
        result = summary.build_overview([], [], date(2026, 10, 1))
        self.assertIn("nie masz otwartych terminów", result["text"])
        self.assertFalse(result["today_events"])

    def test_ai_payload_is_counts_only_and_cached(self):
        stats = {"today": 2, "overdue": 1, "tomorrow": 0, "active_services": 1, "unscheduled": 0, "private": "secret-client"}
        body = {"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": "Dzisiaj dwa terminy."}]}]}
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-secret"}), patch.object(summary, "urlopen", return_value=BytesIO(json.dumps(body).encode())) as send:
            for _ in range(2):
                self.assertEqual(summary.generate(stats, "2026-10-01"), "Dzisiaj dwa terminy.")
            send.assert_called_once()
            payload = json.loads(send.call_args.args[0].data)
            self.assertFalse(payload["store"])
            self.assertNotIn("secret-client", json.dumps(payload))
            self.assertNotIn("test-secret", json.dumps(payload))
            self.assertEqual(json.loads(payload["input"])["counts"]["today"], 2)

    def test_failed_generation_is_safe_and_not_cached(self):
        stats = {key: 0 for key in ("today", "overdue", "tomorrow", "active_services", "unscheduled")}
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-secret"}), patch.object(summary, "urlopen", side_effect=URLError("test-secret")):
            with self.assertRaises(ValueError) as error:
                summary.generate(stats, "2026-10-01")
            self.assertNotIn("test-secret", str(error.exception))
            self.assertFalse(summary._cache)
