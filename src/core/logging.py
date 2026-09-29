import logging
import os
import sys
import threading

import httpx
import structlog


def _send_to_datadog_async(event_dict: dict):
    """Dispatches log payload directly to Datadog Logs HTTP Intake API."""
    api_key = os.getenv("DD_API_KEY")
    if not api_key:
        return
    site = os.getenv("DD_SITE", "us5.datadoghq.com")
    url = f"https://http-intake.logs.{site}/api/v2/logs"

    level = str(event_dict.get("level", "info")).lower()
    event_name = str(event_dict.get("event", "log_event"))

    payload = [
        {
            "ddsource": "python",
            "ddtags": f"env:{os.getenv('DD_ENV', 'production')},service:{os.getenv('DD_SERVICE', 'chaos-lab')},version:1.0.0",
            "hostname": "chaos-lab-local",
            "service": os.getenv("DD_SERVICE", "chaos-lab"),
            "status": "error" if level in ("error", "critical") else "warn" if level in ("warn", "warning") else "info",
            "message": f"[{level.upper()}] {event_name}",
            "attributes": {k: v for k, v in event_dict.items() if k not in ("level", "event")},
        }
    ]

    try:
        httpx.post(
            url,
            headers={"Content-Type": "application/json", "DD-API-KEY": api_key},
            json=payload,
            timeout=4.0,
        )
    except Exception:
        pass


def datadog_http_processor(_, __, event_dict: dict) -> dict:
    """Structlog processor forwarding warnings, errors and chaos triggers to Datadog."""
    level = str(event_dict.get("level", "info")).lower()
    if level in ("warn", "warning", "error", "critical") or "chaos" in str(event_dict.get("event", "")).lower():
        threading.Thread(target=_send_to_datadog_async, args=(dict(event_dict),), daemon=True).start()
    return event_dict


def setup_logging():
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            datadog_http_processor,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


logger = structlog.get_logger()
