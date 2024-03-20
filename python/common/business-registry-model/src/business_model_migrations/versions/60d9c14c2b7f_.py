"""empty message

Revision ID: 60d9c14c2b7f
Revises: 4aed1fbbba29
Create Date: 2023-06-27 07:18:59.688194

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "60d9c14c2b7f"
down_revision = "4aed1fbbba29"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("legal_entities", schema=None) as batch_op:
        batch_op.drop_column("cco_expiry_date")

    with op.batch_alter_table("legal_entities_history", schema=None) as batch_op:
        batch_op.drop_column("cco_expiry_date")


def downgrade():
    with op.batch_alter_table("legal_entities", schema=None) as batch_op:
        batch_op.add_column(sa.Column("cco_expiry_date", sa.DateTime(timezone=True), nullable=True))

    with op.batch_alter_table("legal_entities_history", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("cco_expiry_date", sa.DateTime(timezone=True), autoincrement=False, nullable=True)
        )
