# XiaoLei API Specification

小蕾 API - Veritas 的后台大脑接口

## Overview

这是一个 FastAPI 服务，作为 Veritas 和小蕾 (Clawdbot) 之间的桥梁。

**端口：** 8768
**位置：** `backend/xiaolei_api/`

## Endpoints

### POST /chat

与小蕾对话，支持 SSE 流式输出。

**Request:**
```json
{
  "message": "用户输入的消息",
  "context": "可选的上下文（如当前选中的文本）",
  "button_prompt": "可选的快捷按钮 prompt"
}
```

**Response (SSE Stream):**
```
data: {"type": "token", "content": "小"}
data: {"type": "token", "content": "蕾"}
data: {"type": "token", "content": "回复"}
data: {"type": "artifact", "content": "生成的文档内容", "filename": "output.md"}
data: {"type": "done"}
```

### POST /rag/search

搜索 RAG 图书馆。

**Request:**
```json
{
  "query": "carbon audit assurance",
  "limit": 10,
  "collection": "papers"
}
```

**Response:**
```json
{
  "results": [
    {
      "title": "Paper Title",
      "authors": "Author, A.",
      "year": 2024,
      "relevance": 0.92,
      "snippet": "相关段落..."
    }
  ]
}
```

### GET /buttons

获取快捷按钮列表。

**Response:**
```json
{
  "buttons": [
    {
      "id": "citation",
      "name": "Look for citation",
      "prompt": "Search our library and find sources that strongly support this sentence...",
      "icon": "search"
    }
  ]
}
```

### POST /buttons

添加新按钮。

### DELETE /buttons/{id}

删除按钮。

### GET /health

健康检查。

## Implementation Notes

1. **不使用另一个 LLM** - 调用现有的 Clawdbot/小蕾
2. **RAG 集成** - 调用 localhost:8767 (Library API)
3. **按钮存储** - JSON 文件: `data/buttons.json`
4. **SSE 流式** - 实时返回小蕾的回复

## 与 Clawdbot 的连接

使用 Clawdbot 的 sessions API 或直接 HTTP 调用。

选项 A: 通过 lily-remote (8765)
```python
response = requests.post("https://localhost:8765/execute", json={
    "command": "clawdbot chat 'user message'"
})
```

选项 B: 直接调用 Clawdbot sessions API
```python
# 需要进一步研究 Clawdbot 的 API
```

## Quick Buttons 预设

1. **Look for citation**
   - Prompt: "Search our library and find sources that strongly support this sentence. Return all reasonably relevant results with title, author, year, and a brief explanation of why it's relevant."

2. **Harvard referencing**
   - Prompt: "Check this citation list against our library, identify any missing ones, then generate a Harvard-style reference list in the artifact."

3. **Summarize paper**
   - Prompt: "Summarize this academic paper, including: research question, methodology, key findings, and implications."

4. **Find similar papers**
   - Prompt: "Find papers in our library that are similar to this one in terms of topic, methodology, or theoretical framework."

5. **Check argument**
   - Prompt: "Analyze this argument for logical consistency and identify any potential weaknesses or gaps in reasoning."
