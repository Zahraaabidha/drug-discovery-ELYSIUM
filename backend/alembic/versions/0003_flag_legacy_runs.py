"""flag discovery runs created before the compound registry

Runs created by earlier versions sampled molecules from the bundled reference library and could fall
back to placeholder scores when DeepPurpose failed, without recording which. Their provenance cannot
be verified, so they are kept but clearly labelled instead of being presented as valid results.

Revision ID: 0003
Revises: 0002
"""
import json

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

NOTE = {
    "legacy": True,
    "note": ("Created before the compound registry. Molecules were sampled from the reference library (not newly "
             "generated) and scores may be placeholder values from a fallback scorer. Kept for history only; "
             "do not use as scientific evidence."),
}


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text("UPDATE discovery_runs SET status = 'legacy_unverified', metrics = :metrics WHERE status IS NULL"),
        {"metrics": json.dumps(NOTE)},
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("UPDATE discovery_runs SET status = NULL, metrics = NULL WHERE status = 'legacy_unverified'"))
