# PRD: Ex-portario — 突破封印 📦

**Spell Name:** Ex-portario（拉丁语 *exportare* 传送/导出 → "突破封印下载全文"）  
**Version:** 1.0  
**Author:** 小蕾 (Design based on 老爷's vision)  
**Date:** 2026-02-16  
**Status:** Draft — 等 VF Store 批处理完成后再实现  

---

## 1. 概述

Ex-portario 将现有的 `download-papers` skill 封装成 Agent-B 的魔法按钮，与其他魔咒统一风格。核心能力：突破 paywall，按用户指定条件筛选并下载学术论文全文。

### 与其他魔咒的关系

```
📦 Ex-portario（下载全文）
    ↓ 自动触发
🌱 Proliferomaxima（从引用网络扩展）
    ↓ 扩充弹药库
✨ Citalio（自动补全引用）+ 🪄 Veritafactum（验证引用）
    ↓ 写论文时施法
📝 完美学术论文
```

---

## 2. 用户故事

> 作为学术研究者，我想从 Proliferomaxima 发现的引用网络中，按条件筛选出重要论文并下载全文，自动入库生成高质量 VF profiles，而不是盲目下载所有东西。

---

## 3. 筛选条件设计

### 3.1 筛选维度

| 维度 | 参数 | 示例 |
|------|------|------|
| 📰 期刊 | `--journals` | `AOS, AAAJ, CPA, BAR` |
| 🔍 关键词 | `--keywords` | `carbon accounting, sustainability audit` |
| 📅 年份范围 | `--year-from`, `--year-to` | `2015` 到 `2026` |
| 👤 作者 | `--authors` | `Gendron, Humphrey, Power` |
| 📊 数量上限 | `--limit` | `50` |
| 🏷️ 来源 | `--source` | `proliferomaxima` / `manual` / `all` |
| 📄 全文状态 | `--only-missing` | 只下载 VF Store 中 `full_article: false` 的 |

### 3.2 筛选组合逻辑

- 多个条件之间为 AND 关系
- 同维度内多个值为 OR 关系
- 例：`--journals AOS,AAAJ --year-from 2015 --limit 50`
  → 下载 AOS 或 AAAJ 的、2015年后的论文，最多50篇

---

## 4. 交互流程

### 4.1 预览优先原则

**绝不盲目下载！** 用户必须先预览再确认。

```
Step 1: 用户设置筛选条件
Step 2: 系统查询符合条件的论文列表（从 Proliferomaxima 发现的 + VF Store 元数据）
Step 3: 显示预览列表（标题、作者、年份、期刊、当前状态）
Step 4: 用户确认/取消勾选
Step 5: 施法！开始下载
Step 6: 进度条 + 实时状态更新
Step 7: 结果报告（成功/失败/跳过）
```

### 4.2 下载后自动流程

```
下载 PDF → 解析为 Markdown → 入库 Library RAG → 生成 full_article VF Profile
→ 替换已有的 abstract-only profile（如果存在）
```

---

## 5. CLI 设计

### 5.1 命令结构

```bash
# 预览符合条件的论文
cli exportario preview --journals AOS,AAAJ --year-from 2015 --limit 50

# 从预览中下载（需要 run_id）
cli exportario run <preview_id> [--confirm]

# 手动指定 reference list 文件
cli exportario run --input references.csv --limit 20

# 查看状态
cli exportario status <run_id>

# 查看结果
cli exportario results <run_id>
```

### 5.2 CLI 输出示例

```
$ cli exportario preview --journals AOS --year-from 2020 --limit 10

📦 Ex-portario Preview
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Found 47 papers matching criteria (showing top 10):

 # │ Title                                    │ Authors        │ Year │ Journal │ Status
───┼──────────────────────────────────────────┼────────────────┼──────┼─────────┼──────────
 1 │ Audit as constitutive practice            │ Humphrey et al │ 2021 │ AOS     │ 🟡 abstract-only
 2 │ The making of carbon markets              │ Callon, M.     │ 2020 │ AOS     │ 🔴 not in VF
 3 │ Performativity in accounting research     │ Gendron, Y.    │ 2022 │ AOS     │ 🔴 not in VF
...

Preview ID: prev_abc123
To download: cli exportario run prev_abc123 --confirm
```

---

## 6. GUI 设计

### 6.1 入口位置

统一魔法栏（Spell Bar）中的按钮：

```
┌────────────────────────────────────────────────────┐
│ 🪄 Spells                                          │
│                                                    │
│ [📦 Ex-portario] [🌱 Proliferomaxima]              │
│ [✨ Citalio]     [🪄 Veritafactum]                 │
└────────────────────────────────────────────────────┘
```

### 6.2 配置面板

点击 📦 Ex-portario 后弹出：

```
┌─ 📦 Ex-portario ─────────────────────────────┐
│                                               │
│ Source:  ○ Proliferomaxima discoveries        │
│          ○ Manual reference list              │
│          ○ All VF Store (abstract-only)       │
│                                               │
│ Filters:                                      │
│   Journals:  [AOS, AAAJ, CPA          ] ▼    │
│   Keywords:  [carbon accounting        ]      │
│   Years:     [2015] to [2026]                 │
│   Authors:   [                         ]      │
│   Max:       [50] papers                      │
│                                               │
│ [🔍 Preview]                                  │
│                                               │
│ ┌─ Preview Results ─────────────────────┐    │
│ │ ☑ Humphrey (2021) AOS    🟡 abstract  │    │
│ │ ☑ Callon (2020) AOS      🔴 missing   │    │
│ │ ☑ Gendron (2022) AOS     🔴 missing   │    │
│ │ ☐ Smith (2019) AOS       🟢 full      │    │
│ │ ...                                    │    │
│ └────────────────────────────────────────┘    │
│                                               │
│ Selected: 3/10     [✨ Cast Ex-portario!]     │
└───────────────────────────────────────────────┘
```

### 6.3 进度与结果

```
┌─ 📦 Downloading... ──────────────────────────┐
│ ████████████░░░░░░░░ 3/10 (30%)              │
│                                               │
│ ✅ Humphrey (2021) — downloaded + VF updated  │
│ ✅ Callon (2020) — downloaded + VF created    │
│ ⏳ Gendron (2022) — downloading...           │
│ ⏸ 7 remaining                                │
└───────────────────────────────────────────────┘
```

### 6.4 状态图标

| 图标 | 含义 |
|------|------|
| 🟢 | 已有全文 VF profile |
| 🟡 | 仅有 abstract-only profile |
| 🔴 | VF Store 中不存在 |
| ✅ | 下载成功 |
| ❌ | 下载失败 |
| ⏳ | 下载中 |

---

## 7. API 设计

```
POST   /api/v1/exportario/preview     # 按条件预览符合的论文
POST   /api/v1/exportario/run         # 开始下载（需 preview_id + 选中列表）
GET    /api/v1/exportario/status/:id  # 查询状态
GET    /api/v1/exportario/results/:id # 获取结果
```

### Request: Preview
```json
{
    "source": "proliferomaxima",
    "filters": {
        "journals": ["AOS", "AAAJ"],
        "keywords": ["carbon accounting"],
        "year_from": 2015,
        "year_to": 2026,
        "authors": [],
        "only_missing_fulltext": true
    },
    "limit": 50
}
```

### Request: Run
```json
{
    "preview_id": "prev_abc123",
    "selected_paper_ids": ["paper_1", "paper_2", "paper_3"]
}
```

---

## 8. 技术实现

### 8.1 新增文件

| 文件 | 用途 |
|------|------|
| `services/exportario/__init__.py` | Package init |
| `services/exportario/previewer.py` | 查询 VF Store + Proliferomaxima 数据，生成预览列表 |
| `services/exportario/downloader.py` | 封装 download-papers skill，处理实际下载 |
| `services/exportario/post_processor.py` | 下载后自动：解析 → 入库 → 生成/升级 VF profile |
| `routes/exportario_routes.py` | API routes |
| `cli/exportario_handlers.py` | CLI 子命令 |
| `components/exportario/ExportarioPanel.tsx` | 前端面板 |

### 8.2 复用现有能力

| 能力 | 来源 |
|------|------|
| PDF 下载 | `download-papers` skill (DOI resolver, university proxy) |
| PDF → Markdown | Library RAG parser |
| Library RAG 入库 | `paper_processor.py` |
| VF Profile 生成 | `/api/v1/vf/generate` |
| VF Store 查询 | `profile_store.py` |

---

## 9. Spell Bar 统一设计

### 9.1 所有魔咒统一入口

前端新增 `SpellBar` 组件，取代散落的按钮：

```typescript
// components/spells/SpellBar.tsx
const SPELLS = [
    { id: 'exportario',       icon: '📦', name: 'Ex-portario',       desc: '下载全文' },
    { id: 'proliferomaxima',  icon: '🌱', name: 'Proliferomaxima',  desc: '引用增殖' },
    { id: 'citalio',          icon: '✨', name: 'Citalio',          desc: '补全引用' },
    { id: 'veritafactum',     icon: '🪄', name: 'Veritafactum',     desc: '验证引用' },
];
```

### 9.2 CLI 统一命名

所有魔咒 CLI 命令遵循统一模式：
```bash
cli <spell-name> preview   # 预览（如适用）
cli <spell-name> run       # 执行
cli <spell-name> status    # 查状态
cli <spell-name> results   # 看结果
```

### 9.3 API 统一模式

所有魔咒 API 遵循统一 RESTful 模式：
```
POST   /api/v1/<spell>/run
GET    /api/v1/<spell>/status/:id
GET    /api/v1/<spell>/results/:id
```

---

## 10. 与 Proliferomaxima 联动

### 最佳工作流

```
1. Proliferomaxima 扫描 → 发现 8,000 引用
2. 其中 3,000 有 abstract → 自动生成 abstract-only profiles
3. 老爷打开 Ex-portario → 筛选 "AOS + 2015年后" → 预览 47 篇
4. 勾选 20 篇重要的 → Cast!
5. Ex-portario 下载 → 自动升级为 full_article profiles
6. Citalio + Veritafactum 现在有了更精准的全文支持
```

### 自动升级逻辑

当 Ex-portario 下载了一篇已有 abstract-only profile 的论文：
1. 生成新的 full_article VF profile
2. 覆盖旧的 abstract-only 版本
3. 更新 `full_article: false → true`
4. 保留 `cited_by` 引用关系

---

## 11. 实现优先级

**暂不实现** — 等 VF Store 批处理完成后再开发。

优先级排序：
1. ✅ VF Store 批处理（进行中）
2. ⏳ Citalio 集成（码农小蕾已交付）
3. ⏳ Proliferomaxima 开发
4. ⏳ **Ex-portario 封装**
5. ⏳ Spell Bar 统一 UI

---

*Ex-portario! 📦 突破封印，知识自由！*
