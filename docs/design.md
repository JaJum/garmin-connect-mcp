# garmin-connect-mcp 详细设计

- 文档类型：M0 设计文档
- 项目名称：`garmin-connect-mcp`
- 版本：v1.0
- 日期：2026-10-03
- 状态：设计冻结候选版
- 简历方向：方案 A，MCP 工程能力

本文档是 `plan.md` 的实现级补充。后续代码、测试和 README 应以本文档为接口依据；若实现与本文档冲突，先修改本文档，再修改代码。

---

## 1. 设计目标

### 1.1 主要目标

1. 实现一个模块化、可测试的 Garmin Connect MCP Server。
2. 使用 Python、FastMCP 和 `python-garminconnect`。
3. 通过明确分层隔离 MCP 协议、工具注册、安全调用、Garmin 数据和报告生成。
4. 提供可读、可解释、可演示的健康日报和健康周报。
5. 默认只开放只读工具，避免误写或破坏 Garmin 数据。
6. 让 CI 可以在没有真实 Garmin 账号的情况下验证核心功能。
7. 简历重点体现 MCP 工程能力，而非简单 API 封装。

### 1.2 非目标

- 不追求覆盖 `python-garminconnect` 的全部接口。
- 不在第一版实现删除、修改、上传等写操作。
- 不实现 Garmin 私有协议逆向。
- 不实现医学诊断或健康建议。
- 不依赖在线图表服务生成报告。
- 不在日志、报告或异常中暴露密码、Token 和原始敏感响应。

---

## 2. 总体架构

```text
MCP Client
    │
    │ JSON-RPC / stdio
    ▼
FastMCP Server
    │
    ▼
Tool Registry
├── ToolDefinition
├── Schema validation
├── allowlist / denylist
├── permission level
└── statistics
    │
    ▼
SafeCall
├── argument validation
├── authentication gate
├── timeout
├── exception mapping
├── redaction
└── response envelope
    │
    ├──────────────────────┐
    ▼                      ▼
GarminGateway          ReportEngine
    │                      │
    ▼                      ▼
python-garminconnect   Collector
                       Analytics
                       Renderer
                           │
                           ├─ MarkdownRenderer
                           └─ HtmlSvgRenderer
```

### 2.1 分层职责

| 层 | 职责 | 不应负责 |
|---|---|---|
| MCP 层 | 协议、工具暴露、参数接收 | Garmin 登录、报告计算 |
| Registry 层 | 工具定义、过滤、权限、统计 | 实际数据请求 |
| SafeCall 层 | 超时、错误、脱敏、响应格式 | 具体指标计算 |
| GarminGateway | 封装 `python-garminconnect` | MCP Schema |
| ReportEngine | 数据聚合、趋势、异常、渲染 | MCP 协议 |
| Config | 配置读取和校验 | 业务逻辑 |

### 2.2 依赖方向

```text
tools → safety → gateway → garminconnect
tools → safety → report → gateway
server → registry → tools
```

禁止：

```text
gateway → mcp
report → fastmcp
tools → os.environ（应通过 config 获取）
```

这样可以让报告引擎和 Garmin Gateway 独立测试。

---

## 3. 包和模块设计

```text
src/garmin_connect_mcp/
├── __init__.py
├── __main__.py
├── server.py
├── config.py
├── errors.py
├── safety.py
├── registry.py
├── gateway.py
├── report/
│   ├── __init__.py
│   ├── models.py
│   ├── collector.py
│   ├── analytics.py
│   ├── markdown.py
│   └── html_svg.py
└── tools/
    ├── __init__.py
    ├── profile.py
    ├── activities.py
    ├── health.py
    ├── training.py
    └── reports.py
```

### 3.1 `server.py`

职责：

- 读取配置；
- 创建 Garmin Gateway；
- 创建 FastMCP 实例；
- 构建 Tool Registry；
- 注册工具；
- 启动 transport；
- 输出启动统计。

不直接包含业务工具实现。

### 3.2 `config.py`

职责：

- 读取环境变量；
- 解析布尔值；
- 解析整数和浮点数；
- 校验冲突配置；
- 计算 Token 和报告目录；
- 生成脱敏配置快照。

配置对象建议使用 `dataclass`：

```python
@dataclass(frozen=True)
class AppConfig:
    email: str | None
    password: str | None
    token_dir: str | None
    is_cn: bool
    call_timeout: float
    enabled_tools: frozenset[str]
    disabled_tools: frozenset[str]
    report_dir: str
    report_default_format: str
    include_visuals: bool
```

配置读取必须是纯函数，便于单元测试。

### 3.3 `errors.py`

定义：

- 业务异常基类；
- 输入错误；
- 认证错误；
- 网络错误；
- 限流错误；
- 上游错误；
- 数据缺失；
- 报告错误；
- 超时；
- 错误码枚举；
- 错误到 MCP 响应的转换。

### 3.4 `safety.py`

提供：

```text
SafeCall.call(handler, ...)
```

统一处理：

- 参数类型和范围检查；
- 认证状态；
- 调用超时；
- 异常映射；
- 日志脱敏；
- 统一响应封装；
- 调用耗时统计。

### 3.5 `registry.py`

核心类型：

```python
@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    handler: Callable[..., Any]
    input_model: type
    module: str
    permission: PermissionLevel
    enabled_by_default: bool = True
```

Registry 负责：

- 注册；
- 重名检测；
- allowlist/denylist；
- Schema 校验；
- 最终工具列表；
- 按模块统计；
- 工具名规范化。

### 3.6 `gateway.py`

Gateway 是唯一允许导入 `garminconnect` 的业务模块。

它需要提供：

```text
get_profile()
get_activities(start, limit)
get_activity(activity_id)
get_steps(date)
get_sleep(date)
get_stress(date)
get_hrv(date)
get_body_composition(start, end)
get_training_status(date)
get_training_readiness(date)
get_vo2max(start, end)
```

Gateway 不返回 MCP 响应，只返回领域数据或抛出领域异常。

---

## 4. MCP Server 设计

### 4.1 Transport

第一版只支持：

```text
stdio
```

预留：

```text
streamable-http
sse
```

但不在第一版默认启用。

配置：

```text
GARMIN_MCP_TRANSPORT=stdio
```

### 4.2 Server 名称

```text
Garmin Connect MCP
```

包命令：

```text
garmin-connect-mcp
```

### 4.3 启动流程

```text
1. 加载并校验配置
2. 创建 Gateway（不立即阻塞登录）
3. 创建 FastMCP
4. 构建 Tool Registry
5. 应用 allowlist / denylist
6. 注册工具
7. 输出工具统计
8. 启动 stdio transport
9. 首次工具调用时等待认证完成
```

### 4.4 登录策略

MCP 握手不应被 Garmin 登录长时间阻塞。

设计：

- 创建 `PendingGateway`；
- 后台线程执行 Token 恢复或登录；
- 工具调用通过 `SafeCall` 等待初始化；
- 初始化超时返回 `AUTH_TIMEOUT` 或 `TIMEOUT`；
- 日志只输出状态，不输出凭据。

### 4.5 启动统计

启动时向 stderr 输出：

```text
Garmin Connect MCP started
transport=stdio
region=global|cn
registered_tools=12
enabled_tools=all|filtered
report_dir=...
```

注意：

- stderr 可用于诊断；
- stdout 必须保留给 MCP JSON-RPC；
- 不得把普通 print 输出到 stdout。

---

## 5. 工具注册与过滤

### 5.1 工具权限

```text
READ        只读数据
WRITE       修改非破坏性数据
DESTRUCTIVE 删除或不可逆操作
```

第一版所有工具均为 `READ`。

### 5.2 过滤变量

```text
GARMIN_ENABLED_TOOLS
GARMIN_DISABLED_TOOLS
```

规则：

1. 名称统一转小写；
2. 去除首尾空格；
3. allowlist 非空时只允许其中的工具；
4. allowlist 为空时使用 denylist；
5. allowlist 和 denylist 同时存在时 allowlist 优先；
6. 未匹配名称输出 stderr 警告；
7. 过滤后没有工具时启动失败；
8. 过滤不删除业务代码，只控制注册。

### 5.3 工具定义示例

```json
{
  "name": "get_sleep_summary",
  "description": "获取指定日期的 Garmin 睡眠摘要",
  "module": "health",
  "permission": "READ",
  "input": {
    "date": "YYYY-MM-DD"
  }
}
```

### 5.4 工具命名规则

- 使用小写 snake_case；
- 动词开头：`get_`、`generate_`；
- 名称稳定，不随意更改；
- 工具名同时作为 allowlist/denylist key；
- 不在名称中加入版本号。

---

## 6. SafeCall 和响应格式

### 6.1 成功响应

```json
{
  "status": "success",
  "data": {},
  "meta": {
    "source": "garmin_connect",
    "generated_at": "2026-11-03T10:30:00+08:00",
    "request_id": "..."
  }
}
```

### 6.2 错误响应

```json
{
  "status": "error",
  "error": {
    "code": "INVALID_ARGUMENT",
    "message": "end_date 必须大于或等于 start_date"
  },
  "meta": {
    "generated_at": "2026-11-03T10:30:00+08:00",
    "request_id": "..."
  }
}
```

### 6.3 错误码

| 错误码 | 含义 |
|---|---|
| `INVALID_ARGUMENT` | 参数缺失、格式错误或范围错误 |
| `AUTH_REQUIRED` | 尚未完成 Garmin 认证 |
| `AUTH_EXPIRED` | Token 过期 |
| `AUTH_TIMEOUT` | 登录/Token 初始化超时 |
| `NETWORK_ERROR` | 网络连接失败 |
| `RATE_LIMITED` | Garmin 返回限流 |
| `UPSTREAM_ERROR` | Garmin 返回非预期错误 |
| `DATA_NOT_FOUND` | 指定日期或活动不存在 |
| `REPORT_GENERATION_FAILED` | 报告生成失败 |
| `TIMEOUT` | 单次调用超过配置超时 |
| `OUTPUT_ERROR` | 报告文件写入失败 |
| `INTERNAL_ERROR` | 未分类内部错误 |

### 6.4 脱敏规则

以下内容不得出现在响应或日志：

- 密码；
- Token；
- Cookie；
- Authorization header；
- 原始登录响应；
- 个人邮箱完整地址；
- Garmin 返回的原始敏感 JSON。

邮箱显示时使用：

```text
j***@example.com
```

### 6.5 超时

默认：

```text
GARMIN_MCP_CALL_TIMEOUT=90
```

规则：

- `0` 表示不启用；
- 超时返回 `TIMEOUT`；
- 报告生成可单独设置更长超时；
- 超时不能留下未处理线程；
- 不自动无限重试写操作。

---

## 7. 领域数据模型

### 7.1 日期

统一使用 ISO 格式：

```text
YYYY-MM-DD
```

校验：

- 日期必须真实存在；
- `end_date >= start_date`；
- 周报默认范围不超过 31 天；
- 日报固定为单日。

### 7.2 数据点状态

```text
VALID       完整有效
PARTIAL     部分有效
MISSING     缺失
ERROR       获取失败
```

### 7.3 通用指标模型

```python
@dataclass
class MetricPoint:
    date: str
    value: float | int | None
    status: DataStatus
    source: str
```

### 7.4 覆盖率模型

```python
@dataclass
class Coverage:
    expected_days: int
    valid_days: int
    partial_days: int
    missing_days: int
    ratio: float
```

计算：

```text
ratio = (valid_days + 0.5 * partial_days) / expected_days
```

比例保留两位小数，范围 `0.00～1.00`。

### 7.5 趋势模型

```text
UP          上升
DOWN        下降
STABLE      基本稳定
UNKNOWN     数据不足
```

趋势算法：

1. 至少 3 个有效点才计算；
2. 使用首尾有效值或简单线性斜率；
3. 变化小于 5% 视为稳定；
4. 数据点不足返回 `UNKNOWN`；
5. 不对缺失值按 0 处理。

---

## 8. 第一版工具接口

### 8.1 通用规则

- 输入使用 ISO 日期；
- 返回统一响应信封；
- 只读工具权限为 `READ`；
- 每个工具都有清晰描述；
- 每个工具都有单元测试；
- 工具内部不直接读取环境变量。

### 8.2 用户模块

#### `get_profile`

输入：无。

输出重点：

- 显示名；
- 用户 ID（可脱敏）；
- 头像 URL（可选）；
- 区域信息。

#### `get_user_settings`

输入：无。

输出重点：

- 单位制；
- 时区；
- 基本偏好。

不得返回密码、Token、安全问题等敏感信息。

### 8.3 活动模块

#### `get_recent_activities`

```json
{
  "start": 0,
  "limit": 20
}
```

约束：

- `start >= 0`；
- `1 <= limit <= 100`；
- 默认 `limit=20`。

#### `get_activity`

```json
{
  "activity_id": 123456789
}
```

约束：

- `activity_id` 必须为正整数；
- 不存在时返回 `DATA_NOT_FOUND`；
- 不默认下载大型 GPS 详情。

### 8.4 健康模块

#### `get_daily_steps`

```json
{
  "date": "2026-11-02"
}
```

#### `get_sleep_summary`

```json
{
  "date": "2026-11-02"
}
```

返回：

- 总睡眠；
- 深睡；
- 浅睡；
- REM；
- 清醒；
- 数据状态。

#### `get_stress_summary`

```json
{
  "date": "2026-11-02"
}
```

#### `get_hrv_summary`

```json
{
  "date": "2026-11-02"
}
```

#### `get_body_composition`

```json
{
  "start_date": "2026-10-27",
  "end_date": "2026-11-02"
}
```

### 8.5 训练模块

#### `get_training_status`

```json
{
  "date": "2026-11-02"
}
```

#### `get_training_readiness`

```json
{
  "date": "2026-11-02"
}
```

#### `get_vo2max_trend`

```json
{
  "start_date": "2026-10-01",
  "end_date": "2026-11-02"
}
```

### 8.6 报告模块

#### `generate_health_weekly_report`

```json
{
  "start_date": "2026-10-27",
  "end_date": "2026-11-02",
  "output_format": "markdown",
  "include_visuals": true,
  "output_dir": null
}
```

#### `generate_health_daily_report`

```json
{
  "date": "2026-11-02",
  "output_format": "markdown",
  "include_visuals": true,
  "output_dir": null
}
```

字段规则：

- `output_format`：`markdown` 或 `html`；
- `include_visuals`：HTML 默认 `true`；
- `output_dir`：可选，必须是可写目录；
- 不允许输出路径覆盖 Token 目录；
- 默认报告目录由 `GARMIN_REPORT_DIR` 或 `reports/` 决定。

---

## 9. 报告引擎设计

### 9.1 结构

```text
ReportEngine
├── ReportRequest
├── ReportCollector
├── ReportAnalytics
├── ReportModel
└── ReportRenderer
    ├── MarkdownRenderer
    └── HtmlSvgRenderer
```

### 9.2 报告请求

```python
@dataclass(frozen=True)
class ReportRequest:
    start_date: date
    end_date: date
    output_format: str
    include_visuals: bool
    output_dir: str
```

日报将单个日期转换为：

```text
start_date = date
end_date = date
```

### 9.3 数据收集

收集器按日期获取：

- 睡眠；
- 静息心率；
- HRV；
- 压力；
- 步数；
- 训练状态/准备度；
- 活动；
- 训练负荷（如果上游支持）。

每个数据源必须独立容错：

```text
睡眠失败 → sleep.status = ERROR
其他数据仍继续收集
最终报告标记 partial
```

### 9.4 聚合规则

#### 平均睡眠

- 只统计 `VALID` 数据；
- 单位统一为分钟；
- 展示时转换成 `7h 12m`；
- 没有有效数据时显示“数据不足”。

#### 静息心率

- 输出最低值和最高值；
- 同时输出平均值；
- 缺失日期不参与计算。

#### HRV 趋势

- 计算有效点；
- 输出平均值；
- 输出趋势方向；
- 输出相对基线变化；
- 数据点少于 3 个时为 `UNKNOWN`。

#### 压力变化

- 输出平均压力；
- 输出最高压力日期；
- 输出趋势；
- 不把压力值解释为疾病。

#### 训练负荷

- 输出总量；
- 输出日均值；
- 输出最高负荷日期；
- 如果接口不可用，标记为 `unavailable`，不伪造为 0。

#### 活动统计

- 活动总数；
- 活动类型分布；
- 总时长；
- 总距离（仅对支持距离的活动）。

### 9.5 异常提示

默认规则应可配置，并且只输出“数据提示”。

示例规则：

| 指标 | 默认提示条件 |
|---|---|
| 睡眠 | 低于个人 7 日基线 20% |
| HRV | 低于个人 7 日基线 15% |
| 静息心率 | 高于个人 7 日基线 10% |
| 压力 | 高于个人 7 日基线 20% |
| 训练负荷 | 超过近期平均值 1.5 倍 |
| 数据覆盖率 | 低于 70% |

每个提示必须包含：

- 指标；
- 日期；
- 实际值；
- 基线值；
- 变化比例；
- 数据覆盖率；
- `非医学诊断` 声明。

禁止输出：

```text
你生病了。
你过度训练了。
你有心血管疾病风险。
```

### 9.6 缺失数据

- `MISSING` 不参与均值；
- `ERROR` 不参与均值；
- `PARTIAL` 根据字段可用性参与；
- 报告必须显示缺失天数；
- 图表必须跳过缺失点；
- 不使用 0 填充。

### 9.7 Markdown 输出结构

```markdown
# Garmin 健康周报

- 报告周期：2026-10-27 至 2026-11-02
- 数据覆盖率：86%
- 生成时间：2026-11-03 10:30

## 核心指标
| 指标 | 数值 | 趋势 |
|---|---:|---|
| 平均睡眠 | 7h 12m | ↑ |
| 静息心率 | 52–61 bpm | → |
| HRV | 48 ms | ↓ |
| 平均压力 | 31 | → |

## 异常提示
- 11 月 1 日 HRV 低于 7 日基线 18%。

## 数据质量
- 7 天中 6 天有效。
- 1 天缺少 HRV 数据。

> 数据提示仅供趋势参考，不构成医学诊断。
```

### 9.8 HTML 输出结构

HTML 特性：

- 单文件；
- 内嵌 CSS；
- 内嵌 SVG；
- 不加载 CDN；
- 不执行远程脚本；
- 可离线打开；
- 包含日期、覆盖率、指标、图表和异常提示。

图表：

- 睡眠柱状图；
- HRV 折线图；
- 压力折线图；
- 静息心率折线图；
- 训练负荷柱状图。

图表必须显示：

- 缺失日期；
- 有效数据点数量；
- 异常日期高亮；
- 图例和单位；
- 非医学诊断声明。

### 9.9 报告输出

文件名：

```text
weekly_YYYY-MM-DD_YYYY-MM-DD.md
weekly_YYYY-MM-DD_YYYY-MM-DD.html
daily_YYYY-MM-DD.md
daily_YYYY-MM-DD.html
```

返回内容：

```json
{
  "status": "success",
  "data": {
    "report_type": "weekly",
    "format": "html",
    "path": "C:/.../weekly_2026-10-27_2026-11-02.html",
    "coverage": 0.86,
    "missing_days": 1
  }
}
```

报告工具同时返回简短摘要，避免客户端必须打开文件才能知道结果。

---

## 10. 配置设计

### 10.1 认证配置

| 变量 | 类型 | 说明 |
|---|---|---|
| `GARMIN_EMAIL` | string | 邮箱 |
| `GARMIN_PASSWORD` | string | 密码，不记录日志 |
| `GARMIN_EMAIL_FILE` | path | 邮箱文件 |
| `GARMIN_PASSWORD_FILE` | path | 密码文件 |
| `GARMIN_IS_CN` | bool | 是否中国区 |
| `GARMINTOKENS` | path | Token 目录 |
| `GARMINTOKENS_BASE64` | path | Base64 Token 目录 |

冲突规则：

- `GARMIN_EMAIL` 与 `GARMIN_EMAIL_FILE` 不能同时设置；
- `GARMIN_PASSWORD` 与 `GARMIN_PASSWORD_FILE` 不能同时设置；
- 冲突启动失败。

### 10.2 MCP 配置

| 变量 | 默认值 |
|---|---|
| `GARMIN_MCP_TRANSPORT` | `stdio` |
| `GARMIN_MCP_CALL_TIMEOUT` | `90` |
| `GARMIN_ENABLED_TOOLS` | 空 |
| `GARMIN_DISABLED_TOOLS` | 空 |

### 10.3 报告配置

| 变量 | 默认值 |
|---|---|
| `GARMIN_REPORT_DIR` | `reports` |
| `GARMIN_REPORT_DEFAULT_FORMAT` | `markdown` |
| `GARMIN_REPORT_INCLUDE_VISUALS` | `true` |
| `GARMIN_REPORT_MAX_DAYS` | `31` |

### 10.4 配置校验

启动时检查：

- 超时必须为非负数；
- 默认格式必须为 `markdown` 或 `html`；
- 最大报告天数必须大于 0；
- 报告目录不能等于或位于 Token 目录内；
- 过滤后的工具数量不能为 0；
- 非法布尔值给出明确错误。

---

## 11. 安全设计

### 11.1 凭据

- 密码只从环境变量或本地文件读取；
- 不把密码写入配置快照；
- 不把密码放入异常信息；
- Token 文件默认仅当前用户可读；
- 文件权限失败不能导致敏感内容泄露；
- 不提供“打印 Token”的工具。

### 11.2 日志

允许记录：

- 工具名；
- 调用耗时；
- 状态码；
- 错误码；
- 数据覆盖率；
- 报告路径。

禁止记录：

- 密码；
- Token；
- Cookie；
- Authorization；
- 完整邮箱；
- 原始认证响应。

### 11.3 输出路径

- 默认写入 `reports/`；
- 支持 `GARMIN_REPORT_DIR`；
- 禁止写入 Token 目录；
- 禁止使用未规范化的 `..` 路径穿越；
- 目录自动创建，但权限遵循运行用户；
- 写入失败返回 `OUTPUT_ERROR`。

### 11.4 Git

`.gitignore` 至少包含：

```text
.venv/
__pycache__/
*.pyc
.env
.garmin_tokens/
.garmin_tokens_base64
reports/
```

### 11.5 医疗免责声明

所有报告必须包含：

```text
报告内容根据可穿戴设备数据自动汇总，仅供趋势参考，不构成医学诊断或医疗建议。
```

---

## 12. 测试设计

### 12.1 测试分层

```text
tests/
├── unit/
├── integration/
├── e2e/
└── fixtures/
```

### 12.2 单元测试

必须覆盖：

- 配置解析；
- 冲突配置；
- 布尔和数字转换；
- 日期校验；
- 报告范围校验；
- 工具注册；
- 重名检测；
- allowlist/denylist；
- 权限检查；
- SafeCall 成功；
- SafeCall 超时；
- 异常映射；
- 脱敏；
- 覆盖率计算；
- 趋势计算；
- 异常阈值；
- 缺失数据；
- Markdown 渲染；
- HTML/SVG 渲染；
- 输出路径安全。

### 12.3 集成测试

使用 mock Gateway，不访问网络：

- `tools/list` 返回预期工具；
- 每个工具有 Schema；
- `tools/call` 成功；
- `tools/call` 错误返回统一格式；
- mock 数据可以生成日报；
- mock 数据可以生成周报；
- 单个数据源失败时报告降级生成；
- 报告写入指定目录；
- 报告不含敏感信息。

### 12.4 E2E

真实 Garmin 测试：

- 默认跳过；
- 只在显式设置环境变量时运行；
- 不在普通 CI 执行；
- 不提交真实响应；
- 只验证读取和报告生成；
- 不执行写操作。

### 12.5 CI

GitHub Actions：

```text
Python 3.10
Python 3.11
Python 3.12
Python 3.13
```

命令：

```text
uv sync
uv run pytest tests/unit tests/integration
```

CI 必须证明：

- 无真实账号可运行；
- 无 Token 可运行；
- 无网络也能运行核心测试；
- 报告可以由 fixture 生成。

---

## 13. 可观测性

### 13.1 日志级别

```text
ERROR   影响调用失败
WARN    降级、缺失、过滤警告
INFO    启动、工具统计、报告完成
DEBUG   仅开发环境
```

### 13.2 每次调用记录

- `request_id`；
- 工具名；
- 起止时间；
- 耗时；
- 状态；
- 错误码；
- 数据点数量；
- 是否生成文件。

不得记录入参中的凭据和完整敏感数据。

### 13.3 启动指标

- 注册工具数；
- 过滤后工具数；
- transport；
- region；
- report format；
- 初始化状态。

---

## 14. 性能和并发

### 14.1 性能目标

本项目主要是 I/O 密集型，不追求高吞吐。

目标：

- 普通单日工具调用：低于 10 秒（网络正常时）；
- 报告调用：可配置更长超时；
- MCP 启动不等待真实登录；
- 同一时刻只进行必要的 Garmin 请求；
- 对报告数据请求实施简单并发上限，避免触发限流。

### 14.2 重试策略

- 网络超时：最多重试 1 次；
- 限流：不立即重试；
- 认证失败：不重试；
- 写操作：不自动重试；
- 报告单个指标失败：继续其他指标。

### 14.3 缓存

第一版不引入复杂缓存。

预留：

- 报告原始数据缓存；
- 同日期报告结果缓存；
- 缓存必须标记生成时间；
- 缓存不能缓存 Token。

---

## 15. 依赖设计

核心依赖：

```text
python-dotenv
python-garminconnect
mcp
```

测试依赖：

```text
pytest
pytest-asyncio
pytest-mock
pytest-timeout
```

报告依赖：

- 第一版优先使用 Python 标准库生成 Markdown 和 SVG；
- 不强制引入 matplotlib；
- 如后续需要更复杂图表，再单独评估。

原则：

- 不为了一个简单图表引入大型依赖；
- 所有依赖固定版本或锁定；
- 不依赖外部 CDN；
- 不在运行时下载资源。

---

## 16. 版本和兼容性

### 16.1 Python

目标：

```text
Python 3.10+
```

CI 覆盖：

```text
3.10
3.11
3.12
3.13
```

### 16.2 MCP

- 使用 FastMCP；
- 依赖版本在 `pyproject.toml` 中限定范围；
- 升级 MCP SDK 前运行完整测试；
- 不使用未文档化内部接口。

### 16.3 Garmin 客户端

- 固定已验证的 `python-garminconnect` 版本；
- 升级时检查方法签名、返回结构和中国区行为；
- Gateway 隔离第三方库，降低升级影响。

---

## 17. 实现顺序

### 阶段 1：骨架

1. 创建 `pyproject.toml`；
2. 创建 `src/garmin_connect_mcp`；
3. 实现 `config.py`；
4. 实现 `errors.py`；
5. 实现 `registry.py`；
6. 创建 mock Gateway；
7. 实现最小 FastMCP Server；
8. 用 MCP Inspector 验证 `tools/list`。

### 阶段 2：真实数据

9. 实现 `gateway.py`；
10. 接入 `python-garminconnect`；
11. 处理 Token 和中国区；
12. 实现 profile、activities、health、training 工具；
13. 实现 SafeCall；
14. 验证 10～12 个只读工具。

### 阶段 3：报告

15. 实现 `ReportRequest`；
16. 实现 `ReportCollector`；
17. 实现 `ReportAnalytics`；
18. 实现 MarkdownRenderer；
19. 实现 HtmlSvgRenderer；
20. 实现日报和周报工具；
21. 用 fixture 生成报告。

### 阶段 4：质量

22. 补齐单元测试；
23. 补齐集成测试；
24. 实现 GitHub Actions；
25. 完成安全审查；
26. 完成 README 和演示。

---

## 18. 完成定义（Definition of Done）

项目只有同时满足以下条件才算完成：

- [ ] `uv run pytest tests/unit tests/integration` 通过；
- [ ] MCP Inspector 可以完成初始化；
- [ ] `tools/list` 返回设计内工具；
- [ ] 至少 10 个数据工具可以调用；
- [ ] allowlist/denylist 生效；
- [ ] 认证失败返回统一错误；
- [ ] 日报可由 mock 数据生成；
- [ ] 周报可由 mock 数据生成；
- [ ] Markdown 报告可读；
- [ ] HTML 报告可以离线打开；
- [ ] 缺失数据不会按 0 计算；
- [ ] 报告包含数据覆盖率；
- [ ] 报告包含非医学诊断声明；
- [ ] 日志和报告不含密码、Token、Cookie；
- [ ] 真实账号测试默认跳过；
- [ ] GitHub Actions 不需要真实账号；
- [ ] README 包含安装、启动、演示和测试说明；
- [ ] README 注明参考项目来源；
- [ ] `.gitignore` 不会提交 Token 和报告数据。

---

## 19. 后续可扩展方向

第一版完成后可以按需增加：

- 周报对比上一周期；
- 月报；
- 自定义指标；
- PNG 图表；
- SQLite 本地历史；
- 报告缓存；
- streamable-http；
- 写操作权限；
- 更多 Garmin 接口；
- 多用户配置；
- 健康目标跟踪。

但这些不应阻塞第一版完成。

---

## 20. 设计决策记录

### 决策 1：使用 Python

原因：参考项目、Garmin 客户端和 FastMCP 生态一致，能将时间投入 MCP 工程和报告功能。

### 决策 2：第一版只读

原因：降低误操作和数据损坏风险，符合 MCP 工程演示目标。

### 决策 3：报告使用 Markdown + HTML/SVG

原因：Markdown 适合 LLM 和笔记，HTML/SVG 可离线可视化，不引入大型图表依赖。

### 决策 4：报告不是医学诊断

原因：Garmin 数据是非医疗级设备数据，必须明确边界。

### 决策 5：工具数量控制在 12～14 个

原因：简历价值来自架构、安全、测试和报告产品化，而不是工具数量堆叠。

### 决策 6：Registry 和 SafeCall 独立成层

原因：这是本项目区别于简单 API wrapper 的核心工程亮点，也方便测试。
