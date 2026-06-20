"""Backward-compatible object storage imports."""

from app.infrastructure.storage import (
    LocalObjectStorage,
    ObjectStorage,
    S3ObjectStorage,
    get_storage,
)

__all__ = [
    "LocalObjectStorage",
    "ObjectStorage",
    "S3ObjectStorage",
    "get_storage",
]
