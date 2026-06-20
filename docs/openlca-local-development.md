# 本地真实 openLCA 开发工具链

本文说明如何将已有 openLCA 工作区以只读方式挂载到本机 gdt-server，通过 REST
发现真实 UUID、生成测试用例，并运行真实计算集成测试。

该工具链不会下载背景数据库，不会创建或修改 Product System，也不会将第一次 API
计算结果自动认定为测试基准。

## 1. 前置条件

- 已安装并启动 Docker Desktop Linux 引擎。
- 已有可用的 openLCA 工作区，其中包含目标数据库。
- 已确认 gdt-server、背景数据库和数据源许可允许当前本机使用。
- 启动 gdt-server 前关闭 openLCA Desktop，避免数据库文件锁和并发访问。
- 建议在首次挂载前备份整个 openLCA 工作区。

工作区应至少包含：

```text
openLCA-data-x.x/
├── databases/
│   └── <数据库名称>
└── libraries/
```

## 2. 创建本地配置

```powershell
Copy-Item .env.openlca.example .env.openlca.local
```

编辑 `.env.openlca.local`：

```env
OPENLCA_LICENSE_ACCEPTED=true
OPENLCA_WORKSPACE_PATH=C:/Users/your-name/openLCA-data-1.4
OPENLCA_DATABASE_NAME=wardrobe-pcf
OPENLCA_HOST_PORT=8080
OPENLCA_TIMEOUT_SECONDS=600
OPENLCA_TEST_CASE_FILE=tests/openlca-case.local.json
```

要求：

- `OPENLCA_LICENSE_ACCEPTED` 只有在完成许可确认后才能设为 `true`。
- `OPENLCA_WORKSPACE_PATH` 必须是工作区根目录，而不是单个数据库目录。
- `OPENLCA_DATABASE_NAME` 必须与 `databases` 下的目录名称完全一致。
- `.env.openlca.local` 已被 Git 忽略，不应提交真实路径或内部数据库信息。
- 如果服务需要 Token，在当前 PowerShell 会话中设置
  `$env:OPENLCA_API_TOKEN`，不要写入配置文件。

gdt-server 默认固定到提交
`2e3a1787c13ca119761942b8855ac31407cbb4cd`。升级前应核对数据库格式、官方
变更和许可，然后显式修改 `OPENLCA_GDT_SERVER_CONTEXT`。

## 3. 管理本地服务

启动只读服务：

```powershell
.\scripts\openlca-local.ps1 -Action Start
```

脚本会依次检查：

1. 许可确认。
2. 工作区与目标数据库。
3. openLCA Desktop 是否已关闭。
4. Docker Desktop Linux 引擎。
5. gdt-server 构建和启动。
6. `http://127.0.0.1:8080/api/version` 是否在超时前可用。

其他命令：

```powershell
.\scripts\openlca-local.ps1 -Action Status
.\scripts\openlca-local.ps1 -Action Logs
.\scripts\openlca-local.ps1 -Action Stop
```

服务仅绑定 `127.0.0.1`，不会监听局域网地址。工作区在容器中挂载为只读。

## 4. 发现真实 UUID 和参数

工具默认读取 `.env.openlca.local` 并连接本地 REST 服务。

检查版本：

```powershell
.\.venv\Scripts\python.exe scripts\openlca-inspect.py health
```

查找 Product System：

```powershell
.\.venv\Scripts\python.exe scripts\openlca-inspect.py `
  list-product-systems --filter wardrobe
```

查找 Impact Method：

```powershell
.\.venv\Scripts\python.exe scripts\openlca-inspect.py `
  list-impact-methods --filter "GWP 100"
```

查找过程 UUID：

```powershell
.\.venv\Scripts\python.exe scripts\openlca-inspect.py `
  list-processes --filter transport
```

查看 Product System 参数及 context：

```powershell
.\.venv\Scripts\python.exe scripts\openlca-inspect.py parameters `
  --product-system-id <PRODUCT_SYSTEM_UUID> `
  --json
```

列表命令均支持 `--filter` 和 `--json`。

## 5. 获取独立基准

先在 openLCA Desktop 中使用同一个 Product System、Impact Method 和参数执行计算，
记录目标 Climate change/GWP 100 数值。该 Desktop 结果是独立测试基准。

REST 端可以执行一次诊断计算并显示全部影响结果：

```powershell
.\.venv\Scripts\python.exe scripts\openlca-inspect.py baseline `
  --product-system-id <PRODUCT_SYSTEM_UUID> `
  --impact-method-id <IMPACT_METHOD_UUID> `
  --json
```

传递简单参数：

```powershell
.\.venv\Scripts\python.exe scripts\openlca-inspect.py baseline `
  --product-system-id <PRODUCT_SYSTEM_UUID> `
  --impact-method-id <IMPACT_METHOD_UUID> `
  --parameter mass=2.5 `
  --parameter distance=100
```

如参数需要 context，应先生成测试用例，再使用：

```powershell
.\.venv\Scripts\python.exe scripts\openlca-inspect.py baseline `
  --product-system-id <PRODUCT_SYSTEM_UUID> `
  --impact-method-id <IMPACT_METHOD_UUID> `
  --case-file tests/openlca-case.local.json
```

REST 诊断结果只能用于对照，不能替代 Desktop 独立基准。

## 6. 生成并完善测试用例

```powershell
.\.venv\Scripts\python.exe scripts\openlca-inspect.py case-template `
  --product-system-id <PRODUCT_SYSTEM_UUID> `
  --impact-method-id <IMPACT_METHOD_UUID>
```

工具会从 Product System 读取默认参数和 context，并生成
`tests/openlca-case.local.json`。为避免覆盖人工审核内容，文件已存在时命令会失败；
只有明确需要重建时才使用 `--force`。

生成文件中的：

```json
"expected_total_kg_co2e": null
```

必须替换为 Desktop 独立计算结果。默认容差为：

```text
max(0.01 kg CO₂e, |预期结果| × 0.1%)
```

`stage_process_uuids` 可在只验证引擎基准时保持为空；后续验证完整 PCF 阶段对账时，
应填入真实 provider process UUID。

## 7. 运行真实集成测试

```powershell
.\scripts\openlca-local.ps1 -Action Test
```

该命令会检查服务和测试用例，然后运行：

```powershell
.\.venv\Scripts\python.exe -m pytest `
  --run-openlca `
  -m openlca_integration `
  tests/test_openlca_integration.py -q
```

默认测试仍可独立运行，不会连接 openLCA：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## 8. 常见问题

### Docker Desktop 未启动

启动 Docker Desktop，确认 Linux containers 引擎可用：

```powershell
docker info
```

### 数据库不存在

确认配置指向工作区根目录，并检查：

```powershell
Get-ChildItem "<OPENLCA_WORKSPACE_PATH>/databases"
```

### openLCA Desktop 正在运行

保存工作并退出 Desktop，再启动 gdt-server。不要让两个进程同时访问同一工作区。

### 服务启动超时

查看日志：

```powershell
.\scripts\openlca-local.ps1 -Action Logs
```

大型数据库可能需要增加：

```env
OPENLCA_TIMEOUT_SECONDS=1200
OPENLCA_CONTAINER_MEMORY=16g
```

### UUID 找不到

UUID 必须来自当前挂载数据库。重新执行列表命令确认对象名称和 ID，不要复用其他数据库
或其他版本中的 UUID。

### 基准测试不一致

确认 Desktop 和 REST 使用完全相同的数据库版本、Product System、Impact Method、
参数值和参数 context。不要通过扩大容差掩盖模型或数据库差异。
