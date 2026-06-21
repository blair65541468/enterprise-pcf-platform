# Java 架构与开发规范

## 模块边界

项目是单 Maven 模块的 Spring Modulith 模块化单体。顶层业务包就是模块边界：
`catalog`、`imports`、`snapshots`、`calculations`、`approvals`、`exports`、`audit`
和 `health`。`shared` 只能提供通用能力，不得依赖任何业务模块。

跨模块调用只能指向模块通过 `@NamedInterface` 暴露的 `api`、`application` 或明确的
领域契约。禁止访问其他模块的 `infrastructure` 包。

## 模块内依赖方向

```text
api -> application -> domain
           |
           v
    application port <- infrastructure adapter
```

- Controller 只处理认证信息、参数校验、请求转换和响应。
- application service 定义事务边界并依赖接口，不依赖 JDBC、JPA 实现或外部客户端。
- domain 不依赖 Spring MVC、RabbitMQ、S3、Excel 或 openLCA 客户端。
- infrastructure 实现 application port；普通 CRUD 优先使用 Spring Data JPA。
- 原生 SQL 仅用于锁、`FOR UPDATE SKIP LOCKED`、批量写入和复杂报表查询。

## 持久化规则

- 一个 JPA 实体一个文件，字段显式映射到现有 PostgreSQL 表和列。
- UUID 保持 `varchar(36)`，金额和排放量使用 `BigDecimal`，时间使用 `Instant`。
- JSON 使用 Hibernate JSON 类型；不得改变 Flyway V1/V2。
- application service 负责 `@Transactional`，Repository 不自行提交。
- 批量导入必须分批 `flush/clear`，避免持久化上下文无限增长。
- 快照、批准后的因子和模板、审计事件继续由数据库触发器保护。

## 兼容性规则

- 不修改现有 `/v1` URL、HTTP 方法、状态码、snake_case 字段及 `detail` 错误结构。
- 不修改 18 个公开 OpenAPI Schema、Excel 模板、正式导出结构和 manifest hash。
- 不修改 RabbitMQ exchange、queue、routing key、消息格式或 gdt-server REST 契约。
- Python 仍是迁移期间的生产基线；Java 影子验证阶段禁止双写正式数据库。

## 自动化门禁

- Spring Modulith：模块无循环依赖，且只能访问公开 named interface。
- ArchUnit：Controller 不访问 Repository；application 不依赖 infrastructure/JDBC；
  `shared` 不依赖业务模块。
- Testcontainers PostgreSQL：执行 Flyway V1→V3，并以 Hibernate `validate` 校验映射。
- Spotless、单元测试、API 路径契约和 JaCoCo 在 `mvn verify` 中执行。
