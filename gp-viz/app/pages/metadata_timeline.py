#!/usr/bin/env python3
"""
Metadata Timeline Visualization Page
Shows Journal, Country, and Methodology evolution over time
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import requests
import pandas as pd
from collections import Counter
import os

st.set_page_config(page_title="Metadata Timeline Analysis", layout="wide")

st.markdown(
    """
    <style>
    .main-header {
        font-size: 2rem;
        font-weight: bold;
        color: #1f2937;
        margin-bottom: 1rem;
    }
    .section-header {
        font-size: 1.3rem;
        font-weight: 600;
        color: #374151;
        margin-top: 2rem;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #e5e7eb;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
    }
    .metric-value {
        font-size: 2.5rem;
        font-weight: bold;
    }
    .metric-label {
        font-size: 0.9rem;
        opacity: 0.9;
    }
    </style>
    """,
    unsafe_allow_html=True
)

API_BASE = os.environ.get('GP_VIZ_API_URL', 'http://gp-viz-api:8080')

@st.cache_data(ttl=300)
def fetch_all_papers():
    """Fetch all 124 papers from the API"""
    try:
        response = requests.get(f"{API_BASE}/papers?query=*&limit=124", timeout=10)
        response.raise_for_status()
        data = response.json()
        records = []
        for r in data.get('results', []):
            meta = r.get('payload', {}).get('meta', {})
            records.append({
                'paper_id': r.get('id', ''),
                'title': meta.get('title', ''),
                'authors': meta.get('authors', ''),
                'year': int(meta.get('year', 0)) if meta.get('year') else 0,
                'journal': meta.get('journal', '').replace('&amp;', '&'),
                'country': meta.get('country', 'Unknown').split(';')[0].strip(),
                'paper_type': meta.get('paper_type', 'Unknown'),
                'jnl_rank': meta.get('jnl_rank', '')
            })
        return pd.DataFrame(records)
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def fetch_timeline_data():
    """Fetch F1 timeline data"""
    try:
        response = requests.get(f"{API_BASE}/viz/f1", timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching timeline: {e}")
        return {}

def create_year_range_filter(df):
    """Create year range selector"""
    min_year = int(df['year'].min()) if len(df) > 0 else 1995
    max_year = int(df['year'].max()) if len(df) > 0 else 2025
    
    col1, col2 = st.columns(2)
    with col1:
        start_year = st.slider("Start Year", min_year, max_year, min_year, key="start_year")
    with col2:
        end_year = st.slider("End Year", min_year, max_year, max_year, key="end_year")
    
    return start_year, end_year

def safe_groupby_count(df, group_cols, min_count=1):
    """Safely group by and count, handling edge cases"""
    if df.empty or len(df) == 0:
        return pd.DataFrame(columns=group_cols + ['count'])
    result = df.groupby(group_cols).size().reset_index(name='count')
    return result[result['count'] >= min_count]

def render_overview_metrics(df):
    """Render overview metrics cards"""
    if df.empty:
        st.warning("No data available")
        return
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.markdown(
            f"""<div class="metric-card">
                <div class="metric-value">{len(df)}</div>
                <div class="metric-label">Total Papers</div>
            </div>""",
            unsafe_allow_html=True
        )
    
    with col2:
        unique_journals = df['journal'].nunique()
        st.markdown(
            f"""<div class="metric-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
                <div class="metric-value">{unique_journals}</div>
                <div class="metric-label">Unique Journals</div>
            </div>""",
            unsafe_allow_html=True
        )
    
    with col3:
        unique_countries = df['country'].nunique()
        st.markdown(
            f"""<div class="metric-card" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
                <div class="metric-value">{unique_countries}</div>
                <div class="metric-label">Countries</div>
            </div>""",
            unsafe_allow_html=True
        )
    
    with col4:
        qual_count = len(df[df['paper_type'] == 'Empirical - Qual'])
        st.markdown(
            f"""<div class="metric-card" style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);">
                <div class="metric-value">{qual_count}</div>
                <div class="metric-label">Qual Papers</div>
            </div>""",
            unsafe_allow_html=True
        )
    
    with col5:
        quant_count = len(df[df['paper_type'] == 'Empirical - Quant'])
        st.markdown(
            f"""<div class="metric-card" style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);">
                <div class="metric-value">{quant_count}</div>
                <div class="metric-label">Quant Papers</div>
            </div>""",
            unsafe_allow_html=True
        )

def render_journal_analysis(df):
    """Render journal evolution visualizations"""
    st.markdown('<div class="section-header">📚 Journal Evolution Over Time</div>', unsafe_allow_html=True)
    
    if df.empty or 'journal' not in df.columns:
        st.warning("No journal data available")
        return
    
    # Get top journals
    top_n = st.slider("Number of Top Journals to Show", 3, 20, 10, key="journal_top_n")
    top_journals = df['journal'].value_counts().head(top_n).index.tolist()
    
    # Create journal evolution chart
    journal_year = safe_groupby_count(df[df['journal'].isin(top_journals)], ['year', 'journal'])
    
    if journal_year.empty:
        st.warning("Insufficient data for journal timeline")
        return
    
    fig = go.Figure()
    colors = px.colors.qualitative.Set3 + px.colors.qualitative.Pastel
    
    for idx, journal in enumerate(top_journals):
        journal_data = journal_year[journal_year['journal'] == journal]
        if not journal_data.empty:
            fig.add_trace(go.Scatter(
                x=journal_data['year'],
                y=journal_data['count'],
                mode='lines+markers',
                name=journal[:40] + '...' if len(journal) > 40 else journal,
                line=dict(width=3, color=colors[idx % len(colors)]),
                marker=dict(size=8)
            ))
    
    fig.update_layout(
        title=f"Top {top_n} Journals - Publications by Year",
        xaxis_title="Year",
        yaxis_title="Number of Papers",
        hovermode='x unified',
        height=500,
        template='plotly_white',
        legend=dict(orientation='h', yanchor='bottom', y=-0.3, xanchor='center', x=0.5)
    )
    
    st.plotly_chart(fig, width="stretch")
    
    # Journal distribution pie chart
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Journal timeline heatmap by period
        df['period'] = pd.cut(df['year'], 
                              bins=[1994, 1999, 2004, 2009, 2014, 2019, 2025],
                              labels=['1995-99', '2000-04', '2005-09', '2010-14', '2015-19', '2020-25'])
        
        pivot_data = safe_groupby_count(df[df['journal'].isin(top_journals)], ['period', 'journal'])
        if not pivot_data.empty:
            pivot_table = pivot_data.pivot(index='journal', columns='period', values='count').fillna(0)
            
            fig2 = go.Figure(data=go.Heatmap(
                z=pivot_table.values,
                x=[str(c) for c in pivot_table.columns],
                y=[j[:30] + '...' if len(j) > 30 else j for j in pivot_table.index],
                colorscale='YlGnBu',
                text=pivot_table.values,
                texttemplate='%{text:.0f}',
                textfont={'size': 10}
            ))
            
            fig2.update_layout(
                title='Journal × Time Period Heatmap',
                xaxis_title='Time Period',
                yaxis_title='Journal',
                height=400,
                template='plotly_white'
            )
            
            st.plotly_chart(fig2, width="stretch")
    
    with col2:
        # Top journals bar chart
        journal_counts = df['journal'].value_counts().head(top_n)
        fig3 = go.Figure(go.Bar(
            x=journal_counts.values,
            y=[j[:30] + '...' if len(j) > 30 else j for j in journal_counts.index],
            orientation='h',
            marker_color='#3b82f6'
        ))
        fig3.update_layout(
            title='Top Journals (Total)',
            xaxis_title='Number of Papers',
            height=400,
            template='plotly_white',
            margin=dict(l=150)
        )
        st.plotly_chart(fig3, width="stretch")

def render_country_analysis(df):
    """Render geographic evolution visualizations"""
    st.markdown('<div class="section-header">🌍 Geographic Evolution Over Time</div>', unsafe_allow_html=True)
    
    if df.empty or 'country' not in df.columns:
        st.warning("No country data available")
        return
    
    # Clean country data
    df['country_clean'] = df['country'].apply(lambda x: x.split(';')[0].strip() if isinstance(x, str) else 'Unknown')
    
    # Get top countries
    top_n = st.slider("Number of Top Countries to Show", 3, 15, 8, key="country_top_n")
    top_countries = df['country_clean'].value_counts().head(top_n).index.tolist()
    
    country_year = safe_groupby_count(df[df['country_clean'].isin(top_countries)], ['year', 'country_clean'])
    
    if country_year.empty:
        st.warning("Insufficient data for country timeline")
        return
    
    col1, col2 = st.columns([3, 2])
    
    with col1:
        # Stacked area chart for countries
        fig = go.Figure()
        colors = px.colors.qualitative.Bold + px.colors.qualitative.Vivid
        
        for idx, country in enumerate(top_countries):
            country_data = country_year[country_year['country_clean'] == country]
            if not country_data.empty:
                fig.add_trace(go.Scatter(
                    x=country_data['year'],
                    y=country_data['count'],
                    mode='lines',
                    name=country,
                    stackgroup='one',
                    fillcolor=colors[idx % len(colors)],
                    line=dict(width=0.5, color=colors[idx % len(colors)])
                ))
        
        fig.update_layout(
            title=f"Geographic Distribution Over Time (Stacked)",
            xaxis_title="Year",
            yaxis_title="Number of Papers",
            hovermode='x unified',
            height=450,
            template='plotly_white',
            showlegend=True,
            legend=dict(orientation='h', yanchor='bottom', y=-0.25, xanchor='center', x=0.5)
        )
        
        st.plotly_chart(fig, width="stretch")
    
    with col2:
        # Country distribution pie chart
        country_counts = df['country_clean'].value_counts().head(top_n)
        fig2 = go.Figure(go.Pie(
            labels=country_counts.index,
            values=country_counts.values,
            hole=0.4,
            textinfo='label+percent',
            textposition='outside'
        ))
        fig2.update_layout(
            title='Country Distribution',
            height=450,
            template='plotly_white'
        )
        st.plotly_chart(fig2, width="stretch")
    
    # Regional evolution timeline chart
    fig3 = go.Figure()
    for country in top_countries[:5]:  # Show top 5 as separate lines
        country_data = country_year[country_year['country_clean'] == country]
        if not country_data.empty:
            fig3.add_trace(go.Scatter(
                x=country_data['year'],
                y=country_data['count'],
                mode='lines+markers',
                name=country,
                line=dict(width=2)
            ))
    
    fig3.update_layout(
        title="Top 5 Countries - Publication Trends",
        xaxis_title="Year",
        yaxis_title="Number of Papers",
        hovermode='x unified',
        height=400,
        template='plotly_white'
    )
    st.plotly_chart(fig3, width="stretch")

def render_methodology_analysis(df):
    """Render methodology evolution visualizations"""
    st.markdown('<div class="section-header">🔬 Methodology Evolution (Qual vs Quant)</div>', unsafe_allow_html=True)
    
    if df.empty or 'paper_type' not in df.columns:
        st.warning("No methodology data available")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Grouped bar chart by year
        method_year = safe_groupby_count(df, ['year', 'paper_type'])
        
        if not method_year.empty:
            fig = go.Figure()
            
            qual_data = method_year[method_year['paper_type'] == 'Empirical - Qual']
            quant_data = method_year[method_year['paper_type'] == 'Empirical - Quant']
            
            if not qual_data.empty:
                fig.add_trace(go.Bar(
                    x=qual_data['year'],
                    y=qual_data['count'],
                    name='Qualitative',
                    marker_color='#8b5cf6'
                ))
            
            if not quant_data.empty:
                fig.add_trace(go.Bar(
                    x=quant_data['year'],
                    y=quant_data['count'],
                    name='Quantitative',
                    marker_color='#10b981'
                ))
            
            fig.update_layout(
                title='Methodology Distribution by Year',
                xaxis_title='Year',
                yaxis_title='Number of Papers',
                barmode='group',
                height=400,
                template='plotly_white'
            )
            st.plotly_chart(fig, width="stretch")
    
    with col2:
        # Stacked area chart showing proportion
        fig2 = go.Figure()
        
        qual_years = df[df['paper_type'] == 'Empirical - Qual']['year'].value_counts().sort_index()
        quant_years = df[df['paper_type'] == 'Empirical - Quant']['year'].value_counts().sort_index()
        
        all_years = sorted(set(qual_years.index) | set(quant_years.index))
        
        qual_values = [qual_years.get(y, 0) for y in all_years]
        quant_values = [quant_years.get(y, 0) for y in all_years]
        
        fig2.add_trace(go.Scatter(
            x=all_years,
            y=qual_values,
            mode='lines',
            name='Qualitative',
            stackgroup='one',
            fillcolor='rgba(139, 92, 246, 0.7)',
            line=dict(width=0.5, color='#8b5cf6')
        ))
        
        fig2.add_trace(go.Scatter(
            x=all_years,
            y=quant_values,
            mode='lines',
            name='Quantitative',
            stackgroup='one',
            fillcolor='rgba(16, 185, 129, 0.7)',
            line=dict(width=0.5, color='#10b981')
        ))
        
        fig2.update_layout(
            title='Cumulative Methodology Trends',
            xaxis_title='Year',
            yaxis_title='Number of Papers',
            height=400,
            template='plotly_white'
        )
        st.plotly_chart(fig2, width="stretch")
    
    # Period-wise methodology comparison
    df['period'] = pd.cut(df['year'], 
                          bins=[1994, 1999, 2004, 2009, 2014, 2019, 2025],
                          labels=['1995-99', '2000-04', '2005-09', '2010-14', '2015-19', '2020-25'])
    
    period_method = safe_groupby_count(df, ['period', 'paper_type'])
    if not period_method.empty:
        pivot_method = period_method.pivot(index='period', columns='paper_type', values='count').fillna(0)
        
        fig3 = go.Figure()
        if 'Empirical - Qual' in pivot_method.columns:
            fig3.add_trace(go.Bar(
                x=pivot_method.index,
                y=pivot_method['Empirical - Qual'],
                name='Qualitative',
                marker_color='#8b5cf6'
            ))
        if 'Empirical - Quant' in pivot_method.columns:
            fig3.add_trace(go.Bar(
                x=pivot_method.index,
                y=pivot_method['Empirical - Quant'],
                name='Quantitative',
                marker_color='#10b981'
            ))
        
        # Add percentage lines
        total_by_period = pivot_method.sum(axis=1)
        if 'Empirical - Qual' in pivot_method.columns:
            qual_pct = (pivot_method['Empirical - Qual'] / total_by_period * 100).fillna(0)
            fig3.add_trace(go.Scatter(
                x=pivot_method.index,
                y=qual_pct,
                name='Qual %',
                mode='lines+markers',
                yaxis='y2',
                line=dict(color='#7c3aed', width=3, dash='dot')
            ))
        
        fig3.update_layout(
            title='Methodology by Time Period with Qualitative % Trend',
            xaxis_title='Time Period',
            yaxis_title='Number of Papers',
            yaxis2=dict(title='Qualitative %', overlaying='y', side='right', range=[0, 100]),
            barmode='group',
            height=400,
            template='plotly_white',
            legend=dict(orientation='h', yanchor='bottom', y=-0.25, xanchor='center', x=0.5)
        )
        st.plotly_chart(fig3, width="stretch")

def render_theme_analysis(df, timeline_data):
    """Render theme evolution analysis"""
    st.markdown('<div class="section-header">📊 Theme Evolution (From F1 Timeline)</div>', unsafe_allow_html=True)
    
    if timeline_data and 'series' in timeline_data:
        fig = go.Figure()
        
        years = timeline_data.get('years', [])
        series = timeline_data.get('series', [])
        
        colors = {'CSR/ESG/Sustainability': '#06b6d4', 
                  'Performance Audit': '#f59e0b',
                  'Carbon (GHG)': '#10b981',
                  'Other': '#6b7280'}
        
        for s in series:
            theme_name = s.get('name', 'Unknown')
            values = s.get('values', [])
            
            # Calculate statistics
            total = sum(values)
            peak = max(values) if values else 0
            latest = values[-1] if values else 0
            first_nonzero_idx = next((i for i, v in enumerate(values) if v > 0), len(values))
            emergence_year = years[first_nonzero_idx] if first_nonzero_idx < len(years) else years[0]
            
            fig.add_trace(go.Scatter(
                x=years,
                y=values,
                mode='lines',
                name=f"{theme_name} (Total: {total}, Peak: {peak}, Latest: {latest})",
                stackgroup='one',
                fillcolor=colors.get(theme_name, '#888888'),
                line=dict(width=1, color=colors.get(theme_name, '#888888')),
                hovertemplate=f"{theme_name}<br>Year: %{{x}}<br>Papers: %{{y}}<br>Total: {total}<extra></extra>"
            ))
        
        fig.update_layout(
            title='Theme Evolution Over Time (Stacked Area with Statistics)',
            xaxis_title='Year',
            yaxis_title='Number of Papers',
            hovermode='x unified',
            height=500,
            template='plotly_white',
            legend=dict(orientation='h', yanchor='bottom', y=-0.25, xanchor='center', x=0.5)
        )
        
        st.plotly_chart(fig, width="stretch")
        
        # Theme statistics table
        theme_stats = []
        for s in series:
            values = s.get('values', [])
            if values:
                theme_stats.append({
                    'Theme': s.get('name', 'Unknown'),
                    'Total': sum(values),
                    'Peak': max(values),
                    'Latest': values[-1],
                    'First Appearance': years[next((i for i, v in enumerate(values) if v > 0), 0)],
                    'Growth (First→Latest)': values[-1] - next((v for v in values if v > 0), 0)
                })
        
        if theme_stats:
            stats_df = pd.DataFrame(theme_stats).sort_values('Total', ascending=False)
            st.dataframe(stats_df, width="stretch", hide_index=True)

def main():
    st.markdown('<div class="main-header">📚 Metadata Timeline Analysis</div>', unsafe_allow_html=True)
    st.markdown(
        "**Analysis of Journal, Geographic, and Methodology Evolution Over Time** | "
        "Data: 124 Papers (1995-2025)"
    )
    
    # Load data
    with st.spinner("Loading papers data..."):
        df = fetch_all_papers()
        timeline_data = fetch_timeline_data()
    
    if df.empty:
        st.error("Could not load paper data. Please ensure the GP-Viz API is running.")
        return
    
    # Filter valid years
    df = df[df['year'] > 1990]
    
    # Filters
    st.sidebar.header("🔧 Filters")
    
    # Year range filter
    min_year = int(df['year'].min())
    max_year = int(df['year'].max())
    year_range = st.sidebar.slider("Year Range", min_year, max_year, (min_year, max_year))
    
    # Apply filters
    df_filtered = df[(df['year'] >= year_range[0]) & (df['year'] <= year_range[1])]
    
    # Journal filter (optional)
    all_journals = sorted(df_filtered['journal'].unique())
    selected_journals = st.sidebar.multiselect("Filter by Journal (optional)", all_journals)
    if selected_journals:
        df_filtered = df_filtered[df_filtered['journal'].isin(selected_journals)]
    
    # Country filter (optional)
    all_countries = sorted(df_filtered['country_clean'].unique() if 'country_clean' in df_filtered.columns else [])
    selected_countries = st.sidebar.multiselect("Filter by Country (optional)", all_countries)
    if selected_countries and 'country_clean' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['country_clean'].isin(selected_countries)]
    
    # Show filtered count
    st.sidebar.markdown(f"**Filtered Papers:** {len(df_filtered)}")
    
    # Render sections
    render_overview_metrics(df_filtered)
    
    st.divider()
    render_theme_analysis(df_filtered, timeline_data)
    
    st.divider()
    render_journal_analysis(df_filtered)
    
    st.divider()
    render_country_analysis(df_filtered)
    
    st.divider()
    render_methodology_analysis(df_filtered)
    
    # Download section
    st.divider()
    st.markdown('<div class="section-header">💾 Export Data</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        csv = df_filtered.to_csv(index=False)
        st.download_button(
            label="📥 Download Filtered Data (CSV)",
            data=csv,
            file_name=f"paper_metadata_{year_range[0]}-{year_range[1]}.csv",
            mime='text/csv'
        )
    
    with col2:
        json_data = df_filtered.to_json(orient='records', indent=2)
        st.download_button(
            label="📥 Download Filtered Data (JSON)",
            data=json_data,
            file_name=f"paper_metadata_{year_range[0]}-{year_range[1]}.json",
            mime='application/json'
        )

if __name__ == "__main__":
    main()
