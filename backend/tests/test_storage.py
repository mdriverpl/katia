"""S3 contract and upload rollback tests; no external bucket or database access."""
import importlib
from io import BytesIO
import os
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

from botocore.exceptions import ClientError
from botocore.response import StreamingBody
from botocore.stub import Stubber
from fastapi import HTTPException, UploadFile
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

with patch.dict(os.environ, {"DATABASE_URL": "sqlite://", "APP_SECRET": "s3-isolated-test-secret"}), patch("dotenv.load_dotenv"):
    api = importlib.import_module("backend.app.main")
storage = importlib.import_module("backend.app.storage")


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        api.Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.document = api.Document(company_id=uuid4(), title="Test", status="nowy")
        self.db.add(self.document)
        self.db.commit()
        self.client = Mock()
        self.patches = [patch.object(api, "storage_backend", return_value="s3"), patch.object(api, "s3_client", return_value=self.client), patch.object(api, "upload_bucket", return_value="katias3")]
        for item in self.patches:
            item.start()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.db.close()
        self.engine.dispose()

    def upload(self, *contents):
        files = [UploadFile(filename=f"test-{index}.txt", file=BytesIO(content)) for index, content in enumerate(contents)]
        return api.upload_files(self.document.id, files, None, self.db)

    def test_delete_document_removes_s3_and_database_files(self):
        self.upload(b"delete me")
        document_id = self.document.id
        result = api.delete_document(document_id, None, self.db)
        self.assertTrue(result["deleted"])
        self.assertIsNone(result["cleanup_warning"])
        self.client.delete_object.assert_called_once()
        self.assertIsNone(self.db.get(api.Document, document_id))
        self.assertEqual(list(self.db.scalars(select(api.DocumentFile))), [])

    def test_delete_reports_s3_cleanup_failure(self):
        self.upload(b"delete me")
        self.client.delete_object.side_effect = RuntimeError("offline")
        with self.assertLogs(api.__name__, level="ERROR"):
            result = api.delete_document(self.document.id, None, self.db)
        self.assertTrue(result["deleted"])
        self.assertTrue(result["cleanup_warning"])

    def test_s3_round_trip_and_legacy_database_file(self):
        attachment = self.upload(b"hello")[0]
        self.assertEqual(attachment.content, b"")
        self.assertEqual(attachment.size, 5)
        self.assertEqual(attachment.s3_bucket, "katias3")
        self.client.put_object.assert_called_once_with(Bucket="katias3", Key=attachment.s3_key, Body=b"hello", ContentType="application/octet-stream")
        self.assertNotIn("s3_key", api.DocumentFileOutput.model_validate(attachment).model_dump())
        body = StreamingBody(BytesIO(b"hello"), 5)
        self.client.get_object.return_value = {"Body": body}
        response = api.download_file(self.document.id, attachment.id, None, self.db)
        self.assertEqual(response.body, b"hello")
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.client.get_object.assert_called_once_with(Bucket="katias3", Key=attachment.s3_key)
        legacy = api.DocumentFile(document_id=self.document.id, name="old.txt", content=b"old", size=3)
        self.db.add(legacy)
        self.db.commit()
        self.assertEqual(api.download_file(self.document.id, legacy.id, None, self.db).body, b"old")

    def test_failed_batch_rolls_back_and_removes_objects(self):
        self.client.put_object.side_effect = [None, ClientError({"Error": {"Code": "AccessDenied"}}, "PutObject")]
        with self.assertRaises(HTTPException) as error:
            self.upload(b"one", b"two")
        self.assertEqual(error.exception.status_code, 502)
        self.assertEqual(self.client.delete_object.call_count, 2)
        self.assertEqual(list(self.db.scalars(select(api.DocumentFile))), [])

    def test_database_failure_cleans_up_s3(self):
        with patch.object(self.db, "commit", side_effect=RuntimeError("database failed")):
            with self.assertRaises(RuntimeError):
                self.upload(b"one")
        self.client.delete_object.assert_called_once()
        self.assertEqual(list(self.db.scalars(select(api.DocumentFile))), [])

    def test_validation_happens_before_upload(self):
        with self.assertRaises(HTTPException) as error:
            self.upload(b"one", b"x" * (20 * 1024 * 1024 + 1))
        self.assertEqual(error.exception.status_code, 413)
        self.client.put_object.assert_not_called()

    def test_client_configuration_and_missing_credentials(self):
        storage.s3_client.cache_clear()
        self.addCleanup(storage.s3_client.cache_clear)
        with patch.dict(os.environ, {"S3_ACCESS_KEY_ID": "test-key", "S3_SECRET_ACCESS_KEY": "test-secret", "S3_ENDPOINT_URL": "https://s3.hostava.pl", "S3_REGION": "auto"}):
            client = storage.s3_client()
            self.assertEqual(client.meta.endpoint_url, "https://s3.hostava.pl")
            self.assertEqual(client.meta.region_name, "auto")
            self.assertEqual(client.meta.config.s3["addressing_style"], "path")
            with Stubber(client) as stub:
                params = {"Bucket": "katias3", "Key": "test/key", "Body": b"test", "ContentType": "application/octet-stream"}
                stub.add_response("put_object", {}, params)
                client.put_object(**params)
                stub.assert_no_pending_responses()
        storage.s3_client.cache_clear()
        with patch.dict(os.environ, {"S3_ACCESS_KEY_ID": "", "S3_SECRET_ACCESS_KEY": ""}):
            with self.assertRaises(HTTPException) as error:
                storage.s3_client()
            self.assertEqual(error.exception.status_code, 503)


if __name__ == "__main__":
    unittest.main()
