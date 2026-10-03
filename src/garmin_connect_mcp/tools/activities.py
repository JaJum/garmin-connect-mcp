"""Activity MCP tools."""

from __future__ import annotations

from typing import Any

from garmin_connect_mcp.errors import InvalidArgumentError
from garmin_connect_mcp.safety import safe_tool_call, source_name


def register_tools(app: Any, gateway: Any) -> Any:
    """Register activity tools on the MCP app."""

    @app.tool()
    def get_recent_activities(start: int = 0, limit: int = 20) -> str:
        """List recent activities with pagination support."""
        if start < 0:
            raise InvalidArgumentError("start must be >= 0")
        if limit < 1 or limit > 100:
            raise InvalidArgumentError("limit must be between 1 and 100")
        return safe_tool_call(
            gateway.get_activities,
            start,
            limit,
            source=source_name(gateway),
        )

    @app.tool()
    def get_activity(activity_id: int) -> str:
        """Return a single Garmin activity by numeric activity ID."""
        if isinstance(activity_id, bool) or activity_id <= 0:
            raise InvalidArgumentError("activity_id must be a positive integer")
        return safe_tool_call(
            gateway.get_activity,
            activity_id,
            source=source_name(gateway),
        )

    return app
