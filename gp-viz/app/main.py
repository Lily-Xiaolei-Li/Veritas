from __future__ import annotations

from collections import defaultdict
import os

import plotly.graph_objects as go
import requests
import streamlit as st

from utils.config import Settings


API_BASE = os.environ.get('GP_VIZ_API_URL', 'http://gp-viz-api:8080')


def _inject_global_style() -> None:
    st.markdown(
        """
        <style>
          .block-container {padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1400px;}
          .gp-banner {
              background: linear-gradient(110deg, #0f172a 0%, #1d4ed8 55%, #38bdf8 100%);
              color: #fff; border-radius: 14px; padding: 1rem 1.2rem; margin-bottom: 1rem;
              box-shadow: 0 8px 20px rgba(15, 23, 42, .20);
          }
          .gp-card {
              border: 1px solid #e5e7eb; border-radius: 12px; padding: .75rem .95rem; margin-bottom: .75rem;
              background: #ffffff;
          }
          .gp-muted {color: #64748b; font-size: .9rem;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _call_api(url: str, timeout: int = 8):
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    return r.json()


def _call_search(base_url: str, query: str, limit: int):
    params = {"query": query, "limit": str(limit)}
    r = requests.get(f"{base_url}/papers", params=params, timeout=8)
    r.raise_for_status()
    return r.json()


def _build_timeline_figure(raw: dict, selected_years: list[int] | None = None, selected_themes: list[str] | None = None) -> go.Figure:
    years = raw.get("years", [])
    series = raw.get("series", [])
    idx = list(range(len(years)))
    if selected_years:
        idx = [i for i, y in enumerate(years) if selected_years[0] <= y <= selected_years[1]]
        years = [years[i] for i in idx]

    fig = go.Figure()
    for item in series:
        if selected_themes and item.get("name") not in selected_themes:
            continue
        values = item.get("values", [])
        values = [values[i] for i in idx] if len(values) >= len(idx) else values
        fig.add_trace(go.Scatter(x=years, y=values, name=item.get("name", ""), mode="lines", stackgroup="one", line=dict(width=0)))

    fig.update_layout(
        title="F1 Timeline: Stacked Area",
        xaxis_title="Year",
        yaxis_title="Count",
        hovermode="x unified",
        height=500,
        margin=dict(l=30, r=20, t=50, b=35),
    )
    return fig


def _build_heatmap_figure(raw: dict, rows_filter: list[str] | None = None, cols_filter: list[str] | None = None) -> go.Figure:
    z = raw.get("z", [])
    x = raw.get("x", [])
    y = raw.get("y", [])

    if cols_filter:
        col_idx = [i for i, c in enumerate(x) if c in cols_filter]
        x = [x[i] for i in col_idx]
        z = [[row[i] for i in col_idx] for row in z]
    if rows_filter:
        row_idx = [i for i, r in enumerate(y) if r in rows_filter]
        y = [y[i] for i in row_idx]
        z = [z[i] for i in row_idx]

    fig = go.Figure(data=go.Heatmap(z=z, x=x, y=y, colorscale="YlGnBu"))
    fig.update_layout(title=f"F2 Theme Matrix: {raw.get('sheet', 'Heatmap')}", xaxis_title="Dimension", yaxis_title="Theme", height=600)
    return fig


def _build_theme_total_bar(timeline: dict) -> go.Figure:
    totals = [(item.get("name", ""), sum(item.get("values", []))) for item in timeline.get("series", [])]
    totals.sort(key=lambda x: x[1], reverse=True)
    x = [i[0] for i in totals]
    y = [i[1] for i in totals]
    fig = go.Figure(go.Bar(x=x, y=y, marker_color="#2563eb"))
    fig.update_layout(title="F3 Theme Total Ranking", xaxis_title="Theme", yaxis_title="Total", height=460)
    return fig


def _build_yearly_total_line(timeline: dict) -> go.Figure:
    years = timeline.get("years", [])
    totals = [0.0] * len(years)
    for s in timeline.get("series", []):
        vals = s.get("values", [])
        for i in range(min(len(vals), len(totals))):
            totals[i] += vals[i]
    fig = go.Figure(go.Scatter(x=years, y=totals, mode="lines+markers", line=dict(color="#0f766e", width=3)))
    fig.update_layout(title="F4 Annual Overall Trend", xaxis_title="Year", yaxis_title="Total", height=460)
    return fig


def _build_theme_share_pie(timeline: dict) -> go.Figure:
    labels = []
    values = []
    for s in timeline.get("series", []):
        labels.append(s.get("name", ""))
        values.append(sum(s.get("values", [])))
    fig = go.Figure(go.Pie(labels=labels, values=values, hole=0.45))
    fig.update_layout(title="F5 Theme Share", height=460)
    return fig


def _build_theme_growth_scatter(timeline: dict) -> go.Figure:
    years = timeline.get("years", [])
    if len(years) < 2:
        return go.Figure()

    growth_map: dict[str, float] = {}
    volume_map: dict[str, float] = {}
    for s in timeline.get("series", []):
        vals = s.get("values", [])
        if len(vals) >= 2:
            growth_map[s.get("name", "")] = vals[-1] - vals[0]
            volume_map[s.get("name", "")] = sum(vals)

    fig = go.Figure(
        data=go.Scatter(
            x=list(volume_map.values()),
            y=[growth_map[k] for k in volume_map.keys()],
            mode="markers+text",
            text=list(volume_map.keys()),
            textposition="top center",
            marker=dict(size=12, color="#7c3aed"),
        )
    )
    fig.update_layout(title="F6 Volume vs Growth", xaxis_title="Total Volume", yaxis_title="Growth (last-first)", height=460)
    return fig


def _build_summary_table(timeline: dict) -> list[dict]:
    data = []
    for s in timeline.get("series", []):
        vals = s.get("values", [])
        data.append(
            {
                "theme": s.get("name", ""),
                "total": round(sum(vals), 2),
                "peak": round(max(vals), 2) if vals else 0,
                "latest": round(vals[-1], 2) if vals else 0,
            }
        )
    return sorted(data, key=lambda x: x["total"], reverse=True)


def _render_download_buttons(fig: go.Figure, base_name: str) -> None:
    try:
        png_data = fig.to_image(format="png", scale=2)
    except Exception:
        st.caption("当前环境缺少图像导出引擎，可用图表工具栏导出。")
        return
    st.download_button("导出 PNG", data=png_data, file_name=f"{base_name}.png", mime="image/png", width="stretch")


def main() -> None:
    st.set_page_config(page_title="GP Visualization System", layout="wide")
    _inject_global_style()

    st.markdown('<div class="gp-banner"><h2 style="margin:0">GP Visualization System</h2><div class="gp-muted" style="color:#e2e8f0">Unified dashboard for F1-F7 analytics and assistant workflow.</div></div>', unsafe_allow_html=True)

    settings = Settings.from_env()
    st.markdown('<div class="gp-card">', unsafe_allow_html=True)
    st.json({"api_base": API_BASE, "collection": settings.data_source_collection, "xlsx": settings.excel_path, "qdrant": f"{settings.qdrant_host}:{settings.qdrant_port}"})
    st.markdown("</div>", unsafe_allow_html=True)

    try:
        health = _call_api(f"{API_BASE}/health")
        st.success(f"API OK: {health}")
    except Exception as exc:
        st.warning(f"API not reachable: {exc}")

    try:
        viz_filters = _call_api(f"{API_BASE}/viz/filters")
        timeline = _call_api(f"{API_BASE}/viz/f1")
        heatmaps = _call_api(f"{API_BASE}/viz/f2").get("sheets", [])
    except Exception as exc:
        st.warning(f"Visualization endpoints unavailable: {exc}")
        viz_filters, timeline, heatmaps = {}, {"years": [], "series": []}, []

    tabs = st.tabs(["F1 时间线", "F2 热力图", "F3 主题排名", "F4 总体趋势", "F5 占比分析", "F6 增长分析", "F7 汇总表"])

    with tabs[0]:
        years = timeline.get("years", [])
        if years:
            y0, y1 = st.slider("年份区间", min_value=min(years), max_value=max(years), value=(min(years), max(years)), step=1)
            chosen_years = [y0, y1]
        else:
            chosen_years = None
        themes = [s.get("name") for s in timeline.get("series", [])]
        selected = st.multiselect("主题筛选", options=themes, default=themes)
        fig = _build_timeline_figure(timeline, chosen_years, selected)
        st.plotly_chart(fig, width="stretch")
        _render_download_buttons(fig, "f1_timeline")

    with tabs[1]:
        sheet_map = {s["sheet"]: s for s in heatmaps}
        selected_sheet = st.selectbox("热力图表", options=list(sheet_map.keys()) if sheet_map else ["(none)"])
        if selected_sheet in sheet_map:
            s = sheet_map[selected_sheet]
            rows = st.multiselect("行筛选", options=s.get("y", []), default=s.get("y", []))
            cols = st.multiselect("列筛选", options=s.get("x", []), default=s.get("x", []))
            fig = _build_heatmap_figure(s, rows_filter=rows, cols_filter=cols)
            st.plotly_chart(fig, width="stretch")
            _render_download_buttons(fig, "f2_heatmap")

    with tabs[2]:
        st.plotly_chart(_build_theme_total_bar(timeline), width="stretch")

    with tabs[3]:
        st.plotly_chart(_build_yearly_total_line(timeline), width="stretch")

    with tabs[4]:
        st.plotly_chart(_build_theme_share_pie(timeline), width="stretch")

    with tabs[5]:
        fig = _build_theme_growth_scatter(timeline)
        if fig.data:
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("数据不足，无法计算增长。")

    with tabs[6]:
        st.dataframe(_build_summary_table(timeline), width="stretch")
        st.caption(f"辅助过滤源：{viz_filters.get('count', 0)} 条去重论文元数据")

    st.divider()
    st.subheader("Search + Assistant")
    query = st.text_input("Query", value="")
    limit = st.slider("Top K", 1, 30, 8)
    if st.button("Run search"):
        if query.strip():
            data = _call_search(API_BASE, query, limit)
            st.success(f"Found {data.get('count', 0)} items")
        else:
            st.warning("请输入检索关键词")


if __name__ == "__main__":
    main()
