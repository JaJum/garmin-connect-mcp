"""Safe tool-call boundary for MCP tools."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Callable

from garmin_connect_mcp.errors import (
    DataNotFoundError,
    GarminMCPError,
    InvalidArgumentError,
)


def source_name(gateway: Any) -> str:
    """Return a stable, non-sensitive data-source label."""
    return (
        "mock_garmin_gateway"
        if gateway.__class__.__name__ == "MockGarminGateway"
        else "garmin_connect"
    )


def _meta(source: str) -> dict[str, Any]:
    return {
        "source": source,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "request_id": uuid.uuid4().hex,
    }


def success_response(data: Any, *, source: str = "garmin_connect") -> str:
    """Wrap successful tool data in the project response envelope."""
    return json.dumps(
        {"status": "success", "data": data, "meta": _meta(source)},
        ensure_ascii=False,
    )


def error_response(code: str, message: str, *, source: str = "garmin_connect") -> str:
    """Wrap an error in the project response envelope."""
    return json.dumps(
        {
            "status": "error",
            "error": {"code": code, "message": message},
            "meta": _meta(source),
        },
        ensure_ascii=False,
    )


def safe_tool_call(
    handler: Callable[..., Any],
    *args: Any,
    source: str = "garmin_connect",
    **kwargs: Any,
) -> str:
    """Invoke a gateway method and convert all outcomes to stable JSON strings."""
    try:
        data = handler(*args, **kwargs)
    except DataNotFoundError as exc:
        return error_response(exc.code, exc.message, source=source)
    except InvalidArgumentError as exc:
        return error_response(exc.code, exc.message, source=source)
    except GarminMCPError as exc:
        return error_response(exc.code, exc.message, source=source)
    except (ValueError, TypeError) as exc:
        return error_response("INVALID_ARGUMENT", str(exc), source=source)
    except TimeoutError:
        return error_response("TIMEOUT", "The Garmin data request timed out.", source=source)
    except Exception:
        return error_response(
            "UPSTREAM_ERROR",
            "Garmin data request failed.",
            source=source,
        )
    return success_response(data, source=source)


__all__ = ["error_response", "safe_tool_call", "source_name", "success_response"]
