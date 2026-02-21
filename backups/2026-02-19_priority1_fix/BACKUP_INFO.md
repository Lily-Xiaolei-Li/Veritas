# 备份信息 - Priority 1 修复前

**备份时间:** 2026-02-19 18:58 (Sydney)
**备份原因:** Priority 1 修复 - 将 230 篇有 chunks 但不在 Qdrant 的论文导入

---

## 📁 备份内容

### 1. SQLite 数据库
- **文件:** `central_index.sqlite.bak`
- **原路径:** `backend/data/central_index.sqlite`
- **大小:** 1.44 MB
- **内容:** 1290 篇论文的索引

### 2. Qdrant vf_profiles 快照
- **快照名:** `vf_profiles-8582934033346056-2026-02-19-07-58-44.snapshot`
- **存储位置:** Qdrant snapshots 目录
- **内容:** 1055 篇论文的 VF profiles

### 3. Qdrant academic_papers 快照
- **快照名:** `academic_papers-8582934033346056-2026-02-19-07-58-45.snapshot`
- **存储位置:** Qdrant snapshots 目录
- **内容:** 154,379 个 chunks

---

## 🔄 恢复方法

### 恢复 SQLite
```powershell
Copy-Item "backups\2026-02-19_priority1_fix\central_index.sqlite.bak" "backend\data\central_index.sqlite" -Force
```

### 恢复 Qdrant (如需要)
```powershell
# 列出快照
Invoke-RestMethod -Uri "http://localhost:6333/collections/vf_profiles/snapshots" -Method Get

# 恢复快照
Invoke-RestMethod -Uri "http://localhost:6333/collections/vf_profiles/snapshots/recover" -Method Put -Body '{"location": "vf_profiles-8582934033346056-2026-02-19-07-58-44.snapshot"}' -ContentType "application/json"
```

---

## 📋 修复任务

- **方案 A:** 导入 vf_profiles meta records
- **方案 B:** 向量化章节内容导入 academic_papers
- **执行者:** 码农小蕾 (coder)
- **预计影响:** 230 篇论文

---

*备份由小蕾创建* 🌸
