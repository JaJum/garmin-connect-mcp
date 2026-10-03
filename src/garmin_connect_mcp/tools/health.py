"""Health data MCP tools."""

from __future__ import annotations

from typing import Any

from garmin_connect_mcp.errors import InvalidArgumentError
from garmin_connect_mcp.safety import safe_tool_call, source_name


def _validate_date_range(start_date: str, end_date: str) -> None:
    if not start_date or not end_date:
        raise InvalidArgumentError("start_date and end_date are required")
    if end_date < start_date:
        raise InvalidArgumentError("end_date must be >= start_date")


def register_tools(app: Any, gateway: Any) -> Any:
    """Register health data tools on the MCP app."""

    @app.tool()
    def get_daily_steps(start_date: str, end_date: str) -> str:
        """Return daily step totals for an inclusive date range."""
        _validate_date_range(start_date, end_date)
        return safe_tool_call(
            gateway.get_daily_steps,
            start_date,
            end_date,
            source=source_name(gateway),
        )

    @app.tool()
    def get_sleep_summary(date: str) -> str:
        """Return a lightweight sleep summary for one date."""
        return safe_tool_call(gateway.get_sleep_summary, date, source=source_name(gateway))

    @app.tool()
    def get_stress_summary(date: str) -> str:
        """Return a lightweight stress summary for one date."""
        return safe_tool_call(gateway.get_stress_summary, date, source=source_name(gateway))

    @app.tool()
    def get_hrv_summary(start_date: str, end_date: str) -> str:
        """Return HRV points, coverage, and trend for a date range."""
        _validate_date_range(start_date, end_date)
        return safe_tool_call(
            gateway.get_hrv_summary,
            start_date,
            end_date,
            source=source_name(gateway),
        )

    @app.tool()
    def get_body_composition(start_date: str, end_date: str) -> str:
        """Return body composition points for an inclusive date range."""
        _validate_date_range(start_date, end_date)
        return safe_tool_call(
            gateway.get_body_composition,
            start_date,
            end_date,
            source=source_name(gateway),
        )

    return app
