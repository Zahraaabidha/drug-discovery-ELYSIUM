"""baseline: tables that existed before the compound registry

Revision ID: 0001
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def _has(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    # Idempotent: databases created by the old Base.metadata.create_all() already have these.
    if not _has("discovery_runs"):
        op.create_table(
            "discovery_runs",
            sa.Column("id", sa.String, primary_key=True),
            sa.Column("target_id", sa.String, nullable=False, index=True),
            sa.Column("num_molecules", sa.Integer, nullable=False),
            sa.Column("created_at", sa.DateTime),
        )
    if not _has("molecules"):
        op.create_table(
            "molecules",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("run_id", sa.String, sa.ForeignKey("discovery_runs.id"), nullable=False, index=True),
            sa.Column("smiles", sa.String, nullable=False, index=True),
            sa.Column("score", sa.Float, nullable=False),
            sa.Column("source", sa.String, nullable=False),
            sa.Column("notes", sa.Text),
            sa.Column("admet_mw", sa.Float), sa.Column("admet_logp", sa.Float),
            sa.Column("admet_hbd", sa.Integer), sa.Column("admet_hba", sa.Integer),
            sa.Column("admet_tpsa", sa.Float), sa.Column("admet_rotatable_bonds", sa.Integer),
            sa.Column("admet_lipinski_pass", sa.Integer), sa.Column("admet_lipinski_violations", sa.Integer),
            sa.Column("similar_drug_fp", sa.String), sa.Column("tanimoto_fp", sa.Float),
            sa.Column("similar_drug_semantic", sa.String), sa.Column("tanimoto_semantic", sa.Float),
            sa.Column("scorer_used", sa.String),
        )
    if not _has("kg_nodes"):
        op.create_table(
            "kg_nodes",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("node_type", sa.String, index=True),
            sa.Column("external_id", sa.String, index=True),
            sa.Column("name", sa.String, nullable=False, index=True),
            sa.Column("smiles", sa.String),
            sa.Column("info", sa.Text),
        )
    if not _has("kg_edges"):
        op.create_table(
            "kg_edges",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("source_id", sa.Integer, sa.ForeignKey("kg_nodes.id"), nullable=False),
            sa.Column("target_id", sa.Integer, sa.ForeignKey("kg_nodes.id"), nullable=False),
            sa.Column("relation", sa.String, index=True),
            sa.Column("weight", sa.Float),
            sa.Column("extra", sa.Text),
        )


def downgrade() -> None:
    for t in ("kg_edges", "kg_nodes", "molecules", "discovery_runs"):
        if _has(t):
            op.drop_table(t)
