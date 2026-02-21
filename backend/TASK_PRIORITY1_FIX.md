# 任务: Priority 1 修复

**派发者:** 小蕾
**执行者:** 码农小蕾
**时间:** 2026-02-19

---

## 🎯 目标

将 230 篇有 chunks 文件夹但不在 Qdrant 的论文导入系统，使 `lookup_introduction()` 等工具能正常工作。

---

## ⚠️ 重要提醒

1. **数据已备份！** 位置: `backups/2026-02-19_priority1_fix/`
2. **不要删除任何现有数据**，只做添加操作
3. **每完成一步测试一下**，确保没问题再继续

---

## 📋 任务清单

### 方案 A: 导入 vf_profiles (让工具工作)

- [ ] **Step 1:** 读取 Priority 1 论文列表
  - 文件: `data/priority1_fix_plan.json`
  - 或从 SQLite 查询: `SELECT * FROM papers WHERE paper_id LIKE 'CHUNKS_%'`

- [ ] **Step 2:** 为每篇论文创建 vf_profiles record
  ```python
  # 每篇论文需要一个 meta record:
  {
      "paper_id": "CHUNKS_xxx" 或 clean_id (去掉 CHUNKS_ 前缀),
      "chunk_id": "meta",
      "meta": {
          "title": "...",
          "year": 2024,
          "doi": "10.xxx/xxx",
          "authors": [...],
      }
  }
  ```

- [ ] **Step 3:** 更新 SQLite papers.chunks_folder
  - 确保 `chunks_folder` 字段指向正确的文件夹名（不含 CHUNKS_ 前缀）

- [ ] **Step 4:** 测试
  ```python
  from tools import lookup_introduction
  result = lookup_introduction("CHUNKS_Andon_et_al_2014_...")
  assert result['found'] == True
  ```

### 方案 B: 导入 academic_papers (语义搜索)

- [ ] **Step 5:** 读取每篇论文的章节文件
  - 位置: `library-rag/data/chunks/{folder_name}/`
  - 文件: `introduction.txt`, `conclusion.txt`, `abstract.txt` 等

- [ ] **Step 6:** 向量化并导入 Qdrant academic_papers
  ```python
  # 每个章节一个 point:
  {
      "paper_name": "folder_name",
      "filename": "folder_name.md",
      "source": "parsed",
      "section": "introduction",  # 或 conclusion, abstract 等
      "text": "章节内容...",
      "chunk_index": 1,
      "total_chunks": N,
  }
  ```

- [ ] **Step 7:** 更新 SQLite 标记
  - `in_vf_store = 1`
  - `vf_profile_exists = 1`

---

## 📂 关键路径

- **SQLite:** `backend/data/central_index.sqlite`
- **Chunks:** `C:\Users\Lily Xiaolei Li (UoN)\clawd\projects\library-rag\data\chunks\`
- **Qdrant:** `http://localhost:6333`
- **Collections:** `vf_profiles`, `academic_papers`

---

## 🔧 参考代码

### 导入 vf_profiles
```python
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
import uuid

client = QdrantClient(host='localhost', port=6333)

# 插入 meta record
point = PointStruct(
    id=str(uuid.uuid4()),
    vector=[0.0] * 1536,  # 占位向量
    payload={
        "paper_id": paper_id,
        "chunk_id": "meta",
        "meta": {
            "title": title,
            "year": year,
            "doi": doi,
        }
    }
)

client.upsert(collection_name="vf_profiles", points=[point])
```

### 生成 embedding
```python
from openai import OpenAI

client = OpenAI()
response = client.embeddings.create(
    model="text-embedding-3-small",
    input=text
)
embedding = response.data[0].embedding
```

---

## ✅ 完成标准

1. `lookup_introduction("CHUNKS_xxx")` 返回 `found=True`
2. 230 篇论文都能提取章节
3. SQLite 标记已更新
4. 无报错

---

**完成后通知小蕾汇报！** 🌸
