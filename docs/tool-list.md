# garmin-connect-mcp 最终工具清单

- 文档状态：**已确认 / Frozen**
- 版本：v1.0
- 日期：2026-10-03
- 项目：`garmin-connect-mcp`
- 总数：**14 个**
- 远程权限：全部为 `READ`
- 第一版是否包含写操作：**否**
- 报告工具是否修改 Garmin 数据：**否**，只读取数据并写入本地报告文件

本清单已根据 `D:\garmin_mcp-main\garmin_mcp-main` 中参考项目的实际工具定义进行核对。`上游映射` 表示参考项目中可供参考的工具或接口，不代表本项目直接复制其实现。

---

## 1. 最终结论

第一版固定为以下 14 个工具：

### 用户模块（2 个）

1. `get_profile`
2. `get_settings`

### 活动模块（2 个）

3. `get_recent_activities`
4. `get_activity`

### 健康模块（5 个）

5. `get_daily_steps`
6. `get_sleep_summary`
7. `get_stress_summary`
8. `get_hrv_summary`
9. `get_body_composition`

### 训练模块（3 个）

10. `get_training_status`
11. `get_training_readiness`
12. `get_vo2max_trend`

### 报告模块（2 个）

13. `generate_health_daily_report`
14. `generate_health_weekly_report`

---

## 2. 工具总表

| 序号 | 工具名 | 模块 | 权限 | 输入 | 主要输出 | 上游映射 |
|---:|---|---|---|---|---|---|
| 1 | `get_profile` | profile | READ | 无 | 用户基本资料 | `get_user_profile` |
| 2 | `get_settings` | profile | READ | 无 | 单位、时区、偏好设置 | `get_userprofile_settings` |
| 3 | `get_recent_activities` | activities | READ | `start`, `limit` | 最近活动列表 | `get_activities` |
| 4 | `get_activity` | activities | READ | `activity_id` | 单个活动详情 | `get_activity` |
| 5 | `get_daily_steps` | health | READ | `start_date`, `end_date` | 每日步数 | `get_daily_steps` / `get_stats` |
| 6 | `get_sleep_summary` | health | READ | `date` | 睡眠摘要 | `get_sleep_summary` |
| 7 | `get_stress_summary` | health | READ | `date` | 压力摘要 | `get_stress_summary` |
| 8 | `get_hrv_summary` | health | READ | `start_date`, `end_date` | HRV 数据与趋势 | `get_hrv_data` / `get_hrv_trend` |
| 9 | `get_body_composition` | health | READ | `start_date`, `end_date` | 体重、体脂等 | `get_body_composition` |
| 10 | `get_training_status` | training | READ | `date` | 训练状态 | `get_training_status` |
| 11 | `get_training_readiness` | training | READ | `date` | 训练准备度 | `get_training_readiness` |
| 12 | `get_vo2max_trend` | training | READ | `start_date`, `end_date` | VO2 Max 趋势 | `get_vo2max_trend` |
| 13 | `generate_health_daily_report` | reports | READ + 本地输出 | `date`, `output_format`, `include_visuals`, `output_dir` | 日报文件和摘要 | 本地 `ReportEngine` |
| 14 | `generate_health_weekly_report` | reports | READ + 本地输出 | `start_date`, `end_date`, `output_format`, `include_visuals`, `output_dir` | 周报文件和摘要 | 本地 `ReportEngine` |

说明：

- `READ + 本地输出` 表示不修改 Garmin 远程数据，但会在本地生成报告文件。
- 所有报告文件都必须经过输出路径安全检查。
- 报告工具不得写入 Token 目录。

---

## 3. 工具详细定义

### 3.1 `get_profile`

**模块：** `profile`  
**权限：** `READ`  
**输入：** 无  
**是否需要真实数据：** 是  
**上游映射：** `get_user_profile`

返回：

- 显示名称；
- 用户 ID（必要时脱敏）；
- 头像地址（可选）；
- 基本账户信息。

不返回：

- 密码；
- Token；
- Cookie；
- 认证头；
- 安全问题或完整敏感账号信息。

---

### 3.2 `get_settings`

**模块：** `profile`  
**权限：** `READ`  
**输入：** 无  
**是否需要真实数据：** 是  
**上游映射：** `get_userprofile_settings`

返回：

- 单位制；
- 时区；
- 基本显示偏好；
- Garmin 可提供的非敏感设置。

如果上游接口不返回某项设置，返回 `null` 或 `DATA_NOT_FOUND`，不能伪造默认值。

---

### 3.3 `get_recent_activities`

**模块：** `activities`  
**权限：** `READ`  
**上游映射：** `get_activities`

输入：

```json
{
  "start": 0,
  "limit": 20
}
```

约束：

- `start >= 0`
- `1 <= limit <= 100`
- 默认 `start=0`
- 默认 `limit=20`

返回：

- 活动 ID；
- 活动名称；
- 活动类型；
- 开始时间；
- 距离；
- 时长；
- 摘要字段。

不默认返回大型 GPS 轨迹或完整图表数据。

---

### 3.4 `get_activity`

**模块：** `activities`  
**权限：** `READ`  
**上游映射：** `get_activity`

输入：

```json
{
  "activity_id": 123456789
}
```

约束：

- `activity_id` 必须是正整数；
- 不存在时返回 `DATA_NOT_FOUND`；
- 不默认下载大型详情数据；
- 不执行删除、修改或标注操作。

---

### 3.5 `get_daily_steps`

**模块：** `health`  
**权限：** `READ`  
**上游映射：** `get_daily_steps` / `get_stats`

输入：

```json
{
  "start_date": "2026-10-27",
  "end_date": "2026-11-02"
}
```

约束：

- ISO 日期 `YYYY-MM-DD`；
- `end_date >= start_date`；
- 第一版范围不超过 31 天。

返回：

- 每日步数；
- 有效日期；
- 缺失日期；
- 数据覆盖率。

缺失数据必须标记为 `MISSING`，不能按 0 计算。

---

### 3.6 `get_sleep_summary`

**模块：** `health`  
**权限：** `READ`  
**上游映射：** `get_sleep_summary`

输入：

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
- 清醒时间；
- 睡眠开始/结束时间；
- 数据状态。

---

### 3.7 `get_stress_summary`

**模块：** `health`  
**权限：** `READ`  
**上游映射：** `get_stress_summary`

输入：

```json
{
  "date": "2026-11-02"
}
```

返回：

- 平均压力；
- 最大压力；
- 压力数据状态；
- 可用时提供摘要指标。

不能把压力数值解释成疾病、焦虑症或医学风险。

---

### 3.8 `get_hrv_summary`

**模块：** `health`  
**权限：** `READ`  
**上游映射：** `get_hrv_data` / `get_hrv_trend`

输入：

```json
{
  "start_date": "2026-10-27",
  "end_date": "2026-11-02"
}
```

返回：

- 每日 HRV；
- 有效点数量；
- 平均值；
- 趋势方向；
- 缺失数据；
- 数据覆盖率。

当有效点少于 3 个时，趋势必须返回 `UNKNOWN`，不能强行给出升降结论。

---

### 3.9 `get_body_composition`

**模块：** `health`  
**权限：** `READ`  
**上游映射：** `get_body_composition`

输入：

```json
{
  "start_date": "2026-10-27",
  "end_date": "2026-11-02"
}
```

返回：

- 体重；
- 体脂率；
- 肌肉量（若上游提供）；
- BMI（若上游提供）；
- 测量日期；
- 数据状态。

没有智能秤数据时返回 `DATA_NOT_FOUND` 或空数组，不能生成虚构数据。

---

### 3.10 `get_training_status`

**模块：** `training`  
**权限：** `READ`  
**上游映射：** `get_training_status`

输入：

```json
{
  "date": "2026-11-02"
}
```

返回：

- 训练状态；
- 负荷状态；
- VO2 Max（若上游提供）；
- 恢复信息；
- 数据日期。

---

### 3.11 `get_training_readiness`

**模块：** `training`  
**权限：** `READ`  
**上游映射：** `get_training_readiness`

输入：

```json
{
  "date": "2026-11-02"
}
```

返回：

- 准备度分数；
- 贡献因素；
- 数据状态；
- 日期。

输出不得包含“建议立即训练”“禁止训练”等医疗或强制训练指令。

---

### 3.12 `get_vo2max_trend`

**模块：** `training`  
**权限：** `READ`  
**上游映射：** `get_vo2max_trend`

输入：

```json
{
  "start_date": "2026-10-01",
  "end_date": "2026-11-02"
}
```

返回：

- 每日或有效 VO2 Max 点；
- 趋势；
- 数据覆盖率；
- 缺失日期。

趋势方向只能描述数据变化，不得承诺健康结果。

---

### 3.13 `generate_health_daily_report`

**模块：** `reports`  
**权限：** `READ + 本地输出`  
**上游映射：** 本项目 `ReportEngine`

输入：

```json
{
  "date": "2026-11-02",
  "output_format": "markdown",
  "include_visuals": true,
  "output_dir": null
}
```

支持格式：

- `markdown`
- `html`

日报内容：

- 当日睡眠；
- 静息心率；
- HRV；
- 压力；
- 步数；
- 训练状态；
- 训练准备度；
- 与近期基线比较；
- 异常提示；
- 数据覆盖率；
- 非医学诊断声明。

输出：

- Markdown 文件或 HTML 文件；
- 文件路径；
- 报告摘要；
- 缺失数据说明。

---

### 3.14 `generate_health_weekly_report`

**模块：** `reports`  
**权限：** `READ + 本地输出`  
**上游映射：** 本项目 `ReportEngine`

输入：

```json
{
  "start_date": "2026-10-27",
  "end_date": "2026-11-02",
  "output_format": "markdown",
  "include_visuals": true,
  "output_dir": null
}
```

约束：

- `end_date >= start_date`；
- 默认最大范围 31 天；
- 缺失数据不能按 0 处理。

周报内容：

- 平均睡眠；
- 最低/最高静息心率；
- HRV 趋势；
- 压力变化；
- 训练负荷；
- 活动数量和类型；
- 异常指标提示；
- 数据覆盖率；
- Markdown 表格；
- HTML/SVG 可视化图表；
- 非医学诊断声明。

---

## 4. 报告字段与底层数据工具的关系

报告工具不是简单拼接单个工具结果，而是通过 `ReportEngine` 聚合多个数据源：

```text
generate_health_weekly_report
        │
        ├── get_daily_steps 数据
        ├── 睡眠数据
        ├── 静息心率数据
        ├── HRV 数据
        ├── 压力数据
        ├── 训练状态/准备度
        ├── 活动数据
        └── 训练负荷（可用时）
```

报告工具必须：

1. 独立处理每个数据源失败；
2. 记录有效、部分和缺失日期；
3. 计算覆盖率；
4. 生成 Markdown 或 HTML；
5. 返回文件路径和摘要；
6. 不把报告工具实现为对其他 MCP 工具的递归调用。

---

## 5. 明确排除的工具

第一版明确不加入以下类别。

### 5.1 写操作

排除：

- `set_activity_name`
- `set_activity_type`
- `set_activity_description`
- `set_activity_event_type`
- `set_perceived_effort`
- `set_activity_feel`
- `set_activity_exercise_sets`
- `create_manual_activity`
- `delete_activity`
- `set_heart_rate_zones`

原因：第一版定位为只读、安全、可演示的 MCP 工程项目。

### 5.2 大数据量接口

排除：

- 完整 GPS 轨迹；
- 大型活动详情图表；
- 完整逐秒心率序列；
- 未整理的原始 FIT 数据。

原因：避免 MCP 上下文膨胀和响应超时。

### 5.3 专业设备分析

第一版排除：

- FTP；
- 乳酸阈值；
- Di2；
- 功率曲线；
- 爬坡 VAM；
- FIT 深度解析。

原因：需要专业设备数据，且会扩大测试和演示范围。

### 5.4 破坏性或高风险接口

排除：

- 删除活动；
- 删除食物日志；
- 删除课程；
- 修改训练计划；
- 覆盖用户设置。

---

## 6. 工具过滤名称

`GARMIN_ENABLED_TOOLS` 和 `GARMIN_DISABLED_TOOLS` 使用以下精确名称：

```text
get_profile
get_settings
get_recent_activities
get_activity
get_daily_steps
get_sleep_summary
get_stress_summary
get_hrv_summary
get_body_composition
get_training_status
get_training_readiness
get_vo2max_trend
generate_health_daily_report
generate_health_weekly_report
```

过滤规则：

- 大小写不敏感；
- 去除首尾空格；
- allowlist 优先；
- 未匹配名称输出警告；
- 过滤后为 0 个工具时启动失败；
- 工具名不得在第一版中途更改。

---

## 7. 测试优先级

### P0：必须先测

- `get_profile`
- `get_recent_activities`
- `get_sleep_summary`
- `get_stress_summary`
- `get_training_status`
- `generate_health_weekly_report`

### P1：第一版完成前必须测

- `get_settings`
- `get_activity`
- `get_daily_steps`
- `get_hrv_summary`
- `get_body_composition`
- `get_training_readiness`
- `get_vo2max_trend`
- `generate_health_daily_report`

### 每个工具最低测试要求

- 输入 Schema 正确；
- 非法输入返回 `INVALID_ARGUMENT`；
- mock 数据可成功调用；
- 上游错误映射正确；
- 缺失数据不被误算；
- 响应不包含敏感信息；
- 工具可被 `tools/list` 发现；
- 工具可被 `tools/call` 调用。

---

## 8. 第一版完成标准

以下条件全部满足，才认为工具清单实现完成：

- [ ] `tools/list` 返回 14 个工具；
- [ ] 所有工具名称与本文档一致；
- [ ] 所有工具权限均为 `READ`；
- [ ] 12 个数据工具可使用 mock 数据调用；
- [ ] 2 个报告工具可生成本地文件；
- [ ] Markdown 报告可读；
- [ ] HTML 报告可离线打开；
- [ ] allowlist/denylist 生效；
- [ ] 缺失数据标记正确；
- [ ] 报告包含覆盖率和非医学诊断声明；
- [ ] 没有写操作或破坏性操作；
- [ ] 单元测试和集成测试覆盖全部工具；
- [ ] CI 不依赖真实 Garmin 账号；
- [ ] 日志、响应和报告不包含密码或 Token。

---

## 9. 后续版本预留

第二版以后才考虑：

- `get_devices`
- `get_gear`
- `get_workouts`
- `get_calendar_events`
- `get_nutrition_summary`
- `get_training_load_trend`
- `get_recovery_time_remaining`
- SQLite 历史数据；
- 报告周期对比；
- 月报；
- PNG 图表；
- 受控写操作。

这些工具不计入第一版 14 个工具，也不影响第一版验收。
