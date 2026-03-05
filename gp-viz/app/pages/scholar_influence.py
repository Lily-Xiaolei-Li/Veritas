#!/usr/bin/env python3
"""Scholar Influence Analysis Page for GP-Viz.

Analyzes how a specific scholar (e.g., Power, Miller) is cited in the corpus.
Shows citation trends, categories, and network effects over time.
"""

import json
import os
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

API_BASE = os.environ.get('GP_VIZ_API_URL', 'http://gp-viz-api:8080')

st.set_page_config(page_title='Scholar Influence Analysis', layout='wide')

st.markdown(
    """
    <style>
      .title{font-size:1.9rem;font-weight:800;color:#0f172a;margin-bottom:0.2rem}
      .subtitle{color:#64748b;margin-bottom:1rem}
      .metric-card{background:linear-gradient(135deg, #667eea 0%, #764ba2 100%);color:white;padding:1.5rem;border-radius:10px;text-align:center}
      .metric-value{font-size:2.5rem;font-weight:bold}
      .metric-label{font-size:0.9rem;opacity:0.9}
      .cite-category{background:#f8fafc;border-left:4px solid #2563eb;padding:10px 14px;margin:6px 0;border-radius:6px}
    </style>
    """,
    unsafe_allow_html=True,
)


def fetch_scholar_analysis(scholar: str) -> dict:
    """Fetch scholar influence analysis from API."""
    try:
        r = requests.get(f"{API_BASE}/scholar-influence/{scholar}", timeout=60)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API Error: {e}")
        return {}


def plot_citation_trend(plot_data: dict, scholar: str):
    """Plot citation trend over time with stacked categories."""
    if not plot_data or not plot_data.get("years"):
        return go.Figure()
    
    years = plot_data["years"]
    categories = plot_data.get("categories", [])
    stacked = plot_data.get("stacked_data", [])
    
    fig = go.Figure()
    
    # Add total line
    total_counts = [sum(row.get(cat, 0) for cat in categories) for row in stacked]
    fig.add_trace(go.Scatter(
        x=years,
        y=total_counts,
        mode='lines+markers',
        name='Total Citations',
        line=dict(width=3, color='#1e3a5f'),
        marker=dict(size=10),
    ))
    
    # Add stacked areas for categories
    colors = px.colors.qualitative.Set3
    for i, cat in enumerate(categories):
        values = [row.get(cat, 0) for row in stacked]
        if sum(values) > 0:  # Only show if has data
            fig.add_trace(go.Scatter(
                x=years,
                y=values,
                mode='lines',
                name=cat,
                line=dict(width=1),
                stackgroup='one',
                fillcolor=colors[i % len(colors)],
            ))
    
    fig.update_layout(
        title=f'Citation Trend for "{scholar}" Over Time',
        xaxis_title='Year',
        yaxis_title='Number of Citations',
        height=450,
        hovermode='x unified',
        legend=dict(orientation='h', yanchor='bottom', y=-0.3, xanchor='center', x=0.5),
    )
    return fig


def plot_category_distribution(categories: dict, scholar: str):
    """Plot pie chart of citation categories."""
    if not categories:
        return go.Figure()
    
    labels = list(categories.keys())
    values = list(categories.values())
    
    colors = px.colors.qualitative.Set3
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.4,
        marker_colors=[colors[i % len(colors)] for i in range(len(labels))],
        textinfo='label+percent',
        textposition='outside',
    )])
    
    fig.update_layout(
        title=f'Citation Categories for "{scholar}"',
        height=400,
        showlegend=True,
        legend=dict(orientation='h', yanchor='bottom', y=-0.2, xanchor='center', x=0.5),
    )
    return fig


def plot_section_distribution(sections: dict, scholar: str):
    """Plot bar chart of citations by section."""
    if not sections:
        return go.Figure()
    
    sorted_sections = sorted(sections.items(), key=lambda x: x[1], reverse=True)
    labels = [s[0] for s in sorted_sections]
    values = [s[1] for s in sorted_sections]
    
    fig = go.Figure(go.Bar(
        x=labels,
        y=values,
        marker_color='#3b82f6',
        text=values,
        textposition='auto',
    ))
    
    fig.update_layout(
        title=f'Citations by Section for "{scholar}"',
        xaxis_title='Section',
        yaxis_title='Number of Citations',
        height=350,
    )
    return fig


def main():
    st.markdown('<div class="title">📚 Scholar Influence Analysis</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Analyze how scholars (e.g., Power, Miller) are cited in the corpus</div>', unsafe_allow_html=True)
    
    # Input
    col1, col2 = st.columns([2, 1])
    with col1:
        scholar = st.text_input('Scholar Name', value='Power', help='Enter scholar name (e.g., Power, Miller, DeAngelo)')
    with col2:
        st.markdown('<br>', unsafe_allow_html=True)
        analyze_btn = st.button('🔍 Analyze', width="stretch")
    
    if not analyze_btn and not scholar:
        st.info('Enter a scholar name and click Analyze to start')
        return
    
    with st.spinner(f'Analyzing citations for "{scholar}"...'):
        data = fetch_scholar_analysis(scholar)
    
    if not data or data.get('error'):
        st.error(data.get('error', 'No data returned'))
        return
    
    meta = data.get('meta', {})
    
    # Metrics
    st.markdown('### 📊 Overview')
    cols = st.columns(4)
    metrics = [
        ('Total Citations', meta.get('total_citations', 0), '#3b82f6'),
        ('Papers Citing', meta.get('papers_with_citation', 0), '#10b981'),
        ('Categories', len(data.get('categories', {})), '#f59e0b'),
        ('Year Span', f"{min(data.get('time_trend', {}).keys(), default='N/A')}-{max(data.get('time_trend', {}).keys(), default='N/A')}", '#8b5cf6'),
    ]
    
    for col, (label, value, color) in zip(cols, metrics):
        col.markdown(
            f"""<div style="background:{color};color:white;padding:1rem;border-radius:10px;text-align:center">
                <div style="font-size:2rem;font-weight:bold">{value}</div>
                <div style="font-size:0.9rem;opacity:0.9">{label}</div>
            </div>""",
            unsafe_allow_html=True,
        )
    
    # Charts
    st.markdown('### 📈 Trends & Distribution')
    
    tab1, tab2, tab3 = st.tabs(['📈 Citation Trend', '🥧 Category Distribution', '📑 Section Distribution'])
    
    with tab1:
        plot_data = data.get('plot_data', {})
        fig_trend = plot_citation_trend(plot_data, scholar)
        st.plotly_chart(fig_trend, width="stretch")
        st.caption('Shows how citations to this scholar have evolved over time, colored by citation category')
    
    with tab2:
        categories = data.get('categories', {})
        fig_cat = plot_category_distribution(categories, scholar)
        st.plotly_chart(fig_cat, width="stretch")
        st.caption('Categories: theoretical foundation, framework, methodological approach, empirical support, critique/opposition, extension/application, name-dropping')
    
    with tab3:
        sections = data.get('sections', {})
        fig_sec = plot_section_distribution(sections, scholar)
        st.plotly_chart(fig_sec, width="stretch")
    
    # Per-paper breakdown
    st.markdown('### 📄 Per-Paper Breakdown')
    per_paper = data.get('per_paper', {})
    if per_paper:
        df_papers = pd.DataFrame([
            {'Paper ID': pid, 'Citations': info['count'], 'Dominant Category': info['dominant_category']}
            for pid, info in list(per_paper.items())[:20]
        ])
        st.dataframe(df_papers, width="stretch", hide_index=True)
    
    # Sample citations
    st.markdown('### 💬 Sample Citations')
    citations = data.get('citations', [])
    if citations:
        for i, cite in enumerate(citations[:10]):
            with st.expander(f"{i+1}. {cite['paper_id']} ({cite['year'] or 'Unknown'}) - {cite['category']}"):
                st.markdown(f"**Section:** {cite['section']}")
                st.markdown(f"**Context:** {cite['context']}")
                st.markdown(f"**Confidence:** {cite['confidence']:.2f}")
    
    # Export
    st.markdown('### 💾 Export')
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            'Download Full Analysis (JSON)',
            data=json.dumps(data, ensure_ascii=False, indent=2),
            file_name=f'scholar_influence_{scholar}.json',
            mime='application/json',
            width="stretch",
        )


if __name__ == '__main__':
    main()
