from __future__ import annotations

from pathlib import Path

from garmin_connect_mcp.gateway import MockGarminGateway
from garmin_connect_mcp.report.analytics import summarize_report
from garmin_connect_mcp.report.collector import collect_report_data
from garmin_connect_mcp.report.html_svg import render_html
from garmin_connect_mcp.report.markdown import render_markdown
from garmin_connect_mcp.report.models import ReportRequest


def _request(tmp_path: Path, output_format: str = "markdown") -> ReportRequest:
    return ReportRequest(
        start_date="2026-10-27",
        end_date="2026-11-02",
        report_type="weekly",
        output_format=output_format,
        include_visuals=True,
        output_dir=tmp_path / "reports",
    )


def test_collect_and_summarize_mock_report(tmp_path: Path) -> None:
    data = collect_report_data(_request(tmp_path), MockGarminGateway())
    summary = summarize_report(data)

    assert summary["period"]["days"] == 7
    assert summary["coverage"]["ratio"] == 1.0
    assert summary["metrics"]["sleep"]["average"] > 0
    assert summary["metrics"]["hrv"]["coverage"] == 1.0
    assert summary["activities"]["count"] == 5
    assert summary["disclaimer"].endswith("不构成医学诊断或医疗建议。")


def test_markdown_report_contains_core_sections(tmp_path: Path) -> None:
    data = collect_report_data(_request(tmp_path), MockGarminGateway())
    summary = summarize_report(data)
    markdown = render_markdown(data, summary)

    assert markdown.startswith("# Garmin 健康周报")
    assert "## 核心指标" in markdown
    assert "## 每日数据" in markdown
    assert "## 异常指标提示" in markdown
    assert "不构成医学诊断" in markdown
    assert "睡眠：" in markdown


def test_html_report_is_self_contained(tmp_path: Path) -> None:
    data = collect_report_data(_request(tmp_path, "html"), MockGarminGateway())
    summary = summarize_report(data)
    html = render_html(data, summary)

    assert html.startswith("<!doctype html>")
    assert html.count("<svg") >= 4
    assert "<script" not in html
    assert 'src="http' not in html
    assert 'href="http' not in html
    assert "不构成医学诊断" in html
    assert "数据覆盖率" in html
