# Agent-B Research Tools 工具指南

*小蕾整理，2026-02-19*

---

## 📍 位置

`C:\Users\Barry Li (UoN)\clawd\projects\Agent-B-Research\backend\tools\`

---

## 🚀 快速使用

```python
from tools import (
    # 参考文献
    lookup_references,
    
    # 章节提取
    lookup_abstract,
    lookup_introduction,
    lookup_methodology,
    lookup_literature_review,
    lookup_empirical_analysis,
    lookup_conclusion,
    
    # 高级
    lookup_section,        # 自定义章节名
    lookup_all_sections,   # 一次获取所有章节
    AVAILABLE_SECTIONS,    # 可用章节列表
)
```

---

## 📚 工具详解

### 1. reference_lookup.py — 参考文献提取

**功能：** 从 VF Store 的 paper_id 获取完整参考文献列表

**用法：**
```python
from tools import lookup_references

# 单个论文
refs = lookup_references("Hutomo_2020_CarbonAccounting")
# 返回: ["[1] Author (Year). Title...", "[2] ...", ...]

# 获取原始 markdown
refs = lookup_references("paper_id", raw=True)
# 返回: "## References\n\n[1] Author..."
```

**返回格式：**
- 默认返回 `List[str]`，每个元素是一条参考文献
- `raw=True` 返回原始 markdown 字符串

---

### 2. section_lookup.py — 章节提取

**功能：** 从 VF Store 的 paper_id 获取特定语义章节

**可用章节：**
| 章节 | 函数 | 成功率 | 平均长度 |
|------|------|--------|----------|
| Abstract | `lookup_abstract()` | 90% | 1,671 chars |
| Introduction | `lookup_introduction()` | 100% | 8,790 chars |
| Methodology | `lookup_methodology()` | 50%* | 13,014 chars |
| Literature Review | `lookup_literature_review()` | 80% | 13,023 chars |
| Empirical Analysis | `lookup_empirical_analysis()` | 100% | 59,417 chars |
| Conclusion | `lookup_conclusion()` | 100% | ~1.2-13k chars |

*方法论成功率低是因为有些论文把方法论合并在其他部分

**用法：**
```python
from tools import lookup_introduction, lookup_conclusion

# 单个章节
intro = lookup_introduction("Hutomo_2020_CarbonAccounting")
# 返回: "## 1. Introduction\n\nThis paper examines..."

concl = lookup_conclusion("paper_id")
# 返回: "## 5. Conclusion\n\nIn this study, we..."
```

**获取所有章节：**
```python
from tools import lookup_all_sections

sections = lookup_all_sections("paper_id")
# 返回: {
#   "abstract": "...",
#   "introduction": "...",
#   "methodology": "..." or None,
#   "literature_review": "..." or None,
#   "empirical_analysis": "...",
#   "conclusion": "..."
# }
```

**自定义章节名：**
```python
from tools import lookup_section

# 如果论文有特殊章节名
section = lookup_section("paper_id", "theoretical_framework")
```

---

## 🔗 数据来源

这些工具从 **VF Store** 提取数据：
- **路径：** `backend/data/vf_store/`
- **格式：** 每篇论文一个 `.md` 文件，按语义切块
- **索引：** `sync_results.json` 连接 Library 和 VF Store

---

## 💡 使用场景

1. **快速构建理论框架**
   - 提取多篇论文的 literature_review
   - 对比不同论文的理论视角

2. **方法论对照**
   - 提取 methodology 章节
   - 比较研究设计、数据来源、分析方法

3. **生成文献综述草稿**
   - 汇总 introduction + literature_review
   - 识别研究空白

4. **对比论文贡献**
   - 提取 conclusion 章节
   - 总结各论文的主要贡献

---

## 🛠️ 未来扩展（待开发）

- [ ] **对比表工具** — 给一组 paper_ids，自动生成 methods vs. contributions 对比
- [ ] **主题汇总工具** — 自动汇总某主题的 intro + lit review + conclusion 框架
- [ ] **引用网络分析** — 分析论文间的引用关系

---

*拿出来就能用！* 🌸
