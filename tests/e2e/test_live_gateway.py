from __future__ import annotations

import os

import pytest

from garmin_connect_mcp.config import load_config
from garmin_connect_mcp.gateway import create_gateway


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_GARMIN_E2E") != "1",
    reason="Set RUN_GARMIN_E2E=1 to run real Garmin account tests.",
)


def test_live_gateway_profile() -> None:
    config = load_config()
    gateway = create_gateway(config)
    profile = gateway.get_profile()

    assert profile["display_name"]
    assert "password" not in profile
    assert "token" not in profile
