"""compound registry, bioactivity, predictions, collections, evaluation, run provenance

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "compounds",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("inchikey", sa.String(27), nullable=False, unique=True),
        sa.Column("canonical_smiles", sa.String, nullable=False),
        sa.Column("original_smiles", sa.String, nullable=False),
        sa.Column("name", sa.String),
        sa.Column("formula", sa.String),
        sa.Column("origin", sa.String, nullable=False),
        sa.Column("created_at", sa.DateTime),
        sa.Column("mol_weight", sa.Float), sa.Column("logp", sa.Float), sa.Column("tpsa", sa.Float),
        sa.Column("hbd", sa.Integer), sa.Column("hba", sa.Integer),
        sa.Column("rotatable_bonds", sa.Integer), sa.Column("heavy_atoms", sa.Integer),
        sa.Column("ring_count", sa.Integer),
        sa.Column("lipinski_violations", sa.Integer), sa.Column("lipinski_pass", sa.Boolean),
        sa.Column("generation_method", sa.String),
        sa.Column("generation_run_id", sa.String, sa.ForeignKey("discovery_runs.id")),
    )
    for col in ("inchikey", "canonical_smiles", "name", "origin", "mol_weight", "logp", "tpsa",
                "lipinski_violations", "generation_run_id"):
        op.create_index(f"ix_compounds_{col}", "compounds", [col])

    op.create_table(
        "compound_sources",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("compound_id", sa.Integer, sa.ForeignKey("compounds.id"), nullable=False),
        sa.Column("source_db", sa.String, nullable=False),
        sa.Column("external_id", sa.String, nullable=False, server_default=""),
        sa.Column("original_smiles", sa.String, nullable=False),
        sa.Column("url", sa.String),
        sa.Column("retrieved_at", sa.DateTime),
        sa.Column("note", sa.Text),
        sa.UniqueConstraint("compound_id", "source_db", "external_id", name="uq_compound_source"),
    )
    op.create_index("ix_compound_sources_compound_id", "compound_sources", ["compound_id"])
    op.create_index("ix_compound_sources_source_db", "compound_sources", ["source_db"])

    op.create_table(
        "bioactivities",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("compound_id", sa.Integer, sa.ForeignKey("compounds.id"), nullable=False),
        sa.Column("target_symbol", sa.String, nullable=False),
        sa.Column("uniprot_id", sa.String),
        sa.Column("source_db", sa.String, nullable=False),
        sa.Column("external_id", sa.String, nullable=False),
        sa.Column("standard_type", sa.String, nullable=False),
        sa.Column("relation", sa.String),
        sa.Column("value_nm", sa.Float, nullable=False),
        sa.Column("pvalue", sa.Float),
        sa.Column("assay_ref", sa.String),
        sa.Column("evidence_type", sa.String, nullable=False, server_default="experimental"),
        sa.Column("retrieved_at", sa.DateTime),
        sa.UniqueConstraint("compound_id", "target_symbol", "source_db", "external_id", name="uq_bioactivity"),
    )
    for col in ("compound_id", "target_symbol", "uniprot_id", "source_db"):
        op.create_index(f"ix_bioactivities_{col}", "bioactivities", [col])

    op.create_table(
        "predictions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("compound_id", sa.Integer, sa.ForeignKey("compounds.id"), nullable=False),
        sa.Column("run_id", sa.String, sa.ForeignKey("discovery_runs.id")),
        sa.Column("target_symbol", sa.String, nullable=False),
        sa.Column("uniprot_id", sa.String),
        sa.Column("model_name", sa.String, nullable=False),
        sa.Column("model_version", sa.String),
        sa.Column("value", sa.Float, nullable=False),
        sa.Column("units", sa.String, nullable=False, server_default="nM"),
        sa.Column("pkd", sa.Float),
        sa.Column("normalised_score", sa.Float),
        sa.Column("evidence_type", sa.String, nullable=False, server_default="computational_prediction"),
        sa.Column("params", sa.JSON),
        sa.Column("created_at", sa.DateTime),
    )
    for col in ("compound_id", "run_id", "target_symbol"):
        op.create_index(f"ix_predictions_{col}", "predictions", [col])

    op.create_table(
        "annotations",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("compound_id", sa.Integer, sa.ForeignKey("compounds.id"), nullable=False),
        sa.Column("author", sa.String),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime),
    )
    op.create_index("ix_annotations_compound_id", "annotations", ["compound_id"])

    op.create_table(
        "collections",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String, nullable=False, unique=True),
        sa.Column("description", sa.Text),
        sa.Column("created_at", sa.DateTime),
    )
    op.create_table(
        "collection_items",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("collection_id", sa.Integer, sa.ForeignKey("collections.id"), nullable=False),
        sa.Column("compound_id", sa.Integer, sa.ForeignKey("compounds.id"), nullable=False),
        sa.Column("added_at", sa.DateTime),
        sa.UniqueConstraint("collection_id", "compound_id", name="uq_collection_item"),
    )
    op.create_index("ix_collection_items_collection_id", "collection_items", ["collection_id"])
    op.create_index("ix_collection_items_compound_id", "collection_items", ["compound_id"])

    op.create_table(
        "evaluation_reports",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("kind", sa.String, nullable=False),
        sa.Column("created_at", sa.DateTime),
        sa.Column("parameters", sa.JSON),
        sa.Column("dataset", sa.JSON),
        sa.Column("metrics", sa.JSON),
        sa.Column("limitations", sa.Text),
    )
    op.create_index("ix_evaluation_reports_kind", "evaluation_reports", ["kind"])

    with op.batch_alter_table("discovery_runs") as b:
        b.add_column(sa.Column("status", sa.String))
        b.add_column(sa.Column("error", sa.Text))
        b.add_column(sa.Column("seed", sa.Integer))
        b.add_column(sa.Column("params", sa.JSON))
        b.add_column(sa.Column("models", sa.JSON))
        b.add_column(sa.Column("data_sources", sa.JSON))
        b.add_column(sa.Column("metrics", sa.JSON))
    with op.batch_alter_table("molecules") as b:
        b.add_column(sa.Column("compound_id", sa.Integer))
        b.create_foreign_key("fk_molecules_compound", "compounds", ["compound_id"], ["id"])
        b.create_index("ix_molecules_compound_id", ["compound_id"])


def downgrade() -> None:
    with op.batch_alter_table("molecules") as b:
        b.drop_index("ix_molecules_compound_id")
        b.drop_constraint("fk_molecules_compound", type_="foreignkey")
        b.drop_column("compound_id")
    with op.batch_alter_table("discovery_runs") as b:
        for c in ("metrics", "data_sources", "models", "params", "seed", "error", "status"):
            b.drop_column(c)
    for t in ("evaluation_reports", "collection_items", "collections", "annotations",
              "predictions", "bioactivities", "compound_sources", "compounds"):
        op.drop_table(t)
