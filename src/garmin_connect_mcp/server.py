"""FastMCP server for garmin-connect-mcp."""

from __future__ import annotations

import io
import sys

from garmin_connect_mcp.config import AppConfig, load_config
from garmin_connect_mcp.errors import ConfigError
from garmin_connect_mcp.gateway import GarminGateway, create_gateway
from garmin_connect_mcp.tools import register_all_tools

try:
    # MCP 1.x API pinned by pyproject.toml.
    from mcp.server.fastmcp import FastMCP
except ModuleNotFoundError:  # pragma: no cover - compatibility fallback
    try:
        # MCP 2.x renamed FastMCP to MCPServer.
        from mcp.server.mcpserver import MCPServer as FastMCP
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise ModuleNotFoundError(
            "The MCP SDK is unavailable. Run `uv sync` before starting the server."
        ) from exc


TOTAL_TOOL_COUNT = 14


def _load_dotenv_if_available() -> None:
    """Load a local .env file without making dotenv mandatory at import time."""
    try:
        from dotenv import load_dotenv
    except ModuleNotFoundError:
        return
    load_dotenv()


def create_app(config: AppConfig, gateway: GarminGateway) -> FastMCP:
    """Create the MCP app and register all first-version tools."""
    app = FastMCP("Garmin Connect MCP")
    register_all_tools(app, gateway, config)
    return app


def _prepare_stdout_for_stdio() -> None:
    """Keep MCP stdio framing stable on Windows."""
    if sys.platform != "win32":
        return
    try:
        if hasattr(sys.stdout, "buffer"):
            sys.stdout = io.TextIOWrapper(
                sys.stdout.buffer,
                newline="\n",
                write_through=True,
            )
    except (AttributeError, ValueError):  # pragma: no cover - defensive
        pass


def main() -> None:
    """Load configuration, create the gateway, and start the MCP server."""
    _prepare_stdout_for_stdio()
    _load_dotenv_if_available()

    try:
        config = load_config()
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc

    try:
        gateway = create_gateway(config)
    except Exception as exc:
        print(f"Gateway initialization failed: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc

    app = create_app(config, gateway)
    summary = config.redacted_summary()
    print(
        "Garmin Connect MCP starting: "
        f"mode={summary['mode']} "
        f"region={summary['region']} "
        f"transport={summary['transport']} "
        f"tools={TOTAL_TOOL_COUNT}",
        file=sys.stderr,
    )
    app.run(transport=config.transport)


__all__ = ["TOTAL_TOOL_COUNT", "FastMCP", "create_app", "main"]
