"""Account delivery, SMTP secrets and role invariants on isolated SQLite."""
import importlib
import asyncio
import os
import unittest
from unittest.mock import patch, MagicMock, AsyncMock

from fastapi import HTTPException
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

with patch.dict(os.environ, {"DATABASE_URL": "sqlite://", "APP_SECRET": "isolated-account-tests"}), patch("dotenv.load_dotenv"):
    api = importlib.import_module("backend.app.main")


class UserTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        api.Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.admin = api.User(email="admin@example.com", role="admin", password_hash=api.password_hash("old-password-123"))
        self.db.add(self.admin)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_creation_sends_generated_password_and_returns_no_secrets(self):
        with patch.object(api.account_mail, "send_welcome") as send:
            user = api.add_user(api.UserInput(email="Employee@Example.com"), self.admin, self.db)
        address, password, config = send.call_args.args
        self.assertEqual(address, "employee@example.com")
        self.assertGreaterEqual(len(password), 20)
        self.assertTrue(api.password_matches(password, user.password_hash))
        self.assertTrue(user.must_change_password)
        self.assertEqual(user.role, "employee")
        self.assertNotIn("password_hash", api.UserOutput.model_validate(user).model_dump())
        with self.assertRaises(HTTPException) as error:
            api.current_user(user)
        self.assertEqual(error.exception.status_code, 403)
        api.change_password(api.PasswordInput(current_password=password, new_password="my-new-password-123"), user, self.db)
        self.assertFalse(user.must_change_password)
        self.assertEqual(user.token_version, 1)
        with self.assertRaises(HTTPException) as error:
            api.admin_user(user)
        self.assertEqual(error.exception.status_code, 403)

    def test_existing_users_migrate_and_deleted_bootstrap_is_not_recreated(self):
        legacy = create_engine("sqlite://")
        with legacy.begin() as connection:
            connection.execute(text("CREATE TABLE users (id CHAR(32) PRIMARY KEY, email VARCHAR(255) UNIQUE, password_hash VARCHAR(256))"))
            for address in ("admin@tms.local", "existing@example.com"):
                connection.execute(text("INSERT INTO users VALUES (:id, :email, :password)"),
                                   {"id": api.uuid4().hex, "email": address, "password": self.admin.password_hash})
        async def exercise():
            async with api.lifespan(None):
                with Session(legacy) as db:
                    admin = db.scalar(select(api.User).where(api.User.email == "admin@tms.local"))
                    worker = db.scalar(select(api.User).where(api.User.email == "existing@example.com"))
                    self.assertEqual(admin.role, "admin")
                    self.assertEqual(worker.role, "employee")
                    self.assertFalse(admin.blocked)
                    self.assertEqual(admin.token_version, 0)
                    worker.role = "admin"
                    db.delete(admin)
                    db.commit()
            async with api.lifespan(None):
                with Session(legacy) as db:
                    self.assertIsNone(db.scalar(select(api.User).where(api.User.email == "admin@tms.local")))
                    self.assertEqual(db.scalar(select(api.User)).role, "admin")
        try:
            with patch.object(api, "engine", legacy), patch.object(api, "SessionLocal", lambda: Session(legacy)), patch.object(api, "whatsapp_loop", AsyncMock()):
                asyncio.run(exercise())
        finally:
            legacy.dispose()

    def test_failed_mail_rolls_back_account(self):
        with patch.object(api.account_mail, "send_welcome", side_effect=RuntimeError("secret-smtp-password")):
            with self.assertRaises(HTTPException) as error:
                api.add_user(api.UserInput(email="fail@example.com"), self.admin, self.db)
        self.assertEqual(error.exception.status_code, 502)
        self.assertNotIn("secret-smtp-password", error.exception.detail)
        self.assertIsNone(self.db.scalar(select(api.User).where(api.User.email == "fail@example.com")))

    def test_duplicate_email_does_not_send_mail(self):
        with patch.object(api.account_mail, "send_welcome") as send:
            with self.assertRaises(HTTPException) as error:
                api.add_user(api.UserInput(email="ADMIN@example.com"), self.admin, self.db)
        self.assertEqual(error.exception.status_code, 409)
        send.assert_not_called()

    def test_self_delete_and_block_are_rejected(self):
        for action in [lambda: api.delete_user(self.admin.id, self.admin, self.db),
                       lambda: api.update_user(self.admin.id, api.UserUpdate(role="employee", blocked=True), self.admin, self.db)]:
            with self.assertRaises(HTTPException) as error:
                action()
            self.assertEqual(error.exception.status_code, 400)

    def test_smtp_settings_encrypt_preserve_and_clear_password(self):
        data = dict(host="smtp.example.com", port=587, sender="sender@example.com", username="sender", public_url="https://panel.example.com")
        api.save_mail_settings(api.MailSettingsInput(**data, password="smtp-test-secret"), self.admin, self.db)
        record = self.db.get(api.MailSettings, 1)
        self.assertNotIn("smtp-test-secret", record.password_encrypted)
        self.assertEqual(api.mail_config(self.db)["SMTP_PASSWORD"], "smtp-test-secret")
        output = api.get_mail_settings(self.admin, self.db)
        self.assertTrue(output["password_set"])
        self.assertNotIn("password", output)
        self.assertNotIn("password_encrypted", output)
        api.save_mail_settings(api.MailSettingsInput(**data), self.admin, self.db)
        self.assertEqual(api.mail_config(self.db)["SMTP_PASSWORD"], "smtp-test-secret")
        api.save_mail_settings(api.MailSettingsInput(**data, password=""), self.admin, self.db)
        self.assertFalse(api.get_mail_settings(self.admin, self.db)["password_set"])

    def test_smtp_uses_tls_and_configured_sender(self):
        config = {"SMTP_HOST": "smtp.example.com", "SMTP_PORT": 587, "SMTP_SECURITY": "starttls",
                  "SMTP_USERNAME": "sender", "SMTP_PASSWORD": "smtp-secret", "SMTP_FROM": "sender@example.com",
                  "PUBLIC_APP_URL": "https://panel.example.com"}
        smtp = MagicMock()
        smtp.__enter__.return_value = smtp
        smtp.send_message.return_value = {}
        with patch.object(api.account_mail.smtplib, "SMTP", return_value=smtp):
            api.account_mail.send_welcome("user@example.com", "temporary-pass", config)
        smtp.starttls.assert_called_once()
        smtp.login.assert_called_once_with("sender", "smtp-secret")
        message = smtp.send_message.call_args.args[0]
        self.assertEqual(message["To"], "user@example.com")
        self.assertIn("temporary-pass", message.get_content())
        self.assertIn("https://panel.example.com", message.get_content())
