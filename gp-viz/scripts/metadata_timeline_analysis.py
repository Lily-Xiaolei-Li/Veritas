#!/usr/bin/env python3
"""
Metadata Timeline Analysis for GP-Viz
Analyzes Journal, Country, and Methodology evolution over time
"""

import json
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path

def load_papers_data():
    """Load papers data from Qdrant API or JSON"""
    # This would typically call the API, but for now we'll work with sample data structure
    return []

def create_journal_timeline(df, years_range):
    """Create journal evolution timeline"""
    # Group by year and journal
    journal_by_year = df.groupby(['year', 'journal']).size().reset_index(name='count')
    
    # Get top 10 journals overall
    top_journals = df['journal'].value_counts().head(10).index.tolist()
    
    fig = go.Figure()
    
    for journal in top_journals:
        journal_data = journal_by_year[journal_by_year['journal'] == journal]
        fig.add_trace(go.Scatter(
            x=journal_data['year'],
            y=journal_data['count'],
            mode='lines+markers',
            name=journal.replace('&amp;', '&'),
            stackgroup='one'
        ))
    
    fig.update_layout(
        title='Journal Evolution Over Time (Top 10)',
        xaxis_title='Year',
        yaxis_title='Number of Papers',
        hovermode='x unified',
        height=500,
        template='plotly_white'
    )
    
    return fig

def create_country_timeline(df, years_range):
    """Create geographic evolution timeline"""
    # Group by year and country (simplified - take first country if multiple)
    df['country_primary'] = df['country'].apply(lambda x: x.split(';')[0] if isinstance(x, str) else 'Unknown')
    country_by_year = df.groupby(['year', 'country_primary']).size().reset_index(name='count')
    
    # Get top 8 countries
    top_countries = df['country_primary'].value_counts().head(8).index.tolist()
    
    fig = go.Figure()
    
    for country in top_countries:
        country_data = country_by_year[country_by_year['country_primary'] == country]
        fig.add_trace(go.Scatter(
            x=country_data['year'],
            y=country_data['count'],
            mode='lines+markers',
            name=country,
            stackgroup='one'
        ))
    
    fig.update_layout(
        title='Geographic Distribution Over Time (Top 8 Countries)',
        xaxis_title='Year',
        yaxis_title='Number of Papers',
        hovermode='x unified',
        height=500,
        template='plotly_white'
    )
    
    return fig

def create_methodology_timeline(df, years_range):
    """Create Qual vs Quant evolution"""
    method_by_year = df.groupby(['year', 'paper_type']).size().reset_index(name='count')
    
    fig = go.Figure()
    
    for method in ['Empirical - Qual', 'Empirical - Quant']:
        method_data = method_by_year[method_by_year['paper_type'] == method]
        fig.add_trace(go.Bar(
            x=method_data['year'],
            y=method_data['count'],
            name=method,
            marker_color='#2563eb' if method == 'Empirical - Qual' else '#16a34a'
        ))
    
    fig.update_layout(
        title='Methodology Evolution Over Time (Qualitative vs Quantitative)',
        xaxis_title='Year',
        yaxis_title='Number of Papers',
        barmode='group',
        height=500,
        template='plotly_white'
    )
    
    return fig

def create_journal_heatmap(df):
    """Create journal x time period heatmap"""
    # Create 5-year periods
    df['period'] = pd.cut(df['year'], 
                          bins=[1994, 1999, 2004, 2009, 2014, 2019, 2025],
                          labels=['1995-1999', '2000-2004', '2005-2009', '2010-2014', '2015-2019', '2020-2025'])
    
    top_journals = df['journal'].value_counts().head(15).index.tolist()
    
    pivot_data = df[df['journal'].isin(top_journals)].groupby(['period', 'journal']).size().reset_index(name='count')
    pivot_table = pivot_data.pivot(index='journal', columns='period', values='count').fillna(0)
    
    fig = go.Figure(data=go.Heatmap(
        z=pivot_table.values,
        x=pivot_table.columns.tolist(),
        y=[j.replace('&amp;', '&') for j in pivot_table.index.tolist()],
        colorscale='YlGnBu',
        text=pivot_table.values,
        texttemplate='%{text:.0f}',
        textfont={'size': 10}
    ))
    
    fig.update_layout(
        title='Journal × Time Period Heatmap (Top 15 Journals)',
        xaxis_title='Time Period',
        yaxis_title='Journal',
        height=600,
        template='plotly_white'
    )
    
    return fig, pivot_table

def create_metadata_summary(df):
    """Create summary statistics"""
    summary = {
        'total_papers': len(df),
        'year_range': f"{df['year'].min()}-{df['year'].max()}",
        'unique_journals': df['journal'].nunique(),
        'unique_countries': df['country'].nunique(),
        'qual_papers': len(df[df['paper_type'] == 'Empirical - Qual']),
        'quant_papers': len(df[df['paper_type'] == 'Empirical - Quant']),
        'peak_year': df['year'].value_counts().index[0],
        'peak_year_count': df['year'].value_counts().iloc[0]
    }
    return summary

if __name__ == '__main__':
    print("Metadata Timeline Analysis Module Ready")
    print("Use with pandas DataFrame containing: year, journal, country, paper_type")
