# Veritas Architecture Refactor Plan v2

**Author:** 小蕾 (李晓蕾)  
**Date:** 2026-02-21  
**Status:** Ready for Implementation  
**Previous:** ARCHITECTURE-REFACTOR-PLAN.md (ABR version by 超级小蕾)

---

## 1. Executive Summary

### 品牌重塑：ABR → Veritas

**Veritas** (拉丁语"真理") — 学术研究的本质就是追求真理。

将 Veritas (ABR) 重构为三个独立组件：

| 组件 | 名称 | 性质 | 进度 | 依赖 |
|------|------|------|------|------|
| **Veritas Core** | 真理核心 | 基础平台 | 95% | 无 |
| **Scholarly Hollows** | 学术魔法 | 魔法套装插件 | 50% | 依赖 Veritas Core |
| **Gnosiplexio (GP)** | 织智成网 | 独立软件 + 可选插件 | 0% | 可选依赖 Veritas Core |

### 核心设计理念

```
┌─────────────────────────────────────────────────┐
│              VERITAS 学术研究平台                │
│                                                 │
│   "Veritas Fingerprint" — 每篇论文的真相指纹    │
│                                                 │
│   Library RAG (全文) → VF Store (指纹) → 魔法   │
│         噪音多            精炼         高效施法  │
└─────────────────────────────────────────────────┘
```

---

## 2. Architecture Overview

### 2.1 高层架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         VERITAS Ecosystem                                │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                      Veritas Core (基础平台)                        │ │
│  │                                                                      │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │ │
│  │  │ Library RAG  │  │  VF Store    │  │  Session &   │              │ │
│  │  │ (Qdrant:     │  │  (Qdrant:    │  │  Artifact    │              │ │
│  │  │  academic_   │  │  vf_profiles)│  │  Manager     │              │ │
│  │  │  papers)     │  │              │  │  (PostgreSQL)│              │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │ │
│  │                                                                      │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │ │
│  │  │ VF Middleware│  │  AI Chat     │  │  Workbench   │              │ │
│  │  │ (Profile生成)│  │  (LLM API)   │  │  UI Shell    │              │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │ │
│  │                                                                      │ │
│  │  ══════════════════════════════════════════════════════════════    │ │
│  │                    Veritas Core API (REST + SSE)                    │ │
│  │  • /api/v1/library/*      (Library RAG 操作)                       │ │
│  │  • /api/v1/vf/*           (VF Store 操作)                          │ │
│  │  • /api/v1/sessions/*     (Session 管理)                           │ │
│  │  • /api/v1/artifacts/*    (Artifact CRUD)                          │ │
│  │  • /api/v1/chat           (LLM 对话)                               │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                              ▲                                           │
│                              │ 通过 Core API 访问                        │
│                              │                                           │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │              Scholarly Hollows (SH) 魔法套装                        │ │
│  │                                                                      │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │ │
│  │  │ Veritafactum │  │   Citalio    │  │Proliferomaxima│             │ │
│  │  │ (真知照见)   │  │ (引经据典)   │  │ (寻书万卷)   │              │ │
│  │  │ 逐句验证引用 │  │ 自动引文推荐 │  │ 引用网络增殖 │              │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │ │
│  │                                                                      │ │
│  │  ┌──────────────┐                                                   │ │
│  │  │  Ex-portario │                                                   │ │
│  │  │ (破壁取珠)   │                                                   │ │
│  │  │ 全文批量下载 │                                                   │ │
│  │  └──────────────┘                                                   │ │
│  │                                                                      │ │
│  │  ══════════════════════════════════════════════════════════════    │ │
│  │                    SH API Layer (/api/v1/sh/*)                      │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                    Gnosiplexio (GP) 织智成网                             │
│                    独立知识图谱软件                                       │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │  │
│  │  │ Graph Store │  │ Visualizer  │  │  Query      │               │  │
│  │  │ (Neo4j)     │  │ (D3.js)     │  │  Engine     │               │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘               │  │
│  │                                                                    │  │
│  │  Data Adapters: [Veritas Adapter] [Semantic Scholar] [BibTeX]    │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Component Specifications

### 3.1 Veritas Core (基础平台)

**职责：** 提供完整的学术研究辅助功能，无需任何插件即可独立运行。

#### 包含模块

| 模块 | 功能 | 存储 |
|------|------|------|
| **Library RAG** | 学术论文全文向量搜索 | Qdrant: `academic_papers` |
| **VF Store** | Veritas Fingerprint 存储 | Qdrant: `vf_profiles` |
| **VF Middleware** | 从论文生成 VF Profile (8个语义chunks) | - |
| **Session Manager** | 会话管理 | PostgreSQL |
| **Artifact Manager** | 文档/产出物管理 | PostgreSQL + 文件系统 |
| **AI Chat** | LLM 对话功能 | - |
| **Workbench UI** | 主界面外壳 | - |
| **Plugin Loader** | 插件加载系统 | - |

#### VF Profile 结构 (8 Semantic Chunks)

```python
class VFProfile:
    paper_id: str           # e.g., "Smith2024_deep_learning"
    chunks: {
        "meta":              # 元数据 (title, authors, year)
        "abstract":          # 摘要
        "theory":            # 理论框架
        "literature":        # 文献综述
        "research_questions": # 研究问题
        "contributions":     # 贡献
        "key_concepts":      # 关键概念
        "cited_for":         # 引用用途
    }
    in_library: bool        # 是否在本地图书馆
    created_at: datetime
```

#### Core API Endpoints

```yaml
# Library RAG
POST   /api/v1/library/search       # 语义搜索
GET    /api/v1/library/papers/{id}  # 获取论文
POST   /api/v1/library/ingest       # 导入论文 (供 Ex-portario 使用)

# VF Store
GET    /api/v1/vf/profiles          # 列出所有 Profile
POST   /api/v1/vf/profiles          # 创建 Profile
GET    /api/v1/vf/profiles/{id}     # 获取单个 Profile
DELETE /api/v1/vf/profiles/{id}     # 删除 Profile
POST   /api/v1/vf/search            # 语义搜索 VF Store
POST   /api/v1/vf/generate          # 生成 VF Profile
POST   /api/v1/vf/sync              # 同步图书馆

# Sessions
GET    /api/v1/sessions             # 列出会话
POST   /api/v1/sessions             # 创建会话
GET    /api/v1/sessions/{id}        # 获取会话

# Artifacts
GET    /api/v1/artifacts            # 列出产出物
POST   /api/v1/artifacts            # 创建产出物
GET    /api/v1/artifacts/{id}       # 获取产出物

# Chat
POST   /api/v1/chat                 # 发送消息 (SSE streaming)

# Plugins
GET    /api/v1/plugins              # 列出已安装插件
```

---

### 3.2 Scholarly Hollows (魔法套装)

**职责：** 高级学术 AI 功能，作为 Veritas Core 的插件运行。

#### ⚠️ 核心原则：通过 API 访问，不直接操作数据库

```python
# ✅ 正确：通过 Core API
response = await http_client.post(
    f"{VERITAS_CORE_URL}/api/v1/vf/search",
    json={"query": query, "limit": 10}
)

# ❌ 错误：直接访问 Qdrant
client = QdrantClient(...)  # 禁止！
```

#### 四大魔法

| 魔法 | 中文名 | 功能 | 依赖的 Core API |
|------|--------|------|-----------------|
| **Veritafactum** | 真知照见 | 逐句验证引用正确性 | `POST /api/v1/vf/search` |
| **Citalio** | 引经据典 | 为句子推荐合适引用 | `POST /api/v1/vf/search` |
| **Proliferomaxima** | 寻书万卷 | 从引用网络批量扩展 VF Store | `POST /api/v1/vf/profiles`, `POST /api/v1/library/ingest` |
| **Ex-portario** | 破壁取珠 | 穿透付费墙下载全文 | `POST /api/v1/library/ingest` |

#### 插件结构

```
scholarly-hollows/
├── manifest.json           # 插件元数据
├── requirements.txt
├── routes/
│   ├── __init__.py
│   ├── veritafactum.py
│   ├── citalio.py
│   ├── proliferomaxima.py
│   └── exportario.py
├── services/
│   ├── veritafactum/
│   ├── citalio/
│   ├── proliferomaxima/
│   └── exportario/
└── frontend/
    └── components/
```

#### manifest.json

```json
{
  "name": "scholarly-hollows",
  "version": "1.0.0",
  "display_name": "Scholarly Hollows",
  "description": "Academic magic spells for Veritas",
  "requires_veritas_version": ">=1.0.0",
  "api_prefix": "/api/v1/sh",
  "routes_module": "routes",
  "frontend_components": [
    "veritafactum",
    "citalio", 
    "proliferomaxima",
    "exportario"
  ]
}
```

#### SH API Endpoints

```yaml
POST /api/v1/sh/veritafactum/check    # 验证引用
POST /api/v1/sh/citalio/recommend     # 推荐引用
POST /api/v1/sh/proliferomaxima/run   # 运行增殖
POST /api/v1/sh/exportario/download   # 下载论文
```

---

### 3.3 Gnosiplexio (GP) — 织智成网

**职责：** 学术知识图谱生成与可视化。

#### 双运行模式

| 模式 | 说明 | 数据源 |
|------|------|--------|
| **独立模式** | 不依赖 Veritas | Semantic Scholar API, 本地 BibTeX |
| **Veritas Add-On** | 连接 Veritas Core | Veritas Core API (VF Store + Library) |

#### 数据源适配器接口

```python
from abc import ABC, abstractmethod
from typing import List, Optional

class DataSourceAdapter(ABC):
    """Gnosiplexio 数据源适配器接口"""
    
    @abstractmethod
    async def search_papers(self, query: str, limit: int) -> List[Paper]:
        """搜索论文"""
        pass
    
    @abstractmethod
    async def get_paper_profile(self, paper_id: str) -> Optional[VFProfile]:
        """获取论文 Profile"""
        pass
    
    @abstractmethod
    async def get_references(self, paper_id: str) -> List[Reference]:
        """获取引用列表"""
        pass


class VeritasAdapter(DataSourceAdapter):
    """Veritas Core 适配器"""
    
    def __init__(self, api_url: str = "http://localhost:8001"):
        self.api_url = api_url
    
    async def search_papers(self, query: str, limit: int) -> List[Paper]:
        response = await self.client.post(
            f"{self.api_url}/api/v1/library/search",
            json={"query": query, "limit": limit}
        )
        return [Paper(**p) for p in response.json()["results"]]
    
    async def get_paper_profile(self, paper_id: str) -> Optional[VFProfile]:
        response = await self.client.get(
            f"{self.api_url}/api/v1/vf/profiles/{paper_id}"
        )
        if response.status_code == 404:
            return None
        return VFProfile(**response.json())
```

---

## 4. Code Mapping (现有代码归属)

### 4.1 归属 Veritas Core

| 现有位置 | 新位置 |
|----------|--------|
| `backend/app/routes/session_routes.py` | `veritas-core/backend/app/routes/` |
| `backend/app/routes/artifact_routes.py` | `veritas-core/backend/app/routes/` |
| `backend/app/routes/chat_routes.py` | `veritas-core/backend/app/routes/` |
| `backend/app/routes/library_routes.py` | `veritas-core/backend/app/routes/` |
| `backend/app/routes/vf_routes.py` | `veritas-core/backend/app/routes/` |
| `backend/app/services/vf_middleware/` | `veritas-core/backend/app/services/` |
| `backend/app/services/knowledge_source/` | `veritas-core/backend/app/services/` |
| `backend/app/models/` | `veritas-core/backend/app/models/` |
| `backend/app/database.py` | `veritas-core/backend/app/` |
| `backend/app/config.py` | `veritas-core/backend/app/` |
| `backend/cli/` | `veritas-core/backend/cli/` |
| `backend/xiaolei_api/` | `veritas-core/backend/xiaolei_api/` |
| `frontend/` (除 SH 组件) | `veritas-core/frontend/` |

### 4.2 归属 Scholarly Hollows

| 现有位置 | 新位置 |
|----------|--------|
| `backend/app/routes/checker_routes.py` | `scholarly-hollows/routes/veritafactum.py` |
| `backend/app/routes/citalio_routes.py` | `scholarly-hollows/routes/citalio.py` |
| `backend/app/routes/proliferomaxima_routes.py` | `scholarly-hollows/routes/proliferomaxima.py` |
| `backend/app/services/checker/` | `scholarly-hollows/services/veritafactum/` |
| `backend/app/services/citalio/` | `scholarly-hollows/services/citalio/` |
| `backend/app/services/proliferomaxima/` | `scholarly-hollows/services/proliferomaxima/` |
| `frontend/src/components/checker/` | `scholarly-hollows/frontend/veritafactum/` |
| `frontend/src/components/citalio/` | `scholarly-hollows/frontend/citalio/` |
| `frontend/src/components/proliferomaxima/` | `scholarly-hollows/frontend/proliferomaxima/` |

### 4.3 归属 Gnosiplexio

| 现有位置 | 新位置 |
|----------|--------|
| `backend/app/routes/gnosiplexio_routes.py` | `gnosiplexio/api/routes/` |
| `backend/app/services/gnosiplexio/` | `gnosiplexio/core/` |
| `docs/PRD-gnosiplexio.md` | `gnosiplexio/docs/` |

---

## 5. Plugin Loading System

### 5.1 Core 端插件加载器

```python
# veritas-core/backend/app/plugins.py

import importlib
import json
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI

class PluginManager:
    """Veritas Core 插件管理器"""
    
    def __init__(self, plugin_dir: str = "/opt/veritas/plugins"):
        self.plugin_dir = Path(plugin_dir)
        self.loaded_plugins: List[str] = []
    
    def discover(self) -> List[dict]:
        """发现已安装插件"""
        plugins = []
        if not self.plugin_dir.exists():
            return plugins
        
        for path in self.plugin_dir.iterdir():
            manifest_path = path / "manifest.json"
            if manifest_path.exists():
                with open(manifest_path) as f:
                    manifest = json.load(f)
                    manifest["path"] = str(path)
                    plugins.append(manifest)
        return plugins
    
    def load(self, app: FastAPI, plugin_name: str) -> bool:
        """加载插件路由到 FastAPI"""
        try:
            plugin_path = self.plugin_dir / plugin_name
            manifest_path = plugin_path / "manifest.json"
            
            with open(manifest_path) as f:
                manifest = json.load(f)
            
            # 动态导入路由模块
            spec = importlib.util.spec_from_file_location(
                f"plugins.{plugin_name}",
                plugin_path / manifest["routes_module"] / "__init__.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # 注册路由
            if hasattr(module, "router"):
                app.include_router(
                    module.router,
                    prefix=manifest.get("api_prefix", f"/api/v1/plugins/{plugin_name}"),
                    tags=[manifest["display_name"]]
                )
            
            self.loaded_plugins.append(plugin_name)
            return True
            
        except Exception as e:
            print(f"Failed to load plugin {plugin_name}: {e}")
            return False
    
    def load_all(self, app: FastAPI):
        """加载所有发现的插件"""
        for plugin in self.discover():
            self.load(app, plugin["name"])
```

### 5.2 在 main.py 中使用

```python
# veritas-core/backend/app/main.py

from fastapi import FastAPI
from app.plugins import PluginManager

app = FastAPI(title="Veritas Core")

# ... 注册 Core 路由 ...

# 加载插件
plugin_manager = PluginManager()
plugin_manager.load_all(app)

# 插件列表端点
@app.get("/api/v1/plugins")
async def list_plugins():
    return {
        "plugins": plugin_manager.discover(),
        "loaded": plugin_manager.loaded_plugins
    }
```

---

## 6. Database & Storage

### 6.1 数据归属

| 数据 | 存储 | 归属 |
|------|------|------|
| `vf_profiles` collection | Qdrant | Veritas Core |
| `academic_papers` collection | Qdrant | Veritas Core |
| `sessions` table | PostgreSQL | Veritas Core |
| `artifacts` table | PostgreSQL | Veritas Core |
| `users` table | PostgreSQL | Veritas Core |
| Knowledge Graph | Neo4j | Gnosiplexio (独立) |

### 6.2 SH 数据访问原则

**SH 插件不直接访问数据库**，只通过 Veritas Core API：

```python
# scholarly-hollows/services/citalio/searcher.py

import httpx

class CitationSearcher:
    def __init__(self, core_url: str = "http://localhost:8001"):
        self.core_url = core_url
        self.client = httpx.AsyncClient()
    
    async def search(self, query: str, limit: int = 10) -> list:
        """通过 Core API 搜索引文"""
        response = await self.client.post(
            f"{self.core_url}/api/v1/vf/search",
            json={
                "query": query,
                "chunk_types": ["cited_for", "contributions"],
                "limit": limit
            }
        )
        response.raise_for_status()
        return response.json()["results"]
```

---

## 7. Migration Phases

### Phase 1: 准备工作 (1-2 天)

| Task | 说明 | 验收标准 |
|------|------|---------|
| 1.1 | 创建新仓库结构 | `veritas-core/`, `scholarly-hollows/`, `gnosiplexio/` 目录存在 |
| 1.2 | 编写 Core API OpenAPI 规范 | `veritas-core/api-spec.yaml` 完整 |
| 1.3 | 定义插件接口规范 | `PluginManager` 类可用 |
| 1.4 | 更新所有文档中的命名 | ABR → Veritas |

### Phase 2: Veritas Core 提取 (2-3 天)

| Task | 说明 | 验收标准 |
|------|------|---------|
| 2.1 | 移动 Core 后端代码 | 所有 Core 路由/服务在新位置 |
| 2.2 | 移动 Core 前端代码 | Workbench UI 可运行 |
| 2.3 | 实现插件加载系统 | `PluginManager` 可发现和加载插件 |
| 2.4 | 测试 Core 独立运行 | 无插件时所有 Core 功能正常 |

### Phase 3: Scholarly Hollows 插件化 (2-3 天)

| Task | 说明 | 验收标准 |
|------|------|---------|
| 3.1 | 重构 SH 为插件结构 | `manifest.json` 存在且有效 |
| 3.2 | 修改 SH 使用 Core API | 无直接数据库访问 |
| 3.3 | 打包 SH 前端组件 | 组件可被 Core 动态加载 |
| 3.4 | 测试 SH 作为插件 | 安装后所有魔法可用 |

### Phase 4: Gnosiplexio 独立化 (2-3 天)

| Task | 说明 | 验收标准 |
|------|------|---------|
| 4.1 | 创建独立项目结构 | `gnosiplexio/` 完整 |
| 4.2 | 实现 DataSourceAdapter 接口 | 基类可用 |
| 4.3 | 实现 VeritasAdapter | 可连接 Veritas Core |
| 4.4 | 测试双模式运行 | 独立模式和 Add-On 模式均可用 |

### Phase 5: 集成测试 (1-2 天)

| Task | 说明 | 验收标准 |
|------|------|---------|
| 5.1 | Core + SH 集成测试 | 所有 SH 魔法通过 Core API 正常工作 |
| 5.2 | Core + GP 集成测试 | GP 可通过 VeritasAdapter 读取数据 |
| 5.3 | 全栈测试 | Core + SH + GP 同时运行正常 |
| 5.4 | 性能测试 | API 调用无明显延迟增加 |

---

## 8. Naming Convention

### 8.1 品牌命名

| 旧名 | 新名 |
|------|------|
| Veritas | **Veritas** |
| ABR Core | **Veritas Core** |
| ABR | **Veritas** |

### 8.2 代码命名

| 类型 | 约定 | 示例 |
|------|------|------|
| 仓库名 | 小写短横线 | `veritas-core`, `scholarly-hollows` |
| Python 包 | 小写下划线 | `veritas_core`, `scholarly_hollows` |
| API 路径 | 小写短横线 | `/api/v1/vf/profiles` |
| 环境变量 | 大写下划线 | `VERITAS_CORE_URL` |

### 8.3 文件命名

```
veritas-core/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── plugins.py          # 插件管理器
│   │   ├── routes/
│   │   │   ├── vf_routes.py
│   │   │   ├── library_routes.py
│   │   │   └── ...
│   │   └── services/
│   │       ├── vf_middleware/
│   │       └── ...
│   └── cli/
├── frontend/
└── docs/

scholarly-hollows/
├── manifest.json
├── routes/
│   ├── __init__.py             # 导出 router
│   ├── veritafactum.py
│   └── ...
├── services/
└── frontend/

gnosiplexio/
├── core/
├── adapters/
│   ├── base.py                 # DataSourceAdapter
│   ├── veritas_adapter.py
│   └── ...
├── api/
└── frontend/
```

---

## 9. Configuration Examples

### 9.1 Veritas Core 配置

```yaml
# veritas-core/config.yaml

server:
  host: 0.0.0.0
  port: 8001

database:
  postgres_url: postgresql://veritas:pass@localhost:5432/veritas
  qdrant_url: http://localhost:6333

plugins:
  enabled: true
  directory: /opt/veritas/plugins

llm:
  provider: openrouter
  api_key: ${OPENROUTER_API_KEY}
```

### 9.2 SH 插件安装

```bash
# 安装 Scholarly Hollows 插件
cd /opt/veritas/plugins
git clone https://github.com/your-org/scholarly-hollows.git
cd scholarly-hollows
pip install -r requirements.txt

# 重启 Veritas Core
systemctl restart veritas-core
```

### 9.3 Gnosiplexio 配置

```yaml
# gnosiplexio/config.yaml

# 独立模式
data_source: semantic_scholar
semantic_scholar:
  api_key: ${SEMANTIC_SCHOLAR_API_KEY}

# 或 Veritas Add-On 模式
data_source: veritas
veritas:
  api_url: http://localhost:8001
  api_key: ${VERITAS_API_KEY}
```

---

## 10. Open Questions

| # | 问题 | 建议 | 状态 |
|---|------|------|------|
| 1 | VF Profile 生成放哪里？ | **Veritas Core** — VF Store 是 Core 核心 | ✅ 已决定 |
| 2 | Ex-portario 如何写入 Library？ | 通过 Core API `/api/v1/library/ingest` | ✅ 已决定 |
| 3 | 前端组件动态加载方案？ | 待定 (Module Federation 或 ESM import) | ❓ 待决定 |
| 4 | 版本兼容检查机制？ | manifest.json 中 `requires_veritas_version` | ✅ 已决定 |

---

## 11. Summary

### Veritas 生态系统

```
┌──────────────────────────────────────────────────────────┐
│                    VERITAS                               │
│              "In Veritas, Scientia"                      │
│                                                          │
│  ┌────────────────┐                                     │
│  │  Veritas Core  │  ← 基础平台 (95% done)              │
│  │  真理核心      │     可独立运行                       │
│  └───────┬────────┘                                     │
│          │                                               │
│          │ API                                           │
│          ▼                                               │
│  ┌────────────────┐                                     │
│  │   Scholarly    │  ← 魔法插件 (50% done)              │
│  │    Hollows     │     需要 Core                        │
│  └────────────────┘                                     │
│                                                          │
│  ┌────────────────┐                                     │
│  │  Gnosiplexio   │  ← 知识图谱 (0% done)               │
│  │      (GP)      │     可独立 / 可连接 Core             │
│  └────────────────┘                                     │
└──────────────────────────────────────────────────────────┘
```

### 核心原则

1. **Veritas Core 独立运行** — 不装任何插件也能完整使用
2. **SH 通过 API 访问** — 不直接操作数据库
3. **GP 双模式** — 独立或作为 Veritas Add-On
4. **插件机制** — manifest.json + 动态加载

---

*文档版本：v2.0*  
*最后更新：2026-02-21*  
*作者：小蕾 (李晓蕾) 🌸*
