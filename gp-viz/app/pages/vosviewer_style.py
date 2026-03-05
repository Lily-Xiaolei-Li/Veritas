#!/usr/bin/env python3
"""VOSviewer-style trend dashboard (improved).
- clear stacked ribbon chart
- explicit trend lines (trend-analysis first-class)
- Top-N annotations on right
- 3D dual-metadata trend view for two fields simultaneously
- VOSviewer "Time-Volume-Weight" 3D variant (x=Year, y=Primary, z=Count, color=Secondary dominant)
"""

import os
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
import numpy as np

API_BASE = os.environ.get('GP_VIZ_API_URL', 'http://gp-viz-api:8080')

DIM_LABEL = {
    'journal': 'Journal',
    'country': 'Country',
    'paper_type': 'Methodology'
}

st.set_page_config(page_title='VOSviewer-style Metadata Evolution', layout='wide')

st.markdown(
    """
    <style>
      .title{font-size:1.9rem;font-weight:800;color:#0f172a;margin-bottom:0.2rem}
      .subtitle{color:#64748b;margin-bottom:1rem}
      .panel{background:#ffffff;border:1px solid #e2e8f0;border-radius:12px;padding:12px;box-shadow:0 1px 4px rgba(0,0,0,.06)}
      .sideItem{background:#f8fafc;border-radius:8px;padding:8px 10px;margin:6px 0}
      .kpi{font-size:1.4rem;font-weight:700}
      .note{font-size:12px;color:#64748b}
      .highlight{background:linear-gradient(120deg,#fef3c7 0%,#fde68a 100%);padding:10px 12px;border-radius:8px;border-left:4px solid #f59e0b;margin:8px 0}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=300)
def fetch_data(limit: int = 124) -> pd.DataFrame:
    r = requests.get(f"{API_BASE}/papers", params={"query": "*", "limit": limit}, timeout=30)
    r.raise_for_status()
    rows = []
    for it in r.json().get('results', []):
        m = it.get('payload', {}).get('meta', {})
        rows.append({
            'paper_id': it.get('id', ''),
            'year': int(m.get('year', 0) or 0),
            'journal': (m.get('journal') or '').replace('&amp;', '&').strip(),
            'country': (m.get('country') or 'Unknown').split(';')[0].strip(),
            'paper_type': m.get('paper_type') or 'Unknown',
        })
    return pd.DataFrame(rows)


def build_matrix(df: pd.DataFrame, key: str, top_n: int) -> tuple[pd.DataFrame, list[str]]:
    top_items = df[key].value_counts().head(top_n).index.tolist()
    years = sorted(df['year'].unique())
    pivot = (
        df[df[key].isin(top_items)]
        .pivot_table(index='year', columns=key, values='paper_id', aggfunc='count', fill_value=0)
        .reindex(years, fill_value=0)
    )
    return pivot, top_items


def build_vosviewer_3d(df: pd.DataFrame, primary: str, secondary: str, top_primary: int, top_secondary: int):
    """
    Build VOSviewer-style 3D: x=Year, y=Primary (category index), z=Count, color=Secondary dominant level
    """
    # Get top items for both dimensions
    top_pri = df[primary].value_counts().head(top_primary).index.tolist()
    top_sec = df[secondary].value_counts().head(top_secondary).index.tolist()
    
    # Filter data
    filt = df[df[primary].isin(top_pri)]
    
    # Build yearly counts per primary item
    yearly_counts = (
        filt.groupby(['year', primary])
        .size()
        .reset_index(name='count')
    )
    
    # Find dominant secondary for each (year, primary) combination
    dominant_secondary = []
    for _, row in yearly_counts.iterrows():
        year, pri_item = row['year'], row[primary]
        subset = filt[(filt['year'] == year) & (filt[primary] == pri_item)]
        if len(subset) > 0:
            # Get most common secondary value
            sec_counts = subset[secondary].value_counts()
            dominant = sec_counts.index[0] if len(sec_counts) > 0 else 'Unknown'
            dominant_count = sec_counts.iloc[0] if len(sec_counts) > 0 else 0
            total = len(subset)
            dominance_ratio = dominant_count / total if total > 0 else 0
        else:
            dominant = 'Unknown'
            dominance_ratio = 0
        dominant_secondary.append({
            'year': year,
            primary: pri_item,
            'count': row['count'],
            'dominant_secondary': dominant,
            'dominance_ratio': dominance_ratio
        })
    
    result_df = pd.DataFrame(dominant_secondary)
    
    # Create mappings for visualization
    pri_mapping = {item: idx for idx, item in enumerate(top_pri)}
    sec_mapping = {item: idx for idx, item in enumerate(top_sec)}
    
    result_df['primary_idx'] = result_df[primary].map(pri_mapping)
    result_df['secondary_idx'] = result_df['dominant_secondary'].map(sec_mapping).fillna(-1)
    
    return result_df, top_pri, top_sec


def plot_ribbon(pivot: pd.DataFrame, title: str):
    colors = px.colors.qualitative.Set3
    fig = go.Figure()
    for i, col in enumerate(pivot.columns):
        y = pivot[col].tolist()
        fig.add_trace(go.Scatter(
            x=pivot.index.tolist(),
            y=y,
            mode='lines',
            name=col,
            line=dict(color='rgba(255,255,255,0.12)', width=0.5),
            stackgroup='one',
            fillcolor=colors[i % len(colors)],
            hovertemplate=f"{col}: %{{y}}<extra>Year %{{x}}</extra>",
        ))

    fig.update_layout(
        title=title,
        xaxis_title='Year',
        yaxis_title='Count',
        height=450,
        legend_title='Items',
        hovermode='x unified',
        margin=dict(l=40, r=20, t=60, b=40),
    )
    return fig


def plot_lines(pivot: pd.DataFrame, title: str):
    long_df = pivot.reset_index().melt(id_vars='year', var_name='item', value_name='count')
    fig = px.line(
        long_df,
        x='year', y='count', color='item',
        title=title,
        markers=True,
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig.update_layout(height=360, legend_title='Items', xaxis_title='Year', yaxis_title='Count')
    return fig


def plot_time_band(pivot: pd.DataFrame):
    band = pivot.copy()
    band[band > 0] = 1
    fig = go.Figure(data=go.Heatmap(
        z=band.T.values,
        x=band.index.astype(str).tolist(),
        y=band.columns.tolist(),
        colorscale=[[0, '#f8fafc'], [1, '#2563eb']],
        showscale=False,
    ))
    fig.update_layout(title='Presence Band (1/0 per year)', height=280, xaxis_title='Year', yaxis_title='Top-N item')
    return fig


def plot_vosviewer_3d(df_vos: pd.DataFrame, primary: str, secondary: str, top_pri: list, top_sec: list):
    """
    VOSviewer-style 3D: x=Year, y=Primary category, z=Count (volume), color=Secondary dominant
    """
    if df_vos.empty:
        return go.Figure()
    
    # Create color mapping for secondary categories
    colors = px.colors.qualitative.Bold + px.colors.qualitative.Vivid
    sec_colors = {sec: colors[i % len(colors)] for i, sec in enumerate(top_sec)}
    sec_colors['Other'] = '#94a3b8'
    
    # Map secondary to colors
    df_vos['color'] = df_vos['dominant_secondary'].map(sec_colors).fillna('#94a3b8')
    
    # Create 3D scatter with size based on count (volume) and color based on secondary
    fig = go.Figure()
    
    # Add traces for each secondary category (for legend)
    for sec in top_sec:
        sec_data = df_vos[df_vos['dominant_secondary'] == sec]
        if len(sec_data) > 0:
            fig.add_trace(go.Scatter3d(
                x=sec_data['year'],
                y=sec_data['primary_idx'],
                z=sec_data['count'],
                mode='markers',
                name=sec,
                marker=dict(
                    size=np.sqrt(sec_data['count']) * 2.5 + 3,
                    color=sec_colors[sec],
                    opacity=0.85,
                    line=dict(color='rgba(255,255,255,0.4)', width=1)
                ),
                text=sec_data.apply(
                    lambda r: f"Year: {r['year']}<br>"
                              f"{DIM_LABEL.get(primary)}: {r[primary]}<br>"
                              f"Papers: {r['count']}<br>"
                              f"Dominant {DIM_LABEL.get(secondary)}: {r['dominant_secondary']} ({r['dominance_ratio']*100:.1f}%)",
                    axis=1
                ),
                hoverinfo='text'
            ))
    
    # Handle "Other" secondary values not in top list
    other_data = df_vos[~df_vos['dominant_secondary'].isin(top_sec)]
    if len(other_data) > 0:
        fig.add_trace(go.Scatter3d(
            x=other_data['year'],
            y=other_data['primary_idx'],
            z=other_data['count'],
            mode='markers',
            name='Other',
            marker=dict(
                size=np.sqrt(other_data['count']) * 2.5 + 3,
                color='#94a3b8',
                opacity=0.6,
            ),
            text=other_data.apply(
                lambda r: f"Year: {r['year']}<br>"
                          f"{DIM_LABEL.get(primary)}: {r[primary]}<br>"
                          f"Papers: {r['count']}<br>"
                          f"Dominant {DIM_LABEL.get(secondary)}: {r['dominant_secondary']}",
                axis=1
            ),
            hoverinfo='text'
        ))
    
    # Add trajectory lines for each primary item (to show trend over time)
    for idx, pri_item in enumerate(top_pri):
        pri_data = df_vos[df_vos[primary] == pri_item].sort_values('year')
        if len(pri_data) > 1:
            fig.add_trace(go.Scatter3d(
                x=pri_data['year'],
                y=[idx] * len(pri_data),
                z=pri_data['count'],
                mode='lines',
                showlegend=False,
                line=dict(color='rgba(100,100,100,0.3)', width=2, dash='dot'),
                hoverinfo='skip'
            ))
    
    fig.update_layout(
        title=f'VOSviewer 3D: Time-Volume-Weight<br><sup>{DIM_LABEL.get(primary)} trends colored by dominant {DIM_LABEL.get(secondary)}</sup>',
        height=600,
        scene=dict(
            xaxis_title='Year (Time)',
            yaxis_title=DIM_LABEL.get(primary),
            zaxis_title='Paper Count (Volume)',
            yaxis=dict(
                tickvals=list(range(len(top_pri))),
                ticktext=top_pri
            ),
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=1.2)
            )
        ),
        legend_title=f'Dominant {DIM_LABEL.get(secondary)}',
        margin=dict(l=0, r=0, t=80, b=0),
    )
    return fig


def plot_vosviewer_2d_projection(df_vos: pd.DataFrame, primary: str, secondary: str, top_pri: list, top_sec: list):
    """
    2D projection of the VOSviewer view: Year vs Primary, bubble size = Count, color = Secondary
    """
    colors = px.colors.qualitative.Bold + px.colors.qualitative.Vivid
    sec_color_map = {sec: colors[i % len(colors)] for i, sec in enumerate(top_sec)}
    
    fig = go.Figure()
    
    for sec in top_sec:
        sec_data = df_vos[df_vos['dominant_secondary'] == sec]
        if len(sec_data) > 0:
            fig.add_trace(go.Scatter(
                x=sec_data['year'],
                y=sec_data[primary],
                mode='markers',
                name=sec,
                marker=dict(
                    size=sec_data['count'] * 3 + 5,
                    color=sec_color_map[sec],
                    opacity=0.7,
                    line=dict(color='white', width=1)
                ),
                text=sec_data.apply(
                    lambda r: f"{r['count']} papers<br>Dominant: {r['dominant_secondary']}",
                    axis=1
                ),
                hovertemplate='%{text}<extra></extra>'
            ))
    
    fig.update_layout(
        title=f'2D Projection: {DIM_LABEL.get(primary)} × Year (bubble = volume, color = {DIM_LABEL.get(secondary)})',
        xaxis_title='Year',
        yaxis_title=DIM_LABEL.get(primary),
        height=500,
        yaxis=dict(categoryorder='array', categoryarray=top_pri),
        legend_title=f'Dominant {DIM_LABEL.get(secondary)}'
    )
    return fig


def sidebar_metrics(df: pd.DataFrame, pivot: pd.DataFrame, top_col: str):
    total = len(df)
    st.markdown(f"<div class='panel'><div class='kpi'>{total}</div><div class='subtitle'>Total Papers</div></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='panel'><div class='kpi'>{df['year'].min()}-{df['year'].max()}</div><div class='subtitle'>Year Span</div></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='panel'><div class='kpi'>{df[top_col].nunique()}</div><div class='subtitle'>Total {DIM_LABEL.get(top_col, top_col.replace('_',' ').title())}</div></div>", unsafe_allow_html=True)

    st.markdown('### Top-N with trend summary')
    if pivot.shape[1] == 0:
        st.info('No data for selected dimension')
        return

    summary_rows = []
    for c in pivot.columns:
        s = pivot[c]
        total_item = int(s.sum())
        peak_year = int(s.idxmax()) if s.max() else int(df['year'].min())
        peak_val = int(s.max()) if s.max() else 0
        first = int(s[s > 0].index.min()) if (s > 0).any() else int(df['year'].min())
        last = int(s[s > 0].index.max()) if (s > 0).any() else int(df['year'].max())
        summary_rows.append((c, total_item, peak_year, peak_val, first, last))

    summary_rows = sorted(summary_rows, key=lambda x: x[1], reverse=True)
    for idx, (c, t, py, pv, f, l) in enumerate(summary_rows, 1):
        w = t / total * 100 if total else 0
        st.markdown(
            f"""
            <div class='sideItem'>
              <div><b>{idx}. {c[:46]}</b></div>
              <div style='color:#334155;margin-bottom:4px'>{t} papers ({w:.1f}%) • peak {pv} in {py}</div>
              <div style='height:7px;background:#e2e8f0;border-radius:4px'>
                <div style='height:7px;width:{w:.1f}%;background:#2563eb;border-radius:4px'></div>
              </div>
              <div style='font-size:12px;color:#64748b'>Window: {f}→{l}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def main():
    st.markdown('<div class="title">📊 VOSviewer-Style Metadata Evolution</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Stacked trend ribbons + top-N trends + VOSviewer 3D Time-Volume-Weight</div>', unsafe_allow_html=True)

    with st.spinner('Loading data ...'):
        df = fetch_data(124)

    if df.empty:
        st.error('No records found.')
        return

    df = df[df['year'] > 1994].copy()

    col1, col2, col3, col4 = st.columns([1.1, 0.9, 1, 1.1])
    with col1:
        mode = st.selectbox('View mode', [
            'Ribbon', 'Trend line', 'Time band', 
            'VOSviewer 3D (Time-Volume-Weight)',
            'VOSviewer 2D Projection'
        ])
    with col2:
        dim = st.selectbox('Primary dimension', options=['journal', 'country', 'paper_type'],
                           format_func=lambda x: DIM_LABEL.get(x, x))
    with col3:
        top_n = st.slider('Top-N items', 3, 12, 8)
    with col4:
        if 'VOSviewer' in mode:
            sec = st.selectbox('Secondary (color)', options=[x for x in ['journal', 'country', 'paper_type'] if x != dim],
                               index=0, format_func=lambda x: DIM_LABEL.get(x, x))
        else:
            sec = 'country'

    if 'VOSviewer' in mode:
        top_sec = st.slider('Top-N (secondary) for coloring', 2, 8, 4)
    else:
        top_sec = 0

    left, right = st.columns([2.8, 1.2])

    vos_modes = ['VOSviewer 3D (Time-Volume-Weight)', 'VOSviewer 2D Projection']
    
    if mode not in vos_modes:
        pivot, cols = build_matrix(df, dim, top_n)
        if pivot.shape[1] > top_n:
            pivot = pivot[cols[:top_n]]

        if mode == 'Ribbon':
            fig = plot_ribbon(pivot, f'{DIM_LABEL[dim]} ribbons over time (Top {top_n})')
        elif mode == 'Trend line':
            fig = plot_lines(pivot, f'{DIM_LABEL[dim]} trend lines (Top {top_n})')
        else:
            fig = plot_time_band(pivot)

        with left:
            st.plotly_chart(fig, width="stretch")
            if mode == 'Ribbon':
                st.caption('Tip: use Trend line for explicit trajectories; Ribbon for compositional shift view.')
        with right:
            sidebar_metrics(df, pivot, dim)
            st.download_button('Export filtered CSV', df.to_csv(index=False), file_name='meta_filtered.csv', mime='text/csv', width="stretch")
            st.download_button('Export pivot CSV', pivot.to_csv().encode('utf-8'), file_name='meta_topN_pivot.csv', mime='text/csv', width="stretch")

    else:
        # VOSviewer modes
        df_vos, top_pri, top_sec = build_vosviewer_3d(df, dim, sec, top_n, top_sec)
        
        if mode == 'VOSviewer 3D (Time-Volume-Weight)':
            fig = plot_vosviewer_3d(df_vos, dim, sec, top_pri, top_sec)
        else:
            fig = plot_vosviewer_2d_projection(df_vos, dim, sec, top_pri, top_sec)

        with left:
            st.plotly_chart(fig, width="stretch")
            st.markdown(
                f"""<div class='highlight'>
                <b>VOSviewer Interpretation Guide:</b><br>
                • <b>X-axis (Year)</b>: Temporal progression<br>
                • <b>Y-axis ({DIM_LABEL.get(dim)})</b>: Primary metadata categories<br>
                • <b>Z-axis / Bubble size</b>: Paper count (volume/weight)<br>
                • <b>Color</b>: Dominant {DIM_LABEL.get(sec)} for that (Year, {DIM_LABEL.get(dim)}) combination<br>
                • <b>Dotted lines</b>: Trend trajectory of each {DIM_LABEL.get(dim)} over time
                </div>""",
                unsafe_allow_html=True
            )
            
            # Show summary table
            st.markdown('### Trend summary by primary item')
            summary = df_vos.groupby(dim).agg({
                'count': ['sum', 'max', 'mean'],
                'year': ['min', 'max'],
                'dominant_secondary': lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else 'N/A'
            }).round(2)
            summary.columns = ['Total Papers', 'Peak Count', 'Avg Count', 'First Year', 'Last Year', 'Most Common Secondary']
            st.dataframe(summary, width="stretch")
            
        with right:
            st.markdown(f"<div class='panel'><div class='kpi'>{len(df_vos)}</div><div class='subtitle'>Data points (Year × Primary)</div></div>", unsafe_allow_html=True)
            st.markdown(f"<div class='panel'><div class='kpi'>{df_vos['dominant_secondary'].nunique()}</div><div class='subtitle'>Distinct dominant {DIM_LABEL.get(sec)}</div></div>", unsafe_allow_html=True)
            
            # Show dominant secondary distribution
            st.markdown('### Dominant secondary distribution')
            dom_counts = df_vos['dominant_secondary'].value_counts().head(6)
            for sec_name, cnt in dom_counts.items():
                pct = cnt / len(df_vos) * 100
                st.markdown(f"{sec_name}: {cnt} ({pct:.1f}%)")
            
            st.download_button('Export VOSviewer data', df_vos.to_csv(index=False), file_name='meta_vosviewer_3d.csv', mime='text/csv', width="stretch")


if __name__ == '__main__':
    main()
