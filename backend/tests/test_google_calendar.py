"""Google calendar export and OAuth tests; no real Google account or network."""
import copy
import importlib
import os
import unittest
from datetime import date, datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

from fastapi import HTTPException, Request, Response
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.app import google_calendar as google
with patch.dict(os.environ, {"DATABASE_URL": "sqlite://", "APP_SECRET": "isolated-google-tests"}), patch("dotenv.load_dotenv"):
    api = importlib.import_module("backend.app.main")


class GoogleExportTests(unittest.TestCase):
    def event(self, **changes):
        return {"id": "source-1", "title": "Odbiór dokumentu", "due_date": date(2026, 10, 1),
                "status": "planowany", "company_id": "client-1", "notes": "Private note", **changes}

    def test_all_day_and_timed_events_do_not_export_private_fields(self):
        body = google.event_body(self.event(), "Jan Kowalski", "namespace")
        self.assertEqual(body["start"], {"date": "2026-10-01"})
        self.assertEqual(body["end"], {"date": "2026-10-02"})
        self.assertIn("Jan Kowalski", body["description"])
        self.assertNotIn("Private note", body["description"])
        for day, offset in [(date(2026, 7, 1), "+02:00"), (date(2026, 12, 1), "+01:00")]:
            body = google.event_body(self.event(due_date=day, scheduled_time="09:30"), "", "namespace")
            self.assertTrue(body["start"]["dateTime"].endswith("09:30:00" + offset))
            self.assertTrue(body["end"]["dateTime"].endswith("10:30:00" + offset))
        body = google.event_body(self.event(scheduled_time="rano"), "", "namespace")
        self.assertIn("date", body["start"])
        self.assertIn("rano", body["description"])
        body = google.event_body(self.event(due_date=date(2026, 10, 25), scheduled_time="02:30"), "", "namespace")
        start = datetime.fromisoformat(body["start"]["dateTime"])
        end = datetime.fromisoformat(body["end"]["dateTime"])
        self.assertEqual(end - start, timedelta(hours=1))

    def test_export_retries_without_duplicates_updates_and_deletes(self):
        stored = {}
        def provider(method, url, data=None, token=None, form=False):
            if method == "GET" and "?" in url:
                return {"items": list(copy.deepcopy(stored).values())}
            if method == "POST":
                self.assertNotIn(data["id"], stored)
                stored[data["id"]] = copy.deepcopy(data)
                return data
            key = url.rsplit("/", 1)[1]
            if method == "PUT":
                stored[key] = {"id": key, **copy.deepcopy(data)}
                return stored[key]
            if method == "DELETE":
                del stored[key]
                return {}
            raise AssertionError((method, url))
        with patch.object(google, "request", side_effect=provider):
            result = google.sync_events("token", "calendar", "namespace", [self.event()], {})
            self.assertEqual(result["created"], 1)
            result = google.sync_events("token", "calendar", "namespace", [self.event()], {})
            self.assertEqual(result["unchanged"], 1)
            self.assertEqual(len(stored), 1)
            result = google.sync_events("token", "calendar", "namespace", [self.event(title="Nowa nazwa", due_date=date(2026, 10, 2))], {})
            self.assertEqual(result["updated"], 1)
            self.assertEqual(next(iter(stored.values()))["summary"], "Nowa nazwa")
            result = google.sync_events("token", "calendar", "namespace", [], {})
            self.assertEqual(result["deleted"], 1)
            self.assertEqual(stored, {})

    def test_google_deleted_event_is_recreated_with_stable_replacement_id(self):
        with patch.object(google, "request", side_effect=[{"items": []}, google.GoogleError("conflict", 409), {"status": "cancelled"}, {}]) as request:
            result = google.sync_events("token", "calendar", "namespace", [self.event()], {})
        first = request.call_args_list[1].args[2]["id"]
        second = request.call_args_list[3].args[2]["id"]
        self.assertNotEqual(first, second)
        self.assertEqual(result["created"], 1)

    def test_pagination_and_interrupted_insert_recovery(self):
        body = google.event_body(self.event(), "", "namespace")
        with patch.object(google, "request", side_effect=[{"items": [], "nextPageToken": "next"}, {"items": []}, google.GoogleError("conflict", 409), body, {}]) as request:
            result = google.sync_events("token", "calendar", "namespace", [self.event()], {})
        self.assertIn("pageToken=next", request.call_args_list[1].args[1])
        self.assertEqual(result["updated"], 1)


class GoogleConnectionTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        api.Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.admin = api.User(email="admin@example.com", role="admin", password_hash="unused")
        self.db.add(self.admin)
        self.db.commit()
        api.save_google_calendar(api.GoogleCalendarInput(client_id="test.apps.googleusercontent.com", client_secret="oauth-secret",
            public_url="https://panel.example.com"), self.admin, self.db)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def start(self):
        response = Response()
        result = api.connect_google_calendar(response, self.admin, self.db)
        params = parse_qs(urlsplit(result["url"]).query)
        self.assertEqual(params["scope"], [google.SCOPE])
        self.assertEqual(params["code_challenge_method"], ["S256"])
        self.assertIn("HttpOnly", response.headers["set-cookie"])
        self.assertIn("Secure", response.headers["set-cookie"])
        state = params["state"][0]
        request = Request({"type": "http", "headers": [(b"cookie", f"google_calendar_state={state}".encode())]})
        return state, request

    def test_configuration_hides_secrets_and_requires_secure_origin(self):
        settings = api.google_calendar_settings(self.admin, self.db)
        self.assertTrue(settings["client_secret_set"])
        self.assertNotIn("oauth-secret", str(settings))
        stored = self.db.get(api.GoogleCalendarSettings, 1)
        self.assertNotEqual(stored.client_secret_encrypted, "oauth-secret")
        from pydantic import ValidationError
        for origin in ("http://public.example.com", "https://example.com/path", "https://user:password@example.com", "https://example.com?next=bad"):
            with self.assertRaises(ValidationError):
                api.GoogleCalendarInput(client_id="client", public_url=origin)

    def test_callback_connects_once_and_encrypts_refresh_token(self):
        state, request = self.start()
        credentials = {"access_token": "access", "refresh_token": "refresh", "scope": google.SCOPE}
        with patch.object(google, "exchange_code", return_value=credentials) as exchange, patch.object(google, "create_calendar", return_value="calendar@example.com"):
            result = api.google_calendar_callback(request, state, "code", "", self.db)
            self.assertEqual(result.status_code, 303)
            self.assertEqual(result.headers["location"], "https://panel.example.com/?google_calendar=connected")
            self.assertTrue(exchange.call_args.args[4])
            with self.assertRaises(HTTPException) as error:
                api.google_calendar_callback(request, state, "code", "", self.db)
            self.assertEqual(error.exception.status_code, 400)
            exchange.assert_called_once()
        stored = self.db.get(api.GoogleCalendarSettings, 1)
        self.assertNotEqual(stored.refresh_token_encrypted, "refresh")
        self.assertEqual(api.fernet.decrypt(stored.refresh_token_encrypted.encode()), b"refresh")
        self.assertTrue(api.google_calendar_settings(self.admin, self.db)["connected"])

    def test_callback_rejects_missing_cookie_expired_state_and_blocked_admin(self):
        state, request = self.start()
        with patch.object(google, "exchange_code") as exchange:
            with self.assertRaises(HTTPException):
                api.google_calendar_callback(Request({"type": "http", "headers": []}), state, "code", "", self.db)
            self.admin.blocked = True
            self.db.commit()
            with self.assertRaises(HTTPException) as error:
                api.google_calendar_callback(request, state, "code", "", self.db)
            self.assertEqual(error.exception.status_code, 403)
            self.admin.blocked = False
            pending = self.db.scalar(select(api.GoogleCalendarOAuthState))
            pending.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
            self.db.commit()
            with self.assertRaises(HTTPException) as error:
                api.google_calendar_callback(request, state, "code", "", self.db)
            self.assertEqual(error.exception.status_code, 400)
            exchange.assert_not_called()

    def test_denied_consent_is_consumed_without_network_calls(self):
        state, request = self.start()
        with patch.object(google, "exchange_code") as exchange:
            result = api.google_calendar_callback(request, state, "", "access_denied", self.db)
            exchange.assert_not_called()
        self.assertIn("google_calendar=error", result.headers["location"])
        self.assertIsNone(self.db.scalar(select(api.GoogleCalendarOAuthState)))
        self.assertIsNotNone(self.db.get(api.GoogleCalendarSettings, 1).last_error)

    def test_sync_error_is_reported_and_disconnect_removes_credentials(self):
        stored = self.db.get(api.GoogleCalendarSettings, 1)
        stored.refresh_token_encrypted = api.fernet.encrypt(b"refresh").decode()
        stored.calendar_id = "calendar@example.com"
        self.db.commit()
        with patch.object(google, "refresh_access", side_effect=google.GoogleError("Token expired", 401)):
            with self.assertRaises(HTTPException) as error:
                api.run_google_sync(self.db)
            self.assertEqual(error.exception.status_code, 502)
        self.assertEqual(stored.last_error, "Token expired")
        with patch.object(google, "request", return_value={}):
            api.disconnect_google_calendar(self.admin, self.db)
        self.assertIsNone(stored.refresh_token_encrypted)
        self.assertFalse(stored.automatic)
        with patch.object(google, "refresh_access") as refresh:
            self.assertTrue(api.run_google_sync(self.db, automatic=True)["skipped"])
            refresh.assert_not_called()
