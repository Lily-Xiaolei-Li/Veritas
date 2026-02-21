# ABR Architecture Refactor Plan

**Author:** 超级小蕾 (Veritas Research 项目负责人)  
**Date:** 2026-02-19  
**Status:** Draft — 待老爷在 Linux 环境实施

---

## 1. Executive Summary

将 Veritas (ABR) 拆分为三个独立组件：

| 组件 | 名称 | 性质 | 依赖 |
|------|------|------|------|
| **ABR Core** | Veritas Research Basic | 基础平台 | 无 |
| **SH Add-On** | Scholarly Hollows | 魔法套装插件 | 依赖 ABR Core |
| **Gnosiplexio** | 织智成网 | 独立软件 + ABR 兼容插件 | 可选依赖 ABR Core |

**目标：**
- ABR Core 可独立运行，不依赖任何 Add-On
- Scholarly Hollows 作为升级功能，需要 ABR Core
- Gnosiplexio 既可独立使用，也可作为 ABR Add-On

---

## 2. Current State Analysis

### 2.1 现有目录结构

```
Veritas/
├── backend/
│   ├── app/
│   │   ├── routes/           # API 路由（混合了 Core 和 SH）
│   │   ├── services/         # 业务逻辑
│   │   │   ├── checker/      # Veritafactum (SH)
│   │   │   ├── citalio/      # Citalio (SH)
│   │   │   ├── proliferomaxima/  # Proliferomaxima (SH)
│   │   │   ├── gnosiplexio/  # Gnosiplexio (独立)
│   │   │   ├── vf_middleware/    # VF Store (Core? SH?)
│   │   │   └── knowledge_source/ # 知识源 (Core)
│   │   ├── models/           # 数据模型
│   │   └── ...
│   └── ...
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── checker/      # Veritafactum UI (SH)
│   │   │   ├── citalio/      # Citalio UI (SH)
│   │   │   ├── proliferomaxima/  # Proliferomaxima UI (SH)
│   │   │   ├── workbench/    # 工作台 (Core)
│   │   │   └── ...
│   │   └── ...
│   └── ...
├── docs/
│   ├── PRD-*.md              # 各功能 PRD
│   └── ...
└── ...
```

### 2.2 问题分析

1. **耦合严重** — Core 和 SH 代码混在一起，无法独立部署
2. **边界模糊** — VF Middleware 是 Core 还是 SH？（答案：应该是 Core）
3. **前端混杂** — 所有组件在同一个 Next.js 应用中
4. **Gnosiplexio** — 目前只有 PRD，代码结构不支持独立运行

---

## 3. Target Architecture

### 3.1 高层架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         ABR Ecosystem                                    │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                      ABR Core (Basic)                               │ │
│  │                                                                      │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │ │
│  │  │ Library RAG  │  │  VF Store    │  │  Session &   │              │ │
│  │  │ (Qdrant:     │  │  (Qdrant:    │  │  Artifact    │              │ │
│  │  │  academic_   │  │  vf_profiles)│  │  Manager     │              │ │
│  │  │  papers)     │  │              │  │  (PostgreSQL)│              │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │ │
│  │                                                                      │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │ │
│  │  │ File Browser │  │  AI Chat     │  │  Workbench   │              │ │
│  │  │              │  │  (LLM API)   │  │  UI Shell    │              │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │ │
│  │                                                                      │ │
│  │  ══════════════════════════════════════════════════════════════    │ │
│  │                    Core API Layer (REST + SSE)                      │ │
│  │  • GET/POST /api/v1/library/*      (RAG operations)                │ │
│  │  • GET/POST /api/v1/vf/*           (VF Store operations)           │ │
│  │  • GET/POST /api/v1/sessions/*     (Session management)            │ │
│  │  • GET/POST /api/v1/artifacts/*    (Artifact CRUD)                 │ │
│  │  • POST /api/v1/chat               (LLM chat)                      │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                              ▲                                           │
│                              │ Depends on Core API                       │
│                              │                                           │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │              Scholarly Hollows (SH) Add-On                          │ │
│  │                                                                      │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │ │
│  │  │ Veritafactum │  │   Citalio    │  │Proliferomaxima│             │ │
│  │  │ (真知照见)   │  │ (引经据典)   │  │ (寻书万卷)   │              │ │
│  │  │              │  │              │  │              │              │ │
│  │  │ 逐句验证引用 │  │ 自动引文推荐 │  │ 引用网络增殖 │              │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │ │
│  │                                                                      │ │
│  │  ┌──────────────┐                                                   │ │
│  │  │  Ex-portario │                                                   │ │
│  │  │ (破壁取珠)   │                                                   │ │
│  │  │              │                                                   │ │
│  │  │ 全文批量下载 │                                                   │ │
│  │  └──────────────┘                                                   │ │
│  │                                                                      │ │
│  │  ══════════════════════════════════════════════════════════════    │ │
│  │                    SH API Layer (REST)                              │ │
│  │  • POST /api/v1/sh/veritafactum/run                                │ │
│  │  • POST /api/v1/sh/citalio/search                                  │ │
│  │  • POST /api/v1/sh/proliferomaxima/run                             │ │
│  │  • POST /api/v1/sh/exportario/download                             │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                    Gnosiplexio (织智成网)                                │
│                    Independent Software                                  │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    Knowledge Graph Engine                         │  │
│  │                                                                    │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │  │
│  │  │ Graph Store │  │ Visualizer  │  │  Query      │               │  │
│  │  │ (Neo4j/     │  │ (D3.js/     │  │  Engine     │               │  │
│  │  │  NetworkX)  │  │  Cytoscape) │  │  (Cypher)   │               │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘               │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                              ▲                                          │
│                              │                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    Data Source Adapters                           │  │
│  │                                                                    │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │  │
│  │  │ ABR Adapter │  │ Semantic    │  │  Custom     │               │  │
│  │  │ (VF Store + │  │ Scholar     │  │  Adapter    │               │  │
│  │  │  Library)   │  │ Adapter     │  │  Interface  │               │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘               │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 组件职责定义

#### ABR Core (Basic)

**包含：**
- Library RAG — 学术论文全文向量搜索 (Qdrant: `academic_papers`)
- VF Store — Veritas Fingerprint 存储 (Qdrant: `vf_profiles`)
- VF Middleware — Profile 生成服务（从论文生成 VF Profile）
- Session Manager — 会话管理 (PostgreSQL)
- Artifact Manager — 文档/产出物管理 (PostgreSQL + 文件系统)
- AI Chat — LLM 对话功能 (OpenRouter/Ollama/etc.)
- File Browser — 本地文件浏览
- Workbench UI — 主界面外壳

**不包含：**
- 任何 SH 魔法功能
- Gnosiplexio 知识图谱

**独立运行能力：**
- ✅ 可以完全不安装任何 Add-On
- ✅ 提供完整的学术研究辅助（RAG、VF Profile、AI 写作）

---

#### Scholarly Hollows (SH) Add-On

**包含魔法：**

| 魔法 | 中文名 | 功能 | Core API 依赖 |
|------|--------|------|---------------|
| Veritafactum | 真知照见 | 逐句验证引用正确性 | VF Store 搜索 |
| Citalio | 引经据典 | 为句子推荐合适引用 | VF Store 搜索 |
| Proliferomaxima | 寻书万卷 | 从引用网络批量增殖 VF Store | VF Store 写入、Library RAG |
| Ex-portario | 破壁取珠 | 穿透付费墙下载全文 | Library RAG 写入 |

**安装方式：**
- 作为 ABR 插件安装
- 需要 ABR Core 已安装且运行
- 通过 Core API 访问数据，不直接操作数据库

---

#### Gnosiplexio (独立软件)

**核心功能：**
- 学术知识图谱生成与可视化
- 论文/概念/作者关系网络
- 引用网络分析
- 知识发现与推荐

**数据源模式：**
1. **独立模式** — 使用自己的数据源（Semantic Scholar API、本地文献库等）
2. **ABR Add-On 模式** — 读取 ABR 的 VF Store + Library RAG

**接口设计：**
```python
class DataSourceAdapter(ABC):
    """Gnosiplexio 数据源适配器接口"""
    
    @abstractmethod
    async def get_papers(self, query: str, limit: int) -> List[Paper]:
        """搜索论文"""
        pass
    
    @abstractmethod
    async def get_paper_references(self, paper_id: str) -> List[Reference]:
        """获取论文引用列表"""
        pass
    
    @abstractmethod
    async def get_paper_profile(self, paper_id: str) -> Optional[VFProfile]:
        """获取论文 VF Profile（如果有）"""
        pass

class ABRAdapter(DataSourceAdapter):
    """ABR 数据源适配器 — 连接 ABR Core API"""
    
    def __init__(self, abr_api_url: str, api_key: Optional[str] = None):
        self.api_url = abr_api_url
        self.api_key = api_key
    
    async def get_papers(self, query: str, limit: int) -> List[Paper]:
        # 调用 ABR Core: GET /api/v1/library/search
        pass
    
    async def get_paper_profile(self, paper_id: str) -> Optional[VFProfile]:
        # 调用 ABR Core: GET /api/v1/vf/profiles/{paper_id}
        pass
```

---

## 4. Refactoring Steps

### Phase 1: 准备工作

**1.1 创建新目录结构（不移动代码）**

```bash
mkdir -p abr-core/{backend,frontend,docs}
mkdir -p abr-scholarly-hollows/{backend,frontend,docs}
mkdir -p gnosiplexio/{core,adapters,frontend,docs}
```

**1.2 定义 Core API 契约**

创建 `abr-core/api-spec.yaml` (OpenAPI 3.0)：

```yaml
openapi: 3.0.0
info:
  title: ABR Core API
  version: 1.0.0
  description: Veritas Research Core Platform API

paths:
  # Library RAG
  /api/v1/library/search:
    post:
      summary: Semantic search in library
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                query: { type: string }
                limit: { type: integer, default: 10 }
                filters: { type: object }
      responses:
        200:
          description: Search results
          
  /api/v1/library/papers/{paper_id}:
    get:
      summary: Get paper by ID
      
  # VF Store
  /api/v1/vf/profiles:
    get:
      summary: List VF profiles
    post:
      summary: Create VF profile
      
  /api/v1/vf/profiles/{profile_id}:
    get:
      summary: Get VF profile by ID
      
  /api/v1/vf/search:
    post:
      summary: Semantic search in VF Store
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                query: { type: string }
                chunk_types: { type: array, items: { type: string } }
                limit: { type: integer }
                filters: { type: object }
                
  # Sessions
  /api/v1/sessions:
    get:
      summary: List sessions
    post:
      summary: Create session
      
  # Artifacts
  /api/v1/artifacts:
    get:
      summary: List artifacts
    post:
      summary: Create artifact
      
  # Chat
  /api/v1/chat:
    post:
      summary: Send chat message
```

---

### Phase 2: 后端拆分

**2.1 识别 Core 代码**

| 当前位置 | 归属 | 新位置 |
|----------|------|--------|
| `backend/app/routes/session_routes.py` | Core | `abr-core/backend/app/routes/` |
| `backend/app/routes/artifact_routes.py` | Core | `abr-core/backend/app/routes/` |
| `backend/app/routes/chat_routes.py` | Core | `abr-core/backend/app/routes/` |
| `backend/app/routes/library_routes.py` | Core | `abr-core/backend/app/routes/` |
| `backend/app/routes/vf_routes.py` | Core | `abr-core/backend/app/routes/` |
| `backend/app/routes/auth_routes.py` | Core | `abr-core/backend/app/routes/` |
| `backend/app/services/vf_middleware/` | Core | `abr-core/backend/app/services/` |
| `backend/app/services/knowledge_source/` | Core | `abr-core/backend/app/services/` |
| `backend/app/models/` | Core | `abr-core/backend/app/models/` |
| `backend/app/database.py` | Core | `abr-core/backend/app/` |
| `backend/app/config.py` | Core | `abr-core/backend/app/` |

**2.2 识别 SH 代码**

| 当前位置 | 归属 | 新位置 |
|----------|------|--------|
| `backend/app/routes/checker_routes.py` | SH | `abr-scholarly-hollows/backend/routes/` |
| `backend/app/routes/citalio_routes.py` | SH | `abr-scholarly-hollows/backend/routes/` |
| `backend/app/routes/proliferomaxima_routes.py` | SH | `abr-scholarly-hollows/backend/routes/` |
| `backend/app/services/checker/` | SH | `abr-scholarly-hollows/backend/services/` |
| `backend/app/services/citalio/` | SH | `abr-scholarly-hollows/backend/services/` |
| `backend/app/services/proliferomaxima/` | SH | `abr-scholarly-hollows/backend/services/` |

**2.3 识别 Gnosiplexio 代码**

| 当前位置 | 归属 | 新位置 |
|----------|------|--------|
| `backend/app/routes/gnosiplexio_routes.py` | Gnosiplexio | `gnosiplexio/backend/routes/` |
| `backend/app/services/gnosiplexio/` | Gnosiplexio | `gnosiplexio/core/` |

**2.4 创建 SH 插件加载机制**

在 ABR Core 中添加插件系统：

```python
# abr-core/backend/app/plugins.py

from typing import List, Optional
from fastapi import FastAPI
import importlib
import os

class PluginManager:
    """ABR Core 插件管理器"""
    
    def __init__(self):
        self.plugins: List[str] = []
        
    def discover_plugins(self, plugin_dir: str = "/opt/abr/plugins"):
        """发现已安装的插件"""
        if not os.path.exists(plugin_dir):
            return
        for name in os.listdir(plugin_dir):
            manifest_path = os.path.join(plugin_dir, name, "manifest.json")
            if os.path.exists(manifest_path):
                self.plugins.append(name)
                
    def load_plugin(self, app: FastAPI, plugin_name: str):
        """加载插件路由"""
        try:
            module = importlib.import_module(f"plugins.{plugin_name}.routes")
            if hasattr(module, "router"):
                app.include_router(
                    module.router,
                    prefix=f"/api/v1/sh/{plugin_name}",
                    tags=[f"SH: {plugin_name}"]
                )
        except ImportError as e:
            print(f"Failed to load plugin {plugin_name}: {e}")
```

SH 插件结构：

```
abr-scholarly-hollows/
├── manifest.json
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

`manifest.json`:
```json
{
  "name": "scholarly-hollows",
  "version": "1.0.0",
  "display_name": "Scholarly Hollows",
  "description": "Academic magic spells for ABR",
  "requires_abr_version": ">=1.0.0",
  "entry_point": "routes",
  "frontend_components": [
    "veritafactum",
    "citalio",
    "proliferomaxima"
  ]
}
```

---

### Phase 3: 前端拆分

**3.1 Core 前端**

保留：
- `components/workbench/` — 工作台主框架
- `components/ui/` — 通用 UI 组件
- `components/settings/` — 设置面板
- `components/health/` — 健康检查
- `components/auth/` — 认证
- `lib/` — 工具函数、API 客户端、Store

移除（移到 SH）：
- `components/checker/`
- `components/citalio/`
- `components/proliferomaxima/`

**3.2 SH 前端**

创建独立的 React 组件包：

```
abr-scholarly-hollows/frontend/
├── package.json
├── src/
│   ├── components/
│   │   ├── veritafactum/
│   │   ├── citalio/
│   │   └── proliferomaxima/
│   ├── hooks/
│   └── api/
└── dist/           # 打包后的组件
```

**3.3 动态加载机制**

在 ABR Core 前端添加插件加载：

```typescript
// abr-core/frontend/src/lib/plugins.ts

interface PluginManifest {
  name: string;
  version: string;
  display_name: string;
  frontend_components: string[];
}

async function loadPluginComponents(pluginName: string): Promise<React.ComponentType[]> {
  // 从 /plugins/{name}/dist/ 动态加载组件
  const manifest = await fetch(`/plugins/${pluginName}/manifest.json`).then(r => r.json());
  
  const components = [];
  for (const componentName of manifest.frontend_components) {
    const module = await import(`/plugins/${pluginName}/dist/${componentName}.js`);
    components.push(module.default);
  }
  return components;
}
```

---

### Phase 4: Gnosiplexio 独立化

**4.1 创建独立项目结构**

```
gnosiplexio/
├── README.md
├── pyproject.toml
├── docker-compose.yml
├── core/
│   ├── __init__.py
│   ├── graph_engine.py      # 图引擎核心
│   ├── query_engine.py      # 查询引擎
│   └── visualizer.py        # 可视化
├── adapters/
│   ├── __init__.py
│   ├── base.py              # DataSourceAdapter 接口
│   ├── abr_adapter.py       # ABR 适配器
│   ├── semantic_scholar.py  # Semantic Scholar 适配器
│   └── local_bibtex.py      # 本地 BibTeX 适配器
├── api/
│   ├── __init__.py
│   ├── main.py              # FastAPI 应用
│   └── routes/
├── frontend/
│   ├── package.json
│   └── src/
└── docs/
    └── PRD-gnosiplexio.md   # 从 ABR 移过来
```

**4.2 ABR Adapter 实现**

```python
# gnosiplexio/adapters/abr_adapter.py

from typing import List, Optional
import httpx
from .base import DataSourceAdapter, Paper, Reference, VFProfile

class ABRAdapter(DataSourceAdapter):
    """
    ABR 数据源适配器
    
    连接 ABR Core API，读取 VF Store 和 Library RAG 数据。
    用于 Gnosiplexio 的 ABR Add-On 模式。
    """
    
    def __init__(
        self,
        abr_api_url: str = "http://localhost:8001",
        api_key: Optional[str] = None,
        timeout: float = 30.0
    ):
        self.api_url = abr_api_url.rstrip("/")
        self.api_key = api_key
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers={"Authorization": f"Bearer {api_key}"} if api_key else {}
        )
    
    async def search_papers(
        self,
        query: str,
        limit: int = 50,
        filters: Optional[dict] = None
    ) -> List[Paper]:
        """在 ABR Library RAG 中搜索论文"""
        response = await self.client.post(
            f"{self.api_url}/api/v1/library/search",
            json={"query": query, "limit": limit, "filters": filters or {}}
        )
        response.raise_for_status()
        data = response.json()
        return [Paper(**p) for p in data["results"]]
    
    async def get_paper_profile(self, paper_id: str) -> Optional[VFProfile]:
        """从 ABR VF Store 获取论文 Profile"""
        response = await self.client.get(
            f"{self.api_url}/api/v1/vf/profiles/{paper_id}"
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return VFProfile(**response.json())
    
    async def search_vf_profiles(
        self,
        query: str,
        chunk_types: List[str] = ["cited_for", "theory"],
        limit: int = 20
    ) -> List[VFProfile]:
        """在 ABR VF Store 中语义搜索"""
        response = await self.client.post(
            f"{self.api_url}/api/v1/vf/search",
            json={
                "query": query,
                "chunk_types": chunk_types,
                "limit": limit
            }
        )
        response.raise_for_status()
        return [VFProfile(**p) for p in response.json()["results"]]
    
    async def get_references(self, paper_id: str) -> List[Reference]:
        """获取论文引用列表（从 VF Profile 的 references chunk）"""
        profile = await self.get_paper_profile(paper_id)
        if not profile:
            return []
        return profile.references or []
```

---

## 5. Database & Storage Separation

### 5.1 数据归属

| 数据 | 存储 | 归属 |
|------|------|------|
| `vf_profiles` collection | Qdrant | Core |
| `academic_papers` collection | Qdrant | Core |
| `sessions` table | PostgreSQL | Core |
| `artifacts` table | PostgreSQL | Core |
| `users` table | PostgreSQL | Core |
| `api_keys` table | PostgreSQL | Core |
| Knowledge Graph nodes/edges | Neo4j (新增) | Gnosiplexio |

### 5.2 SH 数据访问

SH Add-On **不直接访问数据库**，只通过 Core API：

```python
# abr-scholarly-hollows/services/citalio/searcher.py

from typing import List
import httpx

class CitalioSearcher:
    """Citalio 搜索服务 — 通过 Core API 访问 VF Store"""
    
    def __init__(self, core_api_url: str = "http://localhost:8001"):
        self.core_api = core_api_url
        self.client = httpx.AsyncClient()
    
    async def search_citations(
        self,
        query: str,
        chunk_types: List[str] = ["cited_for", "theory"],
        limit: int = 10,
        filters: dict = None
    ) -> List[dict]:
        """搜索引文候选"""
        response = await self.client.post(
            f"{self.core_api}/api/v1/vf/search",
            json={
                "query": query,
                "chunk_types": chunk_types,
                "limit": limit,
                "filters": filters or {}
            }
        )
        response.raise_for_status()
        return response.json()["results"]
```

---

## 6. Configuration & Deployment

### 6.1 ABR Core 配置

```yaml
# abr-core/config.yaml

server:
  host: 0.0.0.0
  port: 8001

database:
  postgres_url: postgresql://user:pass@localhost:5432/abr
  qdrant_url: http://localhost:6333

plugins:
  enabled: true
  directory: /opt/abr/plugins
  
auth:
  enabled: false  # 可选

llm:
  provider: openrouter
  api_key: ${OPENROUTER_API_KEY}
```

### 6.2 SH Add-On 安装

```bash
# 安装 SH 插件
cd /opt/abr/plugins
git clone https://github.com/your-org/abr-scholarly-hollows.git scholarly-hollows
cd scholarly-hollows
pip install -r requirements.txt

# 重启 ABR Core 以加载插件
systemctl restart abr-core
```

### 6.3 Gnosiplexio 独立部署

```bash
# 独立模式
docker-compose up -d

# ABR Add-On 模式
docker-compose -f docker-compose.abr.yml up -d
```

`docker-compose.abr.yml`:
```yaml
version: '3.8'
services:
  gnosiplexio:
    image: gnosiplexio:latest
    environment:
      - DATA_SOURCE=abr
      - ABR_API_URL=http://abr-core:8001
      - ABR_API_KEY=${ABR_API_KEY}
    ports:
      - "8002:8002"
    networks:
      - abr-network

networks:
  abr-network:
    external: true
```

---

## 7. Migration Checklist

### 7.1 Phase 1: 准备 (1-2 天)

- [ ] 创建新目录结构
- [ ] 编写 Core API 规范 (OpenAPI)
- [ ] 定义插件接口规范
- [ ] 创建 Gnosiplexio 独立仓库

### 7.2 Phase 2: Core 提取 (2-3 天)

- [ ] 提取 Core 后端代码
- [ ] 提取 Core 前端代码
- [ ] 添加插件加载系统
- [ ] 测试 Core 独立运行

### 7.3 Phase 3: SH 插件化 (2-3 天)

- [ ] 重构 SH 代码为插件结构
- [ ] 修改 SH 使用 Core API（不直接访问 DB）
- [ ] 打包 SH 前端组件
- [ ] 测试 SH 作为插件加载

### 7.4 Phase 4: Gnosiplexio 独立化 (2-3 天)

- [ ] 移动 Gnosiplexio 代码到新仓库
- [ ] 实现 DataSourceAdapter 接口
- [ ] 实现 ABR Adapter
- [ ] 测试独立模式和 ABR Add-On 模式

### 7.5 Phase 5: 集成测试 (1-2 天)

- [ ] Core + SH 集成测试
- [ ] Core + Gnosiplexio 集成测试
- [ ] Core + SH + Gnosiplexio 全栈测试
- [ ] 性能测试

---

## 8. Open Questions

1. **VF Profile 生成** — 应该放 Core 还是 SH？
   - **建议放 Core** — 因为 VF Store 是 Core 的核心数据，生成逻辑应该在 Core 中
   - SH 只是使用 VF Profile，不负责生成

2. **Ex-portario 数据写入** — 如何处理？
   - Ex-portario 下载的全文需要写入 Library RAG
   - **建议** — Core API 提供 `/api/v1/library/ingest` 端点，Ex-portario 通过 API 写入

3. **前端组件动态加载** — 用什么方案？
   - Module Federation (Webpack 5)?
   - 简单 ESM 动态 import?
   - 需要根据实际需求决定

4. **版本兼容** — 如何处理 Core 和 SH 版本不匹配？
   - **建议** — manifest.json 中声明 `requires_abr_version`，Core 加载时检查

---

## 9. References

- [PRD-citalio.md](./PRD-citalio.md)
- [PRD-proliferomaxima.md](./PRD-proliferomaxima.md)
- [PRD-gnosiplexio.md](./PRD-gnosiplexio.md)
- [PRD-vf-middleware.md](./PRD-vf-middleware.md)
- [DESIGN-sentence-checker.md](./DESIGN-sentence-checker.md)

---

*此文档由超级小蕾撰写，等待老爷在 Linux 环境实施。*

🌟 Scholarly Hollows — 学术魔法，尽在掌握 🌟
