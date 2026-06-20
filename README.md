# Enterprise PCF Platform

企业产品碳足迹试点中间服务。首个目标产品是 `INT-WD-001`，边界为原材料、入厂运输、制造和包装至工厂大门。

## 已实现

- FastAPI 内部 API 和 OpenAPI 文档。
- PostgreSQL/SQLite 兼容的版本化数据模型。
- 当前工作区 XLSX 适配器、文件 SHA-256、行级问题清单和测试数据隔离。
- BOM 因子映射、`数量 × 单件重量`、`kg ↔ m³` 密度门禁。
- 参数化模板版本、物料到 openLCA process/flow 的审核映射。
- Celery 异步计算；单 Worker 并发固定为 1。
- openLCA REST 适配器，使用官方 `olca-ipc`，并在 `finally` 中释放结果。
- 可重复的模拟计算引擎，用于没有 openLCA 数据库时的集成测试。
- Draft/Calculated/Submitted/Approved/Rejected/Superseded 工作流。
- 提交人与审核人不能相同的四眼审批。
- Approved 结果的 JSON 和 Excel 正式导出。
- append-only 审计事件和计算 manifest 哈希。
- OIDC 验证入口；本地开发可使用 `X-User-Id` 和 `X-Roles`。

## 明确未完成的外部依赖

以下内容不能由代码自动产生，必须由 LCA 专家或许可方提供：

1. GreenDelta 对 gdt-server 网络使用的许可确认。
2. ecoinvent 等背景数据库许可。
3. openLCA Desktop 中的 `WARDROBE-GATE-V1` 产品系统。
4. Product System UUID、Impact Method UUID 及参数名称。
5. 板材密度的批准来源。
6. 企业物料到 openLCA process/reference flow 的审核映射。
7. 衣柜入厂运输距离、运输方式、质量和来源证据。

在以上数据缺失时，快照 API 会返回 `422`，不会静默估算。

## 本地运行

```powershell
cd D:\AirPAQ\冷总RFID相关项目\pcf-platform
C:\Users\22884\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

为本地测试将 `.env` 改为：

```env
DATABASE_URL=sqlite:///./pcf.db
CELERY_TASK_ALWAYS_EAGER=true
OBJECT_STORAGE_BACKEND=local
OBJECT_STORAGE_LOCAL_DIR=./data/objects
OPENLCA_ENGINE=mock
LOCAL_AUTH_ENABLED=true
```

启动：

```powershell
.\.venv\Scripts\uvicorn.exe app.main:app --reload
```

访问：

- API 文档：<http://127.0.0.1:8000/docs>
- 健康检查：<http://127.0.0.1:8000/health>

## Docker Compose

```bash
cp .env.example .env
docker compose up --build postgres redis minio api worker
```

`openlca` 服务位于 `licensed-openlca` profile，只有在完成许可确认、准备好 openLCA 工作区后才应启用：

```bash
docker compose --profile licensed-openlca up --build
```

Compose 会从 GreenDelta 官方源码构建 gdt-server，不会捆绑任何数据库。将批准的工作区路径写入：

```env
OPENLCA_WORKSPACE_PATH=/absolute/path/to/openLCA-data
OPENLCA_DATABASE_NAME=wardrobe-pcf
```

## 数据导入

上传多份 Excel：

```bash
curl -X POST http://127.0.0.1:8000/v1/imports/excel \
  -H "X-User-Id: data.owner" \
  -H "X-Roles: data_submitter" \
  -F "files=@../产品工程技术研发中心/产品基础数据库/R_D_01_Product_Master_Enhanced_20260617210140.xlsx" \
  -F "files=@../产品工程技术研发中心/产品基础数据库/R_D_03_Product_BOM_Complete_Realistic_20260617210551.xlsx" \
  -F "files=@../企业碳足迹基础数据库Carbon Footprint Master Data/01_原材料碳因子库_完善版_20260607213158_20260617210110.xlsx"
```

推荐一次性上传全部源工作簿，适配器会按依赖顺序处理。

导入后的正式计算准备：

1. 审核并批准因子；`m³` 因子必须提交密度。
2. 创建并批准每种物料的 openLCA 映射。
3. 批准衣柜工艺路线。
4. 创建批准的入厂运输活动。
5. 注册并批准 openLCA 模板版本。
6. 创建冻结快照。

## 主要 API

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/v1/imports/excel` | 上传 Excel 包 |
| GET | `/v1/imports/{id}` | 导入状态和问题 |
| POST | `/v1/products/{sku}/snapshots` | 创建不可变输入快照 |
| POST | `/v1/calculations` | 创建幂等异步计算 |
| GET | `/v1/calculations/{id}` | 计算状态和摘要 |
| GET | `/v1/calculations/{id}/contributions` | 贡献结果 |
| POST | `/v1/calculations/{id}/submit` | 提交审批 |
| POST | `/v1/calculations/{id}/approve` | LCA 审核通过 |
| POST | `/v1/calculations/{id}/reject` | 退回 |
| GET | `/v1/calculations/{id}/export.json` | Approved JSON |
| GET | `/v1/calculations/{id}/export.xlsx` | Approved Excel |
| GET | `/v1/calculations/{id}/audit-events` | 审计链 |

准备类管理接口位于 `/v1/admin`，要求 `lca_reviewer` 角色。

## 真实 openLCA 配置

```env
OPENLCA_ENGINE=rest
OPENLCA_URL=http://openlca:8080
OPENLCA_API_TOKEN=
```

模板 API 中必须保存真实 UUID。Worker 的调用顺序：

1. 读取 Product System 和 Impact Method descriptor。
2. 将快照参数转换为 `ParameterRedef`。
3. `client.calculate(setup)`。
4. `wait_until_ready()`。
5. 获取 total impacts 和过程贡献。
6. 保存原始 JSON。
7. 无论成功或失败都执行 `result.dispose()`。

批准模板的 `parameter_schema` 还必须维护生命周期阶段对应的 openLCA
provider/process UUID，确保阶段贡献可以直接从 openLCA 结果汇总并与总量对账：

```json
{
  "contexts": {},
  "stage_process_uuids": {
    "raw_materials": ["process-uuid-a"],
    "inbound_transport": ["process-uuid-b"],
    "manufacturing": ["process-uuid-c"],
    "packaging": ["process-uuid-d"]
  }
}
```

阶段合计或 ISO 14067 分类合计与总量的差异超过 `max(0.01 kg CO₂e, 0.1%)`
时，任务失败并禁止提交审批。

## 测试

```powershell
.\.venv\Scripts\pytest.exe
```

测试使用独立 SQLite 数据库、本地对象存储、Celery eager 模式和确定性模拟引擎，不要求 Docker 或 openLCA。

## 生产控制

- openLCA REST 只对 Worker 网络开放。
- API 用户通过 OIDC；服务账号使用最小权限。
- 正式导出只允许 `Approved` 状态。
- 已批准结果不可修改，新结果批准后旧结果自动 `Superseded`。
- 数据、模板、数据库和方法更新必须创建新版本。
- `mock` 引擎输出明确标记为集成测试结果，不得作为 ISO 14067 声明。
