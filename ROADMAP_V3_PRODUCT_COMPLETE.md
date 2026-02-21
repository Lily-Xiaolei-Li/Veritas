# Roadmap v3 — “完成整个产品”路线图（Veritas）

**目标口径（老爷版）：** 把 Agent B 从“平台雏形 + 若干完成的里程碑”推进到 **可稳定安装、可演示、可扩展、可发布 v1.0** 的完整产品。

> 与 `roadmap.md` 的关系：本文件是“更完整的产品级路线图（含发布/打包/CI/测试/文档/安全/迁移）”。
> 仍遵守原原则：垂直切片、可验证、日志优先、失败可观测。

---

## 0. 当前基线（从仓库现状推断）

- ✅ Phase 0/1 关键基础设施已齐：DB、Auth、SSE、Artifacts、Sessions、Kill Switch、LLM providers、（可选）LangGraph runtime。
- 📌 Roadmap v2 里“下一步”是：
  - **B1.7 Document Processing**
  - **B1.8 Tool Framework**
  - **B1.9 Simple Agent Loop**
  - Phase 2（Docs/DX/Testing/Release）

**产品级缺口**（完成产品必须补齐）：
- 可安装/可复现（one-command / 一键启动 + 环境检测更强）
- 端到端核心流程的自动化测试（API+UI 或最少 API+smoke）
- 版本化、迁移与升级策略（最少：DB migrations + changelog + semver）
- 发布产物（Release notes / license / 安全说明 / 配置模板）
- 文档体系（Quickstart、Dev Guide、Extension Guide、Troubleshooting）

---

## 1. 产品完成定义（Definition of Product Complete）

满足以下即视为“完整产品（v1.0）”：

### 1.1 必须具备的用户故事（MVP）
1. **安装启动**：新用户按 README 在 10–15 分钟内启动成功。
2. **会话**：创建/切换/删除 session；刷新页面不丢。
3. **消息 → 运行 → 结果**：发送消息触发一次 run，看到 streaming 输出，run 有稳定状态（queued/running/succeeded/failed/cancelled）。
4. **工具调用**：至少支持 3 个内置工具（file_read/file_write/shell_exec）并在 UI 有可视化日志。
5. **文档处理**：上传 docx/xlsx/pdf，能抽取内容；生成 docx/xlsx 作为 artifact 下载。
6. **安全**：Kill switch 可靠；危险命令有阻断或审批；日志可追溯；敏感信息不被记录。

### 1.2 非功能指标（上线底线）
- **可观测**：关键路径有结构化日志 + run audit trail。
- **可测**：核心路径至少 1 套端到端 smoke（API 层即可），CI 上跑。
- **可维护**：错误信息可操作；代码有明确边界（routes/services/models）。

---

## 2. 路线图总览（从现在到 v1.0）

> 依赖顺序（建议）：B1.7 → B1.8 → B1.9 → B2.2 Docs → B2.3 DX → B2.4 Testing/Stability → B2.5 Release

### Phase 1 — Platform Foundation（补齐核心能力）
- **B1.7 Document Processing（必须）**
- **B1.8 Tool Framework（必须）**
- **B1.9 Simple Agent Loop（必须）**

### Phase 2 — Polish & Release（产品化）
- **B2.2 Documentation（必须）**
- **B2.3 Developer Experience（必须）**
- **B2.4 Testing & Stability（必须）**
- **B2.5 v1.0 Release（必须）**

### Phase 3 — “开箱即用应用模板”（可选但强烈建议）
- **B3.0 App Template + Example Extension**（让平台“看起来像产品”）

---

## 3. 里程碑拆解（可执行的子里程碑）

下面把 B1.7/1.8/1.9 进一步拆到“每一步可合并的 PR 大小”。

### B1.7 Document Processing（Doc/Excel/PDF）
**目标**：文档读写能力变成平台内置服务 + API + UI 交互。

**B1.7.1 依赖与包管理锁定**
- python 依赖：python-docx, openpyxl, pymupdf（fitz）
- 加入 requirements.txt / poetry?（以仓库既有方式为准）
- 加最小健康检查：import 成功、版本记录

**B1.7.2 后端 Service 层（纯函数优先）**
- `DocumentProcessingService`：
  - `extract_text(path) -> {text, meta}`
  - `extract_tables(path) -> {sheets, cells}`（xlsx）
  - `generate_docx(content, template?) -> file`
  - `generate_xlsx(data) -> file`
- 失败路径：不支持格式、损坏文件、超大文件

**B1.7.3 API endpoints（Explorer/Artifacts 集成）**
- 上传文档 → 生成 artifact + 解析结果（JSON）
- 下载生成文档（artifact）
- 所有操作写 audit log

**B1.7.4 前端最小 UI**
- 在 Explorer 或 Artifacts panel：
  - 上传 docx/xlsx/pdf
  - 展示抽取文本（预览）/ 表格（简版）
  - 生成 docx/xlsx 并下载

**验收**：与 `roadmap.md` B1.7 acceptance criteria 一致。

---

### B1.8 Tool Framework（工具系统）
**目标**：把“能力”抽象成可注册、可发现、可审计的工具。

**B1.8.1 Tool schema + registry（后端）**
- 统一 Tool 定义：name、description、args schema、risk level、timeout、requires_approval
- Registry 支持：列出工具、获取 schema

**B1.8.2 Tool execution runtime（后端）**
- 统一执行入口：
  - 输入：tool_name + args + session_id + run_id
  - 输出：success/failed + stdout/stderr + artifacts + timing
- 审计：每次 tool call 入库（含 redaction）

**B1.8.3 内置工具 v1（最少）**
- file_read（workspace 范围限制）
- file_write（workspace 范围限制 + overwrite policy）
- shell_exec（沙箱/allowlist/阻断危险命令）
- document_read/document_write（复用 B1.7 service）

**B1.8.4 UI 展示**
- Console panel：显示 tool 调用时间线、输入摘要、输出摘要、错误可点击展开。

**验收**：
- `GET /tools` 能列出工具
- 任意 tool 执行可追溯（run → tool events）
- tool 报错不炸 agent loop

---

### B1.9 Simple Agent Loop（最小 agent 跑通）
**目标**：聊天 → LLM → 工具 → 结果，形成稳定“Run”概念。

**B1.9.1 Run contract 冻结**
- 明确 run 状态机（以 `docs/run-state-machine.md` 为唯一真相）
- REST “view model” API：
  - `POST /sessions/{id}/runs`（或类似）
  - `GET /runs/{id}`
  - `GET /sessions/{id}/runs`

**B1.9.2 LLM 调用与流式输出**
- 统一：prompt/messages → provider → streaming tokens
- 失败：provider 不可用、超时、鉴权失败

**B1.9.3 工具调用抽取（最简版）**
- v1 可以先支持“显式工具协议”（例如 JSON 区块）
- 后续再兼容 function calling（不同 provider 差异大）

**B1.9.4 反馈循环**
- tool result → 追加到 messages → 再问 LLM → 最终回答

**B1.9.5 UI 端到端**
- Reasoning panel：发送消息、显示 streaming
- Console panel：显示 tool events
- Artifacts panel：显示新 artifact

**验收**：
- “Create a file called test.txt” → tool 被调用 → 文件出现在 workspace/explorer
- 刷新页面 → session/history 仍在

---

## 4. Phase 2（产品化）详细清单

### B2.2 Documentation（文档体系）
- README：quickstart（Win/Mac/Linux 视情况）
- Developer guide：架构、目录、扩展点
- Extension guide：如何写新 tool/provider/panel
- Security model：沙箱、审批、redaction
- Troubleshooting：常见报错（DB/Docker/ports）

### B2.3 Developer Experience（开发体验）
- `start.bat`/`start.sh` 强化：预检查（Python/Node/PG/Docker）
- `.env.example` 完整
- 可选：docker-compose（只作为可选，不强制）
- 贡献指南（CONTRIBUTING）+ lint/format

### B2.4 Testing & Stability（测试与稳定）
- 后端单测：services + tool runtime + document processing
- API 集成测：sessions/runs/tools/artifacts/doc endpoints
- 最少 1 个 e2e smoke（Playwright 可选；至少 curl/pytest style）
- CI：GitHub Actions（lint+tests）
- 性能基线：大文件上限、解析耗时记录

### B2.5 v1.0 Release（发布）
- LICENSE（MIT）
- CHANGELOG
- semver tag v1.0.0
- Release notes：包含迁移说明
- 安全说明：默认配置、危险项

---

## 5. 可选 Phase 3：让平台“看起来像产品”的 Demo App

**B3.0 App Template（可选但建议）**
- 提供一个 `examples/hello-agentb/`：
  - 自定义 tool（例如：csv_summary）
  - 自定义 panel（展示结果）
  - 打包成“别人克隆就能跑”的示例

---

## 6. 风险与决策点（需要老爷拍板的地方）

1. **工具调用协议 v1**：
   - 方案 A：先用“显式 JSON 区块协议”（最稳）
   - 方案 B：强依赖 provider 的 function calling（更漂亮但更脆）
   - 建议：v1 走 A，v1.1 再做 B

2. **Docker 定位**：
   - README 说“no docker required”，但执行沙箱又写 Docker。需统一措辞：
   - 建议：**Docker 仅用于执行沙箱**，DB 用本地 PG（非 Docker）

3. **PDF 写入**：
   - v1 只做读取（roadmap 已同意写入 deferred）

---

## 7. 建议的交付节奏（现实可落地）

- Sprint 1：B1.7（文档）
- Sprint 2：B1.8（工具框架 + 内置工具）
- Sprint 3：B1.9（simple agent loop）
- Sprint 4：B2.2 + B2.3（文档与 DX）
- Sprint 5：B2.4（测试稳定）
- Sprint 6：B2.5（发布）

---

## 8. “下一步”建议（我建议马上做什么）

1) 先把 **B1.7** 做成最小垂直切片：上传 docx → 提取文本 → artifact + UI 预览
2) 再做 **B1.8** 的 registry + file_read/file_write（让 agent loop 有工具可用）
3) 最后做 **B1.9**：把 run 跑通（message → llm → tool → response）

---

> 备注：当要动 run 状态机或 SSE schema 时，必须先更新 `docs/run-state-machine.md`，并加 contract tests 防回归。
