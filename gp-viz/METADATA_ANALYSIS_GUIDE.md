# Metadata Timeline Analysis Guide 📊

## Overview

This enhanced GP-Viz functionality provides comprehensive **metadata evolution analysis** over time, addressing supervisor feedback about temporal dimensions.

## New Capabilities

### 1. Journal Evolution Analysis 📚
- **Line charts**: Track publication trends for top journals over time
- **Heatmaps**: Journal × Time Period visualization
- **Distribution**: Top journals by total publications
- **Interactive filtering**: Select specific journals to analyze

### 2. Geographic Evolution Analysis 🌍
- **Stacked area charts**: Country contributions over time
- **Pie charts**: Overall country distribution
- **Trend lines**: Individual country publication trajectories
- **Regional insights**: Geographic shifts in research focus

### 3. Methodology Evolution Analysis 🔬
- **Grouped bar charts**: Qual vs Quant by year
- **Stacked areas**: Cumulative methodology trends
- **Percentage trends**: Qualitative research proportion over time
- **Period analysis**: Methodology shifts across time periods

### 4. Theme Evolution Analysis 📊
- **Enhanced F1 visualization**: Theme statistics (Total, Peak, Latest)
- **Growth metrics**: First appearance to latest value tracking
- **Data tables**: Comprehensive theme statistics

## Usage

### Accessing the Tool

1. **Main Dashboard**: `http://localhost:18501` - Original F1-F7 visualizations
2. **Metadata Analysis**: `http://localhost:18501/metadata_timeline` - New comprehensive analysis

### API Endpoints

```bash
# Original endpoints
GET /viz/f1 - Theme timeline
GET /viz/f2 - Heatmap data
GET /viz/filters - Metadata filters
GET /papers?query=...&limit=... - Paper search

# Enhanced usage
GET /papers?query=*&limit=124 - Get all papers with full metadata
```

### Running the Analysis

```bash
# Start services
docker compose up -d

# Access metadata analysis
open http://localhost:18501/metadata_timeline
```

## Data Structure

Each paper record contains:
```json
{
  "paper_id": "uuid",
  "title": "Paper Title",
  "authors": "Author Names",
  "year": 2025,
  "journal": "Journal Name",
  "country": "Primary Country",
  "paper_type": "Empirical - Qual|Quant",
  "jnl_rank": "A*|A|B"
}
```

## Visualization Types

### Time Series Charts
- **Line charts**: Trends over continuous time
- **Stacked areas**: Cumulative contributions
- **Bar charts**: Discrete comparisons

### Aggregated Views
- **Heatmaps**: Cross-dimensional patterns
- **Pie charts**: Distribution proportions
- **Summary tables**: Statistical overview

### Interactive Features
- **Year range sliders**: Focus on specific periods
- **Multi-select filters**: Drill into specific journals/countries
- **Hover tooltips**: Detailed data on demand
- **Export options**: CSV/JSON data download

## Interpreting Results

### Journal Evolution Insights
- **Emerging journals**: New venues entering the field
- **Dominant journals**: Consistent high contributors
- **Temporal shifts**: Changing publication preferences

### Geographic Insights
- **Regional growth**: Emerging research centers
- **Collaboration patterns**: Multi-country studies
- **Globalization**: Increasing diversity over time

### Methodology Insights
- **Paradigm shifts**: Qual→Quant or mixed trends
- **Disciplinary evolution**: Changing research approaches
- **Period effects**: Methodology preferences by era

## Addressing Supervisor Feedback

| Requirement | How GP-Viz Addresses It |
|-------------|------------------------|
| "Create time-related charts" | Full timeline visualization suite |
| "Add total columns to theme tables" | F7-style summaries with Total/Peak/Latest |
| "Show time distribution for each cluster" | Period-based aggregations (5-year intervals) |
| "Each figure clearly states RQ" | All visualizations include descriptive titles |
| "Charts answer specific RQs" | Filtered views target specific research questions |

## Future Enhancements

### Planned Features
- [ ] **Citation network evolution**: Dynamic network visualization
- [ ] **Keyword co-occurrence**: Term evolution over time
- [ ] **Author collaboration**: Co-authorship networks
- [ ] **Power theory tracking**: Specific citation analysis
- [ ] **Methodological sophistication**: Research design complexity trends

### Export Capabilities
- [ ] PNG/SVG chart export
- [ ] LaTeX table generation
- [ ] PowerPoint integration
- [ ] Interactive HTML reports

## Technical Notes

### Dependencies
- Streamlit ≥1.40.0
- Plotly ≥5.24.0
- Pandas ≥2.2.0
- GP-Viz API running on :1880

### Performance
- 124 papers load in <2 seconds
- All visualizations update in real-time
- Cached data refreshes every 5 minutes

## Troubleshooting

### API Connection Issues
```bash
# Check API health
curl http://localhost:1880/health

# Restart services
docker compose restart
```

### Missing Data
- Ensure `GP_EXCEL_PATH` is correctly set in `.env`
- Verify Excel file is in `data/` directory
- Check Docker volume mounts

## Contact

For issues or feature requests, contact the GP-Viz development team.

---

*Generated by GP-Viz | Metadata Timeline Analysis Module v1.0*
