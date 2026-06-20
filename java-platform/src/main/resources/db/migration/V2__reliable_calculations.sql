ALTER TABLE calculation_run ADD COLUMN product_id varchar(36);
ALTER TABLE calculation_run ADD COLUMN request_hash varchar(64);
ALTER TABLE calculation_run ADD COLUMN execution_token varchar(36);
ALTER TABLE calculation_run ADD COLUMN attempt_count integer NOT NULL DEFAULT 0;
ALTER TABLE calculation_run ADD COLUMN heartbeat_at timestamptz;

UPDATE calculation_run r
SET product_id = s.product_id
FROM calculation_snapshot s
WHERE s.id = r.snapshot_id;

ALTER TABLE calculation_run ALTER COLUMN product_id SET NOT NULL;
ALTER TABLE calculation_run
  ADD CONSTRAINT fk_calculation_run_product FOREIGN KEY(product_id) REFERENCES product(id);

CREATE INDEX ix_calculation_run_product_id ON calculation_run(product_id);
CREATE INDEX ix_calculation_run_request_hash ON calculation_run(request_hash);
CREATE INDEX ix_calculation_run_execution_token ON calculation_run(execution_token);
CREATE INDEX ix_calculation_run_heartbeat_at ON calculation_run(heartbeat_at);
CREATE UNIQUE INDEX uq_calculation_run_current_approved
  ON calculation_run(product_id) WHERE status = 'approved';

CREATE TABLE outbox_event (
  id varchar(36) PRIMARY KEY,
  event_type varchar(100) NOT NULL,
  aggregate_type varchar(100) NOT NULL,
  aggregate_id varchar(36) NOT NULL,
  payload json NOT NULL DEFAULT '{}',
  published_at timestamptz,
  attempt_count integer NOT NULL DEFAULT 0,
  last_error text,
  created_at timestamptz NOT NULL,
  CONSTRAINT uq_outbox_event_aggregate UNIQUE(event_type, aggregate_id)
);
CREATE INDEX ix_outbox_event_event_type ON outbox_event(event_type);
CREATE INDEX ix_outbox_event_aggregate_id ON outbox_event(aggregate_id);
CREATE INDEX ix_outbox_event_published_at ON outbox_event(published_at);

CREATE OR REPLACE FUNCTION pcf_prevent_immutable_change()
RETURNS trigger AS $$
BEGIN
  IF TG_TABLE_NAME IN ('calculation_snapshot', 'audit_event') THEN
    RAISE EXCEPTION '% is append-only', TG_TABLE_NAME;
  END IF;
  IF TG_TABLE_NAME = 'factor_version' AND OLD.approved THEN
    RAISE EXCEPTION 'approved factor versions are immutable';
  END IF;
  IF TG_TABLE_NAME = 'model_template_version' AND OLD.approved THEN
    RAISE EXCEPTION 'approved model template versions are immutable';
  END IF;
  IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_pcf_immutable BEFORE UPDATE OR DELETE ON calculation_snapshot
FOR EACH ROW EXECUTE FUNCTION pcf_prevent_immutable_change();
CREATE TRIGGER trg_pcf_immutable BEFORE UPDATE OR DELETE ON audit_event
FOR EACH ROW EXECUTE FUNCTION pcf_prevent_immutable_change();
CREATE TRIGGER trg_pcf_immutable BEFORE UPDATE OR DELETE ON factor_version
FOR EACH ROW EXECUTE FUNCTION pcf_prevent_immutable_change();
CREATE TRIGGER trg_pcf_immutable BEFORE UPDATE OR DELETE ON model_template_version
FOR EACH ROW EXECUTE FUNCTION pcf_prevent_immutable_change();

