import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.metrics import HTTP_DURATION, HTTP_REQUESTS
from app.core.request_context import bind_context, reset_context

logger = logging.getLogger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        tokens = bind_context(request_id=request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "HTTP request failed",
                extra={"method": request.method, "path": request.url.path},
            )
            reset_context(tokens)
            raise
        route = request.scope.get("route")
        route_path = getattr(route, "path", "unmatched")
        status = str(response.status_code)
        duration = time.perf_counter() - started
        HTTP_REQUESTS.labels(request.method, route_path, status).inc()
        HTTP_DURATION.labels(request.method, route_path).observe(duration)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "HTTP request completed",
            extra={
                "method": request.method,
                "route": route_path,
                "status": status,
                "duration_ms": round(duration * 1000, 3),
            },
        )
        reset_context(tokens)
        return response
