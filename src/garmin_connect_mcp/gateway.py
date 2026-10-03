"""Garmin gateway protocol, mock client, live client, and gateway factory."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Protocol, runtime_checkable

from garmin_connect_mcp.config import AppConfig
from garmin_connect_mcp.errors import DataNotFoundError, GarminMCPError


@runtime_checkable
class GarminGateway(Protocol):
    """Data-access boundary used by MCP tools and the report engine."""

    def get_profile(self) -> dict[str, Any]: ...

    def get_settings(self) -> dict[str, Any]: ...

    def get_activities(self, start: int, limit: int) -> list[dict[str, Any]]: ...

    def get_activity(self, activity_id: int) -> dict[str, Any]: ...

    def get_daily_steps(
        self, start_date: str, end_date: str
    ) -> list[dict[str, Any]]: ...

    def get_sleep_summary(self, date_value: str) -> dict[str, Any]: ...

    def get_stress_summary(self, date_value: str) -> dict[str, Any]: ...

    def get_hrv_summary(
        self, start_date: str, end_date: str
    ) -> dict[str, Any]: ...

    def get_body_composition(
        self, start_date: str, end_date: str
    ) -> list[dict[str, Any]]: ...

    def get_training_status(self, date_value: str) -> dict[str, Any]: ...

    def get_training_readiness(self, date_value: str) -> dict[str, Any]: ...

    def get_vo2max_trend(
        self, start_date: str, end_date: str
    ) -> dict[str, Any]: ...


def _parse_day(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"Invalid ISO date: {value!r}") from exc


def _date_range(start_date: str, end_date: str) -> list[date]:
    start = _parse_day(start_date)
    end = _parse_day(end_date)
    if end < start:
        raise ValueError("end_date must be greater than or equal to start_date")
    return [start + timedelta(days=offset) for offset in range((end - start).days + 1)]


def _average(values: list[int | float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 2)


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any, *keys: str) -> list[Any]:
    if isinstance(value, list):
        return value
    data = _as_dict(value)
    for key in keys:
        nested = data.get(key)
        if isinstance(nested, list):
            return nested
    return []


def _number(value: Any) -> int | float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def _seconds_to_minutes(value: Any) -> int | None:
    number = _number(value)
    if number is None:
        return None
    return round(number / 60)


def _safe_profile(raw: Any, client: Any) -> dict[str, Any]:
    data = _as_dict(raw)
    user = _as_dict(data.get("userData"))
    display_name = user.get("displayName")
    if not display_name:
        try:
            display_name = client.get_full_name()
        except Exception:
            display_name = None
    return {
        "user_id": data.get("id"),
        "display_name": display_name,
        "connect_date": data.get("connectDate"),
        "source_type": data.get("sourceType"),
    }


def _safe_settings(raw: Any) -> dict[str, Any]:
    data = _as_dict(raw)
    keys = (
        "displayName",
        "measurementSystem",
        "timeZone",
        "dateFormat",
        "timeFormat",
        "firstDayOfWeek",
        "preferredLocale",
        "availableTrainingDays",
        "numberFormat",
        "heartRateFormat",
    )
    return {key: data.get(key) for key in keys if data.get(key) is not None}


def _extract_sleep_summary(raw: Any, date_value: str) -> dict[str, Any]:
    data = _as_dict(raw)
    daily = _as_dict(data.get("dailySleepDTO"))
    scores = _as_dict(daily.get("sleepScores"))
    overall = _as_dict(scores.get("overall"))
    result: dict[str, Any] = {
        "date": daily.get("calendarDate") or date_value,
        "total_minutes": _seconds_to_minutes(daily.get("sleepTimeSeconds")),
        "deep_minutes": _seconds_to_minutes(daily.get("deepSleepSeconds")),
        "light_minutes": _seconds_to_minutes(daily.get("lightSleepSeconds")),
        "rem_minutes": _seconds_to_minutes(daily.get("remSleepSeconds")),
        "awake_minutes": _seconds_to_minutes(daily.get("awakeSleepSeconds")),
        "sleep_score": overall.get("value"),
        "sleep_start": daily.get("sleepStartTimestampLocal"),
        "sleep_end": daily.get("sleepEndTimestampLocal"),
        "resting_heart_rate_bpm": daily.get("restingHeartRate"),
    }
    result = {key: value for key, value in result.items() if value is not None}
    result["status"] = "VALID" if result.get("total_minutes") is not None else "MISSING"
    return result


def _extract_stress_summary(raw: Any, date_value: str) -> dict[str, Any]:
    data = _as_dict(raw)
    valid_values: list[float] = []
    for item in data.get("stressValuesArray") or []:
        if isinstance(item, (list, tuple)) and len(item) > 1:
            value = _number(item[1])
            if value is not None and value > 0:
                valid_values.append(float(value))
    result: dict[str, Any] = {
        "date": data.get("calendarDate") or date_value,
        "average": data.get("avgStressLevel"),
        "maximum": data.get("maxStressLevel"),
        "data_points_count": len(valid_values),
    }
    if valid_values:
        total = len(valid_values)
        result.update(
            {
                "rest_percent": round(
                    sum(value < 26 for value in valid_values) / total * 100, 1
                ),
                "low_percent": round(
                    sum(26 <= value < 51 for value in valid_values) / total * 100, 1
                ),
                "medium_percent": round(
                    sum(51 <= value < 76 for value in valid_values) / total * 100, 1
                ),
                "high_percent": round(
                    sum(value >= 76 for value in valid_values) / total * 100, 1
                ),
            }
        )
    result = {key: value for key, value in result.items() if value is not None}
    average = result.get("average")
    result["status"] = (
        "VALID"
        if isinstance(average, (int, float)) and not isinstance(average, bool) and average >= 0
        else "MISSING"
    )
    return result


def _extract_hrv_point(raw: Any, date_value: str) -> dict[str, Any]:
    data = _as_dict(raw)
    summary = _as_dict(data.get("hrvSummary"))
    value = summary.get("lastNightAvg")
    return {
        "date": summary.get("calendarDate") or date_value,
        "value": value,
        "weekly_average": summary.get("weeklyAvg"),
        "status": "VALID" if value is not None else "MISSING",
    }


def _curate_readiness_entry(raw: Any) -> dict[str, Any]:
    data = _as_dict(raw)
    result = {
        "date": data.get("calendarDate"),
        "timestamp": data.get("timestampLocal"),
        "score": data.get("score"),
        "level": data.get("level"),
        "feedback": data.get("feedbackShort"),
        "sleep_score": data.get("sleepScore"),
        "recovery_time_hours": (
            round(data["recoveryTime"] / 60, 1)
            if isinstance(_number(data.get("recoveryTime")), (int, float))
            else None
        ),
        "acute_load": data.get("acuteLoad"),
        "hrv_weekly_average": data.get("hrvWeeklyAverage"),
    }
    return {key: value for key, value in result.items() if value is not None}


def _extract_training_status(raw: Any, date_value: str) -> dict[str, Any]:
    data = _as_dict(raw)
    recent = _as_dict(data.get("mostRecentTrainingStatus"))
    latest = _as_dict(recent.get("latestTrainingStatusData"))

    # Garmin nests training status under device IDs. Select the first record
    # that actually carries status fields instead of returning the device map.
    device_data: dict[str, Any] = {}
    if "trainingStatus" in latest or "trainingStatusFeedbackPhrase" in latest:
        device_data = latest
    else:
        for candidate in latest.values():
            candidate_data = _as_dict(candidate)
            if "trainingStatus" in candidate_data or "trainingStatusFeedbackPhrase" in candidate_data:
                device_data = candidate_data
                break

    vo2_section = _as_dict(data.get("mostRecentVO2Max"))
    generic = _as_dict(vo2_section.get("generic"))
    cycling = _as_dict(vo2_section.get("cycling"))
    result = {
        "date": device_data.get("calendarDate") or date_value,
        "status": (
            device_data.get("trainingStatusFeedbackPhrase")
            or device_data.get("trainingStatus")
            or device_data.get("status")
        ),
        "training_status_code": device_data.get("trainingStatus"),
        "sport": device_data.get("sport"),
        "fitness_trend": device_data.get("fitnessTrend"),
        "vo2_max_running": generic.get("vo2MaxPreciseValue")
        or generic.get("vo2MaxValue"),
        "vo2_max_cycling": cycling.get("vo2MaxPreciseValue")
        or cycling.get("vo2MaxValue"),
        "acute_load": _as_dict(device_data.get("acuteTrainingLoadDTO")).get(
            "dailyTrainingLoadAcute"
        )
        or _as_dict(device_data.get("acuteTrainingLoadDTO")).get(
            "acuteTrainingLoad"
        ),
    }
    return {key: value for key, value in result.items() if value is not None}


def _extract_body_points(raw: Any) -> list[dict[str, Any]]:
    data = _as_dict(raw)
    entries = _as_list(data, "dateWeightList")
    points: list[dict[str, Any]] = []
    for item in entries:
        entry = _as_dict(item)
        if not entry:
            continue
        points.append(
            {
                "date": entry.get("date") or entry.get("calendarDate"),
                "weight_kg": entry.get("weight") or entry.get("weightKg"),
                "body_fat_percent": entry.get("bodyFat") or entry.get("bodyFatPercent"),
                "bmi": entry.get("bmi"),
                "muscle_mass": entry.get("muscleMass"),
                "status": "VALID",
            }
        )
    return points


def _extract_vo2_value(raw: Any) -> float | None:
    data = _as_dict(raw)
    vo2_section = _as_dict(data.get("mostRecentVO2Max"))
    containers = (
        _as_dict(vo2_section.get("generic")),
        _as_dict(vo2_section.get("cycling")),
        _as_dict(data.get("userData")),
        data,
    )
    keys = (
        "vo2MaxPreciseValue",
        "vo2MaxValue",
        "vo2MaxRunning",
        "vo2MaxCycling",
        "vo2Max",
    )
    for container in containers:
        for key in keys:
            value = _number(container.get(key))
            if value is not None:
                return float(value)
    return None


class MockGarminGateway:
    """Deterministic offline Garmin gateway for development and tests."""

    def __init__(self) -> None:
        self._activities: list[dict[str, Any]] = [
            {
                "activity_id": 100001,
                "activity_name": "Morning Run",
                "activity_type": "running",
                "start_date": "2026-11-02",
                "distance": 5200,
                "duration": 1620,
            },
            {
                "activity_id": 100002,
                "activity_name": "Strength Training",
                "activity_type": "strength_training",
                "start_date": "2026-11-01",
                "distance": 0,
                "duration": 2700,
            },
            {
                "activity_id": 100003,
                "activity_name": "Cycling",
                "activity_type": "cycling",
                "start_date": "2026-10-31",
                "distance": 24000,
                "duration": 4500,
            },
            {
                "activity_id": 100004,
                "activity_name": "Evening Walk",
                "activity_type": "walking",
                "start_date": "2026-10-30",
                "distance": 3100,
                "duration": 2400,
            },
            {
                "activity_id": 100005,
                "activity_name": "Pool Swim",
                "activity_type": "swimming",
                "start_date": "2026-10-29",
                "distance": 1500,
                "duration": 2100,
            },
        ]

    def get_profile(self) -> dict[str, Any]:
        return {
            "display_name": "Demo Athlete",
            "user_id": "mock-user-001",
            "avatar_url": None,
            "region": "mock",
        }

    def get_settings(self) -> dict[str, Any]:
        return {
            "unit_system": "metric",
            "time_zone": "Asia/Shanghai",
            "first_day_of_week": "monday",
            "distance_format": "kilometer",
        }

    def get_activities(self, start: int, limit: int) -> list[dict[str, Any]]:
        if start < 0:
            raise ValueError("start must be >= 0")
        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100")
        return [dict(item) for item in self._activities[start : start + limit]]

    def get_activity(self, activity_id: int) -> dict[str, Any]:
        for item in self._activities:
            if item["activity_id"] == activity_id:
                return dict(item)
        raise DataNotFoundError(f"Activity not found: {activity_id}")

    def get_daily_steps(
        self, start_date: str, end_date: str
    ) -> list[dict[str, Any]]:
        points: list[dict[str, Any]] = []
        for day in _date_range(start_date, end_date):
            points.append(
                {
                    "date": day.isoformat(),
                    "steps": 7200 + (day.toordinal() % 8) * 650,
                    "status": "VALID",
                }
            )
        return points

    def get_sleep_summary(self, date_value: str) -> dict[str, Any]:
        day = _parse_day(date_value)
        total = 390 + (day.toordinal() % 5) * 15
        deep = 90 + (day.toordinal() % 4) * 10
        rem = 95 + (day.toordinal() % 3) * 10
        light = total - deep - rem - 20
        return {
            "date": day.isoformat(),
            "total_minutes": total,
            "deep_minutes": deep,
            "rem_minutes": rem,
            "light_minutes": light,
            "awake_minutes": 20,
            "status": "VALID",
        }

    def get_stress_summary(self, date_value: str) -> dict[str, Any]:
        day = _parse_day(date_value)
        average = 27 + (day.toordinal() % 8)
        return {
            "date": day.isoformat(),
            "average": average,
            "maximum": average + 24,
            "status": "VALID",
        }

    def get_hrv_summary(
        self, start_date: str, end_date: str
    ) -> dict[str, Any]:
        points: list[dict[str, Any]] = []
        values: list[int] = []
        for day in _date_range(start_date, end_date):
            value = 42 + (day.toordinal() % 10)
            values.append(value)
            points.append(
                {"date": day.isoformat(), "value": value, "status": "VALID"}
            )
        first = values[0] if values else 0
        last = values[-1] if values else 0
        if last > first * 1.05:
            trend = "UP"
        elif last < first * 0.95:
            trend = "DOWN"
        else:
            trend = "STABLE"
        return {
            "points": points,
            "average": _average(values),
            "trend": trend,
            "coverage": 1.0,
        }

    def get_body_composition(
        self, start_date: str, end_date: str
    ) -> list[dict[str, Any]]:
        points: list[dict[str, Any]] = []
        for index, day in enumerate(_date_range(start_date, end_date)):
            if day.toordinal() % 2 == 0:
                points.append(
                    {
                        "date": day.isoformat(),
                        "weight_kg": round(68.5 - index * 0.05, 1),
                        "body_fat_percent": round(18.2 - index * 0.03, 1),
                        "status": "VALID",
                    }
                )
        return points

    def get_training_status(self, date_value: str) -> dict[str, Any]:
        day = _parse_day(date_value)
        statuses = ["productive", "maintaining", "recovery", "productive"]
        return {
            "date": day.isoformat(),
            "status": statuses[day.toordinal() % len(statuses)],
            "vo2max": 48 + day.toordinal() % 3,
            "status_source": "mock",
        }

    def get_training_readiness(self, date_value: str) -> dict[str, Any]:
        day = _parse_day(date_value)
        score = 55 + day.toordinal() % 35
        return {
            "date": day.isoformat(),
            "score": score,
            "level": "high" if score >= 75 else "moderate" if score >= 55 else "low",
            "status": "VALID",
        }

    def get_vo2max_trend(
        self, start_date: str, end_date: str
    ) -> dict[str, Any]:
        points: list[dict[str, Any]] = []
        values: list[float] = []
        for day in _date_range(start_date, end_date):
            value = round(47.5 + (day.toordinal() % 7) * 0.2, 1)
            values.append(value)
            points.append(
                {"date": day.isoformat(), "value": value, "status": "VALID"}
            )
        return {
            "points": points,
            "average": _average(values),
            "coverage": 1.0,
        }


class LiveGarminGateway:
    """Read-only gateway backed by ``python-garminconnect``."""

    def __init__(self, config: AppConfig) -> None:
        try:
            from garminconnect import (
                Garmin,
                GarminConnectAuthenticationError,
                GarminConnectConnectionError,
                GarminConnectTooManyRequestsError,
            )
        except ModuleNotFoundError as exc:  # pragma: no cover
            raise GarminMCPError(
                "The garminconnect dependency is not installed; run `uv sync`.",
                code="INTERNAL_ERROR",
            ) from exc

        self._config = config
        tokenstore = str(config.token_dir) if config.token_dir else None
        client: Any = None

        try:
            client = Garmin(is_cn=config.is_cn)
            client.login(tokenstore)
        except (
            FileNotFoundError,
            GarminConnectAuthenticationError,
            GarminConnectConnectionError,
            GarminConnectTooManyRequestsError,
        ) as token_error:
            if not config.has_credentials:
                raise GarminMCPError(
                    "Garmin tokens are missing or invalid. Run the authentication "
                    "flow first or set GARMIN_MCP_MOCK=true.",
                    code="AUTH_REQUIRED",
                ) from token_error

            client = Garmin(
                email=config.email,
                password=config.password,
                is_cn=config.is_cn,
                return_on_mfa=True,
            )
            try:
                result1, _ = client.client.login(
                    config.email,
                    config.password,
                    return_on_mfa=True,
                )
            except Exception as exc:  # pragma: no cover - upstream auth errors
                raise GarminMCPError(
                    "Garmin login failed; check credentials, network, and region.",
                    code="AUTH_REQUIRED",
                ) from exc
            if result1 == "needs_mfa":
                raise GarminMCPError(
                    "Garmin MFA is required; complete authentication interactively first.",
                    code="AUTH_REQUIRED",
                )

        self._client = client

    def _require(self, value: Any, message: str) -> Any:
        if not value:
            raise DataNotFoundError(message)
        return value

    def get_profile(self) -> dict[str, Any]:
        raw = self._require(
            self._client.get_user_profile(), "No Garmin profile data found."
        )
        return _safe_profile(raw, self._client)

    def get_settings(self) -> dict[str, Any]:
        raw = self._require(
            self._client.get_userprofile_settings(),
            "No Garmin profile settings found.",
        )
        return _safe_settings(raw)

    def get_activities(self, start: int, limit: int) -> list[dict[str, Any]]:
        if start < 0:
            raise ValueError("start must be >= 0")
        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100")
        raw = self._client.get_activities(start, limit)
        return [
            item
            for item in _as_list(raw, "activityList", "activities")
            if isinstance(item, dict)
        ]

    def get_activity(self, activity_id: int) -> dict[str, Any]:
        raw = self._client.get_activity(str(activity_id))
        return _as_dict(
            self._require(raw, f"Activity not found: {activity_id}")
        )

    def get_daily_steps(
        self, start_date: str, end_date: str
    ) -> list[dict[str, Any]]:
        raw = self._client.get_daily_steps(start_date, end_date)
        points: list[dict[str, Any]] = []
        for item in _as_list(raw, "values"):
            entry = _as_dict(item)
            steps = entry.get("totalSteps", entry.get("steps"))
            points.append(
                {
                    "date": entry.get("calendarDate") or entry.get("date"),
                    "steps": steps,
                    "status": "VALID" if steps is not None else "MISSING",
                }
            )
        return points

    def get_sleep_summary(self, date_value: str) -> dict[str, Any]:
        raw = self._require(
            self._client.get_sleep_data(date_value),
            f"No sleep data found for {date_value}.",
        )
        return _extract_sleep_summary(raw, date_value)

    def get_stress_summary(self, date_value: str) -> dict[str, Any]:
        raw = self._require(
            self._client.get_stress_data(date_value),
            f"No stress data found for {date_value}.",
        )
        return _extract_stress_summary(raw, date_value)

    def get_hrv_summary(
        self, start_date: str, end_date: str
    ) -> dict[str, Any]:
        points: list[dict[str, Any]] = []
        values: list[float] = []
        for day in _date_range(start_date, end_date):
            date_text = day.isoformat()
            try:
                raw = self._client.get_hrv_data(date_text)
            except Exception:
                raw = None
            point = _extract_hrv_point(raw, date_text)
            points.append(point)
            value = _number(point.get("value"))
            if value is not None:
                values.append(float(value))
        valid_count = len(values)
        expected = len(points)
        first = values[0] if values else 0.0
        last = values[-1] if values else 0.0
        if valid_count < 3:
            trend = "UNKNOWN"
        elif last > first * 1.05:
            trend = "UP"
        elif last < first * 0.95:
            trend = "DOWN"
        else:
            trend = "STABLE"
        return {
            "points": points,
            "average": _average(values) if values else None,
            "trend": trend,
            "coverage": round(valid_count / expected, 2) if expected else 0.0,
        }

    def get_body_composition(
        self, start_date: str, end_date: str
    ) -> list[dict[str, Any]]:
        raw = self._client.get_body_composition(start_date, end_date)
        return _extract_body_points(raw)

    def get_training_status(self, date_value: str) -> dict[str, Any]:
        raw = self._require(
            self._client.get_training_status(date_value),
            f"No training status found for {date_value}.",
        )
        return _extract_training_status(raw, date_value)

    def get_training_readiness(self, date_value: str) -> dict[str, Any]:
        raw = self._client.get_training_readiness(date_value)
        if isinstance(raw, list):
            entries = [_curate_readiness_entry(item) for item in raw]
            if not entries:
                raise DataNotFoundError(
                    f"No training readiness data found for {date_value}."
                )
            if len(entries) == 1:
                return entries[0]
            return {"date": date_value, "entries": entries}
        entry = _curate_readiness_entry(raw)
        if not entry:
            raise DataNotFoundError(
                f"No training readiness data found for {date_value}."
            )
        return entry

    def get_vo2max_trend(
        self, start_date: str, end_date: str
    ) -> dict[str, Any]:
        points: list[dict[str, Any]] = []
        values: list[float] = []
        for day in _date_range(start_date, end_date):
            date_text = day.isoformat()
            try:
                status = self._client.get_training_status(date_text)
            except Exception:
                status = None
            value = _extract_vo2_value(status)
            if value is None:
                continue
            values.append(value)
            points.append(
                {
                    "date": date_text,
                    "value": round(value, 1),
                    "status": "VALID",
                    "source": "training_status",
                }
            )

        if not points:
            try:
                profile = self._client.get_user_profile()
            except Exception:
                profile = None
            value = _extract_vo2_value(profile)
            if value is not None:
                points.append(
                    {
                        "date": end_date,
                        "value": round(value, 1),
                        "status": "VALID",
                        "source": "profile",
                    }
                )
                values.append(value)

        expected = len(_date_range(start_date, end_date))
        if values:
            first = values[0]
            last = values[-1]
            if len(values) < 3:
                trend = "UNKNOWN"
            elif last > first * 1.02:
                trend = "UP"
            elif last < first * 0.98:
                trend = "DOWN"
            else:
                trend = "STABLE"
        else:
            trend = "UNKNOWN"
        return {
            "points": points,
            "average": _average(values) if values else None,
            "trend": trend,
            "coverage": round(len(values) / expected, 2) if expected else 0.0,
        }


def create_gateway(
    config: AppConfig,
    *,
    mock_gateway: GarminGateway | None = None,
) -> GarminGateway:
    """Create the configured gateway.

    ``GARMIN_MCP_MOCK=true`` selects the deterministic mock client. Otherwise a
    live read-only ``python-garminconnect`` gateway is created.
    """

    if mock_gateway is not None:
        return mock_gateway
    if config.use_mock:
        return MockGarminGateway()
    return LiveGarminGateway(config)


__all__ = [
    "GarminGateway",
    "MockGarminGateway",
    "LiveGarminGateway",
    "create_gateway",
]

