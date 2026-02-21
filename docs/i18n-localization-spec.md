# Veritas 汉化说明书 / i18n Localization Spec

**Author:** 超级小蕾  
**Date:** 2026-02-16  
**Status:** Ready for implementation  

---

## 1. 技术方案

### 框架：`next-intl`

选择理由：
- Next.js App Router 原生集成，零配置冲突
- 支持实时语言切换（无需刷新页面）
- 类型安全（TypeScript 支持）
- 轻量（<3KB gzipped）

### 安装

```bash
npm install next-intl
```

### 文件结构

```
frontend/
├── messages/
│   ├── en.json          # English (default)
│   └── zh.json          # 中文
├── src/
│   ├── i18n/
│   │   ├── config.ts    # i18n configuration
│   │   └── request.ts   # next-intl request config
│   └── components/
│       └── ui/
│           └── LanguageSwitcher.tsx  # 🌐 语言切换按钮
```

### 核心配置

```typescript
// src/i18n/config.ts
export const locales = ['en', 'zh'] as const;
export type Locale = (typeof locales)[number];
export const defaultLocale: Locale = 'en';
```

### 语言切换机制

```typescript
// components/ui/LanguageSwitcher.tsx
// 放在 Toolbar 右上角，Settings 按钮旁边
// 点击切换：EN ⟷ 中文
// 使用 next-intl 的 useLocale() + setLocale()
// 语言偏好存入 localStorage + Zustand store
```

---

## 2. 语言包：魔咒系统 (Spell System)

### `messages/en.json` — Spells Section

```json
{
  "spells": {
    "veritafactum": {
      "name": "Veritafactum",
      "subtitle": "Sentence Verification",
      "description": "Verify each sentence against academic sources"
    },
    "citalio": {
      "name": "Citalio",
      "subtitle": "Citation Recommendation",
      "description": "Automatically suggest relevant citations for your claims"
    },
    "proliferomaxima": {
      "name": "Proliferomaxima",
      "subtitle": "Reference Expansion",
      "description": "Expand VF Store by harvesting citation networks"
    },
    "exportario": {
      "name": "Ex-portario",
      "subtitle": "Full-Text Retrieval",
      "description": "Batch download full texts through institutional access"
    },
    "gnosiplexio": {
      "name": "Gnosiplexio",
      "subtitle": "Knowledge Graph",
      "description": "Visualise knowledge as an interactive network"
    }
  }
}
```

### `messages/zh.json` — Spells Section

```json
{
  "spells": {
    "veritafactum": {
      "name": "真知照见",
      "subtitle": "逐句验证",
      "description": "逐句对照学术文献，验证每一个论断"
    },
    "citalio": {
      "name": "引经据典",
      "subtitle": "智能引文推荐",
      "description": "自动为论述推荐最相关的学术引文"
    },
    "proliferomaxima": {
      "name": "寻书万卷",
      "subtitle": "引用网络增殖",
      "description": "从引用网络中批量扩充知识库"
    },
    "exportario": {
      "name": "破壁取珠",
      "subtitle": "全文自动获取",
      "description": "利用机构账号批量穿透付费墙下载全文"
    },
    "gnosiplexio": {
      "name": "织智成网",
      "subtitle": "知识图谱",
      "description": "将学术知识编织为可交互的可视化网络"
    }
  }
}
```

---

## 3. 语言包：工作台界面 (Workbench UI)

### English

```json
{
  "workbench": {
    "explorer": "Explorer",
    "sessions": "Sessions",
    "artifacts": "Artifacts",
    "chat": "Chat",
    "console": "Console",
    "terminal": "Terminal",
    "reasoning": "Reasoning",
    "newSession": "New Session",
    "deleteSession": "Delete Session",
    "duplicateSession": "Duplicate Session",
    "renameSession": "Rename Session",
    "noArtifacts": "No artifacts yet",
    "dragToReorder": "Drag to reorder"
  },
  "toolbar": {
    "run": "Run",
    "stop": "Stop",
    "save": "Save",
    "settings": "Settings",
    "theme": "Theme",
    "language": "Language",
    "killSwitch": "Kill Switch"
  }
}
```

### 中文

```json
{
  "workbench": {
    "explorer": "文件浏览器",
    "sessions": "会话",
    "artifacts": "文稿",
    "chat": "对话",
    "console": "控制台",
    "terminal": "终端",
    "reasoning": "推理过程",
    "newSession": "新建会话",
    "deleteSession": "删除会话",
    "duplicateSession": "复制会话",
    "renameSession": "重命名会话",
    "noArtifacts": "暂无文稿",
    "dragToReorder": "拖拽排序"
  },
  "toolbar": {
    "run": "运行",
    "stop": "停止",
    "save": "保存",
    "settings": "设置",
    "theme": "主题",
    "language": "语言",
    "killSwitch": "紧急停止"
  }
}
```

---

## 4. 语言包：Checker / Veritafactum

### English

```json
{
  "checker": {
    "title": "Veritafactum",
    "runCheck": "Run Check",
    "checking": "Checking...",
    "results": "Results",
    "verified": "Verified",
    "unverified": "Unverified",
    "needsCitation": "Needs Citation",
    "ownContribution": "Own Contribution",
    "notInLibrary": "Not in Library",
    "accept": "Accept",
    "dismiss": "Dismiss",
    "highlight": "Highlight",
    "confidence": {
      "high": "High",
      "medium": "Medium",
      "low": "Low"
    },
    "categories": {
      "VERIFIED": "Verified — supported by source",
      "NEEDS_CITATION": "Needs Citation",
      "OWN_CONTRIBUTION": "Own Contribution",
      "NOT_IN_LIBRARY": "Source not in library",
      "UNVERIFIED": "Could not verify"
    },
    "annotationCard": {
      "source": "Source",
      "evidence": "Evidence",
      "suggestion": "Suggestion"
    }
  }
}
```

### 中文

```json
{
  "checker": {
    "title": "真知照见",
    "runCheck": "开始验证",
    "checking": "验证中...",
    "results": "验证结果",
    "verified": "已验证",
    "unverified": "未验证",
    "needsCitation": "需要引文",
    "ownContribution": "原创论述",
    "notInLibrary": "文献库中未收录",
    "accept": "采纳",
    "dismiss": "忽略",
    "highlight": "标记",
    "confidence": {
      "high": "高置信",
      "medium": "中置信",
      "low": "低置信"
    },
    "categories": {
      "VERIFIED": "已验证 — 有文献支持",
      "NEEDS_CITATION": "需要补充引文",
      "OWN_CONTRIBUTION": "作者原创论述",
      "NOT_IN_LIBRARY": "来源文献未收录",
      "UNVERIFIED": "无法验证"
    },
    "annotationCard": {
      "source": "来源文献",
      "evidence": "证据",
      "suggestion": "建议"
    }
  }
}
```

---

## 5. 语言包：Citalio

### English

```json
{
  "citalio": {
    "title": "Citalio",
    "runScan": "Scan for Citations",
    "scanning": "Scanning...",
    "results": "Citation Suggestions",
    "autoCite": "Auto-cite (high confidence)",
    "maybeCite": "Maybe cite (review needed)",
    "manualNeeded": "Manual citation needed",
    "noCiteNeeded": "No citation needed",
    "insertCitation": "Insert Citation",
    "acceptAll": "Accept All",
    "candidateCount": "{count} candidates found"
  }
}
```

### 中文

```json
{
  "citalio": {
    "title": "引经据典",
    "runScan": "扫描引文需求",
    "scanning": "扫描中...",
    "results": "引文建议",
    "autoCite": "自动引用（高置信）",
    "maybeCite": "建议引用（需审核）",
    "manualNeeded": "需手动查找引文",
    "noCiteNeeded": "无需引文",
    "insertCitation": "插入引文",
    "acceptAll": "全部采纳",
    "candidateCount": "找到 {count} 个候选引文"
  }
}
```

---

## 6. 语言包：Proliferomaxima

### English

```json
{
  "proliferomaxima": {
    "title": "Proliferomaxima",
    "startExpansion": "Start Expansion",
    "running": "Expanding...",
    "refsFound": "References Found",
    "refsProcessed": "Processed",
    "refsSkipped": "Skipped (no abstract)",
    "refsFailed": "Failed",
    "profilesAdded": "Profiles Added",
    "duplicatesSkipped": "Duplicates Skipped",
    "estimatedTime": "Estimated Time Remaining",
    "completed": "Expansion Complete"
  }
}
```

### 中文

```json
{
  "proliferomaxima": {
    "title": "寻书万卷",
    "startExpansion": "开始增殖",
    "running": "增殖中...",
    "refsFound": "发现引用条目",
    "refsProcessed": "已处理",
    "refsSkipped": "已跳过（无摘要）",
    "refsFailed": "失败",
    "profilesAdded": "新增档案",
    "duplicatesSkipped": "跳过重复项",
    "estimatedTime": "预计剩余时间",
    "completed": "增殖完成"
  }
}
```

---

## 7. 语言包：Gnosiplexio

### English

```json
{
  "gnosiplexio": {
    "title": "Gnosiplexio",
    "networkView": "Network View",
    "timelineView": "Timeline View",
    "egoView": "Ego View",
    "clusterView": "Cluster View",
    "search": "Search knowledge graph...",
    "nodes": "Nodes",
    "edges": "Edges",
    "centrality": "Centrality",
    "credibility": "Credibility Score",
    "citedFor": "Cited For",
    "notFor": "Not Cited For",
    "citedBy": "Cited By",
    "perspectives": "Cross-Perspectives",
    "filterByYear": "Filter by Year",
    "filterByDomain": "Filter by Domain",
    "filterByAuthor": "Filter by Author",
    "export": "Export Graph"
  }
}
```

### 中文

```json
{
  "gnosiplexio": {
    "title": "织智成网",
    "networkView": "网络视图",
    "timelineView": "时间线视图",
    "egoView": "关联视图",
    "clusterView": "聚类视图",
    "search": "搜索知识图谱...",
    "nodes": "节点",
    "edges": "连接",
    "centrality": "中心度",
    "credibility": "可信度评分",
    "citedFor": "被引用于",
    "notFor": "不适用于",
    "citedBy": "被引用方",
    "perspectives": "跨视角解读",
    "filterByYear": "按年份筛选",
    "filterByDomain": "按领域筛选",
    "filterByAuthor": "按作者筛选",
    "export": "导出图谱"
  }
}
```

---

## 8. 语言包：Settings & Auth

### English

```json
{
  "settings": {
    "title": "Settings",
    "apiKeys": "API Keys",
    "personas": "Personas",
    "preferences": "Preferences",
    "language": "Language",
    "theme": "Theme",
    "save": "Save",
    "cancel": "Cancel",
    "reset": "Reset to Default"
  },
  "auth": {
    "login": "Login",
    "logout": "Logout",
    "username": "Username",
    "password": "Password"
  }
}
```

### 中文

```json
{
  "settings": {
    "title": "设置",
    "apiKeys": "API 密钥",
    "personas": "AI 角色",
    "preferences": "偏好设置",
    "language": "语言",
    "theme": "主题",
    "save": "保存",
    "cancel": "取消",
    "reset": "恢复默认"
  },
  "auth": {
    "login": "登录",
    "logout": "退出登录",
    "username": "用户名",
    "password": "密码"
  }
}
```

---

## 9. 语言包：VF Middleware Manager

### English

```json
{
  "vfManager": {
    "title": "VF Middleware Manager v2",
    "loading": "Loading...",
    "stats": "Stats",
    "profiles": "Profiles",
    "generateProfile": "Generate Profile",
    "syncLibrary": "Sync Library",
    "dryRunSync": "Dry Run Sync",
    "reanalyzeAll": "Re-analyze All",
    "exportProfiles": "Export Profiles",
    "bulkCompare": "Bulk Compare",
    "comingSoon": "This feature is coming in a future update",
    "submit": "Submit",
    "generating": "Generating profile...",
    "syncing": "Syncing...",
    "searchPlaceholder": "Search paper_id or title",
    "filterAll": "All",
    "filterInLibrary": "In Library",
    "filterExternal": "External",
    "showing": "Showing {visible} of {filtered} profiles",
    "filteredFrom": "(filtered from {total} total)",
    "noProfiles": "No profiles.",
    "showMore": "Show more ({remaining} remaining)",
    "noTitle": "(no title)",
    "loadingPreview": "Loading preview...",
    "empty": "(empty)",
    "delete": "delete",
    "deleteConfirm": "Delete {paperId}?",
    "profileGenerated": "Profile generated",
    "loadFailed": "Load failed",
    "lookupFailed": "Lookup failed",
    "generateFailed": "Generate failed",
    "syncFailed": "Sync failed",
    "form": {
      "paperId": "paper_id",
      "abstract": "abstract",
      "fullText": "full_text",
      "metadataJson": "metadata JSON",
      "inLibrary": "in_library"
    },
    "chunks": {
      "meta": "Meta",
      "abstract": "Abstract",
      "theory": "Theory",
      "literature": "Literature",
      "research_questions": "Research Questions",
      "contributions": "Contributions",
      "key_concepts": "Key Concepts",
      "cited_for": "Cited For"
    }
  }
}
```

### 中文

```json
{
  "vfManager": {
    "title": "VF 档案管理器 v2",
    "loading": "加载中...",
    "stats": "统计数据",
    "profiles": "档案列表",
    "generateProfile": "生成档案",
    "syncLibrary": "同步文献库",
    "dryRunSync": "试运行同步",
    "reanalyzeAll": "全部重新分析",
    "exportProfiles": "导出档案",
    "bulkCompare": "批量对比",
    "comingSoon": "此功能即将推出",
    "submit": "提交",
    "generating": "生成中...",
    "syncing": "同步中...",
    "searchPlaceholder": "搜索文献ID或标题",
    "filterAll": "全部",
    "filterInLibrary": "库内文献",
    "filterExternal": "外部文献",
    "showing": "显示 {visible} / {filtered} 篇档案",
    "filteredFrom": "（共 {total} 篇中筛选）",
    "noProfiles": "暂无档案",
    "showMore": "显示更多（剩余 {remaining} 篇）",
    "noTitle": "（无标题）",
    "loadingPreview": "加载预览中...",
    "empty": "（空）",
    "delete": "删除",
    "deleteConfirm": "确认删除 {paperId}？",
    "profileGenerated": "档案已生成",
    "loadFailed": "加载失败",
    "lookupFailed": "查询失败",
    "generateFailed": "生成失败",
    "syncFailed": "同步失败",
    "form": {
      "paperId": "文献ID",
      "abstract": "摘要",
      "fullText": "全文",
      "metadataJson": "元数据 JSON",
      "inLibrary": "库内文献"
    },
    "chunks": {
      "meta": "元信息",
      "abstract": "摘要",
      "theory": "理论框架",
      "literature": "文献综述",
      "research_questions": "研究问题",
      "contributions": "学术贡献",
      "key_concepts": "核心概念",
      "cited_for": "引用用途"
    }
  }
}
```

---

## 10. 语言包：通用 (Common)

### English

```json
{
  "common": {
    "loading": "Loading...",
    "error": "Error",
    "retry": "Retry",
    "close": "Close",
    "confirm": "Confirm",
    "cancel": "Cancel",
    "delete": "Delete",
    "edit": "Edit",
    "create": "Create",
    "search": "Search...",
    "noResults": "No results found",
    "copy": "Copy",
    "copied": "Copied!",
    "download": "Download",
    "upload": "Upload",
    "refresh": "Refresh",
    "more": "More",
    "less": "Less",
    "selectAll": "Select All",
    "deselectAll": "Deselect All",
    "fullArticle": "Full Article",
    "abstractOnly": "Abstract Only (Inferred)"
  }
}
```

### 中文

```json
{
  "common": {
    "loading": "加载中...",
    "error": "错误",
    "retry": "重试",
    "close": "关闭",
    "confirm": "确认",
    "cancel": "取消",
    "delete": "删除",
    "edit": "编辑",
    "create": "新建",
    "search": "搜索...",
    "noResults": "未找到结果",
    "copy": "复制",
    "copied": "已复制！",
    "download": "下载",
    "upload": "上传",
    "refresh": "刷新",
    "more": "展开",
    "less": "收起",
    "selectAll": "全选",
    "deselectAll": "取消全选",
    "fullArticle": "全文支撑",
    "abstractOnly": "仅摘要（推断）"
  }
}
```

---

## 11. 实施步骤

### Step 1: 搭架子（~30min）
1. `npm install next-intl`
2. 创建 `messages/en.json` 和 `messages/zh.json`（合并上面所有 section）
3. 创建 `src/i18n/config.ts` 和 `src/i18n/request.ts`
4. 在 `layout.tsx` 包裹 `NextIntlClientProvider`
5. 在 Zustand store 加 `locale` 状态

### Step 2: 语言切换按钮（~15min）
1. 创建 `LanguageSwitcher.tsx` — 简单的 `EN | 中文` 切换按钮
2. 放在 Toolbar 右上角（Settings 旁边）
3. 切换时更新 Zustand store + localStorage

### Step 3: 逐组件替换硬编码字符串（~2-3h）
按优先级：
1. **WorkbenchLayout** — Explorer/Chat/Console 标签
2. **ConsolePanel** — Checker/Citalio/Proliferomaxima tab 名称
3. **CheckerPanel + AnnotationCard** — 验证结果文案
4. **CitalioPanel** — 引文建议文案
5. **ProliferomaximaPanel** — 增殖进度文案
6. **GnosiplexioPanel** — 图谱界面文案
7. **SettingsModal** — 设置页面
8. **Common** — Button, Modal, Error 等通用组件

### Step 4: 验证（~30min）
1. 切换语言，检查所有页面是否正确显示
2. 检查布局（中文通常比英文短，不会溢出）
3. 检查动态内容（如 `{count} candidates found` → `找到 {count} 个候选引文`）

---

## 12. 注意事项

- **不要翻译** API 字段名、JSON key、变量名 — 只翻译用户可见的 UI 文案
- **保留魔咒拉丁名** 作为代码内部标识（`veritafactum`），中文名只出现在 UI 显示层
- **未来扩展** — 加新语言只需添加 `messages/ja.json` 等，零代码改动
- **长度注意** — 中文四字词组比英文短，布局上问题不大；个别地方英文可能更长，用 `truncate` class 兜底

---

## 13. ⚠️ 给码农的重要提醒

**这份说明书不是穷举清单！** 它覆盖了主要界面文案，但前端代码中可能还有其他硬编码字符串没有列出。

**码农必须做到：**
1. **仔细阅读每一个 `.tsx` / `.ts` 文件**，找出所有用户可见的硬编码字符串
2. 凡是出现在 UI 上的英文文字（按钮、标签、提示、placeholder、toast、confirm 对话框等）都要提取到语言包
3. 如果发现本说明书没覆盖的文案，**自行添加到 `en.json` 和 `zh.json`**，不用问，直接加
4. 特别注意：`console.log` / `error.message` 等开发者信息**不需要**翻译，只翻译用户看到的内容
5. 动态拼接的字符串（如 `\`Showing ${count} results\``）要改成 i18n 的插值格式（`t('key', { count })`）

**目标：切换到中文后，界面上不应该残留任何英文 UI 文案（代码标识符和 API 字段名除外）。**

---

*双语界面，让学术魔法触达每一位研究者。* ✨
