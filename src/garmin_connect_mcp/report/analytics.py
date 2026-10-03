"""Aggregate health metrics, trends, coverage, and data alerts."""

from __future__ import annotations

from statistics import mean
from typing import Any

from garmin_connect_mcp.report.models import MetricSeries, ReportData


def _round(value: float | int | None, digits: int = 1) -> float | int | None:
    if value is None:
        return None
    return round(float(value), digits)


def _trend(series: MetricSeries, threshold: float = 0.05) -> str:
    values = series.values
    if len(values) < 3:
        return "UNKNOWN"
    first = values[0]
    last = values[-1]
    if first == 0:
        return "STABLE" if last == 0 else "UP" if last > 0 else "DOWN"
    change = (last - first) / abs(first)
    if change > threshold:
        return "UP"
    if change < -threshold:
        return "DOWN"
    return "STABLE"


def _metric_block(series: MetricSeries, digits: int = 1) -> dict[str, Any]:
    values = series.values
    return {
        "unit": series.unit,
        "average": _round(mean(values), digits) if values else None,
        "minimum": _round(min(values), digits) if values else None,
        "maximum": _round(max(values), digits) if values else None,
        "trend": _trend(series),
        "coverage": series.coverage,
        "valid_points": len(values),
        "total_points": len(series.points),
    }


def _sleep_minutes_display(value: float | None) -> str | None:
    if value is None:
        return None
    total = int(round(value))
    hours, minutes = divmod(total, 60)
    return f"{hours}h {minutes:02d}m"


def _add_alerts(data: ReportData, summary: dict[str, Any]) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []

    def add(
        series: MetricSeries,
        metric_label: str,
        direction: str,
        threshold: float,
        message: str,
    ) -> None:
        values = series.valid_points
        if len(values) < 4:
            return
        baseline = mean(point.value for point in values)
        if baseline <= 0:
            return
        for point in values:
            value = float(point.value)
            changed = (
                direction == "low" and value < baseline * (1 - threshold)
            ) or (
                direction == "high" and value > baseline * (1 + threshold)
            )
            if changed:
                change_percent = round((value - baseline) / baseline * 100, 1)
                alerts.append(
                    {
                        "date": point.date,
                        "metric": metric_label,
                        "value": round(value, 1),
                        "baseline": round(baseline, 1),
                        "change_percent": change_percent,
                        "message": message,
                    }
                )

    add(
        data.sleep_minutes,
        "睡眠",
        "low",
        0.20,
        "睡眠时长明显低于报告期平均值。",
    )
    add(
        data.resting_heart_rate,
        "静息心率",
        "high",
        0.10,
        "静息心率明显高于报告期平均值。",
    )
    add(
        data.hrv,
        "HRV",
        "low",
        0.15,
        "HRV 明显低于报告期平均值。",
    )
    add(
        data.stress,
        "压力",
        "high",
        0.20,
        "压力水平明显高于报告期平均值。",
    )

    load_values = data.training_load.values
    if len(load_values) >= 4:
        baseline = mean(load_values)
        if baseline > 0:
            for point in data.training_load.valid_points:
                value = float(point.value)
                if value > baseline * 1.5:
                    alerts.append(
                        {
                            "date": point.date,
                            "metric": "训练负荷",
                            "value": round(value, 1),
                            "baseline": round(baseline, 1),
                            "change_percent": round(
                                (value - baseline) / baseline * 100, 1
                            ),
                            "message": "训练负荷明显高于报告期平均值。",
                        }
                    )

    if summary["coverage"]["ratio"] < 0.70:
        alerts.append(
            {
                "date": None,
                "metric": "数据覆盖率",
                "value": summary["coverage"]["ratio"],
                "baseline": 0.70,
                "change_percent": None,
                "message": "报告期数据覆盖率偏低，趋势结论可靠性有限。",
            }
        )
    return alerts


def summarize_report(data: ReportData) -> dict[str, Any]:
    """Build the renderer-friendly report summary."""

    core_series = [
        data.steps,
        data.sleep_minutes,
        data.resting_heart_rate,
        data.hrv,
        data.stress,
    ]
    valid_days = {
        point.date
        for series in core_series
        for point in series.valid_points
    }
    expected_days = len(data.steps.points)
    coverage_ratio = (
        round(len(valid_days) / expected_days, 2) if expected_days else 0.0
    )

    activity_by_type: dict[str, int] = {}
    for activity in data.activities:
        activity_type = str(
            activity.get("activity_type")
            or activity.get("activityType")
            or activity.get("typeKey")
            or "unknown"
        )
        if isinstance(activity.get("activityType"), dict):
            activity_type = str(
                activity["activityType"].get("typeKey") or "unknown"
            )
        activity_by_type[activity_type] = activity_by_type.get(activity_type, 0) + 1

    readiness_scores = [
        float(item["score"])
        for item in data.readiness
        if isinstance(item.get("score"), (int, float))
        and not isinstance(item.get("score"), bool)
    ]

    sleep_block = _metric_block(data.sleep_minutes)
    sleep_block["average_display"] = _sleep_minutes_display(
        sleep_block["average"]
    )
    rhr_block = _metric_block(data.resting_heart_rate)
    rhr_block["display_range"] = (
        f"{int(rhr_block['minimum'])}–{int(rhr_block['maximum'])} bpm"
        if rhr_block["minimum"] is not None
        and rhr_block["maximum"] is not None
        else None
    )
    hrv_block = _metric_block(data.hrv)
    stress_block = _metric_block(data.stress)
    load_block = _metric_block(data.training_load)
    load_block["total"] = _round(sum(data.training_load.values), 1)
    steps_block = _metric_block(data.steps, digits=0)
    steps_block["total"] = int(round(sum(data.steps.values))) if data.steps.values else 0
    vo2_block = _metric_block(data.vo2max)

    summary: dict[str, Any] = {
        "report_type": data.request.report_type,
        "period": {
            "start_date": data.request.start_date,
            "end_date": data.request.end_date,
            "days": expected_days,
        },
        "coverage": {
            "ratio": coverage_ratio,
            "valid_days": len(valid_days),
            "expected_days": expected_days,
        },
        "metrics": {
            "sleep": sleep_block,
            "resting_heart_rate": rhr_block,
            "hrv": hrv_block,
            "stress": stress_block,
            "training_load": load_block,
            "steps": steps_block,
            "vo2max": vo2_block,
        },
        "activities": {
            "count": len(data.activities),
            "by_type": activity_by_type,
        },
        "readiness": {
            "count": len(data.readiness),
            "average_score": _round(mean(readiness_scores), 1)
            if readiness_scores
            else None,
        },
        "body_composition": {
            "measurements": len(data.body_composition),
            "latest": data.body_composition[-1] if data.body_composition else None,
        },
        "data_quality": {
            "metric_coverage": {
                "sleep": data.sleep_minutes.coverage,
                "resting_heart_rate": data.resting_heart_rate.coverage,
                "hrv": data.hrv.coverage,
                "stress": data.stress.coverage,
                "training_load": data.training_load.coverage,
                "steps": data.steps.coverage,
            },
            "errors": dict(data.errors),
        },
        "disclaimer": (
            "报告内容根据可穿戴设备数据自动汇总，仅供趋势参考，"
            "不构成医学诊断或医疗建议。"
        ),
    }
    summary["anomalies"] = _add_alerts(data, summary)
    return summary


__all__ = ["summarize_report"]
