from __future__ import annotations

import json

from garmin_connect_mcp.errors import DataNotFoundError
from garmin_connect_mcp.safety import error_response, safe_tool_call, success_response


def test_success_response_envelope() -> None:
    payload = json.loads(success_response({"value": 1}, source="mock"))

    assert payload["status"] == "success"
    assert payload["data"] == {"value": 1}
    assert payload["meta"]["source"] == "mock"
    assert payload["meta"]["request_id"]


def test_data_not_found_is_mapped() -> None:
    def handler() -> None:
        raise DataNotFoundError("missing item")

    payload = json.loads(safe_tool_call(handler, source="mock"))

    assert payload["status"] == "error"
    assert payload["error"]["code"] == "DATA_NOT_FOUND"
    assert payload["error"]["message"] == "missing item"


def test_value_error_maps_to_invalid_argument() -> None:
    def handler() -> None:
        raise ValueError("bad date")

    payload = json.loads(safe_tool_call(handler, source="mock"))

    assert payload["status"] == "error"
    assert payload["error"]["code"] == "INVALID_ARGUMENT"
    assert payload["error"]["message"] == "bad date"


def test_generic_errors_do_not_leak_details() -> None:
    def handler() -> None:
        raise RuntimeError("Authorization: Bearer secret-token")

    payload = json.loads(safe_tool_call(handler, source="mock"))

    assert payload["status"] == "error"
    assert payload["error"]["code"] == "UPSTREAM_ERROR"
    assert "secret-token" not in json.dumps(payload)


def test_error_response_shape() -> None:
    payload = json.loads(error_response("TIMEOUT", "too slow", source="mock"))

    assert payload == {
        "status": "error",
        "error": {"code": "TIMEOUT", "message": "too slow"},
        "meta": payload["meta"],
    }
    assert payload["meta"]["source"] == "mock"
