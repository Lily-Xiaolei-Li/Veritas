# Veritas Academic Workbench - 项目开发日志

## 2026-02-07 - XiaoLei API 集成成功 🎉

### 完成的工作

#### 1. Clawdbot Gateway HTTP API 配置
- ✅ 确认 Gateway HTTP API 已启用（端口 18789）
- ✅ 认证模式：Token-based
- ✅ Endpoint: `http://localhost:18789/v1/chat/completions`
- ✅ Auth Token: `cf8bf99bedae98b1c3feea260670dcb023a0dfb04fddf379`

#### 2. 新增 RAG 研究助手子代理
- ✅ 创建 `rag-assistant` 子代理
- ✅ 工作目录：老爷的论文图书馆 (607篇论文)
- ✅ 工具配置：minimal profile（只读/写/搜索，无危险操作）
- ✅ 模型：Claude Sonnet 4.5

#### 3. Backend 修复
**文件：`backend/config.py`**
- ✅ 添加 `xiaolei_gateway_url` 配置项
- ✅ 添加 `xiaolei_auth_token` 配置项

**文件：`backend/xiaolei_chat_routes.py`**
- ✅ 修复硬编码的错误 URL
- ✅ 添加 `Authorization: Bearer {token}` header
- ✅ 使用环境变量配置的 Gateway URL

**文件：`backend/.env`**
- ✅ 移除 BOM 编码
- ✅ 修复 `CORS_ORIGINS` 格式（改为 JSON 数组）
- ✅ 确认 `XIAOLEI_GATEWAY_URL` 和 `XIAOLEI_AUTH_TOKEN` 配置

#### 4. Frontend 修复
**文件：`frontend/src/lib/api/xiaoleiChat.ts`**
- ✅ 添加 `OpenAIStreamChunk` 接口定义
- ✅ 实现 `parseSSEData()` 智能格式解析
- ✅ 支持 OpenAI-compatible SSE 格式
- ✅ 修复流式响应显示逻辑

#### 5. 测试验证
- ✅ Gateway API 直连测试（curl）：成功
- ✅ Veritas `/api/chat` 代理测试：成功
- ✅ 前端界面显示测试：成功
- ✅ 完整流程端到端测试：通过 ✨

### 技术架构

```
Veritas Frontend (Next.js)
    ↓ HTTP POST
Veritas Backend (FastAPI) /api/chat
    ↓ HTTP POST with Authorization header
Clawdbot Gateway :18789/v1/chat/completions
    ↓ Route to agent
XiaoLei (rag-assistant sub-agent)
    ↓ SSE Stream
Response flows back through the chain
```

### 下一步计划

1. **功能增强**
   - [ ] 实现文献检索功能（搜索论文图书馆）
   - [ ] 集成 RAG 语义搜索
   - [ ] 添加引用管理功能
   
2. **UI 优化**
   - [ ] 改进聊天界面显示
   - [ ] 添加小蕾头像/状态指示
   - [ ] 优化 markdown 渲染

3. **工具集成**
   - [ ] 文献分析工具
   - [ ] 写作辅助功能
   - [ ] 数据分析支持

---

## 团队成员

- **主小蕾** - 项目协调、问题诊断
- **超级小蕾** - 代码修复、深度调试
- **老爷** - 产品设计、需求定义

---

## 技术债务记录

- [ ] Gateway 重启权限配置（目前禁用自动重启）
- [ ] 安全审计警告处理（文件权限 666）
- [ ] 前端 TypeScript 类型定义优化

---

最后更新：2026-02-07 16:59 (小蕾 🌸)

---

## 2026-02-10 - 对话记录回补 + 路线图确认（Step B + B1.8 Tool Framework）✅

### 背景
由于上一次对话被压缩（context compact），我丢失了我们最近几段关键确认与交付记录。老爷把完整对话贴回后，我已逐条核对并在此“补记”，确保项目日志连续。

### 我确认我忘了什么（已补回）
1) 我忘了 **Step B（删掉 Docker 依赖与健康检查残留）** 已经做完并且“真 no-docker”跑通。
2) 我忘了 **B1.8 Tool Framework 第一刀** 已经完成（registry + 内置 file_read/file_write + /tools API + 测试全绿）。
3) 我忘了我们已把 **tool_start/tool_end** 接到 SSE，让 Console panel 能直接可视化工具调用事件（前端无需改）。
4) 我忘了老爷的明确指示：**以后每次汇报必须在开头标注 Stage/里程碑编号**（例如：B1.8.3 shell_exec），用来证明我们严格按路线图推进。

### 路线图确认
- 我已重新阅读并确认：我们以 **Roadmap v3**（`ROADMAP_V3_PRODUCT_COMPLETE.md`）作为“产品完成路线图”，Phase 1 的顺序是 **B1.7 → B1.8 → B1.9**。
- 当前工作严格落在 **B1.8 Tool Framework** 内，没有跑偏。

### 已完成（从对话回补的交付）
**Step B：彻底移除 Docker**
- backend/requirements.txt 移除 docker 依赖
- `app/main.py` 不再依赖 docker_check（避免残留 import）
- 新增 `app/health_checks.py`：仅做资源检查（无 Docker）
- `app/docker_check.py` 改为 legacy 兼容壳：不执行 docker 命令，仅转调 health_checks
- `app/executor.py`：从 Docker 执行器改为本地 subprocess 执行器（保留原 contract）
- `termination_service.py`：移除 docker kill，改为终止本地 execution
- 相关文案/残留字符串清理（exec/session/logging/metrics）
- 对话中声明测试：pytest 318 passed, 2 skipped

**B1.8.1/B1.8.2：工具注册/发现/执行最小闭环**
- 新增 `backend/app/tools/types.py`、`backend/app/tools/registry.py`
- 内置工具：`file_read` / `file_write`
- 路由：`GET /api/v1/tools`、`POST /api/v1/tools/execute`
- 审计：best-effort 写入 tool_execute（便于追溯与 UI 展示）
- 对话中声明测试：pytest 320 passed, 2 skipped

**B1.8 可观测性：Tool 执行事件 → SSE → Console panel**
- 后端在工具执行时推送 SSE：`tool_start` / `tool_end`（含 input/output preview 与 duration）
- 前端 Console panel 原生监听这类事件，因此无需额外 UI 改动即可显示

### 下一步（已获授权）
- **Stage: B1.8.3 — Built-in tools：新增 shell_exec**
  - 复用现有 local executor + 安全控制
  - 接入 tool_start/tool_end SSE
  - 补齐测试覆盖：成功/失败/超时/高风险阻断（最少集）

---

## 2026-02-09 - 本地 E2E 调试：runs 卡住 + checkpointer 初始化修复 ✅

### 现象
- `/api/v1/sessions/{id}/messages` 能返回 `run_id`，但 run 长时间停留在 `running`
- 日志出现 `LLM retry ... after 60s` / `Gemini rate limit exceeded`
- 启动时 checkpointer 报错：`_AsyncGeneratorContextManager has no attribute setup`

### 根因
1. 默认 LLM provider=Gemini，在本地开发时常遇到 quota/rate-limit → retry_after=60s 导致“看起来卡住”
2. `AsyncPostgresSaver.from_conn_string()` 实际是 async context manager，被当作对象误用
3. Windows 下 psycopg3 async 与 ProactorEventLoop 兼容性问题，需要降级策略

### 修复
- `backend/.env`：开发默认切到 mock provider，保证端到端可跑通
- `backend/app/agent/checkpointer.py`：改为显式管理连接 + saver；遇到 ProactorEventLoop incompatibility 时优雅禁用 persistence
- `backend/app/main.py`：根据 `is_checkpointer_ready()` 打印 persistence enabled/disabled
- `TROUBLESHOOTING.md`：补充 runs stuck 的排查与 mock 配置

### 验证
- Backend `/health` `/docs` `/api/v1/sessions` 均 OK
- 端到端：创建 session → 提交 message → messages 出现 assistant 回复（mock）→ run 变为 completed

