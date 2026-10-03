"""Configuration loading and validation for garmin-connect-mcp."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from garmin_connect_mcp.errors import ConfigError

_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
_FALSE_VALUES = frozenset({"0", "false", "no", "off"})
_REPORT_FORMATS = frozenset({"markdown", "html"})
_TRANSPORTS = frozenset({"stdio"})


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Validated runtime configuration.

    Secrets are intentionally excluded from ``redacted_summary()``.
    """

    email: str | None
    password: str | None
    token_dir: Path | None
    token_base64_dir: Path | None
    is_cn: bool
    use_mock: bool
    transport: str
    call_timeout: float
    enabled_tools: frozenset[str]
    disabled_tools: frozenset[str]
    report_dir: Path
    report_default_format: str
    include_visuals: bool
    report_max_days: int

    @property
    def has_credentials(self) -> bool:
        return bool(self.email and self.password)

    def redacted_summary(self) -> dict[str, object]:
        """Return startup-safe configuration without passwords or tokens."""

        return {
            "email": _redact_email(self.email),
            "has_password": self.password is not None,
            "token_dir": str(self.token_dir) if self.token_dir else None,
            "token_base64_dir": (
                str(self.token_base64_dir) if self.token_base64_dir else None
            ),
            "region": "cn" if self.is_cn else "global",
            "mode": "mock" if self.use_mock else "live",
            "transport": self.transport,
            "call_timeout": self.call_timeout,
            "enabled_tools": sorted(self.enabled_tools),
            "disabled_tools": sorted(self.disabled_tools),
            "report_dir": str(self.report_dir),
            "report_default_format": self.report_default_format,
            "include_visuals": self.include_visuals,
            "report_max_days": self.report_max_days,
        }


def _redact_email(email: str | None) -> str | None:
    if not email:
        return None
    if "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    if not local:
        return f"***@{domain}"
    return f"{local[0]}***@{domain}"


def _value(env: Mapping[str, str], key: str) -> str | None:
    raw = env.get(key)
    if raw is None:
        return None
    value = raw.strip()
    return value or None


def _parse_bool(value: str | None, *, key: str, default: bool) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    raise ConfigError(
        f"{key} must be one of true/false/1/0/yes/no/on/off; got {value!r}"
    )


def _parse_float(
    value: str | None,
    *,
    key: str,
    default: float,
    minimum: float,
) -> float:
    if value is None:
        return default
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ConfigError(f"{key} must be a number; got {value!r}") from exc
    if parsed < minimum:
        raise ConfigError(f"{key} must be >= {minimum}; got {parsed}")
    return parsed


def _parse_int(
    value: str | None,
    *,
    key: str,
    default: int,
    minimum: int,
) -> int:
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ConfigError(f"{key} must be an integer; got {value!r}") from exc
    if parsed < minimum:
        raise ConfigError(f"{key} must be >= {minimum}; got {parsed}")
    return parsed


def _parse_choice(
    value: str | None,
    *,
    key: str,
    default: str,
    choices: frozenset[str],
) -> str:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized not in choices:
        allowed = ", ".join(sorted(choices))
        raise ConfigError(f"{key} must be one of: {allowed}; got {value!r}")
    return normalized


def _parse_tool_set(value: str | None, *, key: str) -> frozenset[str]:
    if value is None:
        return frozenset()
    tools = frozenset(item.strip().lower() for item in value.split(",") if item.strip())
    if value.strip() and not tools:
        raise ConfigError(f"{key} must contain at least one tool name")
    return tools


def _read_file_value(path: str, *, key: str) -> str:
    file_path = Path(path).expanduser()
    try:
        content = file_path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise ConfigError(f"Cannot read {key} file: {file_path}") from exc
    if not content:
        raise ConfigError(f"{key} file is empty: {file_path}")
    return content


def _resolve_credentials(
    env: Mapping[str, str],
    *,
    direct_key: str,
    file_key: str,
) -> str | None:
    direct = _value(env, direct_key)
    file_path = _value(env, file_key)
    if direct and file_path:
        raise ConfigError(f"Only one of {direct_key} and {file_key} may be set")
    if file_path:
        return _read_file_value(file_path, key=file_key)
    return direct


def _resolve_path(value: str | None, *, base_dir: Path) -> Path | None:
    if value is None:
        return None
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    return path.resolve(strict=False)


def _ensure_report_is_outside_token_dirs(
    report_dir: Path,
    token_dir: Path | None,
    token_base64_dir: Path | None,
) -> None:
    for protected in (token_dir, token_base64_dir):
        if protected is None:
            continue
        if report_dir == protected or report_dir.is_relative_to(protected):
            raise ConfigError(
                "GARMIN_REPORT_DIR must not be the token directory or a child of it"
            )


def load_config(
    env: Mapping[str, str] | None = None,
    *,
    base_dir: str | Path | None = None,
) -> AppConfig:
    """Load and validate configuration from an environment mapping.

    ``env`` defaults to ``os.environ``. Tests can pass an isolated mapping.
    ``base_dir`` is used to resolve relative paths and defaults to the current
    working directory.
    """

    source = os.environ if env is None else env
    base = Path(base_dir) if base_dir is not None else Path.cwd()
    base = base.expanduser().resolve(strict=False)

    email = _resolve_credentials(
        source, direct_key="GARMIN_EMAIL", file_key="GARMIN_EMAIL_FILE"
    )
    password = _resolve_credentials(
        source, direct_key="GARMIN_PASSWORD", file_key="GARMIN_PASSWORD_FILE"
    )

    token_dir = _resolve_path(_value(source, "GARMINTOKENS"), base_dir=base)
    token_base64_dir = _resolve_path(
        _value(source, "GARMINTOKENS_BASE64"), base_dir=base
    )

    is_cn = _parse_bool(
        _value(source, "GARMIN_IS_CN"), key="GARMIN_IS_CN", default=False
    )
    use_mock = _parse_bool(
        _value(source, "GARMIN_MCP_MOCK"), key="GARMIN_MCP_MOCK", default=False
    )
    transport = _parse_choice(
        _value(source, "GARMIN_MCP_TRANSPORT"),
        key="GARMIN_MCP_TRANSPORT",
        default="stdio",
        choices=_TRANSPORTS,
    )
    call_timeout = _parse_float(
        _value(source, "GARMIN_MCP_CALL_TIMEOUT"),
        key="GARMIN_MCP_CALL_TIMEOUT",
        default=90.0,
        minimum=0.0,
    )
    enabled_tools = _parse_tool_set(
        _value(source, "GARMIN_ENABLED_TOOLS"), key="GARMIN_ENABLED_TOOLS"
    )
    disabled_tools = _parse_tool_set(
        _value(source, "GARMIN_DISABLED_TOOLS"), key="GARMIN_DISABLED_TOOLS"
    )
    if enabled_tools and disabled_tools:
        disabled_tools = frozenset()

    report_dir_value = _value(source, "GARMIN_REPORT_DIR") or "reports"
    report_dir = _resolve_path(report_dir_value, base_dir=base)
    if report_dir is None:  # Defensive: a non-None default is always supplied.
        raise ConfigError("GARMIN_REPORT_DIR could not be resolved")

    report_default_format = _parse_choice(
        _value(source, "GARMIN_REPORT_DEFAULT_FORMAT"),
        key="GARMIN_REPORT_DEFAULT_FORMAT",
        default="markdown",
        choices=_REPORT_FORMATS,
    )
    include_visuals = _parse_bool(
        _value(source, "GARMIN_REPORT_INCLUDE_VISUALS"),
        key="GARMIN_REPORT_INCLUDE_VISUALS",
        default=True,
    )
    report_max_days = _parse_int(
        _value(source, "GARMIN_REPORT_MAX_DAYS"),
        key="GARMIN_REPORT_MAX_DAYS",
        default=31,
        minimum=1,
    )

    _ensure_report_is_outside_token_dirs(report_dir, token_dir, token_base64_dir)

    return AppConfig(
        email=email,
        password=password,
        token_dir=token_dir,
        token_base64_dir=token_base64_dir,
        is_cn=is_cn,
        use_mock=use_mock,
        transport=transport,
        call_timeout=call_timeout,
        enabled_tools=enabled_tools,
        disabled_tools=disabled_tools,
        report_dir=report_dir,
        report_default_format=report_default_format,
        include_visuals=include_visuals,
        report_max_days=report_max_days,
    )


__all__ = ["AppConfig", "load_config"]
