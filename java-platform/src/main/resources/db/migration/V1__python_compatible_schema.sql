CREATE TYPE importstatus AS ENUM ('uploaded', 'processing', 'validated', 'failed');
CREATE TYPE calculationstatus AS ENUM (
  'draft', 'validated', 'queued', 'calculating', 'calculated',
  'submitted', 'approved', 'rejected', 'superseded', 'failed'
);
CREATE TYPE mappingstatus AS ENUM ('draft', 'approved', 'rejected');

CREATE TABLE import_job (
  id varchar(36) PRIMARY KEY,
  status importstatus NOT NULL,
  created_by varchar(100) NOT NULL,
  file_manifest json NOT NULL DEFAULT '[]',
  summary json NOT NULL DEFAULT '{}',
  completed_at timestamptz,
  created_at timestamptz NOT NULL
);

CREATE TABLE product (
  id varchar(36) PRIMARY KEY,
  sku varchar(100) NOT NULL UNIQUE,
  brand_sku varchar(100),
  name varchar(300) NOT NULL,
  target_market varchar(100),
  created_at timestamptz NOT NULL
);
CREATE INDEX ix_product_sku ON product(sku);

CREATE TABLE product_version (
  id varchar(36) PRIMARY KEY,
  product_id varchar(36) NOT NULL REFERENCES product(id),
  version integer NOT NULL,
  source_import_id varchar(36) REFERENCES import_job(id),
  payload json NOT NULL,
  content_hash varchar(64) NOT NULL,
  created_at timestamptz NOT NULL,
  CONSTRAINT uq_product_version UNIQUE(product_id, version)
);
CREATE INDEX ix_product_version_product_id ON product_version(product_id);
CREATE INDEX ix_product_version_content_hash ON product_version(content_hash);

CREATE TABLE material (
  id varchar(36) PRIMARY KEY,
  code varchar(100) NOT NULL UNIQUE,
  name varchar(300) NOT NULL,
  category varchar(200),
  created_at timestamptz NOT NULL
);
CREATE INDEX ix_material_code ON material(code);

CREATE TABLE emission_factor (
  id varchar(36) PRIMARY KEY,
  factor_code varchar(100) NOT NULL UNIQUE,
  material_code varchar(100),
  name varchar(300) NOT NULL,
  created_at timestamptz NOT NULL
);
CREATE INDEX ix_emission_factor_factor_code ON emission_factor(factor_code);
CREATE INDEX ix_emission_factor_material_code ON emission_factor(material_code);

CREATE TABLE factor_version (
  id varchar(36) PRIMARY KEY,
  factor_id varchar(36) NOT NULL REFERENCES emission_factor(id),
  version integer NOT NULL,
  value numeric(20,8) NOT NULL,
  activity_unit varchar(50) NOT NULL,
  co2e_unit varchar(80) NOT NULL,
  source varchar(500) NOT NULL,
  standard varchar(200),
  region varchar(100),
  reference_year integer,
  data_quality varchar(100),
  density_kg_m3 numeric(20,6),
  licence_ref varchar(500),
  content_hash varchar(64) NOT NULL,
  approved boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL,
  CONSTRAINT uq_factor_version UNIQUE(factor_id, version)
);
CREATE INDEX ix_factor_version_factor_id ON factor_version(factor_id);

CREATE TABLE bom_line (
  id varchar(36) PRIMARY KEY,
  product_version_id varchar(36) NOT NULL REFERENCES product_version(id),
  line_no integer NOT NULL,
  material_id varchar(36) NOT NULL REFERENCES material(id),
  part_name varchar(300) NOT NULL,
  material_type varchar(100),
  quantity numeric(20,6) NOT NULL,
  unit varchar(50) NOT NULL,
  weight_kg_each numeric(20,6),
  factor_version_id varchar(36) REFERENCES factor_version(id),
  stage varchar(50) NOT NULL,
  source_row integer,
  created_at timestamptz NOT NULL,
  CONSTRAINT uq_bom_line UNIQUE(product_version_id, line_no)
);
CREATE INDEX ix_bom_line_product_version_id ON bom_line(product_version_id);
CREATE INDEX ix_bom_line_material_id ON bom_line(material_id);

CREATE TABLE supplier (
  id varchar(36) PRIMARY KEY,
  supplier_code varchar(100) NOT NULL UNIQUE,
  name varchar(300) NOT NULL,
  category varchar(200),
  certifications text,
  is_test boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL
);
CREATE INDEX ix_supplier_supplier_code ON supplier(supplier_code);

CREATE TABLE process_route (
  id varchar(36) PRIMARY KEY,
  product_id varchar(36) NOT NULL REFERENCES product(id),
  route_code varchar(100) NOT NULL,
  version varchar(50) NOT NULL,
  approved boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL,
  CONSTRAINT uq_route_version UNIQUE(product_id, version)
);
CREATE INDEX ix_process_route_product_id ON process_route(product_id);

CREATE TABLE route_step (
  id varchar(36) PRIMARY KEY,
  route_id varchar(36) NOT NULL REFERENCES process_route(id),
  sequence integer NOT NULL,
  process_code varchar(100) NOT NULL,
  name varchar(300) NOT NULL,
  standard_time_min numeric(20,6),
  energy_kwh_per_unit numeric(20,6),
  created_at timestamptz NOT NULL,
  CONSTRAINT uq_route_step UNIQUE(route_id, sequence)
);
CREATE INDEX ix_route_step_route_id ON route_step(route_id);

CREATE TABLE equipment (
  id varchar(36) PRIMARY KEY,
  equipment_code varchar(100) NOT NULL UNIQUE,
  name varchar(300) NOT NULL,
  process_code varchar(100),
  area varchar(200),
  rated_power_kw numeric(20,6),
  energy_type varchar(100),
  allocation_pool varchar(100),
  created_at timestamptz NOT NULL
);
CREATE INDEX ix_equipment_equipment_code ON equipment(equipment_code);

CREATE TABLE energy_activity (
  id varchar(36) PRIMARY KEY,
  product_version_id varchar(36) NOT NULL REFERENCES product_version(id),
  route_step_id varchar(36) REFERENCES route_step(id),
  energy_type varchar(100) NOT NULL,
  amount numeric(20,8) NOT NULL,
  unit varchar(50) NOT NULL,
  factor_version_id varchar(36) REFERENCES factor_version(id),
  source varchar(300) NOT NULL,
  approved boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL
);
CREATE INDEX ix_energy_activity_product_version_id ON energy_activity(product_version_id);

CREATE TABLE transport_activity (
  id varchar(36) PRIMARY KEY,
  product_version_id varchar(36) NOT NULL REFERENCES product_version(id),
  material_id varchar(36) REFERENCES material(id),
  supplier_id varchar(36) REFERENCES supplier(id),
  mode varchar(100) NOT NULL,
  distance_km numeric(20,6) NOT NULL,
  mass_kg numeric(20,6) NOT NULL,
  load_factor numeric(10,6),
  factor_version_id varchar(36) REFERENCES factor_version(id),
  source varchar(300) NOT NULL,
  approved boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL
);
CREATE INDEX ix_transport_activity_product_version_id ON transport_activity(product_version_id);

CREATE TABLE material_process_mapping (
  id varchar(36) PRIMARY KEY,
  material_id varchar(36) NOT NULL REFERENCES material(id),
  process_uuid varchar(100) NOT NULL,
  reference_flow_uuid varchar(100) NOT NULL,
  openlca_unit varchar(50) NOT NULL,
  conversion_rule json NOT NULL,
  region varchar(100),
  reference_year integer,
  database_version varchar(100) NOT NULL,
  status mappingstatus NOT NULL,
  reviewed_by varchar(100),
  created_at timestamptz NOT NULL,
  CONSTRAINT uq_material_process_mapping UNIQUE(material_id, database_version)
);
CREATE INDEX ix_material_process_mapping_material_id ON material_process_mapping(material_id);

CREATE TABLE model_template (
  id varchar(36) PRIMARY KEY,
  code varchar(100) NOT NULL UNIQUE,
  name varchar(300) NOT NULL,
  product_family varchar(200) NOT NULL,
  created_at timestamptz NOT NULL
);

CREATE TABLE model_template_version (
  id varchar(36) PRIMARY KEY,
  template_id varchar(36) NOT NULL REFERENCES model_template(id),
  version varchar(100) NOT NULL,
  product_system_uuid varchar(100) NOT NULL,
  impact_method_uuid varchar(100) NOT NULL,
  database_version varchar(100) NOT NULL,
  parameter_schema json NOT NULL,
  approved boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL,
  CONSTRAINT uq_template_version UNIQUE(template_id, version)
);
CREATE INDEX ix_model_template_version_template_id ON model_template_version(template_id);

CREATE TABLE import_issue (
  id varchar(36) PRIMARY KEY,
  import_job_id varchar(36) NOT NULL REFERENCES import_job(id),
  severity varchar(20) NOT NULL,
  file_name varchar(300) NOT NULL,
  row_number integer,
  field varchar(200),
  code varchar(100) NOT NULL,
  message text NOT NULL,
  created_at timestamptz NOT NULL
);
CREATE INDEX ix_import_issue_import_job_id ON import_issue(import_job_id);

CREATE TABLE calculation_snapshot (
  id varchar(36) PRIMARY KEY,
  product_id varchar(36) NOT NULL REFERENCES product(id),
  version integer NOT NULL,
  product_version_id varchar(36) NOT NULL REFERENCES product_version(id),
  route_id varchar(36) REFERENCES process_route(id),
  factor_set_version varchar(100) NOT NULL,
  boundary varchar(100) NOT NULL,
  payload json NOT NULL,
  manifest_hash varchar(64) NOT NULL UNIQUE,
  validation_errors json NOT NULL DEFAULT '[]',
  created_by varchar(100) NOT NULL,
  created_at timestamptz NOT NULL,
  CONSTRAINT uq_snapshot_version UNIQUE(product_id, version)
);
CREATE INDEX ix_calculation_snapshot_product_id ON calculation_snapshot(product_id);

CREATE TABLE calculation_run (
  id varchar(36) PRIMARY KEY,
  snapshot_id varchar(36) NOT NULL REFERENCES calculation_snapshot(id),
  model_template_version_id varchar(36) NOT NULL REFERENCES model_template_version(id),
  idempotency_key varchar(200) NOT NULL UNIQUE,
  status calculationstatus NOT NULL,
  impact_method varchar(200) NOT NULL,
  requested_by varchar(100) NOT NULL,
  submitted_by varchar(100),
  approved_by varchar(100),
  rejection_reason text,
  engine varchar(50) NOT NULL,
  engine_version varchar(100),
  raw_result_object_key varchar(500),
  error text,
  started_at timestamptz,
  completed_at timestamptz,
  submitted_at timestamptz,
  approved_at timestamptz,
  manifest_hash varchar(64),
  created_at timestamptz NOT NULL
);
CREATE INDEX ix_calculation_run_snapshot_id ON calculation_run(snapshot_id);
CREATE INDEX ix_calculation_run_status ON calculation_run(status);
CREATE INDEX ix_calculation_run_manifest_hash ON calculation_run(manifest_hash);

CREATE TABLE result_summary (
  id varchar(36) PRIMARY KEY,
  run_id varchar(36) NOT NULL UNIQUE REFERENCES calculation_run(id),
  total_kg_co2e numeric(20,8) NOT NULL,
  functional_unit varchar(300) NOT NULL,
  boundary varchar(100) NOT NULL,
  impact_method varchar(200) NOT NULL,
  aircraft numeric(20,8) NOT NULL DEFAULT 0,
  biogenic_emissions numeric(20,8) NOT NULL DEFAULT 0,
  biogenic_removals numeric(20,8) NOT NULL DEFAULT 0,
  fossil numeric(20,8) NOT NULL DEFAULT 0,
  land_use_change numeric(20,8) NOT NULL DEFAULT 0,
  raw_materials numeric(20,8) NOT NULL DEFAULT 0,
  inbound_transport numeric(20,8) NOT NULL DEFAULT 0,
  manufacturing numeric(20,8) NOT NULL DEFAULT 0,
  packaging numeric(20,8) NOT NULL DEFAULT 0,
  data_quality_status varchar(50) NOT NULL,
  created_at timestamptz NOT NULL
);

CREATE TABLE result_contribution (
  id varchar(36) PRIMARY KEY,
  run_id varchar(36) NOT NULL REFERENCES calculation_run(id),
  dimension varchar(50) NOT NULL,
  code varchar(200) NOT NULL,
  name varchar(300) NOT NULL,
  amount_kg_co2e numeric(20,8) NOT NULL,
  rank integer,
  metadata_json json NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL
);
CREATE INDEX ix_result_contribution_run_id ON result_contribution(run_id);

CREATE TABLE evidence_document (
  id varchar(36) PRIMARY KEY,
  object_type varchar(100) NOT NULL,
  object_id varchar(36) NOT NULL,
  document_type varchar(100) NOT NULL,
  object_key varchar(500) NOT NULL,
  sha256 varchar(64) NOT NULL,
  valid_from timestamptz,
  valid_until timestamptz,
  metadata_json json NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL
);
CREATE INDEX ix_evidence_document_object_type ON evidence_document(object_type);
CREATE INDEX ix_evidence_document_object_id ON evidence_document(object_id);

CREATE TABLE audit_event (
  id varchar(36) PRIMARY KEY,
  occurred_at timestamptz NOT NULL,
  actor varchar(100) NOT NULL,
  action varchar(100) NOT NULL,
  object_type varchar(100) NOT NULL,
  object_id varchar(36) NOT NULL,
  before_hash varchar(64),
  after_hash varchar(64),
  details json NOT NULL DEFAULT '{}'
);
CREATE INDEX ix_audit_event_occurred_at ON audit_event(occurred_at);
CREATE INDEX ix_audit_event_actor ON audit_event(actor);
CREATE INDEX ix_audit_event_action ON audit_event(action);
CREATE INDEX ix_audit_event_object_type ON audit_event(object_type);
CREATE INDEX ix_audit_event_object_id ON audit_event(object_id);

