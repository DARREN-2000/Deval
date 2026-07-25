"""Observability dimension: can you see what a running service is doing?

These checks are deliberately conservative. They only assert an expectation
when there is evidence the repository actually is a long-running service (a web
framework import, an ASGI/WSGI entry point, etc.). A library or CLI is not
penalized for lacking service logging.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from ..model import Finding, Severity
from ..registry import CheckContext, check

OFF = Severity.OFF
_SRC = (".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".java", ".rb")

# Signals that the repo runs as a service (and therefore should be observable).
_SERVICE_RE = re.compile(
    r"\b(fastapi|flask|django|starlette|aiohttp|tornado|sanic|express|koa|"
    r"nestjs|gin|echo|fiber|spring|micronaut|rails|sinatra|uvicorn|gunicorn|"
    r"asgi|wsgi)\b",
    re.IGNORECASE,
)

# Signals that structured/logging instrumentation is present.
_LOG_RE = re.compile(
    r"\b(logging\.|getlogger|structlog|loguru|pino|winston|bunyan|zap\.|"
    r"slog\.|log/slog|logrus|zerolog|slf4j|logback|log4j|semantic_logger)\b",
    re.IGNORECASE,
)

_ERROR_TRACK_RE = re.compile(
    r"\b(sentry_sdk|@sentry/|raven|rollbar|bugsnag|honeybadger|airbrake|"
    r"opentelemetry.*(error|exception)|datadog)\b",
    re.IGNORECASE,
)


def _scan_sources(ctx: CheckContext):
    is_service = False
    has_logging = False
    has_error_tracking = False
    for rf in ctx.index.by_suffix(*_SRC):
        text = ctx.index.read_text(rf)
        if not is_service and _SERVICE_RE.search(text):
            is_service = True
        if not has_logging and _LOG_RE.search(text):
            has_logging = True
        if not has_error_tracking and _ERROR_TRACK_RE.search(text):
            has_error_tracking = True
    return is_service, has_logging, has_error_tracking


@check("observable-logging", "observability")
def observable_logging(ctx: CheckContext) -> Iterable[Finding]:
    if not ctx.enabled("observable-logging", OFF):
        return
    is_service, has_logging, _ = _scan_sources(ctx)
    if not is_service:
        # Not a long-running service: the expectation does not apply.
        yield ctx.ok("observable-logging", "observability",
                     "No long-running service detected; logging not required")
        return
    if has_logging:
        yield ctx.ok("observable-logging", "observability",
                     "Service emits logs via a logging framework")
    else:
        yield ctx.fail("observable-logging", "observability",
                       "Service has no structured logging",
                       remediation="Adopt a structured logger and log request lifecycle and errors.")


@check("error-tracking", "observability")
def error_tracking(ctx: CheckContext) -> Iterable[Finding]:
    # Opt-in (OFF by default): enabled by the backend/enterprise profiles.
    if not ctx.enabled("error-tracking", OFF):
        return
    _, _, has_error_tracking = _scan_sources(ctx)
    if has_error_tracking:
        yield ctx.ok("error-tracking", "observability",
                     "Errors are reported to a tracker")
    else:
        yield ctx.fail("error-tracking", "observability",
                       "No error tracking / exception reporting detected",
                       remediation="Integrate Sentry, Rollbar, or OpenTelemetry error reporting.")
