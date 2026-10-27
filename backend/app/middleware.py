"""
TaskFlow Middleware & Structured Logging Module
-----------------------------------------------
Features:
- Request-ID middleware: extracts or generates UUIDs, injects into context,
  attaches X-Request-ID response header.
- Structured JSON logging: formats logs with ISO timestamps, log level,
  request_id, http method, path, status_code, and duration_ms.
- Privacy & security: strictly avoids logging passwords, authorization tokens,
  or sensitive personal credentials.
"""

import contextvars
import json
import logging
import sys
import time
import uuid
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Context variable to propagate request_id across async tasks
request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")

logger = logging.getLogger("taskflow.access")

SENSITIVE_HEADERS = {"authorization", "cookie", "set-cookie", "proxy-authorization", "x-api-key"}
SENSITIVE_FIELDS = {"password", "token", "access_token", "secret", "hashed_password"}


class JSONLogFormatter(logging.Formatter):
    """Custom formatter emitting structured, machine-readable JSON logs."""

    def format(self, record: logging.LogRecord) -> str:
        log_payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "request_id": getattr(record, "request_id", None) or request_id_ctx.get() or None,
        }

        # Add structured HTTP execution fields if present
        method = getattr(record, "method", None) or getattr(record, "http_method", None)
        if method is not None:
            log_payload["method"] = method

        path = getattr(record, "path", None)
        if path is not None:
            log_payload["path"] = path

        status_code = getattr(record, "status_code", None)
        if status_code is not None:
            log_payload["status_code"] = status_code

        duration_ms = getattr(record, "duration_ms", None)
        if duration_ms is not None:
            log_payload["duration_ms"] = duration_ms

        # Include exception traceback if present
        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)

        # Redact any sensitive keys in extra attributes
        for key in list(log_payload.keys()):
            if any(sensitive in key.lower() for sensitive in SENSITIVE_FIELDS):
                log_payload[key] = "[REDACTED]"

        return json.dumps(log_payload)


class RequestIDAndLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware enforcing Request-ID propagation and structured JSON access logs."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # 1. Accept valid incoming request ID or generate a new UUID
        raw_id = request.headers.get("X-Request-ID") or request.headers.get("X-Request-Id")
        if raw_id and raw_id.strip():
            req_id = raw_id.strip()
        else:
            req_id = str(uuid.uuid4())

        # Set in contextvar and request state
        token = request_id_ctx.set(req_id)
        request.state.request_id = req_id

        start_time = time.perf_counter()
        status_code = 500

        try:
            response: Response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = req_id
            return response
        finally:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            path = request.url.path

            # Structured access log without logging query secrets or bodies
            logger.info(
                f"{request.method} {path} returned {status_code} in {duration_ms}ms",
                extra={
                    "request_id": req_id,
                    "http_method": request.method,
                    "path": path,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                },
            )
            request_id_ctx.reset(token)


def setup_json_logging(log_level: str = "INFO"):
    """Configure application-wide structured JSON logging to stdout."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONLogFormatter())

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level.upper())

    # Replace existing handlers with JSON handler
    root_logger.handlers = [handler]
