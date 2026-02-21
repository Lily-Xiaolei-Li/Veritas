# PRD: Citalio — 引用显现 ✨

**Project:** Veritas (ABR)  
**Author:** 超级小蕾 (Design) + 老爷 (Vision)  
**Date:** 2026-02-16  
**Status:** Draft  
**Spell Name:** Citalio（拉丁语 *citare* 引用 → "引用显现"）

---

## 1. 概述

Citalio 是 Veritafactum 的姊妹魔咒。Veritafactum 验证已有引用是否正确，**Citalio 为缺少引用的句子自动补全引用**。

### 核心流程

```
用户文本 → 逐句拆分 → 识别需引用的句子 → VF Store 语义搜索 cited_for
→ LLM 评估匹配度 → 自动插入引用建议 → 用户审核
```

### 与 Veritafactum 的关系

| | Veritafactum | Citalio |
|---|---|---|
| **目标** | 验证已有引用 | 补全缺失引用 |
| **输入** | 有引用的句子 | 无引用的句子 |
| **搜索字段** | 全 profile 验证 | 重点搜 `cited_for` |
| **输出** | ✅ 正确 / ❌ 错误 | 📎 建议引用 (Author, Year) |
| **共享基础** | splitter, extractor, classifier, VF Store, RAG | 同左 |

---

## 2. 用户故事

> 作为一个学术写作者，我写了一段文字，里面有些观点来自文献但我忘了（或不知道）该引谁。我施展 Citalio，系统自动找到合适的引用并插入，我只需审核确认。

---

## 3. 技术设计

### 3.1 管线（Pipeline）

复用 Veritafactum 前3步，替换后续步骤：

```
Step 1: Sentence Splitting          ← 复用 checker.splitter
Step 2: Claim/Term Extraction       ← 复用 checker.extractor  
Step 3: Sentence Classification     ← 复用 checker.classifier（只关注 CITE_NEEDED 类型）
Step 4: VF Store Semantic Search    ← 新增：专搜 cited_for + theory 字段 ⭐
Step 5: Citation Relevance Scoring  ← 新增：LLM 判断匹配度 ⭐
Step 6: Citation Insertion          ← 新增：生成带引用的句子 ⭐
Step 7: Report Generation           ← 复用 checker.report_generator（扩展输出格式）
```

### 3.2 Step 4 详细设计：VF Store 搜索

**搜索策略：**

```python
async def search_citations_for_sentence(sentence_text: str) -> list[CitationCandidate]:
    """
    1. 语义搜索 VF Store，重点匹配 cited_for 和 theory chunks
    2. 按相关性排序，返回 top-5 候选
    """
    # 主搜索：cited_for 字段（每篇论文的"可以被引用来支持什么"）
    cited_for_results = vf_store.search(
        query=sentence_text,
        chunk_types=["cited_for"],
        limit=10
    )
    
    # 辅助搜索：theory 和 contributions 字段补充
    theory_results = vf_store.search(
        query=sentence_text,
        chunk_types=["theory", "contributions"],
        limit=5
    )
    
    # 合并去重，按 paper_id 聚合
    candidates = merge_and_rank(cited_for_results, theory_results)
    return candidates[:5]
```

**为什么 `cited_for` 是关键字段：**
- VF profile 生成时，`cited_for` 专门描述"这篇论文可以被引用来支持哪些观点"
- 这和 Citalio 的需求完美匹配：给一个观点 → 找哪篇论文支持它
- 语义搜索 `cited_for` 的准确度远高于搜 abstract 或 full text

### 3.3 Step 5 详细设计：LLM 相关性评估

```python
RELEVANCE_PROMPT = """
你是学术引用专家。给定一个需要引用的句子和一个候选引用，判断该引用是否合适。

句子: {sentence}
候选引用: {paper_title} ({authors}, {year})
该论文可被引用于: {cited_for}

评估标准:
1. 句子的核心观点是否在该论文的引用范围内？
2. 引用是否直接支持（而非间接相关）？
3. 是否比其他候选更合适？

返回 JSON:
{
  "relevant": true/false,
  "confidence": 0.0-1.0,
  "reason": "简短解释",
  "citation_context": "建议的引用方式，如 '(Author, Year)' 或 'Author (Year) argued that...'"
}
"""
```

### 3.4 Step 6 详细设计：引用插入

对每个 `CITE_NEEDED` 句子：
- 如果有高置信度候选（confidence ≥ 0.8）→ 直接建议插入
- 如果有中置信度候选（0.5-0.8）→ 标记为"可能相关"供用户选择
- 如果无合适候选 → 标记为"需手动查找引用"

**插入格式：**
```
原句：Financial literacy varies significantly across demographics.
Citalio：Financial literacy varies significantly across demographics *(Lusardi, 2019; O'Connor et al., 2021)*.
```

### 3.5 数据模型

```python
@dataclass
class CitationCandidate:
    paper_id: str
    authors: list[str]
    year: int
    title: str
    cited_for: str           # VF store 的 cited_for 字段内容
    relevance_score: float   # 语义搜索分数
    confidence: float        # LLM 评估置信度
    reason: str              # LLM 解释
    citation_text: str       # 建议的引用格式 e.g. "(Lusardi, 2019)"

@dataclass  
class CitalioResult:
    sentence_id: str
    original_text: str
    classification: str       # CITE_NEEDED / COMMON / OWN_EMPIRICAL / OWN_CONTRIBUTION
    candidates: list[CitationCandidate]  # 排序后的候选引用
    suggested_text: str       # 插入引用后的建议文本
    action: str               # "auto_cite" / "maybe_cite" / "manual_needed" / "no_cite_needed"
```

---

## 4. API 设计

### 4.1 新增 Endpoints

```
POST   /api/v1/citalio/run          # 提交文本，启动 Citalio 分析
GET    /api/v1/citalio/status/:runId # 查询运行状态
GET    /api/v1/citalio/results/:runId # 获取结果
```

### 4.2 Request/Response

**POST /api/v1/citalio/run**
```json
{
  "text": "Financial literacy varies significantly across demographics. Credit scoring systems operate as panoptic surveillance mechanisms.",
  "session_id": "optional-session-id",
  "options": {
    "min_confidence": 0.5,      // 最低置信度阈值
    "max_citations_per_sentence": 3,
    "include_common_knowledge": false  // 是否也为常识句找引用
  }
}
```

**Response (results)**
```json
{
  "run_id": "abc123",
  "status": "completed",
  "sentences": [
    {
      "id": "s1",
      "text": "Financial literacy varies significantly across demographics.",
      "classification": "CITE_NEEDED",
      "action": "auto_cite",
      "candidates": [
        {
          "paper_id": "Lusardi_2019",
          "authors": ["Lusardi, A."],
          "year": 2019,
          "title": "Financial Literacy and the Need for Financial Education",
          "confidence": 0.92,
          "reason": "Lusardi's work directly addresses demographic variations in financial literacy",
          "citation_text": "(Lusardi, 2019)"
        }
      ],
      "suggested_text": "Financial literacy varies significantly across demographics (Lusardi, 2019)."
    },
    {
      "id": "s2", 
      "text": "Credit scoring systems operate as panoptic surveillance mechanisms.",
      "classification": "CITE_NEEDED",
      "action": "auto_cite",
      "candidates": [
        {
          "paper_id": "Aslam_2020",
          "confidence": 0.95,
          "reason": "Aslam et al. directly theorize credit rating as panoptic surveillance using Foucauldian lens",
          "citation_text": "(Aslam et al., 2026)"
        }
      ],
      "suggested_text": "Credit scoring systems operate as panoptic surveillance mechanisms (Aslam et al., 2026)."
    }
  ],
  "summary": {
    "total_sentences": 2,
    "cite_needed": 2,
    "auto_cited": 2,
    "maybe_cited": 0,
    "manual_needed": 0,
    "no_cite_needed": 0
  }
}
```

---

## 5. 前端集成

### 5.1 编辑器标注

复用 Veritafactum 的 Tiptap annotation 层：

| 状态 | 颜色 | 说明 |
|------|------|------|
| `auto_cite` | 🟢 绿色高亮 | 高置信度，已自动建议引用 |
| `maybe_cite` | 🟡 黄色高亮 | 中置信度，需用户选择 |
| `manual_needed` | 🔴 红色高亮 | VF Store 无匹配，需手动找 |
| `no_cite_needed` | 无标记 | 常识/原创，不需引用 |

### 5.2 用户交互

- 点击绿色句子 → 弹出引用详情，Accept / Dismiss / 换一个
- 点击黄色句子 → 显示多个候选，用户选择最合适的
- 点击红色句子 → 提示"VF Store 中未找到合适引用"
- **一键全部接受** → 批量插入所有高置信度引用

---

## 6. 实现计划

### Phase 1：核心管线（后端）— 预计 2-3 小时

| 任务 | 文件 | 复用/新增 |
|------|------|-----------|
| Citalio engine | `services/citalio/engine.py` | 新增（orchestrator） |
| VF cited_for 搜索 | `services/citalio/citation_searcher.py` | 新增（核心搜索逻辑）⭐ |
| LLM 相关性评估 | `services/citalio/relevance_scorer.py` | 新增（prompt + parsing）⭐ |
| 引用插入器 | `services/citalio/citation_inserter.py` | 新增 |
| API routes | `routes/citalio_routes.py` | 新增 |
| Splitter/Extractor/Classifier | `services/checker/*` | 直接复用 |

### Phase 2：前端 UI — 预计 2-3 小时

| 任务 | 说明 |
|------|------|
| Citalio 按钮 | Workbench 工具栏新增 "✨ Citalio" 按钮 |
| 结果标注层 | 复用 VF annotation，新增绿/黄/红配色 |
| 候选选择面板 | 侧边栏显示候选引用详情 |
| 一键接受 | 批量插入功能 |

### Phase 3：CLI 集成 — 预计 30 分钟

```bash
cli citalio run --session <id> --artifact <id>
cli citalio status <run_id>
cli citalio results <run_id>
```

---

## 7. 为什么这么容易

1. **VF Store 已就位** — 数百篇论文的 `cited_for` 字段已索引，这是 Citalio 的"弹药库"
2. **管线前3步直接复用** — splitter, extractor, classifier 一行代码不用改
3. **Qdrant 搜索已就位** — profile_searcher.py 的搜索逻辑稍作修改即可
4. **前端标注层已就位** — VF 的 Tiptap annotation 加新颜色就行
5. **唯一的新逻辑** — citation_searcher（搜 cited_for）和 relevance_scorer（LLM评估）

总代码量预计 ~500 行新代码 + 复用现有 ~2000 行。

---

## 8. 未来扩展

- **Citalio + Veritafactum 联合施法** — 先 Citalio 补引用，再 Veritafactum 验证，一键完成
- **引用风格适配** — APA / Harvard / Chicago 格式自动切换
- **引用密度分析** — 段落级别的引用分布是否均匀
- **跨库搜索** — 当 VF Store 无匹配时，fallback 到 Semantic Scholar / CrossRef API

---

*Citalio! ✨ 引用显现！*
