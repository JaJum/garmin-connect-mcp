from __future__ import annotations

from pathlib import Path

import pytest

from garmin_connect_mcp.config import ConfigError, load_config


def test_load_config_defaults(tmp_path: Path) -> None:
    config = load_config({}, base_dir=tmp_path)

    assert config.use_mock is False
    assert config.is_cn is False
    assert config.transport == "stdio"
    assert config.call_timeout == 90.0
    assert config.report_dir == (tmp_path / "reports").resolve()
    assert config.report_default_format == "markdown"
    assert config.include_visuals is True
    assert config.report_max_days == 31


def test_bool_choices_and_tool_filters(tmp_path: Path) -> None:
    config = load_config(
        {
            "GARMIN_MCP_MOCK": "YES",
            "GARMIN_IS_CN": "1",
            "GARMIN_REPORT_INCLUDE_VISUALS": "off",
            "GARMIN_ENABLED_TOOLS": "Get_Profile, get_settings",
            "GARMIN_DISABLED_TOOLS": "get_activity",
            "GARMIN_REPORT_MAX_DAYS": "7",
        },
        base_dir=tmp_path,
    )

    assert config.use_mock is True
    assert config.is_cn is True
    assert config.include_visuals is False
    assert config.enabled_tools == frozenset({"get_profile", "get_settings"})
    assert config.disabled_tools == frozenset()
    assert config.report_max_days == 7


def test_invalid_boolean_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="GARMIN_IS_CN"):
        load_config({"GARMIN_IS_CN": "maybe"}, base_dir=tmp_path)


def test_conflicting_credentials_are_rejected(tmp_path: Path) -> None:
    secret_file = tmp_path / "password.txt"
    secret_file.write_text("secret", encoding="utf-8")

    with pytest.raises(ConfigError, match="Only one"):
        load_config(
            {
                "GARMIN_PASSWORD": "inline-secret",
                "GARMIN_PASSWORD_FILE": str(secret_file),
            },
            base_dir=tmp_path,
        )


def test_redacted_summary_does_not_leak_secrets(tmp_path: Path) -> None:
    config = load_config(
        {
            "GARMIN_EMAIL": "person@example.com",
            "GARMIN_PASSWORD": "top-secret",
        },
        base_dir=tmp_path,
    )
    summary_text = str(config.redacted_summary())

    assert "top-secret" not in summary_text
    assert "person@example.com" not in summary_text
    assert config.redacted_summary()["email"] == "p***@example.com"
    assert config.redacted_summary()["has_password"] is True


def test_report_directory_cannot_be_inside_token_directory(tmp_path: Path) -> None:
    token_dir = tmp_path / "tokens"
    token_dir.mkdir()

    with pytest.raises(ConfigError, match="GARMIN_REPORT_DIR"):
        load_config(
            {
                "GARMINTOKENS": str(token_dir),
                "GARMIN_REPORT_DIR": str(token_dir / "reports"),
            },
            base_dir=tmp_path,
        )
