# Citalio Manual Mode — 实现文档

**Project:** Agent-B-Research (ABR)  
**Author:** 超级小蕾  
**Date:** 2026-02-18  
**Status:** ✅ Implemented

---

## 1. 概述

Citalio Manual Mode 是 Citalio 的用户控制版本。与自动模式不同，用户可以：
- 手动选择要搜索的文本
- 设置过滤条件（年份、类型、方法等）
- 查看完整匹配段落（不只是关键词）
- 选择并插入引用

### 为什么需要手动模式？

老爷实测自动模式后发现效果不理想。主要问题：
1. 自动分类可能误判哪些句子需要引用
2. 用户无法控制搜索范围和过滤条件
3. 结果只显示关键词，缺乏上下文

手动模式让用户完全掌控，更符合学术写作的实际流程。

---

## 2. 架构

```
┌─────────────────────────────────────────────────────────────────┐
│                          Frontend                                │
│  ┌─────────────────────┐    ┌─────────────────────────────────┐ │
│  │ CitalioPanel.tsx    │    │ CitalioManualPanel.tsx          │ │
│  │ (Auto/Manual 切换)  │    │ - 搜索框（自动填充选中文本）     │ │
│  │                     │    │ - Chunk type 选择               │ │
│  │                     │    │ - 过滤器面板                    │ │
│  │                     │    │ - 结果列表（完整段落）          │ │
│  │                     │    │ - Insert 按钮                   │ │
│  └─────────────────────┘    └─────────────────────────────────┘ │
│                                       │                          │
│  ┌────────────────────────────────────┼────────────────────────┐ │
│  │ CitalioTabWrapper                  │                        │ │
│  │ - 获取编辑器选中文本               │                        │ │
│  │ - 处理引用插入                     ▼                        │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼ POST /api/v1/citalio/manual/search
┌─────────────────────────────────────────────────────────────────┐
│                          Backend                                 │
│  ┌─────────────────────┐    ┌─────────────────────────────────┐ │
│  │ citalio_routes.py   │───▶│ CitalioManualSearcher           │ │
│  │ - /manual/search    │    │ - 预编码查询（一次）            │ │
│  │ - /manual/filter-   │    │ - 搜索多个 chunk types          │ │
│  │   options           │    │ - 应用过滤器                    │ │
│  └─────────────────────┘    │ - 生成 cite_intext/cite_full    │ │
│                             └─────────────────────────────────┘ │
│                                       │                          │
│                                       ▼                          │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ VFProfileStore                                              │ │
│  │ - semantic_search(query, chunk_id, query_vector)            │ │
│  │ - encode_query(query) → 预编码供复用                        │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                       │                          │
│                                       ▼                          │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ Qdrant (vf_profiles collection)                             │ │
│  │ - 向量搜索 BGE-M3 embeddings                                │ │
│  │ - chunk_id payload filter                                   │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. API 设计

### 3.1 POST /api/v1/citalio/manual/search

**Request:**
```json
{
  "query": "audit legitimacy institutional theory",
  "chunk_types": ["cited_for", "theory", "contributions"],
  "limit": 10,
  "filters": {
    "year_min": 2010,
    "year_max": 2025,
    "paper_type": "empirical",
    "primary_method": "case study",
    "keywords": ["audit", "legitimacy"],
    "journal": "Accounting",
    "in_library": true
  }
}
```

**Response:**
```json
{
  "query": "audit legitimacy institutional theory",
  "results": [
    {
      "paper_id": "Hazgui_2020",
      "authors": ["Mouna Hazgui", "Peter Triantafillou", "Signe Elmer Christensen"],
      "year": 2022,
      "title": "On the legitimacy and apoliticality of public sector performance audit...",
      "journal": "Financial Accountability & Management",
      "matched_chunk_type": "theory",
      "matched_text": "The article is grounded in Suchman's (1995) three-part model of organizational legitimacy: pragmatic, moral, and cognitive legitimacy...",
      "relevance_score": 0.6466813,
      "cite_intext": "(Hazgui et al., 2022)",
      "cite_full": "Hazgui, M., Triantafillou, P., & Christensen, S. E. (2022). On the legitimacy and apoliticality of public sector performance audit: exploratory evidence from Canada and Denmark. Financial Accountability & Management, 38(1), 1-25."
    }
  ]
}
```

### 3.2 GET /api/v1/citalio/manual/filter-options

**Response:**
```json
{
  "paper_types": ["empirical", "theoretical", "review", "conceptual"],
  "primary_methods": ["qualitative", "quantitative", "mixed methods", "case study", "archival"],
  "chunk_types": ["cited_for", "theory", "contributions", "literature", "abstract", "key_concepts", "research_questions"]
}
```

---

## 4. 过滤器字段

### 来自 VF Profile META_KEYS

| 字段 | 类型 | 说明 |
|------|------|------|
| `year_min` / `year_max` | int | 年份范围 |
| `paper_type` | string | empirical / theoretical / review / conceptual |
| `primary_method` | string | qualitative / quantitative / case study / mixed |
| `keywords` | list[str] | 匹配 keywords_author 或 keywords_inferred |
| `journal` | string | 期刊名（模糊匹配） |
| `authors` | string | 作者名（模糊匹配） |
| `in_library` | bool | 是否在 library 中（有全文） |
| `empirical_context` | string | 国家/行业/组织类型（模糊匹配） |

### Chunk Types (搜索目标)

| Chunk | 说明 | 推荐场景 |
|-------|------|----------|
| `cited_for` | 论文可被引用来支持什么 | ⭐ 最常用 |
| `theory` | 理论框架 | 理论背景写作 |
| `contributions` | 研究贡献 | Literature review |
| `literature` | 文献综述 | 找相关研究 |
| `abstract` | 摘要 | 快速匹配 |
| `key_concepts` | 核心概念 | 概念定义 |
| `research_questions` | 研究问题 | 找类似研究 |

---

## 5. 引用格式生成

### cite_intext

```python
def _generate_cite_intext(authors: list[str], year: int) -> str:
    if len(authors) == 0:
        return f"({year})"
    elif len(authors) == 1:
        surname = authors[0].split()[-1]
        return f"({surname}, {year})"
    elif len(authors) == 2:
        s1 = authors[0].split()[-1]
        s2 = authors[1].split()[-1]
        return f"({s1} & {s2}, {year})"
    else:
        surname = authors[0].split()[-1]
        return f"({surname} et al., {year})"
```

### cite_full (Harvard 格式)

```python
def _generate_cite_full(meta: dict) -> str:
    # 格式化作者列表
    authors_str = _format_authors_harvard(meta.get("authors", []))
    year = meta.get("year", "n.d.")
    title = meta.get("title", "Untitled")
    journal = meta.get("journal", "")
    volume = meta.get("volume", "")
    issue = meta.get("issue", "")
    pages = meta.get("pages", "")
    
    ref = f"{authors_str} ({year}). {title}."
    if journal:
        ref += f" {journal}"
        if volume:
            ref += f", {volume}"
            if issue:
                ref += f"({issue})"
        if pages:
            ref += f", {pages}"
        ref += "."
    return ref
```

---

## 6. 前端组件

### CitalioManualPanel.tsx

**主要功能：**
- 搜索输入框（自动填充 selectedText）
- Chunk type 多选按钮
- 可折叠的过滤器面板
- 结果列表，每个结果显示：
  - 标题、作者、年份、期刊
  - 相关度百分比
  - 匹配的 chunk type
  - **完整匹配段落**（可展开/收起）
  - cite_intext（可复制）
  - cite_full（可展开查看）
  - Insert 按钮

### CitalioTabWrapper (in ConsolePanel.tsx)

**获取选中文本：**
```typescript
const selectedText = React.useMemo(() => {
  if (editTargetSelections.length > 0) {
    return editTargetSelections.map((s) => s.text).join("\n");
  }
  return "";
}, [editTargetSelections]);
```

**处理引用插入：**
```typescript
const handleInsertCitation = React.useCallback((intext: string, fullRef: string) => {
  // 1. 在选中文本句尾插入 in-text citation
  const cleanSelected = selectedContent.replace(/[.!?]\s*$/, "");
  const withCitation = `${cleanSelected} ${intext}.`;
  
  // 2. 在 REFERENCES 部分添加完整引用
  if (!hasReferences) {
    newText += "\n\n## REFERENCES\n\n" + fullRef;
  } else {
    // 找到 REFERENCES 位置并追加
  }
}, [...]);
```

---

## 7. 性能优化

### 问题
- BGE-M3 模型首次加载需要 30-60 秒
- 每个 chunk_type 都调用 `semantic_search`，导致重复编码

### 解决方案

**VFProfileStore 支持预编码：**
```python
def semantic_search(
    self, 
    query: str, 
    limit: int = 8, 
    chunk_id: Optional[str] = None,
    query_vector: Optional[List[float]] = None,  # 新增
) -> List[Dict[str, Any]]:
    if query_vector is None:
        query_vector = _safe_encode(query)
    # ...

def encode_query(self, query: str) -> List[float]:
    """预编码查询，供复用"""
    return _safe_encode(query)
```

**手动搜索只编码一次：**
```python
# 预编码查询 ONCE
query_vector = self.store.encode_query(query)

for chunk_type in chunk_types:
    raw_results = self.store.semantic_search(
        query=query,
        limit=limit * 3,
        chunk_id=chunk_type,
        query_vector=query_vector,  # 复用！
    )
```

### 待优化
1. **Qdrant payload filter** — 目前 year/method 等是 Python 过滤，可以改成 Qdrant 级别
2. **模型预热** — 后端启动时预加载 BGE-M3

---

## 8. 文件清单

### 后端

| 文件 | 状态 | 说明 |
|------|------|------|
| `backend/app/routes/citalio_routes.py` | 修改 | 添加 `/manual/search` 和 `/manual/filter-options` |
| `backend/app/services/citalio/manual_search.py` | 新建 | `CitalioManualSearcher` 类 |
| `backend/app/services/vf_middleware/profile_store.py` | 修改 | 添加 `encode_query()` 和 `query_vector` 参数 |

### 前端

| 文件 | 状态 | 说明 |
|------|------|------|
| `frontend/src/components/citalio/CitalioManualPanel.tsx` | 新建 | 手动模式 UI |
| `frontend/src/components/citalio/CitalioPanel.tsx` | 修改 | Auto/Manual 切换 |
| `frontend/src/components/citalio/index.ts` | 修改 | 导出新组件 |
| `frontend/src/lib/api/citalio.ts` | 修改 | 添加 API 函数 |
| `frontend/src/components/workbench/ConsolePanel.tsx` | 修改 | CitalioTabWrapper 传递 props |

---

## 9. 使用示例

### CLI 测试

```powershell
$body = @{
    query = "audit legitimacy"
    chunk_types = @("cited_for", "theory")
    limit = 5
    filters = @{
        year_min = 2010
        paper_type = "empirical"
    }
} | ConvertTo-Json -Depth 3

Invoke-RestMethod -Uri "http://localhost:8001/api/v1/citalio/manual/search" `
    -Method POST -Body $body -ContentType "application/json; charset=utf-8"
```

### 前端使用

1. 在 artifact 编辑器中选择一段文本
2. 打开右侧 Citalio 面板
3. 切换到 Manual 模式（默认）
4. 调整过滤条件（可选）
5. 点击 Search
6. 查看结果，点击 Insert 插入引用

---

*Citalio Manual Mode — 用户掌控的引文搜索 🔍*
