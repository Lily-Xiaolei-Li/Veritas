# Library Export 功能设计

**设计者:** 小蕾
**日期:** 2026-02-19

---

## 🎯 功能目标

一键导出完整数据库为 CSV 格式，便于：
- 在 Excel 中查看和分析
- 备份和分享
- 与其他系统集成

---

## 📋 CLI 命令设计

```bash
# 基础导出
python -m cli library export --output library_export.csv

# 带选项
python -m cli library export \
    --output library_export.csv \
    --format csv \
    --include-empty \
    --filter "year>=2020"
```

### 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--output` | 输出文件路径 | `library_export_{timestamp}.csv` |
| `--format` | 输出格式 (csv/json/xlsx) | `csv` |
| `--include-empty` | 包含空字段 | False |
| `--filter` | 过滤条件 | None |

---

## 📊 CSV 列设计

### 核心标识 (必须)
| 列名 | 来源 | 说明 |
|------|------|------|
| `item_id` | paper_id | 主键标识 |
| `canonical_id` | canonical_id | 规范化 ID |
| `doi` | doi | DOI 标识符 |

### 基本元数据
| 列名 | 来源 | 说明 |
|------|------|------|
| `title` | title | 论文标题 |
| `authors` | authors_json | 作者列表 (逗号分隔) |
| `year` | year | 发表年份 |
| `journal` | journal | 期刊/出处 |
| `paper_type` | paper_type | 论文类型 |
| `primary_method` | primary_method | 主要研究方法 |
| `keywords` | keywords_json | 关键词 (逗号分隔) |

### 数据完整性状态
| 列名 | 来源 | 说明 |
|------|------|------|
| `in_vf_store` | in_vf_store | 是否在 VF Store (0/1) |
| `in_excel_index` | in_excel_index | 是否在 Excel 索引 (0/1) |
| `has_chunks` | has_chunks_folder | 是否有 chunks (0/1) |
| `chunk_count` | lib_chunk_count | Chunk 数量 |

### 章节可用性
| 列名 | 来源 | 说明 |
|------|------|------|
| `has_abstract` | has_abstract | 有摘要 (0/1) |
| `has_introduction` | has_introduction | 有引言 (0/1) |
| `has_methodology` | has_methodology | 有方法论 (0/1) |
| `has_conclusion` | has_conclusion | 有结论 (0/1) |

### VF Store 状态
| 列名 | 来源 | 说明 |
|------|------|------|
| `vf_profile_exists` | vf_profile_exists | VF Profile 存在 (0/1) |
| `vf_chunks_count` | vf_chunks_generated | VF Chunks 数量 |

### 文件路径
| 列名 | 来源 | 说明 |
|------|------|------|
| `pdf_filename` | pdf_filename | PDF 文件名 |
| `chunks_folder` | chunks_folder | Chunks 文件夹路径 |

### 时间戳
| 列名 | 来源 | 说明 |
|------|------|------|
| `created_at` | created_at | 创建时间 |
| `updated_at` | updated_at | 更新时间 |

---

## 📝 CSV 输出示例

```csv
item_id,canonical_id,doi,title,authors,year,journal,paper_type,primary_method,keywords,in_vf_store,in_excel_index,has_chunks,chunk_count,has_abstract,has_introduction,has_methodology,has_conclusion,vf_profile_exists,vf_chunks_count,pdf_filename,chunks_folder,created_at,updated_at
Ahrens_2006,Ahrens_Chapman_2006_DoingQualitative,10.1016/j.aos.2006.01.002,"Doing qualitative field research...","Thomas Ahrens, Christopher S. Chapman",2006,Accounting Organizations and Society,methodological essay,qualitative field research,"qualitative research, field research",1,0,1,119,1,1,0,1,1,8,,Ahrens_Chapman_2006_Doing_qualitative,2026-02-19,2026-02-19
```

---

## 🖥️ GUI 集成

### 位置
`+Source` 菜单 → `Library Tools` → `📤 Export Database`

### 对话框设计

```
┌─────────────────────────────────────────┐
│  📤 Export Library Database             │
├─────────────────────────────────────────┤
│                                         │
│  Format:  ○ CSV  ○ JSON  ○ Excel        │
│                                         │
│  Options:                               │
│  ☑ Include empty fields                 │
│  ☐ Include file paths                   │
│  ☐ Only complete papers                 │
│                                         │
│  Filter by year: [____] to [____]       │
│                                         │
│  Output: [library_export_20260219.csv]  │
│          [Browse...]                    │
│                                         │
├─────────────────────────────────────────┤
│  Papers to export: 1,290                │
│                                         │
│        [Cancel]        [Export]         │
└─────────────────────────────────────────┘
```

---

## 🔧 实现架构

### Backend

```python
# cli/library_handlers.py - 添加

def library_export(args):
    """导出图书馆数据库为 CSV"""
    import csv
    from datetime import datetime
    
    output = args.output or f"library_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    conn = sqlite3.connect(str(CENTRAL_DB))
    cur = conn.cursor()
    
    # 查询所有数据
    cur.execute("""
        SELECT 
            paper_id as item_id,
            canonical_id,
            doi,
            title,
            authors_json,
            year,
            journal,
            paper_type,
            primary_method,
            keywords_json,
            in_vf_store,
            in_excel_index,
            has_chunks_folder as has_chunks,
            lib_chunk_count as chunk_count,
            has_abstract,
            has_introduction,
            has_methodology,
            has_conclusion,
            vf_profile_exists,
            vf_chunks_generated as vf_chunks_count,
            pdf_filename,
            chunks_folder,
            created_at,
            updated_at
        FROM papers
        ORDER BY paper_id
    """)
    
    rows = cur.fetchall()
    columns = [d[0] for d in cur.description]
    
    # 写入 CSV
    with open(output, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        
        for row in rows:
            # 处理 JSON 字段
            processed = []
            for i, val in enumerate(row):
                if columns[i] in ('authors_json', 'keywords_json') and val:
                    try:
                        items = json.loads(val)
                        val = ', '.join(items) if isinstance(items, list) else val
                    except:
                        pass
                processed.append(val)
            writer.writerow(processed)
    
    conn.close()
    
    return success_envelope({
        "output": output,
        "rows": len(rows),
        "columns": columns
    })
```

### API Endpoint

```python
# app/api/library.py

@router.get("/export")
async def export_library(
    format: str = "csv",
    include_empty: bool = True
):
    """导出图书馆数据库"""
    # 生成文件并返回
    pass

@router.get("/export/download")
async def download_export(filename: str):
    """下载导出文件"""
    from fastapi.responses import FileResponse
    return FileResponse(path=filename, media_type='text/csv')
```

### Frontend Component

```typescript
// components/library/ExportDialog.tsx

interface ExportDialogProps {
  open: boolean;
  onClose: () => void;
}

export function ExportDialog({ open, onClose }: ExportDialogProps) {
  const [format, setFormat] = useState<'csv' | 'json' | 'xlsx'>('csv');
  const [loading, setLoading] = useState(false);
  
  const handleExport = async () => {
    setLoading(true);
    const response = await fetch(`/api/library/export?format=${format}`);
    const blob = await response.blob();
    // 下载文件
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `library_export.${format}`;
    a.click();
    setLoading(false);
    onClose();
  };
  
  return (
    <Dialog open={open} onClose={onClose}>
      {/* 对话框内容 */}
    </Dialog>
  );
}
```

---

## ✅ 完成标准

1. CLI: `python -m cli library export --output test.csv --json` 能正常导出
2. API: `GET /api/library/export` 返回 CSV 文件
3. GUI: 点击按钮能下载 CSV 文件
4. CSV 格式正确，Excel 能正常打开
5. 中文字符正确显示 (UTF-8 BOM)

---

## 🎯 实施优先级

1. **Phase 1:** CLI 命令 (最快实现)
2. **Phase 2:** API endpoint
3. **Phase 3:** GUI 对话框

---

*设计完成，待老爷审批！* 🌸
