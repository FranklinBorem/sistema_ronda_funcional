"""schema inicial reconstruido (empresa/tenant, unidade, nvr/camera, ronda, ia, ocorrencia)

Revision ID: 0001_schema_reconstruido
Revises:
Create Date: 2026-08

Baseline do banco reconstruído após perda dos dados de produção
(ação do TI). Não há migration anterior a esta na cadeia ativa —
as 3 migrations do schema antigo foram arquivadas em
migrations/versions_legacy_pre_reset/ (histórico preservado, não
apagado, mas fora da cadeia que `flask db upgrade` percorre).

Ver docs/database/modelo-banco.md para o modelo lógico completo e
docs/decisions/decisoes-pendentes.md (Decisão 1) para o contexto da
unificação Nvr/NvrMonitorado nesta reconstrução.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001_schema_reconstruido"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ── planos (sem FK de saída) ────────────────────────────────────────
    op.create_table(
        "planos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(60), nullable=False),
        sa.Column("limites", postgresql.JSONB(), nullable=False,
                   server_default=sa.text("'{}'::jsonb")),
        sa.Column("features", postgresql.JSONB(), nullable=False,
                   server_default=sa.text("'{}'::jsonb")),
    )

    # ── empresas ─────────────────────────────────────────────────────────
    op.create_table(
        "empresas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(80), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="ativa"),
        sa.Column("plano_id", sa.Integer(), sa.ForeignKey("planos.id"), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False,
                   server_default=sa.text("now()")),
        sa.CheckConstraint("status IN ('ativa','suspensa')", name="ck_empresas_status"),
    )
    op.create_unique_constraint("uq_empresas_slug", "empresas", ["slug"])

    # ── usuarios ─────────────────────────────────────────────────────────
    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id"), nullable=True),
        sa.Column("nome", sa.String(150), nullable=False),
        sa.Column("usuario_login", sa.String(80), nullable=False),
        sa.Column("senha_hash", sa.String(255), nullable=False),
        sa.Column("papel", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="ativo"),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False,
                   server_default=sa.text("now()")),
        sa.UniqueConstraint("empresa_id", "usuario_login", name="uq_usuarios_empresa_login"),
        sa.CheckConstraint(
            "papel IN ('super_admin','admin_empresa','gestor','supervisor',"
            "'operador','visualizador')",
            name="ck_usuarios_papel",
        ),
        sa.CheckConstraint("status IN ('ativo','inativo')", name="ck_usuarios_status"),
    )

    # ── unidades ─────────────────────────────────────────────────────────
    op.create_table(
        "unidades",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id"), nullable=False),
        sa.Column("nome", sa.String(150), nullable=False),
        sa.Column("localizacao", sa.String(250), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="ativa"),
        sa.CheckConstraint("status IN ('ativa','inativa')", name="ck_unidades_status"),
    )
    op.create_index("ix_unidades_empresa_id", "unidades", ["empresa_id"])

    # ── usuario_unidade (associativa N:N) ───────────────────────────────
    op.create_table(
        "usuario_unidade",
        sa.Column("usuario_id", sa.Integer(), sa.ForeignKey("usuarios.id"), primary_key=True),
        sa.Column("unidade_id", sa.Integer(), sa.ForeignKey("unidades.id"), primary_key=True),
    )

    # ── areas ────────────────────────────────────────────────────────────
    op.create_table(
        "areas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("unidade_id", sa.Integer(), sa.ForeignKey("unidades.id"), nullable=False),
        sa.Column("nome", sa.String(100), nullable=False),
    )

    # ── nvrs ─────────────────────────────────────────────────────────────
    op.create_table(
        "nvrs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("unidade_id", sa.Integer(), sa.ForeignKey("unidades.id"), nullable=False),
        sa.Column("nome", sa.String(150), nullable=False),
        sa.Column("fabricante", sa.String(50), nullable=False, server_default="hikvision"),
        sa.Column("modelo", sa.String(80), nullable=True),
        sa.Column("endereco_ip", sa.String(50), nullable=True),
        sa.Column("porta", sa.Integer(), nullable=True, server_default="80"),
        sa.Column("usuario_acesso", sa.String(80), nullable=True),
        sa.Column("credencial_ref", sa.String(255), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="ativo"),
        sa.CheckConstraint("status IN ('ativo','inativo')", name="ck_nvrs_status"),
    )
    op.create_index("ix_nvrs_unidade_id", "nvrs", ["unidade_id"])
    op.create_index("ix_nvrs_endereco_ip", "nvrs", ["endereco_ip"])

    # ── cameras ──────────────────────────────────────────────────────────
    op.create_table(
        "cameras",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nvr_id", sa.Integer(), sa.ForeignKey("nvrs.id"), nullable=False),
        sa.Column("modo_conexao", sa.String(20), nullable=False),
        sa.Column("canal", sa.Integer(), nullable=True),
        sa.Column("endereco_ip", sa.String(50), nullable=True),
        sa.Column("porta", sa.Integer(), nullable=True),
        sa.Column("usuario_acesso", sa.String(80), nullable=True),
        sa.Column("credencial_ref", sa.String(255), nullable=True),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("nome", sa.String(100), nullable=True),
        sa.Column("capacidades", postgresql.JSONB(), nullable=False,
                   server_default=sa.text("'{}'::jsonb")),
        sa.CheckConstraint(
            "modo_conexao IN ('via_nvr','ip_direto')", name="ck_cameras_modo_conexao"
        ),
        sa.CheckConstraint(
            "(modo_conexao = 'via_nvr' AND canal IS NOT NULL) OR "
            "(modo_conexao = 'ip_direto' AND endereco_ip IS NOT NULL)",
            name="ck_cameras_conexao_valida",
        ),
        sa.CheckConstraint(
            "tipo IN ('bullet','dome','dome_interna','ptz','generica')",
            name="ck_cameras_tipo",
        ),
    )
    op.create_index(
        "uq_cameras_nvr_canal", "cameras", ["nvr_id", "canal"], unique=True,
        postgresql_where=sa.text("modo_conexao = 'via_nvr'"),
    )
    op.create_index(
        "uq_cameras_nvr_ip", "cameras", ["nvr_id", "endereco_ip"], unique=True,
        postgresql_where=sa.text("modo_conexao = 'ip_direto'"),
    )

    # ── presets ──────────────────────────────────────────────────────────
    op.create_table(
        "presets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("camera_id", sa.Integer(), sa.ForeignKey("cameras.id"), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("descricao", sa.String(150), nullable=True),
        sa.UniqueConstraint("camera_id", "numero", name="uq_presets_camera_numero"),
    )

    # ── rondas ───────────────────────────────────────────────────────────
    op.create_table(
        "rondas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("unidade_id", sa.Integer(), sa.ForeignKey("unidades.id"), nullable=False),
        sa.Column("usuario_id", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("iniciado_em", sa.DateTime(timezone=True), nullable=False,
                   server_default=sa.text("now()")),
        sa.Column("finalizado_em", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('em_andamento','finalizada','com_alertas','erro')",
            name="ck_rondas_status",
        ),
    )
    op.create_index("ix_rondas_unidade_iniciado", "rondas", ["unidade_id", "iniciado_em"])

    # ── resultados_ronda ─────────────────────────────────────────────────
    op.create_table(
        "resultados_ronda",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ronda_id", sa.Integer(), sa.ForeignKey("rondas.id"), nullable=False),
        sa.Column("nvr_id", sa.Integer(), sa.ForeignKey("nvrs.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("imagens_ref", postgresql.JSONB(), nullable=True),
    )

    # ── regras_deteccao ──────────────────────────────────────────────────
    op.create_table(
        "regras_deteccao",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("camera_id", sa.Integer(), sa.ForeignKey("cameras.id"), nullable=False),
        sa.Column("tipo", sa.String(40), nullable=False),
        sa.Column("parametros", postgresql.JSONB(), nullable=False,
                   server_default=sa.text("'{}'::jsonb")),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.create_index("ix_regras_deteccao_camera_tipo", "regras_deteccao", ["camera_id", "tipo"])

    # ── ocorrencias (antes de eventos_ia, que a referencia) ─────────────
    op.create_table(
        "ocorrencias",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id"), nullable=False),
        sa.Column("unidade_id", sa.Integer(), sa.ForeignKey("unidades.id"), nullable=False),
        sa.Column("origem", sa.String(20), nullable=False),
        sa.Column("tipo", sa.String(40), nullable=True),
        sa.Column("prioridade", sa.String(10), nullable=False, server_default="media"),
        sa.Column("status", sa.String(20), nullable=False, server_default="aberta"),
        sa.Column("responsavel_id", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=True),
        sa.Column("aberto_em", sa.DateTime(timezone=True), nullable=False,
                   server_default=sa.text("now()")),
        sa.Column("tratado_em", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "origem IN ('deteccao_ia','falha_equipamento','manual','mensagem_externa')",
            name="ck_ocorrencias_origem",
        ),
    )
    op.create_index("ix_ocorrencias_empresa_status", "ocorrencias", ["empresa_id", "status"])
    op.create_index("ix_ocorrencias_unidade_aberto", "ocorrencias", ["unidade_id", "aberto_em"])

    # ── eventos_ia ───────────────────────────────────────────────────────
    op.create_table(
        "eventos_ia",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("camera_id", sa.Integer(), sa.ForeignKey("cameras.id"), nullable=False),
        sa.Column("regra_id", sa.Integer(), sa.ForeignKey("regras_deteccao.id"), nullable=True),
        sa.Column("classe", sa.String(40), nullable=False),
        sa.Column("confianca", sa.Numeric(5, 4), nullable=False),
        sa.Column("evidencia_ref", sa.String(255), nullable=True),
        sa.Column("ocorrencia_id", sa.Integer(), sa.ForeignKey("ocorrencias.id"), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False,
                   server_default=sa.text("now()")),
    )
    op.create_index("ix_eventos_ia_camera_timestamp", "eventos_ia", ["camera_id", "timestamp"])

    # ── integracoes ──────────────────────────────────────────────────────
    op.create_table(
        "integracoes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id"), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("configuracao", postgresql.JSONB(), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.UniqueConstraint("empresa_id", "tipo", name="uq_integracoes_empresa_tipo"),
        sa.CheckConstraint("tipo IN ('discord','email','whatsapp')", name="ck_integracoes_tipo"),
    )

    # ── notificacoes ─────────────────────────────────────────────────────
    op.create_table(
        "notificacoes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ocorrencia_id", sa.Integer(), sa.ForeignKey("ocorrencias.id"), nullable=False),
        sa.Column("integracao_id", sa.Integer(), sa.ForeignKey("integracoes.id"), nullable=False),
        sa.Column("enviado_em", sa.DateTime(timezone=True), nullable=False,
                   server_default=sa.text("now()")),
        sa.Column("status_envio", sa.String(20), nullable=False),
    )

    # ── auditoria ────────────────────────────────────────────────────────
    op.create_table(
        "auditoria",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("empresa_id", sa.Integer(), sa.ForeignKey("empresas.id"), nullable=False),
        sa.Column("usuario_id", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=True),
        sa.Column("acao", sa.String(60), nullable=False),
        sa.Column("entidade", sa.String(60), nullable=False),
        sa.Column("entidade_id", sa.Integer(), nullable=True),
        sa.Column("detalhes", postgresql.JSONB(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False,
                   server_default=sa.text("now()")),
    )
    op.create_index("ix_auditoria_empresa_timestamp", "auditoria", ["empresa_id", "timestamp"])


def downgrade():
    # ordem inversa da criação, por causa das FKs
    op.drop_table("auditoria")
    op.drop_table("notificacoes")
    op.drop_table("integracoes")
    op.drop_table("eventos_ia")
    op.drop_table("ocorrencias")
    op.drop_table("regras_deteccao")
    op.drop_table("resultados_ronda")
    op.drop_table("rondas")
    op.drop_table("presets")
    op.drop_table("cameras")
    op.drop_table("nvrs")
    op.drop_table("areas")
    op.drop_table("usuario_unidade")
    op.drop_table("unidades")
    op.drop_table("usuarios")
    op.drop_table("empresas")
    op.drop_table("planos")
