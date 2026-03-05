#!/usr/bin/env python3
"""
VOSviewer-like Trend Analysis (Clearer mode)
- ribbon chart with visible trend bands
- explicit trend line panel
- time bars and top-N annotations
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import os
import requests

st.set_page_config(page_title="VOSviewer Trend Analysis", layout="wide", initial_sidebar_state="collapsed")

API_BASE = os.environ.get('GP_VIZ_API_URL', 'http://gp-viz-api:8080')

# Small CSS
st.markdown(
    """
    <style>
    .block-container{padding-top:1rem;}
    .title-box{background:#0f172a;color:white;padding:12px 18px;border-radius:10px;margin-bottom:12px;}
    .muted{color:#64748b}
    </style>
    """, unsafe_allow_html=True
)

@st.cache_data(ttl=300)
def fetch_df():
    r = requests.get(f"{API_BASE}/papers", params={"query":"*", "limit":124}, timeout=20)
    r.raise_for_status()
    rows = []
    for it in r.json().get('results', []):
        m = it.get('payload',{}).get('meta',{})
        rows.append({
            'year': int(m.get('year',0) or 0),
            'journal': (m.get('journal') or '').replace('&amp;','&').strip(),
            'country': ((m.get('country') or 'Unknown').split(';')[0]).strip(),
            'paper_type': m.get('paper_type') or 'Unknown'
        })
    return pd.DataFrame(rows)


def build_time_matrix(df, key, top_n):
    top_items = df[key].value_counts().head(top_n).index.tolist()
    pivot = df[df[key].isin(top_items)].pivot_table(index='year', columns=key, values='year', aggfunc='size', fill_value=0)
    pivot = pivot.sort_index()
    # ensure all years appear
    years = pd.Series(sorted(df['year'].unique()))
    pivot = pivot.reindex(years, fill_value=0)
    return pivot, top_items


def trend_ribbon(df, key, top_n):
    pivot, top_items = build_time_matrix(df, key, top_n)

    # cumulative stack for ribbon
    fig = go.Figure()
    palette = px.colors.qualitative.Vivid
    for i,c in enumerate(top_items):
        vals = pivot[c].tolist()
        fig.add_trace(go.Scatter(
            x=pivot.index.tolist(),
            y=vals,
            mode='lines',
            line=dict(width=1, color='rgba(255,255,255,0.7)'),
            stackgroup='one',
            fillcolor=palette[i % len(palette)],
            name=c,
            hovertemplate=f"{c}<br>Year=%{{x}}<br>Count=%{{y}}<extra></extra>",
        ))
    fig.update_layout(
        title='Stacked trend ribbon (absolute counts)',
        xaxis_title='Year',
        yaxis_title='Number of papers',
        hovermode='x unified',
        height=420,
        margin=dict(l=40,r=20,t=50,b=40),
    )
    return fig, pivot


def trend_lines(df, key, top_n):
    pivot, top_items = build_time_matrix(df, key, top_n)
    tdf = pivot.reset_index().melt(id_vars='year', var_name=key, value_name='count')
    fig = px.line(
        tdf,
        x='year', y='count', color=key,
        title='Explicit trend lines for top entities',
        markers=True
    )
    fig.update_layout(height=360, xaxis_title='Year', yaxis_title='Count', legend_title=key)
    return fig


def heat_band(df, key, top_n):
    pivot, top_items = build_time_matrix(df, key, top_n)
    if pivot.empty:
        return None
    # normalize 0-1
    p2 = pivot.copy()
    if p2.max().max() > 0:
        p2 = (p2 - p2.min())/(p2.max()-p2.min())
    fig = px.imshow(
        p2.T,
        aspect='auto',
        origin='lower',
        labels=dict(x='Year', y=key, color='Normalized intensity'),
        color_continuous_scale='YlGnBu'
    )
    fig.update_layout(title='Density band (normalized)', height=300)
    return fig


def side_panel(df, pivot):
    total = df.shape[0]
    with st.container():
        st.markdown('### 🎯 Top items (selected)')
        for idx,col in enumerate(pivot.columns):
            series = pivot[col]
            total_item = int(series.sum())
            pct = total_item/total*100 if total else 0
            peak_y = int(series.idxmax()) if not series.empty else None
            peak_c = int(series.max()) if not series.empty else 0
            color = px.colors.qualitative.Safe[idx % len(px.colors.qualitative.Safe)]
            st.markdown(f"**{idx+1}. {col[:40]}**  ({total_item}, {pct:.1f}% of sample)")
            st.markdown(f"<div style='height:7px;background:#e2e8f0;border-radius:4px'><div style='height:7px;width:{pct:.1f}%;background:{color};border-radius:4px'></div></div>",unsafe_allow_html=True)
            st.caption(f"Peak: {peak_y}: {peak_c}")


def main():
    st.markdown('<div class="title-box"><h2>📊 VOSviewer-style Trend Analysis</h2><div class="muted">Clearer trend view for journals / countries / methodology</div></div>', unsafe_allow_html=True)

    with st.spinner('Loading 124-paper dataset...'):
        try:
            df = fetch_df()
        except Exception as e:
            st.error(f'Data error: {e}')
            st.stop()

    df = df[df['year'] > 1994]
    if df.empty:
        st.error('No data after filtering')
        st.stop()

    c1,c2,c3 = st.columns([1,1,1])
    with c1:
        dim = st.selectbox('Metadata dimension', ['journal', 'country', 'paper_type'], format_func=lambda x: {'journal':'Journal', 'country':'Country', 'paper_type':'Methodology'}[x])
    with c2:
        top_n = st.slider('Top-N', 3, 12, 8)
    with c3:
        st.metric('Total Papers', len(df))

    # Summary chips
    y0,y1 = int(df['year'].min()), int(df['year'].max())
    st.caption(f'Time span: {y0}-{y1}; Unique {dim}: {df[dim].nunique()}')

    col_left, col_right = st.columns([2.6,1])

    with col_left:
        fig_ribbon, pivot = trend_ribbon(df, dim, top_n)
        st.plotly_chart(fig_ribbon, width="stretch")

        st.divider()
        fig_lines = trend_lines(df, dim, top_n)
        st.plotly_chart(fig_lines, width="stretch")

        fig_heat = heat_band(df, dim, top_n)
        if fig_heat is not None:
            st.plotly_chart(fig_heat, width="stretch")

    with col_right:
        st.subheader('Top-N annotations')
        side_panel(df, pivot)

    st.download_button('Download raw CSV', df.to_csv(index=False), file_name='meta_124_papers.csv', mime='text/csv')

if __name__ == '__main__':
    main()
