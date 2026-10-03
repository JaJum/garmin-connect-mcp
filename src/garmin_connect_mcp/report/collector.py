"""Collect Garmin data for health reports."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Callable

from garmin_connect_mcp.gateway import GarminGateway
from garmin_connect_mcp.report.models import (
    MetricPoint,
    MetricSeries,
    ReportData,
    ReportRequest,
)


def _dates(start_date: str, end_date: str) -> list[date]:
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    return [
        start + timedelta(days=offset)
        for offset in range((end - start).days + 1)
    ]


def _number(value: Any) -> float | int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def _date_key(item: dict[str, Any]) -> str | None:
    for key in ("date", "calendarDate", "start_date"):
        value = item.get(key)
        if isinstance(value, str) and len(value) >= 10:
            return value[:10]
    for key in ("startTimeGMT", "beginTimestamp", "startTimeLocal"):
        value = item.get(key)
        if isinstance(value, str) and len(value) >= 10:
            return value[:10]
    return None


def _status_for(value: Any, payload: dict[str, Any] | None) -> str:
    if payload and payload.get("status"):
        return str(payload["status"])
    return "VALID" if value is not None else "MISSING"


def _collect_steps(
    gateway: GarminGateway,
    days: list[date],
    source: str,
    errors: dict[str, str],
) -> MetricSeries:
    by_date: dict[str, dict[str, Any]] = {}
    try:
        batch = gateway.get_daily_steps(days[0].isoformat(), days[-1].isoformat())
        for item in batch:
            if isinstance(item, dict):
                item_date = item.get("date") or item.get("calendarDate")
                if item_date:
                    by_date[str(item_date)[:10]] = item
    except Exception:
        errors["steps"] = "Step data could not be loaded."

    points: list[MetricPoint] = []
    for day in days:
        date_text = day.isoformat()
        item = by_date.get(date_text, {})
        value = _number(item.get("steps"))
        points.append(
            MetricPoint(
                date=date_text,
                value=value,
                status=_status_for(value, item),
                source=source,
            )
        )
    return MetricSeries("steps", "步数", "steps", points)


def _collect_sleep(
    gateway: GarminGateway,
    days: list[date],
    source: str,
    errors: dict[str, str],
) -> tuple[MetricSeries, MetricSeries]:
    sleep_points: list[MetricPoint] = []
    rhr_points: list[MetricPoint] = []
    for day in days:
        date_text = day.isoformat()
        payload: dict[str, Any] = {}
        try:
            payload = gateway.get_sleep_summary(date_text)
        except Exception:
            errors.setdefault("sleep", "One or more sleep dates could not be loaded.")
        sleep_value = _number(payload.get("total_minutes"))
        rhr_value = _number(payload.get("resting_heart_rate_bpm"))
        sleep_points.append(
            MetricPoint(
                date_text,
                sleep_value,
                _status_for(sleep_value, payload),
                source,
            )
        )
        rhr_points.append(
            MetricPoint(
                date_text,
                rhr_value,
                _status_for(rhr_value, payload),
                source,
            )
        )
    return (
        MetricSeries("sleep", "睡眠", "minutes", sleep_points),
        MetricSeries(
            "resting_heart_rate", "静息心率", "bpm", rhr_points
        ),
    )


def _collect_stress(
    gateway: GarminGateway,
    days: list[date],
    source: str,
    errors: dict[str, str],
) -> MetricSeries:
    points: list[MetricPoint] = []
    for day in days:
        date_text = day.isoformat()
        payload: dict[str, Any] = {}
        try:
            payload = gateway.get_stress_summary(date_text)
        except Exception:
            errors.setdefault("stress", "One or more stress dates could not be loaded.")
        value = _number(payload.get("average"))
        points.append(
            MetricPoint(
                date_text,
                value,
                _status_for(value, payload),
                source,
            )
        )
    return MetricSeries("stress", "压力", "score", points)


def _collect_training(
    gateway: GarminGateway,
    days: list[date],
    source: str,
    errors: dict[str, str],
) -> tuple[MetricSeries, MetricSeries]:
    load_points: list[MetricPoint] = []
    vo2_points: list[MetricPoint] = []
    for day in days:
        date_text = day.isoformat()
        payload: dict[str, Any] = {}
        try:
            payload = gateway.get_training_status(date_text)
        except Exception:
            errors.setdefault(
                "training_status",
                "One or more training-status dates could not be loaded.",
            )
        load_value = _number(payload.get("acute_load"))
        vo2_value = _number(
            payload.get("vo2_max_running") or payload.get("vo2_max_cycling")
        )
        load_points.append(
            MetricPoint(
                date_text,
                load_value,
                _status_for(load_value, payload),
                source,
            )
        )
        vo2_points.append(
            MetricPoint(
                date_text,
                vo2_value,
                _status_for(vo2_value, payload),
                source,
            )
        )
    return (
        MetricSeries("training_load", "训练负荷", "load", load_points),
        MetricSeries("vo2max", "VO2 Max", "ml/kg/min", vo2_points),
    )


def _series_from_payload(
    payload: dict[str, Any],
    *,
    key: str,
    label: str,
    unit: str,
    value_key: str,
    source: str,
) -> MetricSeries:
    points: list[MetricPoint] = []
    for item in payload.get("points") or []:
        if not isinstance(item, dict):
            continue
        value = _number(item.get(value_key))
        points.append(
            MetricPoint(
                date=str(item.get("date") or ""),
                value=value,
                status=str(
                    item.get("status")
                    or ("VALID" if value is not None else "MISSING")
                ),
                source=str(item.get("source") or source),
            )
        )
    return MetricSeries(key, label, unit, points)


def _collect_activities(
    gateway: GarminGateway,
    request: ReportRequest,
    errors: dict[str, str],
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    try:
        for page in range(5):
            batch = gateway.get_activities(page * 100, 100)
            if not batch:
                break
            for item in batch:
                if not isinstance(item, dict):
                    continue
                item_date = _date_key(item)
                if item_date and request.start_date <= item_date <= request.end_date:
                    selected.append(item)
            if len(batch) < 100:
                break
    except Exception:
        errors["activities"] = "Activity data could not be loaded."
    return selected


def collect_report_data(
    request: ReportRequest,
    gateway: GarminGateway,
) -> ReportData:
    """Collect report data while preserving partial results on upstream errors."""

    days = _dates(request.start_date, request.end_date)
    errors: dict[str, str] = {}
    source = (
        "mock_garmin_gateway"
        if gateway.__class__.__name__ == "MockGarminGateway"
        else "garmin_connect"
    )

    steps = _collect_steps(gateway, days, source, errors)
    sleep, resting_heart_rate = _collect_sleep(gateway, days, source, errors)
    stress = _collect_stress(gateway, days, source, errors)
    training_load, vo2max = _collect_training(gateway, days, source, errors)

    try:
        hrv_payload = gateway.get_hrv_summary(request.start_date, request.end_date)
        hrv = _series_from_payload(
            hrv_payload,
            key="hrv",
            label="HRV",
            unit="ms",
            value_key="value",
            source=source,
        )
    except Exception:
        hrv = MetricSeries("hrv", "HRV", "ms")
        errors["hrv"] = "HRV data could not be loaded."

    try:
        body_composition = gateway.get_body_composition(
            request.start_date, request.end_date
        )
    except Exception:
        body_composition = []
        errors["body_composition"] = "Body composition data could not be loaded."

    readiness: list[dict[str, Any]] = []
    for day in days:
        try:
            item = gateway.get_training_readiness(day.isoformat())
        except Exception:
            errors.setdefault("readiness", "Readiness data is unavailable.")
            continue
        if isinstance(item, dict):
            readiness.append(item)
        elif isinstance(item, list):
            readiness.extend(entry for entry in item if isinstance(entry, dict))

    return ReportData(
        request=request,
        steps=steps,
        sleep_minutes=sleep,
        resting_heart_rate=resting_heart_rate,
        hrv=hrv,
        stress=stress,
        training_load=training_load,
        vo2max=vo2max,
        body_composition=body_composition,
        activities=_collect_activities(gateway, request, errors),
        readiness=readiness,
        errors=errors,
    )


__all__ = ["collect_report_data"]
