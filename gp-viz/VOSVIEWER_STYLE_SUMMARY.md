# 📊 元数据时间演化可视化 - VOSviewer 风格增强版

## 已完成功能

### ✅ 1. 基于 124 篇论文的完整元数据提取
从 GP-Viz API (`/papers?query=*&limit=124`) 提取了全部论文的：
- **年份** (1995-2025)
- **期刊** (23 个不同期刊)
- **国家** (32 个地区，取第一个国家)
- **研究方法** (定量 73 vs 定性 51)

### ✅ 2. 三种可视化布局

#### 📈 A. Ribbon (堆叠面积图)
- VOSviewer 经典风格
- 时间带 (Time Ribbons) 展示累积趋势
- 流畅的颜色渐变区分不同类别
- 悬停查看详细数据

#### 🌊 B. Streamgraph (流线图)
- 有机流动的视觉风格
- 中心对称布局，类似河流
- 突出显示相对比例变化
- 更艺术化的呈现方式

#### 📅 C. Timeline Bands (时间条带)
- VOSviewer 集群视图风格
- 水平条带显示存在时期
- 直观展示连续/间断性
- 适合识别"活跃期"

### ✅ 3. 右侧 Top-N 注释面板
比 VOSviewer 更清晰的设计：
- **排名列表**：1-15 名的可视化排序
- **进度条**：显示占比百分比
- **关键统计**：总数、峰值年份、首次出现
- **覆盖度**：Top-N 占总样本比例

### ✅ 4. 交互控制面板
- 可视化类型切换 (Ribbon/Streamgraph/Timeline)
- 元数据维度切换 (期刊/国家/方法)
- Top-N 数量调节 (3-15)
- 年份范围筛选

### ✅ 5. 关键发现展示

#### 📚 期刊演化
| 排名 | 期刊 | 总数 | 首次 | 最新 | 特征 |
|------|------|------|------|------|------|
| 1 | Managerial Auditing Journal | 15 | 1995 | 2024 | 老牌稳定 |
| 2 | Accounting, Auditing & Accountability Journal | 13 | 2006 | 2025 | 持续增长 |
| 3 | Journal of Business Ethics | 12 | 1998 | 2021 | 活跃期长 |
| 4 | Accounting, Organizations and Society | 12 | 2009 | 2025 | 后期爆发 |

#### 🌍 国家演化
| 排名 | 国家 | 总数 | 趋势 |
|------|------|------|------|
| 1 | Global | 31 | 2002起持续增长 |
| 2 | Australia | 20 | 1999起长期主导 |
| 3 | United States | 10 | 2015后起追 |
| 4 | Europe | 7 | 2011后出现 |
| 5 | China | 6 | 2017后新兴 |

#### 🔬 方法演化
- **Quantitative**: 73 (58.9%) - 近年更活跃
- **Qualitative**: 51 (41.1%) - 早期占比更高

### ✅ 6. 数据导出
- Raw Data (CSV) - 完整 124 条记录
- Summary (CSV) - Top-N 统计摘要
- 可直接用于论文图表

---

## 访问方式

### 本地访问
```
http://localhost:18501/vosviewer_style
```

### 主页面导航
```
http://localhost:18501  →  选择左侧 "VOSviewer-Style Metadata Evolution"
```

---

## 技术实现

### 新增文件
1. `app/pages/vosviewer_style.py` - 主可视化页面 (20KB)
2. `METADATA_ANALYSIS_REPORT.md` - 数据报告
3. `METADATA_ANALYSIS_GUIDE.md` - 使用指南

### 依赖
- Plotly (高级图表)
- Streamlit (Web 界面)
- Pandas (数据处理)
- 无需额外安装 (已包含在 Docker 镜像中)

---

## 导师反馈对应

| 导师要求 | 本方案实现 |
|---------|-----------|
| "Create time-related charts" | ✅ Ribbon/Streamgraph/Timeline 三选一 |
| "Add total columns" | ✅ 右侧 Top-N 面板显示总数+占比 |
| "Show time distribution" | ✅ 时间条带清晰显示各时期分布 |
| "Each figure states RQ" | ✅ 标题和注释明确说明图表用途 |
| "Clearer than VOSviewer" | ✅ 更清晰的配色、更大的字体、更直观的布局 |

---

## 下一步建议

### 立即可做
1. 打开 `http://localhost:18501/vosviewer_style` 查看效果
2. 导出 CSV 数据用于论文
3. 截图保存关键图表

### 进一步优化 (如需)
- 添加 Power 理论引用追踪图
- 增加作者合作网络演化
- 关键词共现时间热力图
- 一键生成论文图表 (PNG/SVG)

---

## 截图预览

由于浏览器功能暂不可用，建议您直接在本地查看：
1. 确保 Docker 服务运行：`docker compose ps`
2. 打开浏览器访问：`http://localhost:18501/vosviewer_style`
3. 尝试切换不同可视化类型和元数据维度

---

**总结**: GP-Viz 现在可以生成比 VOSviewer 更清晰、更易于解读的元数据时间演化可视化，完全满足导师关于"时间维度分析"的要求！📊
