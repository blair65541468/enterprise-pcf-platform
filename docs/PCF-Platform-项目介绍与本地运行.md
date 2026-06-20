# PCF Platform 项目介绍与本地运行

## 1. 项目定位

PCF Platform 是面向企业产品碳足迹（Product Carbon Footprint，PCF）试点的中间服务。当前首个目标产品为 `INT-WD-001`，核算边界覆盖原材料、入厂运输、制造和包装，截止到工厂大门。

平台的职责不是替代 LCA 专家或背景数据库，而是把企业业务数据转换为可审核、可冻结、可计算和可追溯的 PCF 工作流：

1. 从 Excel 导入产品、BOM、排放因子、工艺路线等业务数据。
2. 校验因子审批、单位换算、密度、运输活动和 openLCA 映射等前置条件。
3. 创建不可变的计算输入快照。
4. 通过 mock 或 openLCA 引擎执行计算。
5. 执行提交、审核、驳回和版本替代流程。
6. 导出已批准结果，并保留审计事件和计算清单哈希。

## 2. 核心能力

| 能力 | 实现方式 |
|---|---|
| HTTP API 与接口文档 | FastAPI、OpenAPI/Swagger |
| 数据持久化 | SQLAlchemy；本地支持 SQLite，部署支持 PostgreSQL |
| 数据库版本管理 | Alembic |
| Excel 数据接入 | openpyxl、多文件导入、SHA-256、行级问题清单 |
| 异步计算 | Celery；本地使用 eager 模式，部署使用 Redis Worker |
| 对象存储 | 本地目录或兼容 S3 的对象存储 |
| 计算引擎 | 确定性 mock 引擎或 openLCA REST |
| 身份认证 | 本地请求头或 OIDC |
| 审批控制 | `Calculated → Submitted → Approved/Rejected`，执行四眼原则 |
| 结果交付 | Approved 状态的 JSON、Excel 导出 |
| 可追溯性 | 不可变快照、幂等计算、审计事件、manifest 哈希 |

主要代码分层：

```text
app/api/             HTTP 接口和权限入口
app/core/            配置、认证、事务、异常、日志和指标
app/modules/         catalog、imports、snapshots、calculations 领域模型与契约
app/services/        导入、快照、计算、审批、导出和 outbox 应用服务
app/engines/         mock 与 openLCA 计算适配器
app/infrastructure/  Celery 和对象存储实现
app/tasks.py         计算、outbox 投递和超时恢复任务
tests/               契约、单元、工作流和显式集成测试
```

## 3. 最小本地运行方案

最小方案使用以下组件：

- Python 3.12（项目同时兼容 Python 3.13）
- SQLite
- Celery eager 模式
- 本地对象存储
- mock 计算引擎

该方案不需要 Docker、Redis、PostgreSQL 或 openLCA，适合接口开发和工作流验证。

### 3.1 环境要求

确认当前 Python 版本：

```powershell
python --version
```

预期输出为 `Python 3.12.x` 或 `Python 3.13.x`。项目声明支持 Python
`>=3.12,<3.14`，当前测试基线使用 Python 3.13.4。

### 3.2 创建环境并安装依赖

在 PowerShell 中执行：

```powershell
cd "D:\AirPAQ\冷总RFID相关项目\pcf-platform"

python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

如果系统同时安装了多个 Python 版本，并且 `py` 启动器已注册 Python 3.12，也可以使用：

```powershell
py -3.12 -m venv .venv
```

如果 `py -3.12` 提示找不到运行时，应继续使用版本符合要求的 `python`，或将命令中的 `python` 替换为 Python 3.12 可执行文件的完整路径。

如果 `.venv` 已存在，可跳过创建虚拟环境；重新执行依赖安装命令可以补齐或更新项目依赖。

### 3.3 配置本地模式

编辑 `.env`，确保以下配置生效：

```env
DATABASE_URL=sqlite:///./pcf.db
CELERY_TASK_ALWAYS_EAGER=true
OBJECT_STORAGE_BACKEND=local
OBJECT_STORAGE_LOCAL_DIR=./data/objects
OPENLCA_ENGINE=mock
OIDC_ENABLED=false
LOCAL_AUTH_ENABLED=true
```

配置含义：

- SQLite 数据写入项目目录下的 `pcf.db`。
- Celery eager 模式在 API 进程内同步执行任务，无需 Redis 和独立 Worker。
- 计算原始结果写入 `data/objects`。
- mock 引擎提供确定且可重复的测试结果。
- 本地认证允许使用 `X-User-Id`、`X-Roles` 请求头。

### 3.4 启动服务

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

服务默认监听 `127.0.0.1:8000`：

- Swagger 文档：<http://127.0.0.1:8000/docs>
- API 健康检查：<http://127.0.0.1:8000/health>
- 计算引擎检查：<http://127.0.0.1:8000/health/openlca>

停止服务时在运行窗口按 `Ctrl+C`。

## 4. 跑通最简单的测试

### 4.1 服务存活测试

保持服务运行，另开一个 PowerShell 窗口：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

预期结果：

```text
status
------
ok
```

检查 mock 引擎：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health/openlca
```

预期结果包含：

```text
status  : ok
engine  : mock
version : deterministic-factor-1
```

### 4.2 最小端到端自动化测试

该测试不要求先启动 uvicorn，也不读取本地 `pcf.db`。测试配置会使用独立 SQLite 数据库、本地测试对象目录、Celery eager 模式和 mock 引擎。

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_workflow.py::test_end_to_end_calculation_approval_and_exports -q
```

预期结果：

```text
.                                                                        [100%]
```

该用例实际覆盖：

1. 准备一套通过门禁的试点数据。
2. 创建 `INT-WD-001` 不可变快照。
3. 创建并执行 mock 计算。
4. 校验总结果 `7.525 kg CO₂e` 及各阶段贡献。
5. 验证未批准结果禁止导出。
6. 验证提交人与审核人不能相同。
7. 使用独立审核人完成批准。
8. 验证 JSON、Excel 导出和完整审计事件。

### 4.3 完整测试集

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

截至 2026 年 6 月 20 日的已验证基线：

- Python：`3.13.4`
- 服务健康检查：`{"status":"ok"}`
- 最小端到端测试：通过
- 完整测试集：`35 passed, 3 skipped`，覆盖率 `87.35%`（真实 openLCA 和生产基础设施测试默认跳过）

测试过程中会出现一条来自 FastAPI TestClient/Starlette 的第三方弃用警告。该警告不影响当前测试结论，但后续升级相关依赖时需要重新检查兼容性。

## 5. mock 与真实 openLCA 的边界

mock 引擎根据快照中的活动数据和排放因子直接计算确定性结果，只用于：

- API 联调；
- 数据门禁验证；
- 审批和导出流程验证；
- 自动化测试。

mock 结果会标记为 `integration_test`，不得用于 ISO 14067 声明或正式产品碳足迹报告。

切换到真实 openLCA 至少需要：

1. 确认 GreenDelta gdt-server 的网络使用许可。
2. 获得 ecoinvent 等背景数据库的合法许可。
3. 在 openLCA 中建立并审核产品系统和影响评价方法。
4. 配置 Product System UUID、Impact Method UUID 和参数字典。
5. 完成企业物料到 openLCA process/reference flow 的审核映射。
6. 补齐并批准密度、工艺路线、能源和入厂运输数据。
7. 配置各生命周期阶段对应的 process UUID，并与 openLCA 总量对账。

缺少上述前置数据时，平台会通过 `422` 或计算失败显式阻断，不会静默估算。

## 6. 常用命令

```powershell
# 启动 API
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload

# 最小端到端测试
.\.venv\Scripts\python.exe -m pytest tests/test_workflow.py::test_end_to_end_calculation_approval_and_exports -q

# 全部测试
.\.venv\Scripts\python.exe -m pytest -q

# 查看健康状态
Invoke-RestMethod http://127.0.0.1:8000/health

# 查看 mock/openLCA 引擎状态
Invoke-RestMethod http://127.0.0.1:8000/health/openlca
```
