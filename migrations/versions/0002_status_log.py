"""nvr_status_log e camera_status_log (Fase D — lacuna corrigida)

Revision ID: 0002_status_log
Revises: 0001_schema_reconstruido
Create Date: 2026-08

Adiciona as tabelas de log bruto de disponibilidade (um registro por
ciclo de polling ISAPI), que faltavam no schema reconstruído — ver
docstring de models_v2/monitoramento.py para o contexto completo da
lacuna encontrada durante a implementação da Fase D.
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_status_log"
down_revision = "0001_schema_reconstruido"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "nvr_status_log",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("nvr_id", sa.Integer(), sa.ForeignKey("nvrs.id"), nullable=False),
        sa.Column("online", sa.Boolean(), nullable=False),
        sa.Column("latencia_ms", sa.Integer(), nullable=True),
        sa.Column("detalhes", sa.JSON(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False,
                   server_default=sa.text("now()")),
    )
    op.create_index(
        "ix_nvr_status_log_nvr_timestamp", "nvr_status_log", ["nvr_id", "timestamp"]
    )

    op.create_table(
        "camera_status_log",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("camera_id", sa.Integer(), sa.ForeignKey("cameras.id"), nullable=False),
        sa.Column("online", sa.Boolean(), nullable=False),
        sa.Column("detalhes", sa.JSON(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False,
                   server_default=sa.text("now()")),
    )
    op.create_index(
        "ix_camera_status_log_camera_timestamp", "camera_status_log", ["camera_id", "timestamp"]
    )


def downgrade():
    op.drop_table("camera_status_log")
    op.drop_table("nvr_status_log")
