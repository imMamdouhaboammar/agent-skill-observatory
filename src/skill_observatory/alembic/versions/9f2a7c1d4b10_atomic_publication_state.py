"""add atomic publication observation state

Revision ID: 9f2a7c1d4b10
Revises: 8278fbd6b06e
Create Date: 2026-09-10 07:10:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "9f2a7c1d4b10"
down_revision: str | None = "8278fbd6b06e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "skills",
        sa.Column("source_fingerprint", sa.String(length=64), nullable=False, server_default=""),
    )
    op.add_column(
        "skills",
        sa.Column(
            "analysis_fingerprint",
            sa.String(length=64),
            nullable=False,
            server_default="",
        ),
    )
    op.add_column(
        "skills",
        sa.Column("consecutive_misses", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "skills",
        sa.Column("last_successful_repo_scan_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("skills", "last_successful_repo_scan_at")
    op.drop_column("skills", "consecutive_misses")
    op.drop_column("skills", "analysis_fingerprint")
    op.drop_column("skills", "source_fingerprint")
