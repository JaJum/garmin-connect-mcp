"""MCP tool modules for garmin-connect-mcp."""

from __future__ import annotations

from typing import Any

from garmin_connect_mcp.config import AppConfig
from garmin_connect_mcp.tools import (
    activities,
    health,
    profile,
    reports,
    training,
)


def register_data_tools(app: Any, gateway: Any) -> Any:
    """Register the 12 read-only Garmin data tools."""
    profile.register_tools(app, gateway)
    activities.register_tools(app, gateway)
    health.register_tools(app, gateway)
    training.register_tools(app, gateway)
    return app


def register_report_tools(
    app: Any,
    gateway: Any,
    config: AppConfig,
) -> Any:
    """Register the two health report tools."""
    return reports.register_tools(app, gateway, config)


def register_all_tools(
    app: Any,
    gateway: Any,
    config: AppConfig,
) -> Any:
    """Register all first-version tools."""
    register_data_tools(app, gateway)
    register_report_tools(app, gateway, config)
    return app


__all__ = [
    "register_all_tools",
    "register_data_tools",
    "register_report_tools",
]
