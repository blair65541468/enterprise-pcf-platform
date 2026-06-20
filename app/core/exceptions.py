from dataclasses import dataclass, field
from typing import Any


@dataclass
class DomainError(Exception):
    message: str
    status_code: int = 422
    code: str = "DOMAIN_ERROR"
    details: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.message


class NotFoundError(DomainError):
    def __init__(self, message: str, *, code: str = "NOT_FOUND"):
        super().__init__(message=message, status_code=404, code=code)


class ConflictError(DomainError):
    def __init__(self, message: str, *, code: str = "CONFLICT"):
        super().__init__(message=message, status_code=409, code=code)


class ValidationError(DomainError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "VALIDATION_ERROR",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            status_code=422,
            code=code,
            details=details or {},
        )


class ExternalServiceError(DomainError):
    def __init__(self, message: str, *, code: str = "EXTERNAL_SERVICE_ERROR"):
        super().__init__(message=message, status_code=502, code=code)
