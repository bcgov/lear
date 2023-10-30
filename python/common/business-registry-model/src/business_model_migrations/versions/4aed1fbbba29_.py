"""empty message

Revision ID: 4aed1fbbba29
Revises: 2fd104a5f3b5
Create Date: 2023-06-27 07:16:08.947057

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "4aed1fbbba29"
down_revision = "2fd104a5f3b5"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "consent_continuation_outs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("foreign_jurisdiction", sa.String(length=10), nullable=True),
        sa.Column("foreign_jurisdiction_region", sa.String(length=10), nullable=True),
        sa.Column("expiry_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("legal_entity_id", sa.Integer(), nullable=True),
        sa.Column("filing_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["filing_id"],
            ["filings.id"],
        ),
        sa.ForeignKeyConstraint(
            ["legal_entity_id"],
            ["legal_entities.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id"),
        sqlite_autoincrement=True,
    )
    with op.batch_alter_table("consent_continuation_outs", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_consent_continuation_outs_filing_id"),
            ["filing_id"],
            unique=False,
        )

    op.create_table(
        "sent_to_gazette",
        sa.Column("filing_id", sa.Integer(), nullable=False),
        sa.Column("identifier", sa.String(length=10), nullable=False),
        sa.Column("sent_to_gazette_date", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("filing_id"),
        sa.UniqueConstraint("filing_id"),
        sqlite_autoincrement=True,
    )


def downgrade():
    with op.batch_alter_table("consent_continuation_outs", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_consent_continuation_outs_filing_id"))

    op.drop_table("consent_continuation_outs")
    op.drop_table("sent_to_gazette")
