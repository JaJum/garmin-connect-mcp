"""Data models for health reports."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class ReportRequest:
    """Validated request for a daily or periodic health report."""

    start_date: str
    end_date: str
    report_type: str
    output_format: str
    include_visuals: bool
    output_dir: Path


@dataclass(slots=True)
class MetricPoint:
    """One dated metric value with its data-quality status."""

    date: str
    value: float | int | None
    status: str = "VALID"
    source: str = "garmin_connect"


@dataclass(slots=True)
class MetricSeries:
    """A named series of dated metric points."""

    key: str
    label: str
    unit: str
    points: list[MetricPoint] = field(default_factory=list)

    @property
    def valid_points(self) -> list[MetricPoint]:
        return [
            point
            for point in self.points
            if point.status == "VALID" and point.value is not None
        ]

    @property
    def values(self) -> list[float]:
        return [float(point.value) for point in self.valid_points]

    @property
    def coverage(self) -> float:
        if not self.points:
            return 0.0
        return round(len(self.valid_points) / len(self.points), 2)


@dataclass(slots=True)
class ReportData:
    """Collected data needed to render one health report."""

    request: ReportRequest
    steps: MetricSeries
    sleep_minutes: MetricSeries
    resting_heart_rate: MetricSeries
    hrv: MetricSeries
    stress: MetricSeries
    training_load: MetricSeries
    vo2max: MetricSeries
    body_composition: list[dict[str, Any]] = field(default_factory=list)
    activities: list[dict[str, Any]] = field(default_factory=list)
    readiness: list[dict[str, Any]] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)


__all__ = [
    "MetricPoint",
    "MetricSeries",
    "ReportData",
    "ReportRequest",
]
