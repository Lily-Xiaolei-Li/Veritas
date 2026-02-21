# Library Tools UI 设计

**设计者:** 小蕾
**日期:** 2026-02-19

---

## 📍 位置

在 **VF Manager Panel** 中添加 Library Tools 区域，放在 Stats 卡片下方。

---

## 🎨 布局设计

```
┌─────────────────────────────────────────────────────┐
│  VF Manager                              [Refresh]  │
├─────────────────────────────────────────────────────┤
│  Agent: [helper ▼]  [Generate] [Sync] [Dry Run]    │
├─────────────────────────────────────────────────────┤
│  Stats                                              │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐               │
│  │  1,055  │ │   879   │ │   176   │               │
│  │  Total  │ │In Library│ │External │               │
│  └─────────┘ └─────────┘ └─────────┘               │
├─────────────────────────────────────────────────────┤
│  📚 Library Tools                        NEW!       │
│  ┌─────────────────────────────────────────────────┐│
│  │ Database Status                                 ││
│  │ Total: 1,290 │ Complete: 86% │ VF: 1,055       ││
│  └─────────────────────────────────────────────────┘│
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │
│  │📊 Status │ │✅ Check  │ │🔍 Gaps   │ │📤Export│ │
│  └──────────┘ └──────────┘ └──────────┘ └────────┘ │
├─────────────────────────────────────────────────────┤
│  VF Profiles List...                                │
│  - Ahrens_2006                                      │
│  - Butler_2010                                      │
│  ...                                                │
└─────────────────────────────────────────────────────┘
```

---

## 🔘 按钮功能

| 按钮 | 功能 | API 调用 |
|------|------|----------|
| **📊 Status** | 显示详细状态弹窗 | `GET /api/library/status` |
| **✅ Check** | 完整性检查弹窗 | `GET /api/library/check` |
| **🔍 Gaps** | 数据差距分析弹窗 | `GET /api/library/gaps` |
| **📤 Export** | 导出数据库对话框 | `GET /api/library/export` |

---

## 📦 Export 对话框

```
┌─────────────────────────────────────┐
│  📤 Export Library Database         │
├─────────────────────────────────────┤
│                                     │
│  Format:  (•) CSV  ( ) JSON         │
│                                     │
│  Papers to export: 1,290            │
│                                     │
│      [Cancel]      [Download]       │
└─────────────────────────────────────┘
```

点击 Download 后直接下载文件。

---

## 📊 Status 弹窗

```
┌─────────────────────────────────────┐
│  📊 Library Status                  │
├─────────────────────────────────────┤
│  Total Papers:        1,290         │
│  In VF Store:         1,055 (82%)   │
│  Has Chunks:          1,110 (86%)   │
│  In Excel Index:        640 (50%)   │
│                                     │
│  Section Coverage:                  │
│  ├─ Abstract:           973 (75%)   │
│  ├─ Introduction:     1,093 (85%)   │
│  ├─ Methodology:        813 (63%)   │
│  └─ Conclusion:       1,077 (83%)   │
│                                     │
│              [Close]                │
└─────────────────────────────────────┘
```

---

## 🔧 实现步骤

### 1. 后端 API (如果不存在)

```python
# backend/app/api/library.py

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import subprocess
import json

router = APIRouter(prefix="/api/library", tags=["library"])

@router.get("/status")
async def get_status():
    result = subprocess.run(
        ["python", "-m", "cli", "library", "status", "--json"],
        capture_output=True, text=True, cwd="."
    )
    return json.loads(result.stdout)

@router.get("/check")
async def get_check():
    result = subprocess.run(
        ["python", "-m", "cli", "library", "check", "--json"],
        capture_output=True, text=True, cwd="."
    )
    return json.loads(result.stdout)

@router.get("/gaps")
async def get_gaps():
    result = subprocess.run(
        ["python", "-m", "cli", "library", "gaps", "--json"],
        capture_output=True, text=True, cwd="."
    )
    return json.loads(result.stdout)

@router.get("/export")
async def export_library(format: str = "csv"):
    # 生成文件并返回
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{format}") as f:
        output_path = f.name
    
    subprocess.run(
        ["python", "-m", "cli", "library", "export", 
         "--output", output_path, "--format", format],
        cwd="."
    )
    
    def iterfile():
        with open(output_path, "rb") as f:
            yield from f
        os.unlink(output_path)
    
    return StreamingResponse(
        iterfile(),
        media_type="text/csv" if format == "csv" else "application/json",
        headers={"Content-Disposition": f"attachment; filename=library_export.{format}"}
    )
```

### 2. 前端 API 调用

```typescript
// frontend/src/lib/api/library.ts

export async function fetchLibraryStatus() {
  const res = await fetch("/api/library/status");
  return res.json();
}

export async function fetchLibraryCheck() {
  const res = await fetch("/api/library/check");
  return res.json();
}

export async function fetchLibraryGaps() {
  const res = await fetch("/api/library/gaps");
  return res.json();
}

export async function downloadLibraryExport(format: "csv" | "json" = "csv") {
  const res = await fetch(`/api/library/export?format=${format}`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `library_export.${format}`;
  a.click();
  URL.revokeObjectURL(url);
}
```

### 3. 前端组件

```typescript
// 在 VFManagerPanel.tsx 中添加 Library Tools 区域

// 在 Stats 区域后面添加:
{/* Library Tools */}
<div className="rounded border p-3 bg-white dark:bg-gray-900">
  <h3 className="font-semibold text-sm mb-2 flex items-center gap-2">
    📚 Library Tools
    <span className="text-xs bg-blue-100 text-blue-800 px-1 rounded">NEW</span>
  </h3>
  
  {/* Quick Stats */}
  <div className="text-xs mb-2 p-2 bg-gray-50 dark:bg-gray-800 rounded">
    Total: {libraryStats?.total_papers || "..."} | 
    Complete: {libraryStats?.completeness_pct || "..."}%
  </div>
  
  {/* Action Buttons */}
  <div className="flex flex-wrap gap-2 text-xs">
    <button 
      className="border rounded px-2 py-1 hover:bg-gray-100 dark:hover:bg-gray-800"
      onClick={() => setShowStatusModal(true)}
    >
      📊 Status
    </button>
    <button 
      className="border rounded px-2 py-1 hover:bg-gray-100 dark:hover:bg-gray-800"
      onClick={() => setShowCheckModal(true)}
    >
      ✅ Check
    </button>
    <button 
      className="border rounded px-2 py-1 hover:bg-gray-100 dark:hover:bg-gray-800"
      onClick={() => setShowGapsModal(true)}
    >
      🔍 Gaps
    </button>
    <button 
      className="border rounded px-2 py-1 hover:bg-blue-500 text-white bg-blue-500"
      onClick={() => setShowExportModal(true)}
    >
      📤 Export
    </button>
  </div>
</div>
```

---

## ✅ 完成标准

1. Library Tools 区域显示在 VF Manager 的 Stats 下方
2. 四个按钮都能点击并显示对应内容
3. Export 能正常下载 CSV 文件
4. 样式与现有 VF Manager 一致

---

*设计完成！* 🌸
