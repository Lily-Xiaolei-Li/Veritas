# GP v2.0 Phase Progress Log

## 2026-02-24

### Phase0
- **产出**
  - 整理现有 gp-viz 骨架的环境与接口输入：确认 Qdrant 集合 (`vf_profiles_slr`)、Excel/PDF 路径、XiaoLei API 配置。
  - 清理并修复 `app/utils/config.py`：
    - 同时支持 `GP_VECTR_COLLECTION`（兼容）与 `GP_QDRANT_COLLECTION`。
  - 新建并统一检查脚本说明（`.env.example`, `README.md`）。
- **验证结果**
  - `python -m py_compile ...` 全量通过。
  - `python -m scripts.check_environment`：
    - 环境变量、Excel、PDF、Qdrant collection 均通过；
    - `/chat` 未连通（当前本机未启动 8768）。
- **产出文件**
  - `app/utils/config.py`
  - `README.md`
  - `.env.example`
  - `scripts/check_environment.py`
- **是否可进入下一阶段**：是（阻塞项为 XiaoLei 本机服务，不影响离线开发阶段推进）。

### Phase0.5
- **产出**
  - 通过配置 + 工具层实现最小数据源可检验链路：
    - `app/utils/qdrant_client.py`（Qdrant 滚动读取 + 基础检索打分）
    - `app/utils/excel_probe.py`（Excel 元数据读取）
  - API 端补充 `/check` 与 `/meta` 检查信息端点。
- **验证结果**
  - `Qdrant /collections/{vf_profiles_slr}` 可达。
  - `scripts.check_environment` 已输出 collection 与数据路径状态。
- **产出文件**
  - `app/utils/qdrant_client.py`
  - `app/utils/excel_probe.py`
  - `app/api/routes.py`（新增 `/check`,`/meta`）
- **是否可进入下一阶段**：是。

### Phase1
- **产出**
  - 完成检索与详情 API：
    - `GET /papers`：关键词匹配排序返回 Top K
    - `GET /papers/{paper_id}`：详情
    - `POST /assist`：检索透传
    - `POST /assist-stream`：XiaoLei `/chat` SSE 聚合代理（token + artifact）
  - 更新 Streamlit 主界面以展示搜索、详情与 Assistant 调用。
- **验证结果**
  - `python -m py_compile ...` 全量通过。
  - 由于 XiaoLei 未启动，`/assist-stream` 的联调待服务恢复后验证。
- **产出文件**
  - `app/api/routes.py`
  - `app/main.py`
- **是否可进入下一阶段**：是。

### Phase2
- **产出**
  - 当前版本的 Streamlit 已具备阶段入口与查询交互（已兼容 Phase2 初始可视化）
- **验证结果**
  - 代码可编译通过；服务启动前端依赖服务可达检查。
- **产出文件**
  - `app/main.py`
- **是否可进入下一阶段**：是（待下一轮联调补齐）。

### Phase3
- **产出**
  - 健康检查和环境检查统一化；服务配置和文档清理。
- **验证结果**
  - `docker compose config` 通过（仅提示 `compose file` 版本字段弃用）
- **产出文件**
  - `docker-compose.yml`
  - `README.md`
- **是否可进入下一阶段**：是。

### Phase4
- **产出**
  - 阶段性进展归档，形成可直接接替的阶段状态文件。
- **验证结果**
  - 本地语法/编译校验通过。
- **产出文件**
  - `PHASE_EXECUTION_LOG.md`
- **是否可进入下一阶段**：该阶段为交付收尾，完成。