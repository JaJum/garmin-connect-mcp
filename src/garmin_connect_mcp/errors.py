"""Domain exceptions and stable error codes for garmin-connect-mcp."""

from __future__ import annotations

from typing import Any


class GarminMCPError(Exception):
    """Base exception converted into a stable MCP error envelope."""

    code = "INTERNAL_ERROR"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        if code is not None:
            self.code = code

    @property
    def message(self) -> str:
        return str(self)

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message}


class ConfigError(GarminMCPError):
    """Invalid, conflicting, or unsafe configuration."""

    code = "INVALID_ARGUMENT"


class DataNotFoundError(GarminMCPError):
    """Requested Garmin data does not exist."""

    code = "DATA_NOT_FOUND"


class InvalidArgumentError(GarminMCPError):
    """Invalid tool input."""

    code = "INVALID_ARGUMENT"


__all__ = [
    "GarminMCPError",
    "ConfigError",
    "DataNotFoundError",
    "InvalidArgumentError",
]
