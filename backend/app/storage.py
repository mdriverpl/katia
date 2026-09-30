"""Private S3-compatible storage; credentials stay on the API server."""
import os
from functools import lru_cache

import boto3
from botocore.config import Config
from fastapi import HTTPException


def storage_backend():
    backend = os.getenv("FILE_STORAGE", "database").strip().lower()
    if backend not in {"database", "s3"}:
        raise HTTPException(503, "Nieprawidłowa konfiguracja magazynu plików")
    return backend


@lru_cache(maxsize=1)
def s3_client():
    access_key = os.getenv("S3_ACCESS_KEY_ID", "").strip()
    secret_key = os.getenv("S3_SECRET_ACCESS_KEY", "").strip()
    if not access_key or not secret_key:
        raise HTTPException(503, "Uzupełnij konfigurację magazynu S3 na serwerze")
    return boto3.client(
        "s3",
        endpoint_url=os.getenv("S3_ENDPOINT_URL", "https://s3.hostava.pl"),
        region_name=os.getenv("S3_REGION", "auto"),
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
            connect_timeout=5,
            read_timeout=30,
            retries={"mode": "standard", "total_max_attempts": 3},
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required",
        ),
    )


def upload_bucket():
    bucket = os.getenv("S3_BUCKET", "").strip()
    if not bucket:
        raise HTTPException(503, "Uzupełnij nazwę bucketa S3 na serwerze")
    return bucket
