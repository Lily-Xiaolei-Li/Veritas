# AI-CLI-GUIDE.md

面向 Agent 的操作手册（GP Visualization System）。

## 1) 启动与停止

```bash
docker compose up --build -d
docker compose ps
docker compose logs -f api
docker compose down
```

## 2) 关键接口（建议优先调用）

- `GET /health`：服务健康
- `GET /check`：环境配置 + collection 可用性
- `GET /meta`：Excel 元信息 + collection 状态
- `GET /papers?query=...&limit=...`：检索
- `GET /papers/{paper_id}`：详情
- `GET /viz/f1`：F1 时间线数据
- `GET /viz/f2`：F2 热力图数据
- `GET /viz/filters`：筛选器候选
- `POST /assist-stream`：XiaoLei SSE 聚合

## 3) 标准调试流程（Agent 推荐）

1. 调 `/health`，确认 API 在线。
2. 调 `/check`，确认 Qdrant + 路径配置。
3. 调 `/viz/f1`、`/viz/f2`，确认可视化数据可读。
4. 用 `/papers` + `/papers/{id}` 验证检索链路。
5. 最后验证 `/assist-stream`（依赖 XiaoLei 在线）。

## 4) 常用命令模板

```bash
# Health
curl http://localhost:1880/health

# Search
curl "http://localhost:1880/papers?query=governance&limit=5"

# Detail
curl http://localhost:1880/papers/<paper_id>

# F1
curl http://localhost:1880/viz/f1

# F2
curl http://localhost:1880/viz/f2

# Filters
curl http://localhost:1880/viz/filters
```

## 5) 集成测试（Phase 4）

```bash
python -m unittest tests/test_phase4_integration.py -v
```

该测试文件用 mock 隔离外部依赖，可在离线条件下验证 7 个核心功能。

## 6) Agent 注意事项

- 优先保持 `GP_VECTR_COLLECTION` / `GP_QDRANT_COLLECTION` 与实际 Qdrant 一致。
- 若 UI 图像导出失败，属于运行环境缺少导出引擎，不影响核心功能。
- `assist-stream` 报错通常是上游 XiaoLei 服务不可达，不要误判为本服务逻辑问题。
