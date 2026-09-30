"""WhatsApp transport and reminder tests: isolated SQLite and mocked Meta."""
import importlib
import json
import os
import unittest
from datetime import date, datetime
from io import BytesIO
from unittest.mock import patch
from uuid import uuid4
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

with patch.dict(os.environ, {"DATABASE_URL": "sqlite://", "APP_SECRET": "whatsapp-test"}), patch("dotenv.load_dotenv"):
    api = importlib.import_module("backend.app.main")
wa = api.whatsapp
sms = api.smsapi

ENV = {"WHATSAPP_ACCESS_TOKEN": "test-secret", "WHATSAPP_PHONE_NUMBER_ID": "1234", "WHATSAPP_API_VERSION": "v25.0",
       "WHATSAPP_LINK_TEMPLATE": "space_flow_link", "WHATSAPP_REMINDER_TEMPLATE": "space_flow_reminder",
       "PUBLIC_APP_URL": "https://example.com", "WHATSAPP_AUTO_REMINDERS": "true", "WHATSAPP_TEMPLATE_LANGUAGE": "pl",
       "SMSAPI_ACCESS_TOKEN": "sms-test-secret", "SMSAPI_SENDER": "SpaceFlow"}


class WhatsAppTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, ENV)
        self.env.start()
        self.engine = create_engine("sqlite://")
        api.Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(bind=self.engine)

    def tearDown(self):
        self.engine.dispose()
        self.env.stop()

    def test_phone_requires_country_code(self):
        self.assertEqual(wa.normalize_phone("+48 123-456-789"), "48123456789")
        self.assertEqual(wa.normalize_phone("0048 123456789"), "48123456789")
        for value in (None, "123456789", "+0", "+48hello123456789"):
            with self.assertRaises(wa.WhatsAppError):
                wa.normalize_phone(value)

    def test_config_never_returns_secrets_and_blocks_local_links(self):
        self.assertTrue(wa.configuration()["ready"])
        self.assertNotIn("test-secret", json.dumps(wa.configuration()))
        with patch.dict(os.environ, {"PUBLIC_APP_URL": "http://localhost:5173"}):
            self.assertFalse(wa.configuration()["ready"])

    def test_template_request_and_error_redaction(self):
        with patch.object(wa, "urlopen", return_value=BytesIO(b'{"messages":[{"id":"wamid.test"}]}')) as send:
            self.assertEqual(wa.send_template("+48123456789", "link", ["Anna", "https://example.com"]), "wamid.test")
            payload = json.loads(send.call_args.args[0].data)
            self.assertEqual(payload["to"], "48123456789")
            self.assertEqual(payload["template"]["components"][0]["parameters"][1]["text"], "https://example.com")
            self.assertEqual(send.call_count, 1)
        for cause in (HTTPError("https://example.com", 400, "test-secret", {}, None), URLError("test-secret")):
            with patch.object(wa, "urlopen", side_effect=cause) as send:
                with self.assertRaises(wa.WhatsAppError) as error:
                    wa.send_template("+48123456789", "link", ["Anna", "link"])
                self.assertNotIn("test-secret", str(error.exception))
                self.assertEqual(send.call_count, 1)

    def seed(self):
        with self.sessions() as db:
            client = api.Company(name="Anna", kind="osoba", phone="+48123456789")
            other = api.Company(name="Bez zgody", kind="osoba", phone="+48123456780")
            db.add_all([client, other]); db.flush()
            company_id = client.id
            db.add(api.WhatsAppSubscription(company_id=company_id))
            for owner, day, status in [(client, 11, "planowany"), (client, 11, "wykonany"), (client, 12, "planowany"), (other, 11, "planowany")]:
                db.add(api.Deadline(company_id=owner.id, title="Wizyta", due_date=date(2026, 10, day), status=status, deadline_types=[]))
            hidden = api.DeadlineType(name="Ukryty", name_key="ukryty", client_calendar=False, operator_calendar=True)
            db.add(hidden)
            db.add(api.Deadline(company_id=company_id, title="Operator", due_date=date(2026, 10, 11), status="planowany", deadline_types=["Ukryty"]))
            db.commit()
            return company_id

    def test_automatic_day_before_once_and_only_eligible(self):
        self.seed()
        with patch.object(api, "SessionLocal", self.sessions), patch.object(wa, "send_template", return_value="wamid.test") as send:
            api.whatsapp_run_reminders(datetime(2026, 10, 10, 8))
            send.assert_not_called()
            api.whatsapp_run_reminders(datetime(2026, 10, 10, 9))
            api.whatsapp_run_reminders(datetime(2026, 10, 10, 10))
            self.assertEqual(send.call_count, 1)
            self.assertEqual(send.call_args.args[2][2], "11.10.2026")
            with self.sessions() as db:
                self.assertEqual(db.scalar(select(api.WhatsAppDelivery)).status, "accepted")

    def test_unknown_outcome_not_retried_and_switch_disables_worker(self):
        self.seed()
        with patch.object(api, "SessionLocal", self.sessions), patch.object(wa, "send_template", side_effect=wa.WhatsAppError("Niepotwierdzona")) as send:
            with patch.dict(os.environ, {"WHATSAPP_AUTO_REMINDERS": "false"}):
                api.whatsapp_run_reminders(datetime(2026, 10, 10, 9))
                send.assert_not_called()
            api.whatsapp_run_reminders(datetime(2026, 10, 10, 9))
            api.whatsapp_run_reminders(datetime(2026, 10, 10, 10))
            self.assertEqual(send.call_count, 1)
            with self.sessions() as db:
                self.assertEqual(db.scalar(select(api.WhatsAppDelivery)).status, "unconfirmed")

    def test_duplicate_claim_does_not_send_again(self):
        company_id = self.seed()
        with self.sessions() as db, patch.object(wa, "send_template", return_value="wamid.test") as send:
            company = db.get(api.Company, company_id)
            for _ in range(2):
                api.whatsapp_deliver(db, "same-key", company, "link", "Link", ["Anna", "link"])
            self.assertEqual(send.call_count, 1)

    def test_sms_payload_unicode_and_response(self):
        with patch.object(sms, "urlopen", return_value=BytesIO(b'{"count":1,"list":[{"id":"sms-123","status":"QUEUE"}]}')) as send:
            self.assertEqual(sms.send_message("+48 123456789", "link", ["Łukasz", "https://example.com/#/service/token"]), "sms-123")
            request = send.call_args.args[0]
            payload = parse_qs(request.data.decode())
            self.assertEqual(request.full_url, "https://api.smsapi.pl/sms.do")
            self.assertEqual(payload["to"], ["48123456789"])
            self.assertEqual(payload["from"], ["SpaceFlow"])
            self.assertIn("Łukasz", payload["message"][0])
            self.assertIn("#/service/token", payload["message"][0])
            self.assertEqual(request.get_header("Authorization"), "Bearer sms-test-secret")
            self.assertNotIn("sms-test-secret", request.full_url)
            self.assertNotIn("sms-test-secret", json.dumps(sms.configuration()))

    def test_sms_rejects_http_200_errors_and_unknown_responses_without_retry(self):
        for body in (b'{"error":13,"message":"sms-test-secret"}', b'{"list":[{"id":"x","error":14}]}', b'{"list":[]}', b'not json'):
            with patch.object(sms, "urlopen", return_value=BytesIO(body)) as send:
                with self.assertRaises(sms.SmsApiError) as error:
                    sms.send_message("+48123456789", "link", ["Anna", "link"])
                self.assertNotIn("sms-test-secret", str(error.exception))
                self.assertEqual(send.call_count, 1)
        with patch.object(sms, "urlopen", side_effect=URLError("sms-test-secret")) as send:
            with self.assertRaises(sms.SmsApiError):
                sms.send_message("+48123456789", "link", ["Anna", "link"])
            self.assertEqual(send.call_count, 1)

    def test_default_sms_routes_reminders_and_change_does_not_duplicate(self):
        self.seed()
        with self.sessions() as db:
            db.add(api.NotificationSettings(id=1, default_method="smsapi", automatic=True)); db.commit()
        with patch.object(api, "SessionLocal", self.sessions), patch.object(sms, "send_message", return_value="sms-123") as sms_send, patch.object(wa, "send_template") as wa_send:
            api.whatsapp_run_reminders(datetime(2026, 10, 10, 9))
            sms_send.assert_called_once()
            wa_send.assert_not_called()
            with self.sessions() as db:
                self.assertEqual(db.scalar(select(api.WhatsAppDelivery)).provider, "smsapi")
                db.get(api.NotificationSettings, 1).default_method = "whatsapp"; db.commit()
            api.whatsapp_run_reminders(datetime(2026, 10, 10, 10))
            wa_send.assert_not_called()

    def test_sms_missing_config_does_not_fall_back_to_whatsapp(self):
        self.seed()
        with self.sessions() as db:
            db.add(api.NotificationSettings(id=1, default_method="smsapi", automatic=True)); db.commit()
        with patch.object(api, "SessionLocal", self.sessions), patch.dict(os.environ, {"SMSAPI_ACCESS_TOKEN": ""}), patch.object(wa, "send_template") as send:
            api.whatsapp_run_reminders(datetime(2026, 10, 10, 9))
            send.assert_not_called()
            with self.sessions() as db:
                self.assertIsNone(db.scalar(select(api.WhatsAppDelivery)))

    def test_link_uses_saved_method_and_remains_idempotent(self):
        company_id = self.seed()
        with self.sessions() as db, patch.object(sms, "send_message", return_value="sms-123") as send, patch.object(wa, "send_template") as wa_send:
            db.add(api.NotificationSettings(id=1, default_method="smsapi", automatic=False))
            service = api.ClientService(company_id=company_id, template_id=uuid4(), name="Test")
            db.add(service); db.commit()
            api.create_public_link(service.id, None, db)
            data = api.WhatsAppLinkInput(request_id=uuid4())
            result = api.notification_send_link(service.id, data, None, db)
            self.assertEqual(result["provider"], "smsapi")
            self.assertIn("https://example.com/#/service/", send.call_args.args[2][1])
            db.get(api.NotificationSettings, 1).default_method = "whatsapp"; db.commit()
            self.assertEqual(api.notification_send_link(service.id, data, None, db)["provider"], "smsapi")
            send.assert_called_once()
            wa_send.assert_not_called()
