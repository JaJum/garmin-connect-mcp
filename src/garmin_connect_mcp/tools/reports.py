"""Health report MCP tools."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from garmin_connect_mcp.config import AppConfig
from garmin_connect_mcp.errors import GarminMCPError, InvalidArgumentError
from garmin_connect_mcp.report.analytics import summarize_report
from garmin_connect_mcp.report.collector import collect_report_data
from garmin_connect_mcp.report.html_svg import render_html
from garmin_connect_mcp.report.markdown import render_markdown
from garmin_connect_mcp.report.models import ReportRequest
from garmin_connect_mcp.safety import safe_tool_call, source_name


def _parse_date(value: str, *, field: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise InvalidArgumentError(f"{field} must use YYYY-MM-DD") from exc


def _resolve_output_dir(value: str, config: AppConfig) -> Path:
    if value and value.strip():
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = config.report_dir / path
        path = path.resolve(strict=False)
    else:
        path = config.report_dir

    for protected in (config.token_dir, config.token_base64_dir):
        if protected is None:
            continue
        if path == protected or path.is_relative_to(protected):
            raise InvalidArgumentError(
                "output_dir must not be the token directory or a child of it"
            )
    return path


def _build_report(
    gateway: Any,
    config: AppConfig,
    *,
    start_date: str,
    end_date: str,
    report_type: str,
    output_format: str,
    include_visuals: bool,
    output_dir: str,
) -> dict[str, Any]:
    start = _parse_date(start_date, field="start_date")
    end = _parse_date(end_date, field="end_date")
    if end < start:
        raise InvalidArgumentError("end_date must be >= start_date")

    days = (end - start).days + 1
    if days > config.report_max_days:
        raise InvalidArgumentError(
            f"report range cannot exceed {config.report_max_days} days"
        )

    normalized_format = str(output_format or "markdown").strip().lower()
    if normalized_format not in {"markdown", "html"}:
        raise InvalidArgumentError("output_format must be markdown or html")

    request = ReportRequest(
        start_date=start.isoformat(),
        end_date=end.isoformat(),
        report_type=report_type,
        output_format=normalized_format,
        include_visuals=bool(include_visuals),
        output_dir=_resolve_output_dir(output_dir, config),
    )

    data = collect_report_data(request, gateway)
    summary = summarize_report(data)
    content = (
        render_html(data, summary)
        if normalized_format == "html"
        else render_markdown(data, summary)
    )

    extension = "html" if normalized_format == "html" else "md"
    if report_type == "daily":
        filename = f"daily_{start.isoformat()}.{extension}"
    else:
        filename = (
            f"weekly_{start.isoformat()}_{end.isoformat()}.{extension}"
        )
    path = request.output_dir / filename

    try:
        request.output_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    except OSError as exc:
        raise GarminMCPError(
            "The report file could not be written.",
            code="OUTPUT_ERROR",
        ) from exc

    return {
        "report_type": report_type,
        "format": normalized_format,
        "path": str(path),
        "period": summary["period"],
        "coverage": summary["coverage"],
        "metrics": summary["metrics"],
        "activities": summary["activities"],
        "anomalies_count": len(summary["anomalies"]),
        "data_quality": summary["data_quality"],
        "disclaimer": summary["disclaimer"],
    }


def register_tools(app: Any, gateway: Any, config: AppConfig) -> Any:
    """Register the daily and weekly report tools."""

    @app.tool()
    def generate_health_daily_report(
        date: str,
        output_format: str = "markdown",
        include_visuals: bool = True,
        output_dir: str = "",
    ) -> str:
        """Generate a local Garmin health report for one date."""
        return safe_tool_call(
            _build_report,
            gateway,
            config,
            start_date=date,
            end_date=date,
            report_type="daily",
            output_format=output_format,
            include_visuals=include_visuals,
            output_dir=output_dir,
            source=source_name(gateway),
        )

    @app.tool()
    def generate_health_weekly_report(
        start_date: str,
        end_date: str,
        output_format: str = "markdown",
        include_visuals: bool = True,
        output_dir: str = "",
    ) -> str:
        """Generate a local Garmin health report for an inclusive date range."""
        return safe_tool_call(
            _build_report,
            gateway,
            config,
            start_date=start_date,
            end_date=end_date,
            report_type="weekly",
            output_format=output_format,
            include_visuals=include_visuals,
            output_dir=output_dir,
            source=source_name(gateway),
        )

    return app
