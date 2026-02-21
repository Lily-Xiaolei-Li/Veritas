# PRD: VF Middleware Manager v2

**Version:** 2.0  
**Date:** 2026-02-15  
**Author:** Lily Xiaolei Li  
**Status:** Draft  

---

## 1. Overview

VF Middleware Manager v1 提供了基础的 Stats / List / Delete 功能（GUI + CLI），以及后端的 Generate / Batch / Lookup API。v2 将其升级为完整的 profile 管理工具，新增单篇生成 GUI、图书馆一键同步、Profile 预览、Agent 选择器、搜索筛选等功能。

### 1.1 Current State (v1)

| Layer | 功能 | 文件 |
|-------|------|------|
| **Backend Routes** | `POST /vf/generate`, `POST /vf/batch`, `GET /vf/lookup`, `GET /vf/stats`, `GET /vf/list`, `DELETE /vf/{paper_id}` | `vf_middleware_routes.py` |
| **Backend Services** | `profile_generator.py`, `profile_store.py`, `profile_searcher.py`, `metadata_index.py` | `services/vf_middleware/` |
| **Frontend** | Stats 展示、Profile 列表、Delete 按钮 | `vf-middleware/page.tsx`, `vfMiddleware.ts` |
| **CLI** | `vf generate`, `vf batch`, `vf lookup`, `vf stats`, `vf list`, `vf delete` | `vf_middleware_handlers.py` |

### 1.2 Tech Stack

- **Backend:** FastAPI + Python, Qdrant (local, collection `vf_profiles`), bge-m3 embeddings (1024d)
- **Frontend:** Next.js + TypeScript, Tailwind CSS
- **CLI:** Python + httpx, 调用 backend REST API
- **LLM:** 通过 backend gateway 配置调用（支持多 persona/agent）

---

## 2. Requirements

### 2.1 Generate（单篇生成）— GUI

**概述：** 在 GUI 中提供表单，允许用户上传或粘贴论文文本来生成 VF profile。

**UI 设计：**
- 页面顶部新增 "Generate Profile" 按钮，点击展开/弹出生成表单
- 表单字段：
  - `paper_id` (text input, required) — 格式建议 `AuthorYear_ShortTitle`
  - `abstract` (textarea)
  - `full_text` (textarea 或 file upload, 支持 `.md` / `.txt`)
  - `metadata` (JSON editor 或结构化字段: title, authors, year)
  - `in_library` (checkbox, default true)
- 提交后显示 spinner + 进度文本（"Generating profile..."）
- 完成后 toast 通知 + 自动刷新列表

**API：** 复用现有 `POST /vf/generate`，无需新增端点。

**前端新增：**
- `vfMiddleware.ts` 新增 `generateVFProfile(req)` 函数
- Generate 表单组件

### 2.2 Library Sync（一键同步）— GUI + CLI

**概述：** 扫描 `library-rag/data/parsed/` 目录下的全部 `.md` 论文，与 VF store 已有 profile 取差集，批量生成缺失的 profile。

**后端新增端点：**

```
POST /vf/sync
  Body: { library_path?: string, agent?: string, dry_run?: bool }
  Response (streaming/SSE): { total, new_count, skipped, current, progress }
```

**Sync 逻辑：**
1. 扫描 `library_path`（默认 `C:\Users\Lily Xiaolei Li (UoN)\clawd\projects\library-rag\data\parsed\`）下所有 `.md` 文件
2. 从每篇 `.md` 前几行提取 metadata（title, authors, year）来构造 `paper_id`
   - 解析规则：markdown 前 matter 或前 10 行中匹配 `# Title`, `Authors:`, `Year:` 等模式
   - `paper_id` 生成格式：`{FirstAuthorLastName}{Year}_{sanitized_short_title}`
3. 查询 metadata_index 获取已有 paper_id 列表
4. 计算差集 = 文件集 - 已有集
5. 逐篇调用 `profile_generator.generate_profile()` 处理差集
6. 通过 SSE 推送进度：`{ processed: N, total: M, current_paper: "...", status: "processing"|"done"|"error" }`

**GUI：**
- "Sync Library" 按钮，位于页面顶部操作栏
- 点击后弹出确认对话框，显示预扫描结果（N 篇待同步）
- 同步过程中显示进度条 + 当前论文名
- 完成后显示摘要（成功/失败/跳过数量）

**CLI 新增命令：** `vf sync`
- `--library-path <path>` — 自定义论文目录（默认值同上）
- `--agent <name>` — 指定处理 agent（默认 helper）
- `--dry-run` — 只列出需要同步的论文，不执行生成
- `--concurrency <N>` — 并发数（默认 1，防止 LLM 过载）
- 输出格式：进度条 + `[12/45] Processing: AuthorYear_Title...`

### 2.3 Lookup / Preview — GUI

**概述：** 在列表中点击某个 profile 可展开详情，查看 8 个 semantic chunk 的完整内容。

**UI 设计：**
- Profile 列表项点击后展开（accordion 模式）
- 展开区域显示 8 张卡片，每张对应一个 chunk：
  - `meta` — 元数据（title, authors, year, etc.）
  - `abstract` — 摘要
  - `theory` — 理论框架
  - `literature` — 文献综述
  - `research_questions` — 研究问题
  - `contributions` — 贡献
  - `key_concepts` — 关键概念
  - `cited_for` — 引用用途
- 每张卡片标题用 badge 样式，内容为 markdown 渲染
- 加载状态：点击展开时调用 API，显示 skeleton loader

**API：** 复用现有 `GET /vf/lookup?paper_id=xxx`，返回中已包含 `profile.chunks`。

**前端新增：**
- `vfMiddleware.ts` 新增 `lookupVFProfile(paperId)` 函数
- ProfileDetail / ChunkCard 组件

### 2.4 Agent 选择器 — GUI + CLI

**概述：** 允许选择不同的 AI agent/persona 来处理 profile 生成，不同 agent 对应不同 LLM model 和 prompt 风格。

**Agent 定义：**

| Agent Name | 说明 | LLM Model | 备注 |
|-----------|------|-----------|------|
| `helper` | 默认通用助手 | 当前 gateway 默认模型 | 默认选项 |
| `dr-xiaolei` | 博士小蕾 | 通过 xiaolei API persona | 学术深度分析 |
| `asst-xiaolei` | 助手小蕾 | 通过 xiaolei API persona | 轻量快速处理 |

**后端：**
- `POST /vf/generate` 和 `POST /vf/sync` 增加可选参数 `agent: str = "helper"`
- `profile_generator.py` 根据 agent 名称选择对应的 LLM 调用配置
- 新增 `GET /vf/agents` — 返回可用 agent 列表及描述

**GUI：**
- 顶部操作栏增加 Agent 下拉选择器（默认 helper）
- 选中的 agent 应用于 Generate 和 Sync 操作
- 下拉项显示 agent 名称 + 简短描述

**CLI：**
- `vf generate --agent dr-xiaolei`
- `vf sync --agent asst-xiaolei`
- 默认 `helper`

### 2.5 预留按钮位 — GUI

**概述：** 在操作栏预留 2-3 个按钮位，为未来功能扩展做准备。

**UI：**
- 按钮位于操作栏，与 Generate / Sync Library 同行
- 状态：disabled, 灰色
- 文本示例：
  - "Re-analyze All" (Coming Soon)
  - "Export Profiles" (Coming Soon)
  - "Bulk Compare" (Coming Soon)
- Hover 时 tooltip 提示 "This feature is coming in a future update"

### 2.6 搜索 / 筛选 — GUI

**概述：** 在 profile 列表上方提供搜索和筛选功能。

**UI：**
- 搜索框：实时搜索，匹配 `paper_id` 或 `title`（前端过滤，数据量 <2000 足够）
- 筛选下拉/标签：
  - All（默认）
  - In Library（`in_library: true`）
  - External（`in_library: false`）
- 搜索 + 筛选可组合使用

**后端（可选增强）：**
- `GET /vf/list` 增加可选 query params：`?search=xxx&filter=in_library`
- v2 初期可纯前端过滤，后续数据量大时迁移到后端

---

## 3. Phase Plan

### Phase 1: 基础增强（搜索/筛选 + Preview）
**预计工期：** 1-2 天

| # | Task | Layer | 验收标准 |
|---|------|-------|---------|
| 1.1 | 搜索框 + 筛选 UI | Frontend | 输入关键词可实时过滤列表；切换 All/In Library/External 正确筛选 |
| 1.2 | Profile Preview（accordion + chunk cards） | Frontend + API层 | 点击 profile 展开 8 个 chunk 卡片，内容正确渲染 |
| 1.3 | `lookupVFProfile()` 前端 API 函数 | Frontend | 调用 `/vf/lookup?paper_id=xxx` 并正确返回数据 |

### Phase 2: Generate GUI + Agent 选择器
**预计工期：** 2-3 天

| # | Task | Layer | 验收标准 |
|---|------|-------|---------|
| 2.1 | Generate 表单 UI | Frontend | 表单包含所有字段；file upload 支持 .md/.txt；提交后显示进度 |
| 2.2 | `generateVFProfile()` 前端 API 函数 | Frontend | 正确调用 `POST /vf/generate` 并处理响应 |
| 2.3 | Agent 选择器 UI（下拉菜单） | Frontend | 可选 helper / dr-xiaolei / asst-xiaolei；选择后应用于 Generate |
| 2.4 | `GET /vf/agents` 端点 | Backend | 返回可用 agent 列表 `[{name, description, model}]` |
| 2.5 | `profile_generator.py` agent 支持 | Backend | 根据 agent 参数切换 LLM 调用配置 |
| 2.6 | CLI `--agent` 参数 | CLI | `vf generate --agent dr-xiaolei` 正常工作 |

### Phase 3: Library Sync
**预计工期：** 3-4 天

| # | Task | Layer | 验收标准 |
|---|------|-------|---------|
| 3.1 | Sync 后端逻辑（扫描 + 差集 + 批量生成） | Backend | 扫描 parsed/ 目录，正确识别新增论文，生成 profile |
| 3.2 | `.md` 文件 metadata 解析器 | Backend | 从 .md 前几行提取 title, authors, year，构造 paper_id |
| 3.3 | `POST /vf/sync` 端点 + SSE 进度推送 | Backend | 返回 SSE 流，包含进度信息 |
| 3.4 | Sync Library GUI（按钮 + 进度条 + 摘要） | Frontend | 点击按钮触发同步，显示进度，完成后刷新列表 |
| 3.5 | CLI `vf sync` 命令 | CLI | `vf sync --dry-run` 列出待同步论文；`vf sync` 执行同步并显示进度 |
| 3.6 | CLI `--dry-run` flag | CLI | 只输出列表不执行 |

### Phase 4: Polish + 预留位
**预计工期：** 0.5 天

| # | Task | Layer | 验收标准 |
|---|------|-------|---------|
| 4.1 | 预留按钮位（disabled × 3） | Frontend | 按钮可见但不可点击，显示 "Coming Soon" |
| 4.2 | UI polish（loading states, error handling, toast） | Frontend | 所有操作有 loading 状态；错误有 toast 提示 |
| 4.3 | 响应式布局检查 | Frontend | 在不同屏幕宽度下布局合理 |

---

## 4. API Changes Summary

### New Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/vf/sync` | Library sync（SSE streaming response） |
| `GET` | `/vf/agents` | 列出可用 agent |

### Modified Endpoints

| Method | Path | Change |
|--------|------|--------|
| `POST` | `/vf/generate` | 新增可选参数 `agent: str` |
| `GET` | `/vf/list` | 新增可选参数 `search`, `filter` |

### New CLI Commands

| Command | Description |
|---------|-------------|
| `vf sync` | 一键同步图书馆论文 |
| `vf sync --dry-run` | 预览待同步列表 |
| `vf sync --agent <name>` | 指定处理 agent |
| `vf generate --agent <name>` | 指定处理 agent |

---

## 5. Data Flow

### Library Sync Flow

```
[GUI: Sync Library] or [CLI: vf sync]
  │
  ▼
POST /vf/sync { library_path, agent, dry_run }
  │
  ├─ 1. Scan library-rag/data/parsed/*.md
  ├─ 2. Parse each .md → extract (title, authors, year) → build paper_id
  ├─ 3. Query metadata_index → get existing paper_ids
  ├─ 4. Diff: new_papers = scanned - existing
  │
  ├─ [if dry_run] → return { new_papers: [...], count: N }
  │
  ├─ 5. For each new paper:
  │     ├─ Read .md full text
  │     ├─ Call profile_generator.generate_profile(agent=agent)
  │     ├─ Upsert to profile_store + metadata_index
  │     └─ SSE push: { processed: i, total: N, current: paper_id }
  │
  └─ 6. SSE push: { status: "done", success: X, failed: Y, skipped: Z }
```

### paper_id 生成规则

从 `.md` 文件前 10 行解析：
- **Title:** 第一个 `# ` 标题行，或 `Title: xxx` 行
- **Authors:** `Authors: xxx` 或 `Author: xxx` 行，逗号分隔
- **Year:** `Year: NNNN` 或从文件名/正文中提取四位数字

```
paper_id = f"{first_author_lastname}{year}_{sanitize(short_title)}"
例: "Smith2024_deep_learning_survey"
```

冲突处理：如果生成的 paper_id 已存在于差集中（不同文件同 id），追加 `_2`, `_3`。

---

## 6. Non-functional Requirements

- **性能：** Sync 1000+ 篇论文时不应 OOM；使用 streaming 避免长时间无响应
- **错误恢复：** 单篇 generate 失败不影响 batch/sync 中其他论文的处理
- **幂等性：** 重复 sync 不会产生重复 profile（以 paper_id 为唯一键）
- **超时：** Sync 端点 timeout 设置为 3600s（CLI）/ SSE 无固定超时

---

## 7. Out of Scope (v2)

- Profile 编辑/手动修改 chunk 内容
- 多用户权限管理
- Profile 版本管理/历史记录
- 跨 collection 迁移工具
- "Re-analyze All" / "Export" / "Bulk Compare"（预留按钮位，v3 实现）
