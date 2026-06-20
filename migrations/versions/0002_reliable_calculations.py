"""Add reliable calculation execution and transactional outbox."""

import sqlalchemy as sa
from alembic import op

revision = "0002_reliable_calculations"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    columns = {column["name"] for column in inspector.get_columns("calculation_run")}
    indexes = {
        index["name"] for index in inspector.get_indexes("calculation_run") if index["name"]
    }
    with op.batch_alter_table("calculation_run") as batch:
        if "product_id" not in columns:
            batch.add_column(sa.Column("product_id", sa.String(length=36), nullable=True))
        if "request_hash" not in columns:
            batch.add_column(sa.Column("request_hash", sa.String(length=64), nullable=True))
        if "execution_token" not in columns:
            batch.add_column(sa.Column("execution_token", sa.String(length=36), nullable=True))
        if "attempt_count" not in columns:
            batch.add_column(
                sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0")
            )
        if "heartbeat_at" not in columns:
            batch.add_column(sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True))
        if "ix_calculation_run_request_hash" not in indexes:
            batch.create_index("ix_calculation_run_request_hash", ["request_hash"])
        if "ix_calculation_run_execution_token" not in indexes:
            batch.create_index("ix_calculation_run_execution_token", ["execution_token"])
        if "ix_calculation_run_heartbeat_at" not in indexes:
            batch.create_index("ix_calculation_run_heartbeat_at", ["heartbeat_at"])
        if "ix_calculation_run_product_id" not in indexes:
            batch.create_index("ix_calculation_run_product_id", ["product_id"])

    if "product_id" not in columns:
        connection.execute(
            sa.text(
                """
                UPDATE calculation_run
                SET product_id = (
                    SELECT calculation_snapshot.product_id
                    FROM calculation_snapshot
                    WHERE calculation_snapshot.id = calculation_run.snapshot_id
                )
                """
            )
        )
        with op.batch_alter_table("calculation_run") as batch:
            batch.create_foreign_key(
                "fk_calculation_run_product",
                "product",
                ["product_id"],
                ["id"],
            )
            batch.alter_column("product_id", existing_type=sa.String(36), nullable=False)

    inspector = sa.inspect(connection)
    run_indexes = {
        index["name"] for index in inspector.get_indexes("calculation_run") if index["name"]
    }
    if "uq_calculation_run_current_approved" not in run_indexes:
        op.create_index(
            "uq_calculation_run_current_approved",
            "calculation_run",
            ["product_id"],
            unique=True,
            postgresql_where=sa.text("status = 'approved'"),
            sqlite_where=sa.text("status = 'approved'"),
        )

    if "outbox_event" not in inspector.get_table_names():
        op.create_table(
            "outbox_event",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("event_type", sa.String(length=100), nullable=False),
            sa.Column("aggregate_type", sa.String(length=100), nullable=False),
            sa.Column("aggregate_id", sa.String(length=36), nullable=False),
            sa.Column("payload", sa.JSON(), nullable=False),
            sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "event_type",
                "aggregate_id",
                name="uq_outbox_event_aggregate",
            ),
        )
        op.create_index("ix_outbox_event_event_type", "outbox_event", ["event_type"])
        op.create_index("ix_outbox_event_aggregate_id", "outbox_event", ["aggregate_id"])
        op.create_index("ix_outbox_event_published_at", "outbox_event", ["published_at"])

    if connection.dialect.name == "postgresql":
        op.execute(
            """
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
              IF TG_OP = 'DELETE' THEN
                RETURN OLD;
              END IF;
              RETURN NEW;
            END;
            $$ LANGUAGE plpgsql
            """
        )
        for table in (
            "calculation_snapshot",
            "audit_event",
            "factor_version",
            "model_template_version",
        ):
            op.execute(
                f"""
                DROP TRIGGER IF EXISTS trg_pcf_immutable ON {table};
                CREATE TRIGGER trg_pcf_immutable
                BEFORE UPDATE OR DELETE ON {table}
                FOR EACH ROW EXECUTE FUNCTION pcf_prevent_immutable_change()
                """
            )


def downgrade() -> None:
    connection = op.get_bind()
    if connection.dialect.name == "postgresql":
        for table in (
            "calculation_snapshot",
            "audit_event",
            "factor_version",
            "model_template_version",
        ):
            op.execute(f"DROP TRIGGER IF EXISTS trg_pcf_immutable ON {table}")
        op.execute("DROP FUNCTION IF EXISTS pcf_prevent_immutable_change()")
    op.drop_index("uq_calculation_run_current_approved", table_name="calculation_run")
    op.drop_index("ix_outbox_event_published_at", table_name="outbox_event")
    op.drop_index("ix_outbox_event_aggregate_id", table_name="outbox_event")
    op.drop_index("ix_outbox_event_event_type", table_name="outbox_event")
    op.drop_table("outbox_event")
    with op.batch_alter_table("calculation_run") as batch:
        batch.drop_index("ix_calculation_run_heartbeat_at")
        batch.drop_index("ix_calculation_run_execution_token")
        batch.drop_index("ix_calculation_run_request_hash")
        batch.drop_column("heartbeat_at")
        batch.drop_column("attempt_count")
        batch.drop_column("execution_token")
        batch.drop_column("request_hash")
        batch.drop_index("ix_calculation_run_product_id")
        batch.drop_constraint("fk_calculation_run_product", type_="foreignkey")
        batch.drop_column("product_id")
