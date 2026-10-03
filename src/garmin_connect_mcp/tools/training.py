"""Training data MCP tools."""

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
    """Register training tools on the MCP app."""

    @app.tool()
    def get_training_status(date: str) -> str:
        """Return curated Garmin training status for one date."""
        return safe_tool_call(gateway.get_training_status, date, source=source_name(gateway))

    @app.tool()
    def get_training_readiness(date: str) -> str:
        """Return Garmin training readiness for one date."""
        return safe_tool_call(gateway.get_training_readiness, date, source=source_name(gateway))

    @app.tool()
    def get_vo2max_trend(start_date: str, end_date: str) -> str:
        """Return VO2 Max trend points, coverage, and direction."""
        _validate_date_range(start_date, end_date)
        return safe_tool_call(
            gateway.get_vo2max_trend,
            start_date,
            end_date,
            source=source_name(gateway),
        )

    return app
