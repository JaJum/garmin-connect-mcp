# garmin-connect-mcp

[![CI](https://github.com/OWNER/garmin-connect-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/OWNER/garmin-connect-mcp/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

一个模块化、可测试的 Garmin Connect MCP Server：通过 [Model Context Protocol](https://modelcontextprotocol.io/) 提供 Garmin 健康数据只读查询，并能生成 Markdown / 自包含 HTML+SVG 的健康日报和周报。

## 功能特性

- **14 个 MCP 工具**：个人资料、设置、活动、步数、睡眠、压力、HRV、身体成分、训练状态、训练准备度、VO2max 趋势，以及健康日报/周报生成
- **健康报告引擎**：数据覆盖率统计、趋势分析、异常指标提示，输出 Markdown 或自包含 HTML+SVG 可视化报告，不依赖任何外部服务
- **安全边界**：只读设计，工具 allowlist/denylist 过滤，统一 SafeCall 调用与错误码，敏感信息脱敏，Token 目录保护
- **双认证模式**：Garmin 账号密码登录或 Token 认证，支持中国区（`GARMIN_IS_CN`）
- **Mock 模式**：无需真实账号即可运行和测试（`GARMIN_MCP_MOCK=true`）
- **多版本测试**：pytest 单元/集成测试，GitHub Actions 上验证 Python 3.10 至 3.13

## 安装

需要 [uv](https://docs.astral.sh/uv/)（或 pip）和 Python 3.10+。

```bash
git clone https://github.com/OWNER/garmin-connect-mcp.git
cd garmin-connect-mcp
uv sync
```

## 配置

支持环境变量或项目根目录下的 `.env` 文件：

| 变量 | 说明 | 必填 |
|---|---|---|
| `GARMIN_EMAIL` | Garmin 账号邮箱 | 二选一 |
| `GARMIN_PASSWORD` | Garmin 账号密码 | 二选一 |
| `GARMIN_EMAIL_FILE` / `GARMIN_PASSWORD_FILE` | 从文件读取凭据（更安全） | 二选一 |
| `GARMINTOKENS` | Token 认证目录（与账号密码二选一） | 二选一 |
| `GARMINTOKENS_BASE64` | Base64 Token 目录 | 否 |
| `GARMIN_IS_CN` | `true` 使用 Garmin 中国区 | 否 |
| `GARMIN_REPORT_DIR` | 报告输出目录（默认 `./reports`） | 否 |
| `GARMIN_MCP_MOCK` | `true` 启用 mock 模式，不需要真实账号 | 否 |

> 提示：密码和 Token 不会被日志输出；`.gitignore` 已排除 `.env`、Token 目录和 `reports/`。

## 启动

```bash
uv run garmin-connect-mcp
```

以 stdio 传输启动 MCP Server。启动日志会显示运行模式（`mock` / `live`）、区域和已注册的工具数量。

### 接入 Claude Desktop / MCP 客户端

在 MCP 客户端配置中添加（以 Claude Desktop 的 `claude_desktop_config.json` 为例）：

```json
{
  "mcpServers": {
    "garmin-connect-mcp": {
      "command": "uv",
      "args": ["--directory", "/path/to/garmin-connect-mcp", "run", "garmin-connect-mcp"],
      "env": {
        "GARMIN_EMAIL": "your@email.com",
        "GARMIN_PASSWORD": "your-password",
        "GARMIN_IS_CN": "true"
      }
    }
  }
}
```

只想先试一试的话，把 `GARMIN_MCP_MOCK` 设为 `true` 即可脱离真实账号运行。

### 工具列表

| 分类 | 工具 |
|---|---|
| 资料 | `get_profile`、`get_settings` |
| 活动 | `get_recent_activities`、`get_activity`、`get_daily_steps` |
| 健康 | `get_sleep_summary`、`get_stress_summary`、`get_hrv_summary`、`get_body_composition` |
| 训练 | `get_training_status`、`get_training_readiness`、`get_vo2max_trend` |
| 报告 | `generate_health_daily_report`、`generate_health_weekly_report` |

## 测试

默认测试不需要真实 Garmin 账号：

```bash
uv sync
uv run pytest tests/unit tests/integration
```

真实账号 E2E 测试默认跳过。需要本地验证真实账号时：

```powershell
$env:RUN_GARMIN_E2E = "1"
uv run pytest tests/e2e
```

CI 会在 Python 3.10、3.11、3.12 和 3.13 上运行单元与集成测试。

## 文档

- [项目计划](plan.md)
- [详细设计](docs/design.md)
- [最终工具清单](docs/tool-list.md)

## 技术栈

- Python 3.10+
- [FastMCP](https://github.com/modelcontextprotocol/python-sdk)（MCP Python SDK）
- [python-garminconnect](https://github.com/cyberjunky/python-garminconnect)
- pytest
- GitHub Actions

## 来源说明

本项目参考了 [Taxuspt/garmin_mcp](https://github.com/Taxuspt/garmin_mcp)（MIT License）的模块化思路，但采用独立项目名、独立包结构和缩小后的工具范围。

## License

[MIT](LICENSE)
