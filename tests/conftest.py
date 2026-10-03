from __future__ import annotations

import shutil
import sys
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from garmin_connect_mcp.config import load_config
from garmin_connect_mcp.gateway import MockGarminGateway, create_gateway
from garmin_connect_mcp.server import create_app


@pytest.fixture
def tmp_path() -> Path:
    """Writable test directory that does not use pytest's Windows tmpdir plugin."""
    base = Path.cwd() / ".pytest-work"
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"case-{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def project_root() -> Path:
    return ROOT


@pytest.fixture
def mock_config(tmp_path: Path):
    return load_config(
        {
            "GARMIN_MCP_MOCK": "true",
            "GARMIN_REPORT_DIR": str(tmp_path / "reports"),
        },
        base_dir=tmp_path,
    )


@pytest.fixture
def mock_gateway() -> MockGarminGateway:
    return MockGarminGateway()


@pytest.fixture
def app(mock_config, mock_gateway):
    return create_app(
        mock_config,
        create_gateway(mock_config, mock_gateway=mock_gateway),
    )
