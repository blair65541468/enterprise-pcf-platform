import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any


def json_default(value: Any):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    raise TypeError(f"Unsupported JSON type: {type(value)!r}")


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=json_default,
    ).encode("utf-8")


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(item) for item in value]
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    return value


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_payload(value: Any) -> str:
    return sha256_bytes(canonical_json(value))


def as_decimal(value: Any, default: Decimal | None = None) -> Decimal | None:
    if value in (None, ""):
        return default
    return Decimal(str(value))
