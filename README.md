<div align="center">

# garmin-connect-mcp

**A modular, testable Garmin Connect MCP Server**

Bring sleep, heart rate, stress, and training data from your Garmin watch into any MCP-capable AI assistant, and generate visual daily and weekly health reports.

[![CI](https://github.com/JaJum/garmin-connect-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/JaJum/garmin-connect-mcp/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-Server-2E7D32)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-4CAF50.svg)](LICENSE)

<img src="https://www.garmin.com.cn/m/cn/g/banner/87582-1-D.jpg" alt="Athlete trail running with a Garmin watch" width="720">

</div>

---

## Table of Contents

- [Why This Project](#why-this-project)
- [Feature Overview](#feature-overview)
- [Quick Start](#quick-start)
- [Connecting an MCP Client](#connecting-an-mcp-client)
- [Tool List](#tool-list)
- [Health Reports](#health-reports)
- [Security Design](#security-design)
- [Testing](#testing)
- [Documentation](#documentation)
- [Acknowledgements](#acknowledgements)

---

## Why This Project

Most Garmin MCP implementations are thin wrappers around the API. This project focuses on **engineering quality**:

- **Ready out of the box** — start with a single command; 14 tools register automatically; try everything in mock mode without a real account
- **Reports as a product** — not just JSON responses, but daily/weekly reports with charts that open directly in your browser
- **Clear security boundaries** — read-only design, credential redaction, and token directory protection; sensitive data never appears in logs
- **Proven by tests** — three test layers (unit + integration + end-to-end), verified on Python 3.10 through 3.13 via GitHub Actions

---

## Feature Overview

<table>
<tr>
<td width="50%" valign="top">

**📊 14 Data Tools**

Profile, activities, steps, sleep, stress, HRV, body composition, training status, training readiness, and VO2max trends — all read-only and safe.

</td>
<td width="50%" valign="top">

**📈 Daily / Weekly Health Reports**

Data coverage, trend analysis, and anomaly alerts. Outputs Markdown or self-contained HTML+SVG reports with zero external dependencies.

</td>
</tr>
<tr>
<td width="50%" valign="top">

**🔐 Two Authentication Modes**

Username/password or token authentication, with Garmin China region support. Credentials can be injected via environment variables or files.

</td>
<td width="50%" valign="top">

**🧪 Mock Mode**

Set `GARMIN_MCP_MOCK=true` to run without a real account, so CI and demos never depend on external services.

</td>
</tr>
</table>

<div align="center">
<img src="https://connect.garmin.cn/_astro/screen-glance.CVT5xs6m.png" alt="Garmin Connect glance dashboard" width="220">
<img src="https://connect.garmin.cn/_astro/screen-activity.CrYaN3pL.png" alt="Garmin Connect activity history screen" width="220">
<img src="https://connect.garmin.cn/_astro/screen-phone-myday.CMAP1jie.png" alt="Garmin Connect mobile today view" width="220">
<br>
<sub>Data source: Official Garmin Connect app</sub>
</div>

---

## Quick Start

**1. Install**

```bash
git clone https://github.com/JaJum/garmin-connect-mcp.git
cd garmin-connect-mcp
uv sync
```

**2. Configure**

Create a `.env` file in the project root (or set environment variables directly):

```bash
GARMIN_EMAIL=your@email.com
GARMIN_PASSWORD=your-password
GARMIN_IS_CN=true          # Required for China region accounts
```

> Just want to try it out? Set `GARMIN_MCP_MOCK=true` to skip a real account and explore every feature with simulated data.

**3. Run**

```bash
uv run garmin-connect-mcp
```

The startup log shows the running mode (`mock` / `live`), the region, and the number of registered tools.

<details>
<summary><b>All Configuration Options</b></summary>

| Variable | Description | Required |
|---|---|---|
| `GARMIN_EMAIL` | Garmin account email | One of the pair |
| `GARMIN_PASSWORD` | Garmin account password | One of the pair |
| `GARMIN_EMAIL_FILE` / `GARMIN_PASSWORD_FILE` | Read credentials from a file (more secure) | One of the pair |
| `GARMINTOKENS` | Token authentication directory (alternative to username/password) | One of the pair |
| `GARMINTOKENS_BASE64` | Base64-encoded token directory | No |
| `GARMIN_IS_CN` | `true` to use Garmin China region | No |
| `GARMIN_REPORT_DIR` | Report output directory (default `./reports`) | No |
| `GARMIN_MCP_MOCK` | `true` to enable mock mode; no real account needed | No |

</details>

---

## Connecting an MCP Client

Using Claude Desktop's `claude_desktop_config.json` as an example:

```json
{
  "mcpServers": {
    "garmin-connect-mcp": {
      "command": "uv",
      "args": ["--directory", "C:/path/to/garmin-connect-mcp", "run", "garmin-connect-mcp"],
      "env": {
        "GARMIN_EMAIL": "your@email.com",
        "GARMIN_PASSWORD": "your-password",
        "GARMIN_IS_CN": "true"
      }
    }
  }
}
```

Any client that supports the MCP stdio transport (Cursor, Windsurf, etc.) can connect the same way.

---

## Tool List

| Category | Tool | Description |
|---|---|---|
| Profile | `get_profile` | Basic athlete profile |
| Profile | `get_settings` | Account settings |
| Activity | `get_recent_activities` | Recent activity list |
| Activity | `get_activity` | Single activity details |
| Activity | `get_daily_steps` | Daily step count |
| Health | `get_sleep_summary` | Sleep summary |
| Health | `get_stress_summary` | Stress summary |
| Health | `get_hrv_summary` | HRV summary |
| Health | `get_body_composition` | Body composition |
| Training | `get_training_status` | Training status |
| Training | `get_training_readiness` | Training readiness |
| Training | `get_vo2max_trend` | VO2max trend |
| Report | `generate_health_daily_report` | Generate a daily health report |
| Report | `generate_health_weekly_report` | Generate a weekly health report |

---

## Health Reports

The report engine automatically computes data coverage, draws trend charts, and flags anomalous metrics:

<div align="center">
<img src="https://connect.garmin.cn/_astro/screen-coach.rqWAXvey.png" alt="Garmin Connect coaching view" width="260">
<img src="https://connect.garmin.cn/_astro/devices.86mv_XfL.png" alt="Garmin device ecosystem" width="300">
</div>

- **Output formats**: Markdown, or self-contained HTML+SVG (directly shareable, no internet required)
- **Daily report**: single-day sleep, resting heart rate, HRV, stress, training load, steps + trend charts
- **Weekly report**: 7-day aggregation, per-day detail table, anomaly alerts, data quality assessment
- **Output directory**: `reports/` under the project by default (already in `.gitignore`, so health data is never committed)

---

## Security Design

- **Read-only toolset** — no operations that modify Garmin data are provided
- **Credential redaction** — passwords and tokens never appear in logs, error messages, or tool return values
- **Token directory protection** — the report output directory is forbidden from pointing at the token storage location
- **Sensitive file isolation** — `.env` and the token directory are excluded by `.gitignore` by default
- **Allowlist / denylist** — filter which tools are exposed to the MCP client as needed

---

## Testing

The default tests require no real Garmin account:

```bash
uv sync
uv run pytest tests/unit tests/integration
```

Real-account E2E tests are skipped by default; enable them manually when needed:

```powershell
$env:RUN_GARMIN_E2E = "1"
uv run pytest tests/e2e
```

CI automatically runs unit and integration tests on Python 3.10, 3.11, 3.12, and 3.13.

---

## Documentation

| Document | Contents |
|---|---|
| [plan.md](plan.md) | Project plan and milestones |
| [docs/design.md](docs/design.md) | Detailed architecture design |
| [docs/tool-list.md](docs/tool-list.md) | Final tool list and parameter reference |

**Tech stack**: Python 3.10+ · [FastMCP](https://github.com/modelcontextprotocol/python-sdk) · [python-garminconnect](https://github.com/cyberjunky/python-garminconnect) · pytest · GitHub Actions

---

## Acknowledgements

This project draws on the modular design ideas of [Taxuspt/garmin_mcp](https://github.com/Taxuspt/garmin_mcp) (MIT License), but uses an independent project name, an independent package structure, and a reduced tool scope.

> **Disclaimer**: Garmin is a registered trademark of Garmin Ltd. Copyrights for Garmin Connect interface screenshots and product images belong to Garmin Ltd., and they are used here solely to illustrate this tool's data sources. This is a community-developed third-party tool with no official affiliation with Garmin Ltd.

## License

[MIT](LICENSE)
