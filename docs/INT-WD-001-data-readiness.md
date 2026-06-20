# INT-WD-001 数据就绪检查

检查日期：2026-06-20  
范围：工作区 13 份业务源 Excel；不包含 `outputs` 下的审核输出文件。

## 导入结果

导入状态：`validated`

| 对象 | 数量 |
|---|---:|
| 物料 | 20 |
| 因子版本 | 31 |
| 产品 | 2 |
| 产品版本 | 2 |
| INT-WD-001 BOM 行 | 16 |
| 工艺路线 | 1 |
| 工序 | 8 |
| 供应商 | 8 |
| 设备 | 12 |

导入警告：

- `DUPLICATE_HEADERS`：原材料因子文件存在“提交人、提交时间、更新时间”重复表头，导入时已重命名，不覆盖原值。
- `NEGATIVE_FACTOR_REVIEW`：物流与废弃因子中存在负值，必须由 LCA 审核人确认系统边界和避免收益重复计算。
- `TEST_RECORD_ISOLATED`：`TEST-001` 已隔离，未进入正式主数据。

## 快照门禁结果

为 `INT-WD-001` 创建 `WD-ROUTE-V1` 快照时被正确阻断，共 35 项：

| 阻断代码 | 数量 | 处理要求 |
|---|---:|---|
| `FACTOR_NOT_APPROVED` | 16 | 审核数值、单位、来源、地区、年份和许可后批准 |
| `OPENLCA_MAPPING_MISSING` | 10 | 补充 process UUID、reference flow UUID、单位及转换规则 |
| `DENSITY_MISSING` | 6 | 为以 m³ 计量的板材因子补充经批准密度 |
| `ROUTE_NOT_APPROVED` | 1 | 审核并批准 `WD-ROUTE-V1` |
| `GRID_FACTOR_MISSING` | 1 | 选择并批准适用工厂购电结构的电力因子 |
| `INBOUND_TRANSPORT_MISSING` | 1 | 补充运输方式、距离、质量、装载率和证据 |

## 进入真实 openLCA 对账前的完成条件

1. 完成上述 35 项阻断数据的审核和批准。
2. 在 openLCA Desktop 发布只读 `WARDROBE-GATE-V1` 产品系统。
3. 注册真实 Product System UUID、Impact Method UUID、数据库版本和参数字典。
4. 在模板 `parameter_schema.stage_process_uuids` 中维护四个生命周期阶段的过程 UUID。
5. 完成 gdt-server 和背景数据库许可确认。
6. 使用 Desktop 基准结果进行 API 对账，差异不得超过 `max(0.01 kg CO₂e, 0.1%)`。

当前 mock 引擎只用于接口和工作流验证，不构成 ISO 14067 产品碳足迹结果。
