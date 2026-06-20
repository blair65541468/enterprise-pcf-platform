from __future__ import annotations

from pathlib import Path

import boto3

from app.config import settings


class ObjectStorage:
    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        raise NotImplementedError

    def get(self, key: str) -> bytes:
        raise NotImplementedError


class LocalObjectStorage(ObjectStorage):
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        target = (self.root / key).resolve()
        if self.root.resolve() not in target.parents:
            raise ValueError("Invalid object key")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return key

    def get(self, key: str) -> bytes:
        return (self.root / key).read_bytes()


class S3ObjectStorage(ObjectStorage):
    def __init__(self):
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
        )
        self.bucket = settings.s3_bucket
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except Exception:
            self.client.create_bucket(Bucket=self.bucket)

    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type)
        return key

    def get(self, key: str) -> bytes:
        return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()


def get_storage() -> ObjectStorage:
    if settings.object_storage_backend == "s3":
        return S3ObjectStorage()
    return LocalObjectStorage(settings.object_storage_local_dir)

