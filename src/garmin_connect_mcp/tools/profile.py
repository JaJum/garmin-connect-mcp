"""User profile and settings MCP tools."""

from __future__ import annotations

from typing import Any

from garmin_connect_mcp.safety import safe_tool_call, source_name


def register_tools(app: Any, gateway: Any) -> Any:
    """Register profile tools on the MCP app."""

    @app.tool()
    def get_profile() -> str:
        """Return safe user profile information from Garmin Connect."""
        return safe_tool_call(gateway.get_profile, source=source_name(gateway))

    @app.tool()
    def get_settings() -> str:
        """Return safe Garmin Connect profile settings and preferences."""
        return safe_tool_call(gateway.get_settings, source=source_name(gateway))

    return app
