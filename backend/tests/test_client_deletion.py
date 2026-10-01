import importlib
import os
import unittest
from datetime import date, datetime, timezone
from unittest.mock import patch, Mock

from fastapi import HTTPException
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

with patch.dict(os.environ, {"DATABASE_URL": "sqlite://", "APP_SECRET": "client-deletion-test"}), patch("dotenv.load_dotenv"):
    api = importlib.import_module("backend.app.main")


class ClientDeletionTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        api.Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.db.execute(text("PRAGMA foreign_keys=ON"))
        self.client = api.Company(kind="osoba", name="Delete me")
        self.other = api.Company(kind="osoba", name="Keep me")
        self.template = api.Service(name="Shared template", deadline_types=[])
        self.db.add_all([self.client, self.other, self.template])
        self.db.flush()
        self.document = api.Document(company_id=self.client.id, title="Delete document")
        self.other_document = api.Document(company_id=self.other.id, title="Keep document")
        self.service = api.ClientService(company_id=self.client.id, template_id=self.template.id, name="Client service")
        self.db.add_all([self.document, self.other_document, self.service])
        self.db.flush()
        self.db.add_all([
            api.DocumentFile(document_id=self.document.id, name="s3.txt", content=b"", size=1, s3_key="client/file", s3_bucket="test-bucket"),
            api.DocumentFile(document_id=self.document.id, name="local.txt", content=b"x", size=1),
            api.Deadline(company_id=self.client.id, document_id=self.document.id, title="Doc term", due_date=date.today()),
            api.Deadline(company_id=self.client.id, title="Own term", due_date=date.today()),
            api.ServicePublicLink(service_id=self.service.id, company_id=self.client.id, token_hash="hash", token_encrypted="encrypted", expires_at=datetime.now(timezone.utc)),
            api.WhatsAppSubscription(company_id=self.client.id),
            api.WhatsAppDelivery(company_id=self.client.id, key="delivery", kind="reminder", title="Reminder"),
        ])
        self.db.commit()
        self.client_id = self.client.id
        self.other_id = self.other.id
        self.template_id = self.template.id

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_cascade_preserves_other_clients_and_templates(self):
        s3 = Mock()
        with patch.object(api, "s3_client", return_value=s3):
            result = api.delete_company(self.client_id, None, self.db)
        self.assertTrue(result["deleted"])
        self.assertIsNone(result["cleanup_warning"])
        s3.delete_object.assert_called_once_with(Bucket="test-bucket", Key="client/file")
        self.assertIsNone(self.db.get(api.Company, self.client_id))
        self.assertIsNotNone(self.db.get(api.Company, self.other_id))
        self.assertIsNotNone(self.db.get(api.Service, self.template_id))
        self.assertEqual(len(list(self.db.scalars(select(api.Document)))), 1)
        for model in (api.DocumentFile, api.Deadline, api.ClientService, api.ServicePublicLink, api.WhatsAppSubscription, api.WhatsAppDelivery):
            self.assertEqual(list(self.db.scalars(select(model))), [], model.__name__)
        with self.assertRaises(HTTPException) as error:
            api.delete_company(self.client_id, None, self.db)
        self.assertEqual(error.exception.status_code, 404)

    def test_failed_transaction_does_not_delete_s3_objects(self):
        with patch.object(self.db, "commit", side_effect=RuntimeError("database failure")), patch.object(api, "s3_client") as s3:
            with self.assertRaises(RuntimeError):
                api.delete_company(self.client_id, None, self.db)
            self.db.rollback()
            s3.assert_not_called()
        self.assertIsNotNone(self.db.get(api.Company, self.client_id))
        self.assertEqual(len(list(self.db.scalars(select(api.DocumentFile)))), 2)

    def test_s3_failure_returns_cleanup_warning(self):
        with patch.object(api, "s3_client", side_effect=RuntimeError("offline")), self.assertLogs(api.__name__, level="ERROR"):
            result = api.delete_company(self.client_id, None, self.db)
        self.assertTrue(result["deleted"])
        self.assertTrue(result["cleanup_warning"])
