"""Render health reports as Markdown."""

from __future__ import annotations

from typing import Any

from garmin_connect_mcp.report.models import MetricSeries, ReportData

_TREND = {"UP": "↑", "DOWN": "↓", "STABLE": "→", "UNKNOWN": "？"}


def _display(value: Any, digits: int = 1) -> str:
    if value is None:
        return "数据不足"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _sleep_display(value: Any) -> str:
    if value is None:
        return "数据不足"
    total = int(round(float(value)))
    hours, minutes = divmod(total, 60)
    return f"{hours}h {minutes:02d}m"


def _sparkline(series: MetricSeries) -> str:
    values = series.values
    if len(values) < 2:
        return "数据不足"
    blocks = "▁▂▃▄▅▆▇█"
    low, high = min(values), max(values)
    span = high - low or 1
    return "".join(
        blocks[int((value - low) / span * (len(blocks) - 1))]
        for value in values
    )


def _index_by_date(series: MetricSeries) -> dict[str, Any]:
    return {
        point.date: point.value
        for point in series.points
        if point.value is not None
    }


def render_markdown(data: ReportData, summary: dict[str, Any]) -> str:
    """Render one self-contained Markdown health report."""

    request = data.request
    title = "Garmin 健康日报" if request.report_type == "daily" else "Garmin 健康周报"
    metrics = summary["metrics"]
    coverage = summary["coverage"]

    lines = [
        f"# {title}",
        "",
        f"- 报告周期：{request.start_date} 至 {request.end_date}",
        f"- 生成格式：Markdown",
        f"- 数据覆盖率：{coverage['ratio']:.0%}（{coverage['valid_days']}/{coverage['expected_days']} 天）",
        "",
        "## 核心指标",
        "",
        "| 指标 | 数值 | 趋势 | 覆盖率 |",
        "|---|---:|:---:|---:|",
        (
            f"| 平均睡眠 | {_sleep_display(metrics['sleep']['average'])} | "
            f"{_TREND.get(metrics['sleep']['trend'], '？')} | {metrics['sleep']['coverage']:.0%} |"
        ),
        (
            f"| 静息心率 | {_display(metrics['resting_heart_rate'].get('display_range'))} | "
            f"{_TREND.get(metrics['resting_heart_rate']['trend'], '？')} | "
            f"{metrics['resting_heart_rate']['coverage']:.0%} |"
        ),
        (
            f"| HRV | {_display(metrics['hrv']['average'])} ms | "
            f"{_TREND.get(metrics['hrv']['trend'], '？')} | {metrics['hrv']['coverage']:.0%} |"
        ),
        (
            f"| 平均压力 | {_display(metrics['stress']['average'])} | "
            f"{_TREND.get(metrics['stress']['trend'], '？')} | {metrics['stress']['coverage']:.0%} |"
        ),
        (
            f"| 训练负荷 | {_display(metrics['training_load'].get('total'))} | "
            f"{_TREND.get(metrics['training_load']['trend'], '？')} | "
            f"{metrics['training_load']['coverage']:.0%} |"
        ),
        (
            f"| 总步数 | {metrics['steps'].get('total', 0):,} | "
            f"{_TREND.get(metrics['steps']['trend'], '？')} | {metrics['steps']['coverage']:.0%} |"
        ),
        (
            f"| 活动数量 | {summary['activities']['count']} | — | — |"
        ),
        "",
    ]

    if request.include_visuals:
        lines.extend(
            [
                "## 趋势概览",
                "",
                f"- 睡眠：`{_sparkline(data.sleep_minutes)}`",
                f"- HRV：`{_sparkline(data.hrv)}`",
                f"- 压力：`{_sparkline(data.stress)}`",
                f"- 静息心率：`{_sparkline(data.resting_heart_rate)}`",
                f"- 训练负荷：`{_sparkline(data.training_load)}`",
                "",
            ]
        )

    lines.extend(
        [
            "## 每日数据",
            "",
            "| 日期 | 步数 | 睡眠 | 静息心率 | HRV | 压力 | 训练负荷 |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    steps = _index_by_date(data.steps)
    sleep = _index_by_date(data.sleep_minutes)
    rhr = _index_by_date(data.resting_heart_rate)
    hrv = _index_by_date(data.hrv)
    stress = _index_by_date(data.stress)
    load = _index_by_date(data.training_load)
    for point in data.steps.points:
        date = point.date
        lines.append(
            f"| {date} "
            f"| {steps.get(date, 0):,} "
            f"| {_sleep_display(sleep.get(date))} "
            f"| {_display(rhr.get(date), 0)} "
            f"| {_display(hrv.get(date), 1)} "
            f"| {_display(stress.get(date), 0)} "
            f"| {_display(load.get(date), 1)} |"
        )

    lines.extend(["", "## 活动摘要", ""])
    if summary["activities"]["count"]:
        for activity_type, count in sorted(summary["activities"]["by_type"].items()):
            lines.append(f"- {activity_type}: {count} 次")
    else:
        lines.append("- 报告期内未找到活动记录。")

    lines.extend(["", "## 异常指标提示", ""])
    if summary["anomalies"]:
        for item in summary["anomalies"]:
            date_text = item["date"] or "整体"
            change = (
                f"，变化 {item['change_percent']:+.1f}%"
                if item.get("change_percent") is not None
                else ""
            )
            lines.append(
                f"- {date_text}：{item['metric']} {item['message']}"
                f"（当前 {item['value']}，参考 {item['baseline']}{change}）"
            )
    else:
        lines.append("- 未发现超过默认阈值的数据异常。")

    lines.extend(["", "## 数据质量", ""])
    for metric, coverage_value in summary["data_quality"]["metric_coverage"].items():
        lines.append(f"- {metric}: {coverage_value:.0%}")
    if summary["data_quality"]["errors"]:
        lines.append("")
        lines.append("### 数据缺失或加载失败")
        for key, message in summary["data_quality"]["errors"].items():
            lines.append(f"- {key}: {message}")

    lines.extend(
        [
            "",
            "---",
            "",
            f"> {summary['disclaimer']}",
            "",
        ]
    )
    return "\n".join(lines)


__all__ = ["render_markdown"]
