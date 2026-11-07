<div align="center">

<img src="assets/logo.png" alt="garmin-connect-mcp logo" width="160">

# garmin-connect-mcp

**一个模块化、可测试的 Garmin Connect MCP Server**

把 Garmin 手表里的睡眠、心率、压力、训练数据接入任何支持 MCP 的 AI 助手，并生成可视化的健康日报与周报。

[![CI](https://github.com/JaJum/garmin-connect-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/JaJum/garmin-connect-mcp/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-Server-2E7D32)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-4CAF50.svg)](LICENSE)

<img src="https://www.garmin.com.cn/m/cn/g/banner/87582-1-D.jpg" alt="越野跑中的运动员与 Garmin 手表" width="720">

</div>

---

## 目录

- [为什么选择它](#为什么选择它)
- [功能一览](#功能一览)
- [快速开始](#快速开始)
- [接入 MCP 客户端](#接入-mcp-客户端)
- [工具列表](#工具列表)
- [健康报告](#健康报告)
- [安全设计](#安全设计)
- [测试](#测试)
- [文档](#文档)
- [来源说明](#来源说明)

---

## 为什么选择它

大多数 Garmin MCP 实现只是 API 的薄封装。本项目把重点放在**工程质量**上：

- **开箱即用** — 一条命令启动，14 个工具自动注册，无需真实账号即可用 mock 模式体验
- **报告即产品** — 不只是返回 JSON，还能产出带图表的日报/周报，直接打开就能看
- **安全边界清晰** — 只读设计、凭据脱敏、Token 目录保护，敏感数据永远不会出现在日志里
- **经得起验证** — 单元 + 集成 + 端到端三层测试，GitHub Actions 上验证 Python 3.10 至 3.13

---

## 功能一览

<table>
<tr>
<td width="50%" valign="top">

**📊 14 个数据工具**

个人资料、活动、步数、睡眠、压力、HRV、身体成分、训练状态、训练准备度、VO2max 趋势，只读安全。

</td>
<td width="50%" valign="top">

**📈 健康日报 / 周报**

数据覆盖率、趋势分析、异常提示，输出 Markdown 或自包含 HTML+SVG 报告，零外部依赖。

</td>
</tr>
<tr>
<td width="50%" valign="top">

**🔐 双认证模式**

账号密码或 Token 认证，支持 Garmin 中国区，凭据可通过环境变量或文件注入。

</td>
<td width="50%" valign="top">

**🧪 Mock 模式**

`GARMIN_MCP_MOCK=true` 即可脱离真实账号运行，让 CI 和演示都不依赖外部服务。

</td>
</tr>
</table>

<div align="center">
<img src="https://connect.garmin.cn/_astro/screen-glance.CVT5xs6m.png" alt="Garmin Connect 数据概览界面" width="220">
<img src="https://connect.garmin.cn/_astro/screen-activity.CrYaN3pL.png" alt="Garmin Connect 活动记录界面" width="220">
<img src="https://connect.garmin.cn/_astro/screen-phone-myday.CMAP1jie.png" alt="Garmin Connect 手机端今日视图" width="220">
<br>
<sub>数据来源：Garmin Connect 官方应用</sub>
</div>

---

## 快速开始

**1. 安装**

```bash
git clone https://github.com/JaJum/garmin-connect-mcp.git
cd garmin-connect-mcp
uv sync
```

**2. 配置**

在项目根目录创建 `.env`（或直接设置环境变量）：

```bash
GARMIN_EMAIL=your@email.com
GARMIN_PASSWORD=your-password
GARMIN_IS_CN=true          # 中国区账号必填
```

> 只想先试一试？设置 `GARMIN_MCP_MOCK=true` 即可跳过真实账号，用模拟数据体验全部功能。

**3. 启动**

```bash
uv run garmin-connect-mcp
```

启动日志会显示运行模式（`mock` / `live`）、区域和已注册的工具数量。

<details>
<summary><b>全部配置项</b></summary>

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

</details>

---

## 接入 MCP 客户端

以 Claude Desktop 的 `claude_desktop_config.json` 为例：

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

任何支持 MCP stdio 传输的客户端（Cursor、Windsurf 等）都可以用同样方式接入。

---

## 工具列表

| 分类 | 工具 | 说明 |
|---|---|---|
| 资料 | `get_profile` | 运动员基本资料 |
| 资料 | `get_settings` | 账号设置 |
| 活动 | `get_recent_activities` | 最近活动列表 |
| 活动 | `get_activity` | 单次活动详情 |
| 活动 | `get_daily_steps` | 每日步数 |
| 健康 | `get_sleep_summary` | 睡眠摘要 |
| 健康 | `get_stress_summary` | 压力摘要 |
| 健康 | `get_hrv_summary` | HRV 摘要 |
| 健康 | `get_body_composition` | 身体成分 |
| 训练 | `get_training_status` | 训练状态 |
| 训练 | `get_training_readiness` | 训练准备度 |
| 训练 | `get_vo2max_trend` | VO2max 趋势 |
| 报告 | `generate_health_daily_report` | 生成健康日报 |
| 报告 | `generate_health_weekly_report` | 生成健康周报 |

---

## 健康报告

报告引擎会自动计算数据覆盖率、绘制趋势图并标记异常指标：

<div align="center">
<img src="https://connect.garmin.cn/_astro/screen-coach.rqWAXvey.png" alt="Garmin Connect 训练指导视图" width="260">
<img src="https://connect.garmin.cn/_astro/devices.86mv_XfL.png" alt="Garmin 设备生态" width="300">
</div>

- **输出格式**：Markdown，或自包含的 HTML+SVG（可直接分享，无需联网）
- **日报**：单日睡眠、静息心率、HRV、压力、训练负荷、步数 + 趋势图
- **周报**：7 天聚合、每日明细表、异常指标提示、数据质量评估
- **输出目录**：默认项目下 `reports/`（已加入 `.gitignore`，健康数据不会被提交）

---

## 安全设计

- **只读工具集** — 不提供任何修改 Garmin 数据的操作
- **凭据脱敏** — 密码和 Token 永远不会出现在日志、报错或工具返回值中
- **Token 目录保护** — 报告输出目录禁止指向 Token 存储位置
- **敏感文件隔离** — `.env`、Token 目录默认被 `.gitignore` 排除
- **allowlist / denylist** — 可按需过滤暴露给 MCP 客户端的工具

---

## 测试

默认测试不需要真实 Garmin 账号：

```bash
uv sync
uv run pytest tests/unit tests/integration
```

真实账号 E2E 测试默认跳过，需要时手动开启：

```powershell
$env:RUN_GARMIN_E2E = "1"
uv run pytest tests/e2e
```

CI 会在 Python 3.10、3.11、3.12 和 3.13 上自动运行单元与集成测试。

---

## 文档

| 文档 | 内容 |
|---|---|
| [plan.md](plan.md) | 项目计划与里程碑 |
| [docs/design.md](docs/design.md) | 详细架构设计 |
| [docs/tool-list.md](docs/tool-list.md) | 最终工具清单与参数说明 |

**技术栈**：Python 3.10+ · [FastMCP](https://github.com/modelcontextprotocol/python-sdk) · [python-garminconnect](https://github.com/cyberjunky/python-garminconnect) · pytest · GitHub Actions

---

## 来源说明

本项目参考了 [Taxuspt/garmin_mcp](https://github.com/Taxuspt/garmin_mcp)（MIT License）的模块化思路，但采用独立项目名、独立包结构和缩小后的工具范围。

> **免责声明**：Garmin 是 Garmin Ltd. 的注册商标，Garmin Connect 的界面截图与产品图片的版权归 Garmin Ltd. 所有，此处仅用于说明本工具的数据来源。本项目为社区开发的第三方工具，与 Garmin Ltd. 无官方关联。

## License

[MIT](LICENSE)
