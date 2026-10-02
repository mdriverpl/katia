"""Inbox MIME, IMAP and atomic document import, without external services."""
import importlib
import asyncio
import os
import ssl
import unittest
from email.message import EmailMessage
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

with patch.dict(os.environ, {"DATABASE_URL": "sqlite://", "APP_SECRET": "isolated-inbox-test"}), patch("dotenv.load_dotenv"):
    api = importlib.import_module("backend.app.main")
inbox = api.inbox


def example():
    message = EmailMessage()
    message['From'] = 'Biuro <test@example.com>'
    message['Subject'] = 'Zażółć — dokument'
    message['Date'] = 'Thu, 01 Oct 2026 12:00:00 +0200'
    message.set_content('Treść wiadomości po polsku.')
    message.add_alternative('<p>HTML alternative</p>', subtype='html')
    message.add_attachment(b'%PDF-example', maintype='application', subtype='pdf', filename='zaświadczenie.pdf')
    return message.as_bytes()


class InboxTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://')
        api.Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.company = api.Company(kind='osoba', name='Jan Kowalski')
        self.kind = api.DocumentType(name='Wniosek', name_key='wniosek')
        self.mail = api.EmailMessage(id=uuid4(), message_id='test', **{key: inbox.parse_message(example())[key] for key in ('subject', 'sender', 'received_at')}, preview='test')
        self.db.add_all([self.company, self.kind, self.mail])
        self.db.flush()
        self.db.add(api.InboxContent(email_id=self.mail.id, raw_encrypted=api.fernet.encrypt(example())))
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def data(self, **changes):
        attachment = inbox.parse_message(example())['attachments'][0]['id']
        return inbox.ImportInput(**{'company_id': self.company.id, 'document_type_id': self.kind.id,
                                    'number': 'ABC/2026', 'attachments': [attachment], **changes})

    def test_multipart_charset_and_attachment(self):
        parsed = inbox.parse_message(example())
        self.assertEqual(parsed['subject'], 'Zażółć — dokument')
        self.assertIn('Treść wiadomości', parsed['body'])
        self.assertNotIn('HTML alternative', parsed['body'])
        self.assertEqual(parsed['attachments'][0]['name'], 'zaświadczenie.pdf')
        self.assertEqual(parsed['attachments'][0]['content'], b'%PDF-example')
        self.assertEqual(parsed['received_at'].hour, 12)

    def test_html_only_becomes_inert_text_and_unknown_charset_falls_back(self):
        message = EmailMessage()
        message.set_content('<p>Wniosek</p><script>evil()</script><img src="https://tracking.invalid/a"><style>hidden</style>', subtype='html')
        parsed = inbox.parse_message(message.as_bytes())
        self.assertIn('Wniosek', parsed['body'])
        self.assertNotIn('evil', parsed['body'])
        self.assertNotIn('tracking', parsed['body'])
        self.assertNotIn('hidden', parsed['body'])
        raw = b'Content-Type: text/plain; charset=unknown-charset\r\n\r\nhello'
        self.assertEqual(inbox.parse_message(raw)['body'], 'hello')

    def test_import_creates_document_file_and_prevents_repeat(self):
        with patch.object(api, 'storage_backend', return_value='database'):
            result = inbox.import_document(api, self.db, self.mail.id, self.data())
            document = self.db.get(api.Document, result['id'])
            self.assertEqual(document.number, 'ABC/2026')
            self.assertEqual(document.company_id, self.company.id)
            file = self.db.scalar(select(api.DocumentFile))
            self.assertEqual(file.content, b'%PDF-example')
            with self.assertRaises(HTTPException) as caught:
                inbox.import_document(api, self.db, self.mail.id, self.data())
            self.assertEqual(caught.exception.status_code, 409)
            self.assertEqual(len(self.db.scalars(select(api.Document)).all()), 1)

    def test_storage_failure_rolls_back_document_receipt_and_s3(self):
        client = MagicMock()
        client.put_object.side_effect = RuntimeError('storage unavailable')
        with patch.object(api, 'storage_backend', return_value='s3'), patch.object(api, 's3_client', return_value=client), patch.object(api, 'upload_bucket', return_value='test'):
            with self.assertRaises(RuntimeError):
                inbox.import_document(api, self.db, self.mail.id, self.data())
        client.delete_object.assert_called_once()
        self.assertEqual(self.db.scalars(select(api.Document)).all(), [])
        self.assertEqual(self.db.scalars(select(api.InboxImport)).all(), [])

    def test_invalid_company_type_and_attachment_do_not_create_document(self):
        for data in (self.data(company_id=uuid4()), self.data(document_type_id=uuid4()), self.data(attachments=[999])):
            with self.assertRaises(HTTPException):
                inbox.import_document(api, self.db, self.mail.id, data)
        self.assertEqual(self.db.scalars(select(api.Document)).all(), [])

    def configured_mailbox(self):
        self.db.add(api.InboxSettings(id=1, host='imap.example.com', port=993, username='test@example.com',
                                      use_smtp_password=False, password_encrypted=api.fernet.encrypt(b'test-password').decode()))
        self.db.commit()
        client = MagicMock()
        client.__enter__.return_value = client
        client.login.return_value = ('OK', [])
        client.select.return_value = ('OK', [b'1'])
        client.response.return_value = ('UIDVALIDITY', [b'42'])
        def uid(command, *args):
            if command == 'search':
                return ('OK', [b'11'])
            if args[-1] == '(RFC822.SIZE)':
                return ('OK', [f'1 (UID 11 RFC822.SIZE {len(example())})'.encode()])
            return ('OK', [(b'1 (BODY[]', example()), b')'])
        client.uid.side_effect = uid
        return client

    def test_sync_is_read_only_encrypted_and_idempotent(self):
        client = self.configured_mailbox()
        with patch.object(inbox.imaplib, 'IMAP4_SSL', return_value=client) as connect:
            self.assertEqual(inbox.sync_inbox(api, self.db)['imported'], 1)
            self.assertEqual(inbox.sync_inbox(api, self.db)['imported'], 0)
            self.assertEqual(connect.call_args.kwargs['ssl_context'].verify_mode, ssl.CERT_REQUIRED)
        client.select.assert_called_with('INBOX', readonly=True)
        self.assertTrue(any(call.args[-1] == '(BODY.PEEK[])' for call in client.uid.call_args_list))
        content = self.db.scalars(select(api.InboxContent)).all()
        self.assertEqual(len(content), 2)
        self.assertNotIn(b'%PDF', content[-1].raw_encrypted)
        self.assertTrue(api.fernet.decrypt(content[-1].raw_encrypted))

    def test_start_now_fetches_no_messages_and_sync_only_imports_new_uid(self):
        client = self.configured_mailbox()
        client.response.side_effect = lambda name: (name, [b'42' if name == 'UIDVALIDITY' else b'12'])
        with patch.object(inbox.imaplib, 'IMAP4_SSL', return_value=client):
            result = inbox.start_from_now(api, self.db)
            self.assertIsNotNone(result['sync_from'])
            client.uid.assert_not_called()
            self.assertEqual(self.db.get(api.InboxBoundary, 1).last_uid, 11)
            # Server may return UID 11 for the reversed 12:* range; it must be ignored.
            self.assertEqual(inbox.sync_inbox(api, self.db)['imported'], 0)
            client.uid.assert_called_once_with('search', None, 'UID', '12:*', 'ALL')
            original_uid = client.uid.side_effect
            client.uid.side_effect = lambda command, *args: ('OK', [b'11 12']) if command == 'search' else original_uid(command, *args)
            self.assertEqual(inbox.sync_inbox(api, self.db)['imported'], 1)
        fetched_ids = [call.args[1] for call in client.uid.call_args_list if call.args[0] == 'fetch']
        self.assertEqual(fetched_ids, [b'12', b'12'])
        self.assertIsNotNone(self.db.get(api.EmailMessage, self.mail.id))

    def test_start_now_on_empty_mailbox_allows_first_arrival(self):
        client = self.configured_mailbox()
        client.response.side_effect = lambda name: (name, [b'42' if name == 'UIDVALIDITY' else b'1'])
        with patch.object(inbox.imaplib, 'IMAP4_SSL', return_value=client):
            inbox.start_from_now(api, self.db)
            self.assertEqual(self.db.get(api.InboxBoundary, 1).last_uid, 0)
            self.assertEqual(inbox.sync_inbox(api, self.db)['imported'], 1)

    def test_failed_start_preserves_cutoff_and_uidvalidity_change_blocks_history(self):
        client = self.configured_mailbox()
        with patch.object(inbox.imaplib, 'IMAP4_SSL', return_value=client):
            inbox.start_from_now(api, self.db)
            previous = self.db.get(api.InboxBoundary, 1).last_uid
            client.response.side_effect = lambda name: (name, [b'42' if name == 'UIDVALIDITY' else None])
            with self.assertRaises(HTTPException) as caught:
                inbox.start_from_now(api, self.db)
            self.assertEqual(caught.exception.status_code, 502)
            self.assertEqual(self.db.get(api.InboxBoundary, 1).last_uid, previous)
            client.response.side_effect = lambda name: (name, [b'43'])
            with self.assertRaises(HTTPException) as caught:
                inbox.sync_inbox(api, self.db)
            self.assertEqual(caught.exception.status_code, 409)
            client.uid.assert_not_called()

    def test_oversized_email_is_not_downloaded_or_retried(self):
        client = self.configured_mailbox()
        client.uid.side_effect = [('OK', [b'11']), ('OK', [b'1 (RFC822.SIZE 30000000)']), ('OK', [b'11'])]
        with patch.object(inbox.imaplib, 'IMAP4_SSL', return_value=client):
            self.assertEqual(inbox.sync_inbox(api, self.db)['skipped'], 1)
            self.assertEqual(inbox.sync_inbox(api, self.db)['skipped'], 0)
        self.assertEqual(client.uid.call_count, 3)

    def test_sender_filter_uses_exact_address_and_changes_can_import_previously_filtered_mail(self):
        client = self.configured_mailbox()
        settings = self.db.get(api.InboxSettings, 1)
        settings.sender_filter = 'other@example.com'
        self.db.commit()
        with patch.object(inbox.imaplib, 'IMAP4_SSL', return_value=client):
            result = inbox.sync_inbox(api, self.db)
            self.assertEqual(result['imported'], 0)
            self.assertEqual(result['filtered'], 1)
            self.assertEqual(result['remaining'], 0)
            self.assertEqual(inbox.sync_inbox(api, self.db)['filtered'], 0)
            settings.sender_filter = 'test@example.com'
            self.db.commit()
            self.assertEqual(inbox.sync_inbox(api, self.db)['imported'], 1)
        self.assertTrue(any(call.args == ('search', None, 'FROM', '"test@example.com"') for call in client.uid.call_args_list))

    def test_prefix_blocks_import_and_is_reflected_in_preview(self):
        self.configured_mailbox()
        settings = self.db.get(api.InboxSettings, 1)
        settings.attachment_prefix = 'FV_'
        self.db.commit()
        detail = next(route.endpoint for route in api.app.routes if route.path == '/api/inbox/{email_id}')
        self.assertFalse(detail(self.mail.id, None, self.db)['attachments'][0]['eligible'])
        with self.assertRaises(HTTPException) as caught:
            inbox.import_document(api, self.db, self.mail.id, self.data())
        self.assertEqual(caught.exception.status_code, 400)
        self.assertEqual(self.db.scalars(select(api.Document)).all(), [])
        settings.attachment_prefix = 'ZAŚ'
        self.db.commit()
        self.assertTrue(detail(self.mail.id, None, self.db)['attachments'][0]['eligible'])
        with patch.object(api, 'storage_backend', return_value='database'):
            inbox.import_document(api, self.db, self.mail.id, self.data())
        self.assertEqual(self.db.scalar(select(api.DocumentFile)).name, 'zaświadczenie.pdf')

    def test_filter_validation_and_legacy_settings_updates_preserve_filters(self):
        from pydantic import ValidationError
        for changes in ({'sender_filter': 'bad"address'}, {'sender_filter': 'a@example.com\r\nALL'}, {'attachment_prefix': '../FV'}):
            with self.assertRaises(ValidationError):
                inbox.SettingsInput(host='imap.example.com', username='test@example.com', **changes)
        save = next(route.endpoint for route in api.app.routes if route.path == '/api/settings/inbox' and 'PUT' in route.methods)
        data = inbox.SettingsInput(host='imap.example.com', username='test@example.com', sender_filter=' TEST@EXAMPLE.COM ', attachment_prefix='FV_')
        save(data, None, self.db)
        save(inbox.SettingsInput(host='imap.example.com', username='test@example.com'), None, self.db)
        settings = self.db.get(api.InboxSettings, 1)
        self.assertEqual(settings.sender_filter, 'test@example.com')
        self.assertEqual(settings.attachment_prefix, 'FV_')
        save(data.model_copy(update={'sender_filter': '', 'attachment_prefix': ''}), None, self.db)
        self.assertEqual(settings.sender_filter, '')
        self.assertTrue(inbox.eligible_attachment('anything.pdf', settings.attachment_prefix))

    def test_existing_inbox_settings_migrate_without_losing_credentials(self):
        legacy = create_engine('sqlite://')
        encrypted = api.fernet.encrypt(b'secret-test-password').decode()
        with legacy.begin() as connection:
            connection.execute(text('CREATE TABLE inbox_settings (id INTEGER PRIMARY KEY, host VARCHAR(255) NOT NULL, port INTEGER NOT NULL, username VARCHAR(255) NOT NULL, use_smtp_password BOOLEAN NOT NULL, password_encrypted TEXT)'))
            connection.execute(text("INSERT INTO inbox_settings VALUES (1, 'imap.example.com', 993, 'test@example.com', false, :password)"), {'password': encrypted})
        async def exercise():
            for _ in range(2):
                async with api.lifespan(None):
                    with Session(legacy) as db:
                        settings = db.get(api.InboxSettings, 1)
                        self.assertEqual(settings.sender_filter, '')
                        self.assertEqual(settings.attachment_prefix, '')
                        self.assertEqual(settings.password_encrypted, encrypted)
        try:
            with patch.object(api, 'engine', legacy), patch.object(api, 'SessionLocal', lambda: Session(legacy)), patch.object(api, 'whatsapp_loop', AsyncMock()):
                asyncio.run(exercise())
        finally:
            legacy.dispose()

    def test_failed_imap_response_is_not_silently_accepted(self):
        client = self.configured_mailbox()
        client.select.return_value = ('NO', [b'private error'])
        with patch.object(inbox.imaplib, 'IMAP4_SSL', return_value=client):
            with self.assertRaises(HTTPException) as caught:
                inbox.sync_inbox(api, self.db)
        self.assertEqual(caught.exception.status_code, 502)
        self.assertNotIn('private', caught.exception.detail)
        client.__exit__.assert_called_once()

    def test_route_permissions_and_settings_secret_roundtrip(self):
        paths = {route.path: route for route in api.app.routes if hasattr(route, 'dependant') and 'GET' in (route.methods or set())}
        self.assertIn(api.admin_user, [dep.call for dep in paths['/api/settings/inbox'].dependant.dependencies])
        self.assertIn(api.current_user, [dep.call for dep in paths['/api/inbox/{email_id}'].dependant.dependencies])
        start_route = next(route for route in api.app.routes if route.path == '/api/settings/inbox/start-now')
        self.assertIn(api.admin_user, [dep.call for dep in start_route.dependant.dependencies])
        save = next(route.endpoint for route in api.app.routes if route.path == '/api/settings/inbox' and 'PUT' in route.methods)
        data = inbox.SettingsInput(host='speed.home.pl', username='test@example.com', use_smtp_password=False, password=' test-pass ')
        save(data, None, self.db)
        row = self.db.get(api.InboxSettings, 1)
        self.assertNotEqual(row.password_encrypted, 'test-pass')
        save(data.model_copy(update={'password': None}), None, self.db)
        self.assertEqual(api.fernet.decrypt(row.password_encrypted.encode()), b' test-pass ')
        with patch.object(inbox, 'smtp_values', return_value={}):
            view = inbox.settings_view(api, self.db)
        self.assertNotIn('password', view)
        self.assertNotIn('password_encrypted', view)
        self.assertTrue(view['password_set'])
