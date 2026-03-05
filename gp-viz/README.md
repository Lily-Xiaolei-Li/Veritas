# GP Visualization System (Phase 4+ Enhanced)

GP Visualization System 用于 Paper 1 SLR 的检索、可视化与辅助问答。

**最新更新 (2026-02-25):** 新增 VOSviewer 风格 3D Time-Volume-Weight 可视化

## 功能概览

### 核心功能 (F1-F7)
- **F1** 时间线堆叠图（Theme × Year）
- **F2** 主题热力图（可按行列筛选）
- **F3** 主题总量排名
- **F4** 年度总体趋势
- **F5** 主题占比分析
- **F6** 体量 vs 增长分析
- **F7** 主题汇总表（total/peak/latest）

### 元数据时间演化分析 ⭐ 新增
- **Ribbon (堆叠面积)**: 展示累积趋势和组成变化
- **Trend line**: 明确的趋势线，适合展示 "shifts"
- **Time band**: 时间段活跃度热图

### VOSviewer 风格 3D 可视化 ⭐ 新增
- **VOSviewer 3D (Time-Volume-Weight)**
  - X轴: Year (时间)
  - Y轴: Primary metadata (如 Journal)
  - Z轴: Paper Count (体量/权重)
  - Color: Dominant Secondary (如 Country)
  - 虚线轨迹: 每个 Primary item 的时间趋势
- **VOSviewer 2D Projection**: 气泡图展示趋势和热点迁移

### Scholar Influence 分析 ⭐ 新增 (2026-02-25)
- **Power 引用追踪**: 分析特定学者在语料库中的引用情况
- **引用分类**: theoretical foundation / framework / methodological approach / empirical support / critique / extension / name-dropping
- **时间趋势**: 该学者被引用的年度变化
- **章节分布**: 引用出现在论文的哪个部分
- **逐论文分析**: 每篇论文对该学者的引用详情
- **API**: `/scholar-influence/{scholar_name}`

### 其他功能
- 论文检索：`/papers`、`/papers/{paper_id}`
- Assistant 代理：`/assist-stream`（对接 XiaoLei `/chat`）

## 项目结构

```text
gp-viz/
├─ app/
│  ├─ api/            # FastAPI 路由
│  ├─ pages/          # Streamlit 多页面
│  │  ├─ metadata_timeline.py     # 元数据时间线
│  │  ├─ metadata_trend_analysis.py # 趋势分析
│  │  └─ vosviewer_style.py       # VOSviewer 3D 可视化 ⭐
│  ├─ utils/          # 数据读取、Qdrant、配置
│  ├─ api_server.py   # API 启动入口
│  └─ main.py         # Streamlit 主页面（F1-F7）
├─ scripts/
│  └─ check_environment.py
├─ tests/
│  └─ test_phase4_integration.py
├─ data/              # Excel 数据文件
├─ docker-compose.yml
└─ .env.example
```

## 快速启动

1. 复制环境变量模板

```bash
cp .env.example .env
```

2. 按需修改 `.env`（Qdrant、Excel、PDF、XiaoLei API）

3. 启动服务

```bash
docker compose up --build -d
```

4. 访问地址

| 页面 | URL |
|------|-----|
| 主页面 (F1-F7) | http://localhost:18501 |
| VOSviewer 风格 | http://localhost:18501/vosviewer_style |
| 元数据时间线 | http://localhost:18501/metadata_timeline |
| **Scholar Influence** ⭐ | http://localhost:18501/scholar_influence |
| API 健康检查 | http://localhost:1880/health |
| API Scholar Analysis | http://localhost:1880/scholar-influence/{scholar_name} |

## VOSviewer 3D 使用指南

### 操作步骤
1. 访问 `http://localhost:18501/vosviewer_style`
2. 选择 **View mode**: "VOSviewer 3D (Time-Volume-Weight)"
3. 选择 **Primary dimension**: Journal / Country / Methodology
4. 选择 **Secondary (color)**: 另一个维度用于颜色编码
5. 调整 **Top-N** 滑块控制显示数量
6. 旋转 3D 图查看不同角度
7. 导出 CSV 数据用于论文

### 解读方式
- **点的位置**: 某期刊在某年的论文数
- **点的大小**: 论文数量（体积）
- **颜色**: 该（年份×期刊）组合中最常见的国家/方法
- **虚线**: 该期刊随时间的趋势轨迹
- **趋势转折**: 热点迁移的视觉证据

## 本地开发（非 Docker）

```bash
pip install -e .
python -m app.api_server        # API
streamlit run app/main.py       # UI
```

## 测试

```bash
python -m unittest tests/test_phase4_integration.py -v
```

测试覆盖 7 个核心功能端点（F1-F7 对应链路），并通过 mock 隔离外部依赖。

## 已确认数据源

- Qdrant collection: `vf_profiles_slr` (124 papers)
- Excel: `Paper 1 SLR data and analysis (5 Jan 2026).xlsx`
- PDF 目录：`P1SLR Library`

## 导师反馈对应

| 导师要求 | GP-Viz 实现 |
|---------|------------|
| "Create time-related charts" | Ribbon / Trend line / 3D VOSviewer |
| "Show time distribution for each cluster" | Time band + 3D 轨迹线 |
| "trends and shifts" | Trend line 模式 + 3D 轨迹可视化 |
| "Clearer than VOSviewer" | 2D 投影 + 交互式 3D + 右侧 Top-N 面板 |

## 常见问题

- `assist-stream` 返回 503：请确认 XiaoLei API 已启动且 `/chat` 可访问。
- 图像导出不可用：当前环境缺少导出引擎时，可使用 Plotly 工具栏导出。
- API 连接失败：检查 Docker 网络，确保 `GP_VIZ_API_URL=http://gp-viz-api:8080`

## 开发记录

- **2026-02-25**: 集成 Scholar Influence 分析 (Power 引用追踪) 到同一 Docker 容器 ⭐
- **2026-02-25**: 新增 VOSviewer 3D Time-Volume-Weight 可视化 (小颖)
- **2026-02-25**: 新增元数据时间演化分析页面 (小蕾)
- **2026-02-24**: Phase 4 完成，F1-F7 功能集成
