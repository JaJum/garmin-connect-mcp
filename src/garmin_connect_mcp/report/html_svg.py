"""Render self-contained HTML health reports with inline SVG charts."""

from __future__ import annotations

from html import escape
from typing import Any

from garmin_connect_mcp.report.models import MetricSeries, ReportData

_TREND = {"UP": "↗", "DOWN": "↘", "STABLE": "→", "UNKNOWN": "?"}


def _fmt(value: Any, digits: int = 1) -> str:
    if value is None:
        return "数据不足"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _fmt_minutes(value: Any) -> str:
    if value is None:
        return "数据不足"
    total = int(round(float(value)))
    hours, minutes = divmod(total, 60)
    return f"{hours}h {minutes:02d}m"


def _chart_shell(title: str, body: str) -> str:
    return (
        '<section class="chart-card">'
        f"<h3>{escape(title)}</h3>"
        f'<div class="chart">{body}</div>'
        "</section>"
    )


def _empty_chart(message: str = "数据不足") -> str:
    return (
        '<div class="empty-chart">'
        f"<span>{escape(message)}</span>"
        "</div>"
    )


def _line_chart(
    title: str,
    series: MetricSeries,
    *,
    color: str,
) -> str:
    points = [(point.date, float(point.value)) for point in series.valid_points]
    if not points:
        return _chart_shell(title, _empty_chart())

    width, height = 760, 230
    left, right, top, bottom = 58, 22, 24, 46
    plot_width = width - left - right
    plot_height = height - top - bottom
    values = [value for _, value in points]
    low, high = min(values), max(values)
    if low == high:
        low -= 1
        high += 1
    span = high - low

    def x(index: int) -> float:
        if len(points) == 1:
            return left + plot_width / 2
        return left + index * plot_width / (len(points) - 1)

    def y(value: float) -> float:
        return top + (high - value) / span * plot_height

    svg = [
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">',
        '<rect x="0" y="0" width="100%" height="100%" rx="12" fill="#ffffff"/>',
    ]
    for tick in range(5):
        tick_value = low + span * tick / 4
        tick_y = y(tick_value)
        svg.append(
            f'<line x1="{left}" y1="{tick_y:.1f}" x2="{width-right}" y2="{tick_y:.1f}" '
            'stroke="#e7edf5" stroke-width="1"/>'
        )
        svg.append(
            f'<text x="{left-10}" y="{tick_y+4:.1f}" text-anchor="end" '
            f'class="axis-label">{tick_value:.1f}</text>'
        )

    polyline = " ".join(f"{x(i):.1f},{y(value):.1f}" for i, (_, value) in enumerate(points))
    svg.append(
        f'<polyline points="{polyline}" fill="none" stroke="{color}" '
        'stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/>'
    )
    for index, (date_text, value) in enumerate(points):
        svg.append(
            f'<circle cx="{x(index):.1f}" cy="{y(value):.1f}" r="4" '
            f'fill="{color}" stroke="#ffffff" stroke-width="2">'
            f"<title>{escape(date_text)}: {value:.1f} {escape(series.unit)}</title>"
            "</circle>"
        )

    label_step = max(1, (len(points) + 5) // 6)
    for index, (date_text, _) in enumerate(points):
        if index % label_step == 0 or index == len(points) - 1:
            svg.append(
                f'<text x="{x(index):.1f}" y="{height-18}" text-anchor="middle" '
                f'class="axis-label">{escape(date_text[5:])}</text>'
            )
    svg.append("</svg>")
    return _chart_shell(title, "".join(svg))


def _bar_chart(
    title: str,
    series: MetricSeries,
    *,
    color: str,
) -> str:
    points = [(point.date, float(point.value)) for point in series.valid_points]
    if not points:
        return _chart_shell(title, _empty_chart())

    width, height = 760, 230
    left, right, top, bottom = 58, 22, 24, 46
    plot_width = width - left - right
    plot_height = height - top - bottom
    values = [value for _, value in points]
    low = min(0.0, min(values))
    high = max(values) or 1.0
    if low == high:
        high = low + 1
    span = high - low
    slot = plot_width / len(points)
    bar_width = max(8.0, min(58.0, slot * 0.62))

    def y(value: float) -> float:
        return top + (high - value) / span * plot_height

    zero_y = y(0)
    svg = [
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">',
        '<rect x="0" y="0" width="100%" height="100%" rx="12" fill="#ffffff"/>',
    ]
    for tick in range(5):
        tick_value = low + span * tick / 4
        tick_y = y(tick_value)
        svg.append(
            f'<line x1="{left}" y1="{tick_y:.1f}" x2="{width-right}" y2="{tick_y:.1f}" '
            'stroke="#e7edf5" stroke-width="1"/>'
        )
        svg.append(
            f'<text x="{left-10}" y="{tick_y+4:.1f}" text-anchor="end" '
            f'class="axis-label">{tick_value:.1f}</text>'
        )

    for index, (date_text, value) in enumerate(points):
        center = left + slot * (index + 0.5)
        value_y = y(value)
        rect_y = min(value_y, zero_y)
        rect_height = max(2.0, abs(zero_y - value_y))
        svg.append(
            f'<rect x="{center-bar_width/2:.1f}" y="{rect_y:.1f}" '
            f'width="{bar_width:.1f}" height="{rect_height:.1f}" rx="5" '
            f'fill="{color}"><title>{escape(date_text)}: {value:.1f} '
            f"{escape(series.unit)}</title></rect>"
        )
        if index % max(1, (len(points) + 5) // 6) == 0 or index == len(points) - 1:
            svg.append(
                f'<text x="{center:.1f}" y="{height-18}" text-anchor="middle" '
                f'class="axis-label">{escape(date_text[5:])}</text>'
            )
    svg.append("</svg>")
    return _chart_shell(title, "".join(svg))


def _daily_rows(data: ReportData) -> str:
    def by_date(series: MetricSeries) -> dict[str, Any]:
        return {
            point.date: point.value
            for point in series.points
            if point.value is not None
        }

    steps = by_date(data.steps)
    sleep = by_date(data.sleep_minutes)
    rhr = by_date(data.resting_heart_rate)
    hrv = by_date(data.hrv)
    stress = by_date(data.stress)
    load = by_date(data.training_load)
    rows = []
    for point in data.steps.points:
        date = point.date
        rows.append(
            "<tr>"
            f"<td>{escape(date)}</td>"
            f"<td>{steps.get(date, 0):,}</td>"
            f"<td>{escape(_fmt_minutes(sleep.get(date)))}</td>"
            f"<td>{escape(_fmt(rhr.get(date), 0))}</td>"
            f"<td>{escape(_fmt(hrv.get(date), 1))}</td>"
            f"<td>{escape(_fmt(stress.get(date), 0))}</td>"
            f"<td>{escape(_fmt(load.get(date), 1))}</td>"
            "</tr>"
        )
    return "".join(rows)


def render_html(data: ReportData, summary: dict[str, Any]) -> str:
    """Render one offline self-contained HTML report with inline SVG charts."""

    request = data.request
    title = "Garmin 健康日报" if request.report_type == "daily" else "Garmin 健康周报"
    metrics = summary["metrics"]
    coverage = summary["coverage"]

    charts = ""
    if request.include_visuals:
        charts = "".join(
            [
                _bar_chart("每日睡眠时长", data.sleep_minutes, color="#5b7cfa"),
                _line_chart("HRV 趋势", data.hrv, color="#12a88f"),
                _line_chart("压力趋势", data.stress, color="#f39c4a"),
                _line_chart("静息心率趋势", data.resting_heart_rate, color="#e45b70"),
                _bar_chart("训练负荷", data.training_load, color="#8a63d2"),
                _bar_chart("每日步数", data.steps, color="#3598db"),
            ]
        )

    anomalies = "".join(
        f'<li><strong>{escape(item.get("date") or "整体")}</strong> '
        f'{escape(item["metric"])}：{escape(item["message"])} '
        f'（当前 {item["value"]}，参考 {item["baseline"]}）</li>'
        for item in summary["anomalies"]
    ) or "<li>未发现超过默认阈值的数据异常。</li>"

    activities = "".join(
        f"<li>{escape(activity_type)}：{count} 次</li>"
        for activity_type, count in sorted(summary["activities"]["by_type"].items())
    ) or "<li>报告期内未找到活动记录。</li>"

    errors = "".join(
        f"<li>{escape(key)}：{escape(message)}</li>"
        for key, message in summary["data_quality"]["errors"].items()
    )

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<style>
:root {{
  --ink: #152238;
  --muted: #64748b;
  --line: #e2e8f0;
  --bg: #f4f7fb;
  --card: #ffffff;
  --blue: #5b7cfa;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  color: var(--ink);
  background: var(--bg);
  font-family: Inter, "Segoe UI", "Microsoft YaHei", sans-serif;
}}
main {{ max-width: 1100px; margin: 0 auto; padding: 36px 22px 56px; }}
header {{
  background: linear-gradient(135deg, #3157d5, #6c63e8);
  color: white; border-radius: 22px; padding: 30px;
  box-shadow: 0 18px 45px rgba(49,87,213,.20);
}}
h1 {{ margin: 0 0 10px; font-size: 32px; }}
.period {{ opacity: .88; }}
.coverage {{
  display: inline-block; margin-top: 18px; padding: 8px 12px;
  border: 1px solid rgba(255,255,255,.28); border-radius: 999px;
  background: rgba(255,255,255,.12);
}}
.grid {{
  display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
  gap: 15px; margin: 22px 0;
}}
.kpi {{
  background: var(--card); border: 1px solid var(--line); border-radius: 17px;
  padding: 18px; box-shadow: 0 8px 25px rgba(30,50,90,.06);
}}
.kpi .label {{ color: var(--muted); font-size: 13px; }}
.kpi .value {{ font-size: 25px; font-weight: 750; margin-top: 7px; }}
.kpi .trend {{ color: var(--muted); margin-top: 5px; font-size: 13px; }}
section.panel, .chart-card {{
  background: var(--card); border: 1px solid var(--line); border-radius: 18px;
  padding: 21px; margin: 18px 0; box-shadow: 0 8px 25px rgba(30,50,90,.05);
}}
h2 {{ margin: 0 0 16px; }}
h3 {{ margin: 0 0 12px; }}
.chart svg {{ width: 100%; height: auto; display: block; }}
.axis-label {{ font-size: 11px; fill: #718096; font-family: inherit; }}
.empty-chart {{
  height: 190px; display: grid; place-items: center; color: var(--muted);
  background: #f8fafc; border-radius: 12px;
}}
table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
th, td {{ padding: 11px 10px; border-bottom: 1px solid var(--line); text-align: right; }}
th:first-child, td:first-child {{ text-align: left; }}
th {{ color: var(--muted); font-weight: 650; }}
ul {{ margin: 8px 0 0; padding-left: 21px; line-height: 1.8; }}
.alerts li::marker {{ color: #e45b70; }}
.disclaimer {{
  margin-top: 24px; border-left: 4px solid var(--blue); padding: 14px 17px;
  background: #eef2ff; color: #344563; border-radius: 10px;
}}
@media (max-width: 700px) {{
  main {{ padding: 18px 10px 35px; }}
  header {{ border-radius: 17px; padding: 22px; }}
  h1 {{ font-size: 25px; }}
  .chart-card {{ padding: 12px; }}
  table {{ font-size: 12px; }}
  th, td {{ padding: 8px 5px; }}
}}
</style>
</head>
<body>
<main>
<header>
  <h1>{escape(title)}</h1>
  <div class="period">{escape(request.start_date)} 至 {escape(request.end_date)}</div>
  <div class="coverage">数据覆盖率 {coverage['ratio']:.0%} · {coverage['valid_days']}/{coverage['expected_days']} 天</div>
</header>

<div class="grid">
  <div class="kpi"><div class="label">平均睡眠</div><div class="value">{escape(_fmt_minutes(metrics['sleep']['average']))}</div><div class="trend">趋势 {_TREND.get(metrics['sleep']['trend'], '?')}</div></div>
  <div class="kpi"><div class="label">静息心率</div><div class="value">{escape(_fmt(metrics['resting_heart_rate'].get('display_range')))}</div><div class="trend">趋势 {_TREND.get(metrics['resting_heart_rate']['trend'], '?')}</div></div>
  <div class="kpi"><div class="label">HRV</div><div class="value">{escape(_fmt(metrics['hrv']['average']))} ms</div><div class="trend">趋势 {_TREND.get(metrics['hrv']['trend'], '?')}</div></div>
  <div class="kpi"><div class="label">平均压力</div><div class="value">{escape(_fmt(metrics['stress']['average']))}</div><div class="trend">趋势 {_TREND.get(metrics['stress']['trend'], '?')}</div></div>
  <div class="kpi"><div class="label">训练负荷</div><div class="value">{escape(_fmt(metrics['training_load'].get('total')))}</div><div class="trend">趋势 {_TREND.get(metrics['training_load']['trend'], '?')}</div></div>
  <div class="kpi"><div class="label">总步数</div><div class="value">{metrics['steps'].get('total', 0):,}</div><div class="trend">活动 {summary['activities']['count']} 次</div></div>
</div>

{charts}

<section class="panel">
  <h2>每日数据</h2>
  <table>
    <thead><tr><th>日期</th><th>步数</th><th>睡眠</th><th>静息心率</th><th>HRV</th><th>压力</th><th>训练负荷</th></tr></thead>
    <tbody>{_daily_rows(data)}</tbody>
  </table>
</section>

<section class="panel">
  <h2>活动摘要</h2>
  <ul>{activities}</ul>
</section>

<section class="panel alerts">
  <h2>异常指标提示</h2>
  <ul>{anomalies}</ul>
</section>

<section class="panel">
  <h2>数据质量</h2>
  <ul>
    <li>睡眠覆盖率：{metrics['sleep']['coverage']:.0%}</li>
    <li>HRV 覆盖率：{metrics['hrv']['coverage']:.0%}</li>
    <li>压力覆盖率：{metrics['stress']['coverage']:.0%}</li>
    <li>训练负荷覆盖率：{metrics['training_load']['coverage']:.0%}</li>
    <li>步数覆盖率：{metrics['steps']['coverage']:.0%}</li>
    {errors}
  </ul>
</section>

<div class="disclaimer">{escape(summary['disclaimer'])}</div>
</main>
</body>
</html>
"""


__all__ = ["render_html"]
