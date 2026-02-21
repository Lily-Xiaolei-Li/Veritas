# Veritas 用户手册

**版本:** 1.0.0 | **更新:** 2026-02-19  
**作者:** Lily Xiaolei Li

---

## 📖 目录

1. [简介](#简介)
2. [快速开始](#快速开始)
3. [GUI 功能指南](#gui-功能指南)
4. [论文库管理](#论文库管理)
5. [研究工具](#研究工具)
6. [常见问题 FAQ](#常见问题-faq)
7. [故障排除](#故障排除)

---

## 简介

### Veritas 是什么？

Veritas 是一个**本地优先的学术研究工作台**，专为研究人员、博士生和学术工作者设计。它帮助您：

- 🗂️ **管理研究材料** — 论文、笔记、草稿集中在 Session 中
- 🤖 **AI 辅助写作** — 使用多种 Persona（角色）完成不同写作任务
- 📚 **智能论文库** — 语义搜索您的论文集，找到相关引用
- ✍️ **迭代式写作流程** — 从模板到初稿，从审稿到定稿的完整工作流

### 核心概念

| 概念 | 说明 |
|------|------|
| **Session** | 一个独立的研究工作空间，如"Chapter 3 草稿" |
| **Artifact** | Session 中的任何文档——论文、模板、草稿、评审意见 |
| **Persona** | AI 的角色设定——Drafter 写作、Reviewer 审稿、Referencer 引用检查 |
| **VF Store** | 向量存储库，存储论文的语义表示，支持智能搜索 |
| **Library** | 您的论文库，包含所有已导入的学术文献 |

### 系统要求

- **操作系统:** Windows 10/11
- **Python:** 3.12+
- **Node.js:** 18+
- **数据库:** PostgreSQL 16+
- **内存:** 4GB+ 可用
- **硬盘:** 5GB+ 空间

---

## 快速开始

### 5 分钟上手

#### 第一步：启动 Veritas

双击 **`Start Veritas (Stable).bat`**

等待约 30 秒，浏览器将自动打开 http://localhost:3000

> 💡 **提示:** 如果没有自动打开，手动访问 http://localhost:3000

#### 第二步：创建第一个 Session

1. 点击左侧边栏的 **"+ New Session"** 按钮
2. 输入名称，例如 "Literature Review Draft"
3. 点击 **Create**

*您的工作空间就绪！*

#### 第三步：添加第一个文档

1. 点击左下角的 **"+Source"** 按钮
2. 选择 **"📄 Add File"**
3. 上传一个 PDF 或 Word 文档
4. 系统会自动转换为 Markdown 格式

#### 第四步：开始对话

1. 在底部的聊天框输入问题，例如：
   
   ```
   请帮我总结这篇论文的主要观点
   ```

2. 按 Enter 或点击发送
3. AI 会阅读您的文档并回复

#### 第五步：保存 AI 输出

1. 在 AI 的回复中，点击 **"Save as Artifact"** 按钮
2. 给它一个名字，如 "Summary Draft"
3. 这个输出就成为了一个可编辑的 Artifact

**恭喜！** 您已经掌握了基本流程。

---

## GUI 功能指南

### 界面布局

打开 Veritas 后，您会看到三个主要区域：

```
┌─────────────────────────────────────────────────────────────┐
│                     顶部导航栏                               │
├──────────────┬──────────────────────────┬──────────────────┤
│              │                          │                  │
│   Session    │       主工作区           │    Artifact      │
│   侧边栏     │    (编辑器/聊天)         │    详情栏        │
│              │                          │                  │
│   [Sessions] │                          │   [Properties]   │
│   [Sources]  │                          │   [Preview]      │
│              │                          │                  │
├──────────────┴──────────────────────────┴──────────────────┤
│                     底部聊天输入框                           │
│   [Persona ▼] [输入消息...              ] [📎] [发送]       │
└─────────────────────────────────────────────────────────────┘
```

### Session 管理

**Session** 是您的研究项目容器。每个 Session 相互独立。

#### 创建 Session
- 点击左侧 **"+ New Session"**
- 输入有意义的名称（如 "Chapter 3 - Methodology"）
- 点击 Create

#### 切换 Session
- 点击左侧 Session 列表中的任一项
- 当前活跃 Session 会高亮显示

#### Session 最佳实践
- ✅ 每个章节或研究问题一个 Session
- ✅ 使用清晰的命名规范
- ❌ 避免把所有工作放在一个 Session

---

### Artifact 管理

**Artifact** 是 Session 中的文档单元。

#### Artifact 类型

| 图标 | 类型 | 说明 |
|------|------|------|
| 📝 | Markdown | 主要格式，支持富文本编辑 |
| 📄 | PDF 转换 | 从 PDF 导入后自动转为 Markdown |
| 💬 | AI 输出 | 保存的 AI 回复 |

#### 创建 Artifact
1. 点击 **"+ New Artifact"**
2. 选择类型（通常是 Markdown）
3. 输入名称
4. 开始编辑

#### 编辑 Artifact
- 点击 Artifact 在主工作区打开编辑器
- 支持 Markdown 语法高亮
- 自动保存（无需手动保存）

#### 删除 Artifact
- 右键点击 Artifact → Delete
- 或在详情栏点击删除图标
- ⚠️ **删除不可恢复，请谨慎操作**

---

### Source 添加 (+Source 菜单)

**+Source** 菜单让您导入各种研究材料。

#### 📄 Add File
- 支持格式：PDF, DOCX, TXT, MD
- PDF/DOCX 会自动转换为 Markdown
- 拖拽文件也可以

#### 🔗 Add URL
- 粘贴网页 URL
- 系统会抓取并转为 Markdown
- 适合导入在线论文、博客文章

#### 📝 Add Text
- 直接粘贴文本内容
- 快速记录笔记或片段

#### 📚 Library Tools (新功能!)
这是论文库管理的入口：

| 功能 | 说明 |
|------|------|
| 📊 Status Overview | 查看库状态概览 |
| ✅ Integrity Check | 检查数据完整性 |
| 🔍 Find Gaps | 找出缺失的数据 |
| 📈 VF Store Stats | 向量存储统计 |

---

### Chat 对话功能

#### 选择 Persona

在聊天框左侧可以选择 AI 角色：

| Persona | 用途 |
|---------|------|
| **Default** | 通用学术助手 |
| **Drafter** | 专业学术写作 |
| **Reviewer** | 模拟期刊审稿人 |
| **Referencer** | 检查和建议引用 |
| **Templator** | 从范文提取模板 |
| **Cleaner** | 清理格式混乱的文档 |
| **Thinker** | 发现隐藏规律 |
| **Skeptic** | 魔鬼代言人，找弱点 |

#### 附加 Artifact 作为上下文

1. 点击聊天框旁的 📎 图标
2. 选择要包含的 Artifact
3. AI 会在回复时参考这些文档

#### 使用 RAG 搜索论文库

在发送消息时启用 RAG：

1. 点击 RAG 开关
2. 选择搜索范围（Library）
3. 设置返回数量（默认 5）

AI 会从您的论文库中找到相关引用。

---

### VF Middleware（向量配置文件）

VF (Vector Fingerprint) 是每篇论文的"数字指纹"，用于语义搜索。

#### 在 GUI 中管理 VF

1. 打开 **VF Manager** 面板
2. 查看已有的 VF 配置文件
3. 为新论文生成 VF

#### VF 的作用
- 🔍 语义搜索：按含义而非关键词查找论文
- 📊 相似度分析：找到研究主题相近的论文
- 📖 智能引用：AI 推荐相关文献

---

## 论文库管理

### 导入论文

#### 方式一：单个 PDF 上传

1. 点击 **+Source → Add File**
2. 选择 PDF 文件
3. 系统自动：
   - 转换为 Markdown
   - 提取元数据
   - 生成 VF 配置文件

#### 方式二：批量导入

1. 准备一个包含 DOI 列表的文本文件
2. 使用 CLI 命令：
   ```powershell
   python -m cli.main source batch --dois doi_list.txt
   ```

#### 方式三：从引用管理器导入

支持从 Zotero、EndNote 导出的 BibTeX 文件：

```powershell
python -m cli.main source batch --bibtex references.bib
```

---

### 查看库状态

#### 在 GUI 中查看

1. 点击 **+Source → Library Tools → Status Overview**
2. 查看：
   - 论文总数
   - VF Store 状态
   - 章节覆盖率

#### 在 CLI 中查看

```powershell
cd backend
python -m cli.main library status --json
```

输出示例：
```json
{
  "total_papers": 156,
  "in_vf_store": 142,
  "section_coverage": {
    "abstract": 140,
    "introduction": 156,
    "conclusion": 150
  },
  "completeness_pct": 91.0
}
```

---

### 导出数据库

将论文库导出为 CSV（可在 Excel 中打开）：

```powershell
python -m cli.main library export --format csv --output my_library.csv
```

导出包含：
- 论文 ID、标题、作者、年份
- DOI、期刊信息
- 章节可用性标记
- VF Store 状态

---

## 研究工具

### 章节提取

从论文中提取特定章节，非常适合文献综述。

#### 提取 Introduction

```python
from tools import lookup_introduction

intro = lookup_introduction("Author_2020_Keywords")
print(intro)  # 输出 Introduction 章节内容
```

#### 提取 Conclusion

```python
from tools import lookup_conclusion

conclusion = lookup_conclusion("Author_2020_Keywords")
print(conclusion)
```

#### 一次获取所有章节

```python
from tools import lookup_all_sections

sections = lookup_all_sections("Author_2020_Keywords")

for name, content in sections.items():
    print(f"=== {name.upper()} ===")
    print(content[:500] if content else "Not available")
```

#### 可用章节

| 章节 | 函数 | 成功率 |
|------|------|--------|
| Abstract | `lookup_abstract()` | 90% |
| Introduction | `lookup_introduction()` | 100% |
| Literature Review | `lookup_literature_review()` | 80% |
| Methodology | `lookup_methodology()` | 50%* |
| Empirical Analysis | `lookup_empirical_analysis()` | 100% |
| Conclusion | `lookup_conclusion()` | 100% |

*方法论成功率较低是因为部分论文将其合并在其他章节中

---

### 参考文献查找

从论文中提取参考文献列表：

```python
from tools import lookup_references

refs = lookup_references("Author_2020_Keywords")

# 返回列表格式
for ref in refs:
    print(ref)
```

输出示例：
```
[1] Smith, J. (2015). Title of paper. Journal Name, 10(2), 123-145.
[2] Brown, A., & Green, B. (2018). Another paper. Conference Proceedings.
...
```

---

### 语义搜索

使用 RAG 在论文库中搜索相关内容：

#### 在 CLI 中搜索

```powershell
python -m cli.main chat send --session <uuid> \
  --rag library --rag-top-k 10 \
  --message "Find papers about carbon accounting disclosure"
```

#### 搜索技巧

1. **使用具体的学术术语**
   - ✅ "voluntary environmental disclosure determinants"
   - ❌ "why companies report green stuff"

2. **组合多个概念**
   - ✅ "carbon emissions AND institutional investors AND legitimacy"

3. **调整返回数量**
   - 初步探索：`--rag-top-k 15`
   - 精确查找：`--rag-top-k 5`

---

## 常见问题 FAQ

### Q: PDF 转换质量不好怎么办？

**A:** PDF 转 Markdown 的质量取决于原 PDF 的结构。如果结果不理想：

1. 尝试使用 **Cleaner** Persona：
   ```
   帮我清理这个文档的格式问题
   ```
2. 或手动调整 Markdown

---

### Q: AI 回复很慢怎么办？

**A:** 可能的原因和解决方案：

1. **网络问题** — 检查 VPN/代理设置
2. **上下文太长** — 减少附加的 Artifact 数量
3. **服务器负载** — 稍后再试

---

### Q: 如何引用论文库中的论文？

**A:** 使用 RAG 功能：

1. 开启 RAG 搜索
2. 让 AI 推荐引用：
   ```
   推荐 3 篇关于 legitimacy theory 的论文，并解释为什么适合引用
   ```
3. AI 只会推荐库中存在的论文

---

### Q: Session 数据存在哪里？

**A:** 
- 数据库位置：PostgreSQL (localhost:5433)
- Artifact 文件：`backend/data/` 目录
- 日志文件：`.run/` 目录

---

### Q: 可以多人协作吗？

**A:** 当前版本为单用户本地版。多人协作功能在路线图中。

---

## 故障排除

### 问题：启动失败，显示 "PostgreSQL connection failed"

**解决步骤：**

1. 检查 PostgreSQL 服务是否运行：
   ```powershell
   Get-Service -Name "postgresql*"
   ```

2. 如果未运行，启动服务：
   ```powershell
   net start postgresql-x64-17
   ```

3. 验证连接：
   ```powershell
   psql -h localhost -p 5433 -U agentb -d agent_b
   ```

---

### 问题：Qdrant 连接失败

**解决步骤：**

1. 启动 Qdrant 服务器：
   ```powershell
   cd C:\path\to\tools\qdrant
   .\qdrant.exe --config-path config\config.yaml
   ```

2. 验证运行：
   - 访问 http://localhost:6333/collections
   - 应看到 JSON 响应

---

### 问题：前端页面空白

**解决步骤：**

1. 检查后端是否运行：
   - 访问 http://localhost:8001/api/v1/health
   - 应返回 `{"status": "healthy"}`

2. 检查前端日志：
   - 查看 `.run/frontend.err.log`

3. 重启服务：
   ```powershell
   # 双击
   Stop Veritas (Stable).bat
   Start Veritas (Stable).bat
   ```

---

### 问题：PDF 上传失败

**可能原因：**

1. **文件太大** — 尝试拆分 PDF
2. **PDF 加密** — 先解除密码保护
3. **扫描件 PDF** — 需要 OCR，当前不支持

---

### 问题：AI 回复中断

**解决步骤：**

1. 刷新页面重试
2. 检查后端日志：`.run/backend.err.log`
3. 如果是 Token 超限，缩短输入或减少上下文

---

### 获取帮助

如果以上方法都无法解决问题：

1. 检查 GitHub Issues
2. 收集日志文件
3. 描述复现步骤
4. 联系技术支持

---

**祝您研究顺利！** 🎓

*Veritas — 让 AI 助力您的学术写作*
