# garmin-connect-mcp

一个模块化、可测试的 Garmin Connect MCP Server，支持健康数据查询和可视化日报/周报。

## 当前状态

第一版开发状态：

- [x] 创建 Python 项目结构
- [x] 创建 `pyproject.toml`
- [x] 创建 `src/garmin_connect_mcp` 包结构
- [x] 实现配置层和 mock Gateway
- [x] 实现最小 MCP Server
- [x] 用 MCP Inspector 验证 tools/list
- [x] 接入 Garmin Client
- [x] 实现 12 个基础数据工具
- [x] 实现 2 个健康日报/周报工具
- [x] 实现健康日报/周报和 Markdown/HTML+SVG 可视化
- [x] 添加测试和 CI

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
## 规划文档

- [项目计划](plan.md)
- [详细设计](docs/design.md)
- [最终工具清单](docs/tool-list.md)

## 计划技术栈

- Python 3.10+
- FastMCP
- `python-garminconnect`
- pytest
- GitHub Actions

## 后续启动方式

完成 M1 后，计划支持：

```bash
uv sync
uv run garmin-connect-mcp
```

## 来源说明

本项目参考了 [Taxuspt/garmin_mcp](https://github.com/Taxuspt/garmin_mcp) 的模块化思路，但采用独立项目名、独立包结构和缩小后的工具范围。








