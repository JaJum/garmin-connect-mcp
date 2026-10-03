from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from garmin_connect_mcp.server import TOTAL_TOOL_COUNT


EXPECTED_TOOLS = {
    "get_profile",
    "get_settings",
    "get_recent_activities",
    "get_activity",
    "get_daily_steps",
    "get_sleep_summary",
    "get_stress_summary",
    "get_hrv_summary",
    "get_body_composition",
    "get_training_status",
    "get_training_readiness",
    "get_vo2max_trend",
    "generate_health_daily_report",
    "generate_health_weekly_report",
}


def _call_tool(app: Any, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    result = asyncio.run(app.call_tool(name, arguments))
    if (
        isinstance(result, tuple)
        and len(result) > 1
        and isinstance(result[1], dict)
        and "result" in result[1]
    ):
        return json.loads(result[1]["result"])
    content = result[0] if isinstance(result, tuple) else result
    return json.loads(content[0].text)


def test_tools_list_registers_final_tool_set(app) -> None:
    tools = asyncio.run(app.list_tools())
    names = {tool.name for tool in tools}

    assert len(tools) == TOTAL_TOOL_COUNT == 14
    assert names == EXPECTED_TOOLS


def test_all_data_tools_can_be_called_with_mock_gateway(app) -> None:
    calls = [
        ("get_profile", {}),
        ("get_settings", {}),
        ("get_recent_activities", {"start": 0, "limit": 2}),
        ("get_activity", {"activity_id": 100001}),
        (
            "get_daily_steps",
            {"start_date": "2026-11-01", "end_date": "2026-11-02"},
        ),
        ("get_sleep_summary", {"date": "2026-11-02"}),
        ("get_stress_summary", {"date": "2026-11-02"}),
        (
            "get_hrv_summary",
            {"start_date": "2026-11-01", "end_date": "2026-11-02"},
        ),
        (
            "get_body_composition",
            {"start_date": "2026-11-01", "end_date": "2026-11-02"},
        ),
        ("get_training_status", {"date": "2026-11-02"}),
        ("get_training_readiness", {"date": "2026-11-02"}),
        (
            "get_vo2max_trend",
            {"start_date": "2026-11-01", "end_date": "2026-11-02"},
        ),
    ]

    for tool_name, arguments in calls:
        payload = _call_tool(app, tool_name, arguments)
        assert payload["status"] == "success", (tool_name, payload)
        assert payload["meta"]["request_id"]


def test_missing_activity_returns_error_envelope(app) -> None:
    payload = _call_tool(app, "get_activity", {"activity_id": 999999})

    assert payload["status"] == "error"
    assert payload["error"]["code"] == "DATA_NOT_FOUND"


def test_generate_daily_report_writes_file(app, tmp_path: Path) -> None:
    output_dir = tmp_path / "generated"
    payload = _call_tool(
        app,
        "generate_health_daily_report",
        {
            "date": "2026-11-02",
            "output_format": "html",
            "include_visuals": True,
            "output_dir": str(output_dir),
        },
    )

    assert payload["status"] == "success"
    assert payload["data"]["format"] == "html"
    report_path = Path(payload["data"]["path"])
    assert report_path.exists()
    assert report_path.parent == output_dir.resolve()
    assert report_path.stat().st_size > 1000
    assert payload["data"]["coverage"]["expected_days"] == 1


def test_generate_weekly_report_writes_markdown(app, tmp_path: Path) -> None:
    output_dir = tmp_path / "generated"
    payload = _call_tool(
        app,
        "generate_health_weekly_report",
        {
            "start_date": "2026-10-27",
            "end_date": "2026-11-02",
            "output_format": "markdown",
            "include_visuals": True,
            "output_dir": str(output_dir),
        },
    )

    assert payload["status"] == "success"
    report_path = Path(payload["data"]["path"])
    markdown = report_path.read_text(encoding="utf-8")
    assert markdown.startswith("# Garmin 健康周报")
    assert "不构成医学诊断" in markdown
    assert payload["data"]["coverage"]["expected_days"] == 7
