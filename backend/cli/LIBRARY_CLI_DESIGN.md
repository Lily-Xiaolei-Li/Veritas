# Library CLI 设计方案

**设计者:** 小蕾
**日期:** 2026-02-19

---

## 📋 命令设计

### 新增 Resource: `library`

| 命令 | 用途 | 来源脚本 |
|------|------|----------|
| `abr library status` | 图书馆状态概览 | check_integrity.py |
| `abr library check` | 完整性检查 | final_integrity_report.py |
| `abr library gaps` | 数据差距分析 | check_gaps.py, find_incomplete.py |
| `abr library match` | 论文匹配检查 | analyze_matching.py |
| `abr library vf-status` | VF Store 状态 | check_vf_structure.py |
| `abr library fix` | 修复建议 | fix_priority1_plan.py |

---

## 🔧 实现步骤

### Step 1: 创建 `library_handlers.py`

```python
# backend/cli/library_handlers.py

from pathlib import Path
import sqlite3
import requests
from .contract import CLIBusinessError, success_envelope

QDRANT_URL = "http://localhost:6333"
CENTRAL_DB = Path(__file__).parent.parent / "data" / "central_index.sqlite"
CHUNKS_DIR = Path(r"C:\Users\Barry Li (UoN)\clawd\projects\library-rag\data\chunks")


def library_status(args):
    """图书馆状态概览"""
    conn = sqlite3.connect(str(CENTRAL_DB))
    cur = conn.cursor()
    
    # 基础统计
    cur.execute("SELECT COUNT(*) FROM papers")
    total = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM papers WHERE in_vf_store = 1")
    in_vf = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM papers WHERE has_chunks_folder = 1")
    has_chunks = cur.fetchone()[0]
    
    # 章节覆盖
    sections = {}
    for sec in ['abstract', 'introduction', 'methodology', 'conclusion']:
        cur.execute(f"SELECT COUNT(*) FROM papers WHERE has_{sec} = 1")
        sections[sec] = cur.fetchone()[0]
    
    conn.close()
    
    return success_envelope({
        "total_papers": total,
        "in_vf_store": in_vf,
        "has_chunks": has_chunks,
        "section_coverage": sections,
        "completeness": f"{100 * has_chunks / total:.1f}%"
    })


def library_check(args):
    """完整性检查"""
    # ... 实现
    pass


def library_gaps(args):
    """数据差距分析"""
    # ... 实现
    pass


def library_match(args):
    """论文匹配检查"""
    paper_id = args.paper_id
    # ... 实现
    pass


def library_vf_status(args):
    """VF Store 状态"""
    # ... 实现
    pass


def library_fix(args):
    """修复建议"""
    # ... 实现
    pass
```

### Step 2: 注册到 `main.py`

```python
# 在 imports 中添加
from .library_handlers import (
    library_status,
    library_check,
    library_gaps,
    library_match,
    library_vf_status,
    library_fix,
)

# 在 _select_handler() 中添加
if resource == "library" and action == "status":
    return library_status
if resource == "library" and action == "check":
    return library_check
if resource == "library" and action == "gaps":
    return library_gaps
if resource == "library" and action == "match":
    return library_match
if resource == "library" and action == "vf-status":
    return library_vf_status
if resource == "library" and action == "fix":
    return library_fix

# 在 _configure_action_parser() 中添加
elif resource == "library" and action == "match":
    action_parser.add_argument("--paper-id", required=True, help="Paper ID to check")
elif resource == "library" and action == "gaps":
    action_parser.add_argument("--priority", type=int, default=None, help="Filter by priority (1-3)")
elif resource == "library" and action == "fix":
    action_parser.add_argument("--priority", type=int, required=True, help="Priority to fix (1-3)")
    action_parser.add_argument("--dry-run", action="store_true", help="Show plan without executing")
```

---

## 🖥️ GUI 集成

### 在 `+Source` 菜单添加 "Library Tools"

**位置:** `frontend/src/components/files/` 或新建 `frontend/src/components/library/`

### 设计

```
+Source 菜单
├── 📄 Add File
├── 🔗 Add URL
├── 📝 Add Text
├── ─────────────
├── 📚 Library Tools  ← 新增
│   ├── 📊 Status Overview
│   ├── ✅ Integrity Check
│   ├── 🔍 Find Gaps
│   ├── 🔧 Run Fixes
│   └── 📈 VF Store Stats
```

### 前端组件结构

```
frontend/src/components/library/
├── LibraryToolsMenu.tsx      # 下拉菜单
├── LibraryStatusPanel.tsx    # 状态面板
├── LibraryGapsPanel.tsx      # 差距分析面板
├── LibraryFixPanel.tsx       # 修复面板
└── index.ts
```

### API 端点

```python
# backend/app/api/library.py

from fastapi import APIRouter

router = APIRouter(prefix="/library", tags=["library"])

@router.get("/status")
async def get_library_status():
    """获取图书馆状态"""
    pass

@router.get("/check")
async def check_integrity():
    """完整性检查"""
    pass

@router.get("/gaps")
async def find_gaps(priority: int = None):
    """找出数据差距"""
    pass

@router.post("/fix")
async def run_fix(priority: int, dry_run: bool = True):
    """执行修复"""
    pass
```

---

## 📁 文件移动计划

将今天创建的脚本整合到正式位置：

```
backend/
├── cli/
│   └── library_handlers.py    # CLI 命令处理
├── app/
│   └── api/
│       └── library.py         # REST API
├── services/
│   └── library_service.py     # 核心业务逻辑
└── scripts/
    └── library/               # 原始脚本备份
        ├── check_integrity.py
        ├── check_gaps.py
        └── ...
```

---

## 🎯 实施优先级

1. **高优先级:** `library status`, `library check` (最常用)
2. **中优先级:** `library gaps`, `library vf-status`
3. **低优先级:** `library fix` (需要更多测试)

---

## 💡 使用示例

```bash
# CLI 使用
python -m cli library status --json
python -m cli library check
python -m cli library gaps --priority 1
python -m cli library match --paper-id "Ahrens_2006"
python -m cli library fix --priority 1 --dry-run

# GUI 使用
# 点击 +Source → Library Tools → Status Overview
```

---

*设计完成，待老爷审批！* 🌸
