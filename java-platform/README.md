# PCF Platform Java

该目录是 Python 生产基线的并行 Java 迁移实现。迁移期间禁止 Java 与 Python
同时写正式数据库；Java 应先连接生产数据和对象存储的只读副本进行影子验证。

## 技术栈

- Java 21、Maven Wrapper
- Spring Boot 4.1、Spring Modulith 2.1
- PostgreSQL 16、Flyway、Spring JDBC/JPA
- RabbitMQ、transactional outbox
- Apache POI、MinIO/S3、gdt-server REST
- Actuator、Micrometer、Prometheus、JSON 日志

## 项目结构

Java 版保持单 Maven 模块、单 Jar，使用 package-by-feature。每个业务模块内部采用传统分层：

```text
com.airpaq.pcf
├── shared/                         # 配置、安全、Web、JSON、存储公共契约
├── catalog/                        # 产品、因子、BOM、路线和映射
├── imports/                        # Excel 导入
├── snapshots/                      # 不可变计算快照
├── calculations/                   # 计算、引擎、outbox 和 RabbitMQ
├── approvals/                      # 提交、四眼审批和驳回
├── exports/                        # JSON/Excel 导出
├── audit/                          # 审计事件
└── health/                         # 存活、就绪和 openLCA 健康检查
```

模块内部约定：

- `api`：Controller 和请求/响应 DTO。
- `application`：用例、事务边界及应用端口。
- `domain`：JPA 实体、枚举、值对象和领域规则。
- `infrastructure`：Spring Data Repository、复杂 SQL、Excel、RabbitMQ、S3 和 openLCA 适配器。

跨模块只能使用 `@NamedInterface` 暴露的 API；Controller 禁止直接访问 Repository，application
禁止依赖 infrastructure。规则由 Spring Modulith 和 ArchUnit 自动验证。详细规范见
[`docs/java-architecture.md`](docs/java-architecture.md)。

## 本地启动

Java 版本不支持 SQLite。Docker 会启动 PostgreSQL、RabbitMQ、MinIO、
Flyway、API、Worker 和 Scheduler：

```powershell
cd "D:\AirPAQ\冷总RFID相关项目\pcf-platform"
Copy-Item java-platform\.env.example java-platform\.env.local

$env:PCF_JAVA_ENV_FILE="java-platform/.env.local"
docker compose --profile java up -d --build `
  java-api java-worker java-scheduler
```

默认入口：

- API：`http://127.0.0.1:8080`
- Swagger：`http://127.0.0.1:8080/docs`
- OpenAPI：`http://127.0.0.1:8080/openapi.json`
- 健康：`http://127.0.0.1:8080/health`
- 就绪：`http://127.0.0.1:8080/health/ready`
- 指标：`http://127.0.0.1:8080/metrics`

停止并保留数据：

```powershell
docker compose --profile java down
```

删除本地测试数据：

```powershell
docker compose --profile java down -v
```

## 运行角色

同一个 Jar 和镜像通过 `PCF_ROLE` 启用角色：

- `api`：HTTP API、Excel 导入、审批和导出。
- `worker`：消费 `pcf.calculation.execute.v1` 并执行计算。
- `scheduler`：投递 outbox 并恢复超时计算。
- `all`：仅适合开发，将三个角色合并到一个进程。

Java 正式切换前不要移除 Python 所需的 Redis/Celery。

## 数据库迁移与接管

新数据库直接执行 Flyway `V1` 到 `V3+`：

```powershell
docker compose --profile java run --rm java-migrate
```

接管已有 Python PostgreSQL 数据库时，先确认：

```sql
select version_num from alembic_version;
```

结果必须为 `0002_reliable_calculations`。备份数据库后，显式建立 Flyway
版本 2 基线：

```powershell
docker run --rm --network <compose-network> flyway/flyway:11.8-alpine `
  -url=jdbc:postgresql://postgres:5432/pcf `
  -user=pcf -password=pcf `
  -baselineVersion=2 `
  -baselineDescription="Alembic 0002 verified" `
  baseline

docker compose --profile java run --rm java-migrate
```

不要启用 `baselineOnMigrate`。项目保留 `alembic_version`，但切换后仅允许
Flyway 管理新迁移。

## openLCA

默认使用 mock 引擎：

```env
OPENLCA_ENGINE=mock
```

调用真实 gdt-server：

```env
OPENLCA_ENGINE=rest
OPENLCA_URL=http://host.docker.internal:8081
OPENLCA_API_TOKEN=
OPENLCA_TIMEOUT_SECONDS=600s
```

Java 客户端直接调用 gdt-server REST，不依赖 Python `olca-ipc`。临时计算结果
句柄始终在 `finally` 中释放。

## 构建与测试

```powershell
cd java-platform
.\mvnw.cmd test
.\mvnw.cmd verify
```

PostgreSQL 映射集成测试使用 Testcontainers，因此运行完整测试前必须启动 Docker Desktop。
它会从空数据库执行 Flyway V1→V3，再以 Hibernate `validate` 校验实体映射。

自动化测试覆盖 canonical JSON、mock 引擎、冻结 API 路径和 Modulith
边界。`verify` 配置了 85% JaCoCo 门禁；迁移尚未达到该覆盖率时会明确失败，
不得通过降低门禁伪造完成状态。

## 已验证的本地链路

在 PostgreSQL 16、RabbitMQ 4.1、MinIO 和 mock 引擎下已验证：

1. Flyway 从空库执行到 `V3`。
2. Java API、Worker、Scheduler 启动并健康。
3. Excel 导入返回 `validated`。
4. 创建不可变快照。
5. outbox 经 RabbitMQ 触发 Worker 计算。
6. 结果为 `7.525 kg CO₂e`，与 Python 测试基线一致。
7. 四眼审批生效。
8. JSON 导出包含 manifest，Excel 导出包含 10 个兼容工作表。

该验证不代表已经可以切换生产流量。切换前仍需完成生产副本影子比对、并发
测试、OIDC 契约测试、真实 openLCA 测试和覆盖率门禁。
