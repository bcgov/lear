"""alter_business_state_enum

Revision ID: 0c3eb026efa0
Revises: 1ec937c2466e
Create Date: 2025-06-04 08:48:56.728321

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '0c3eb026efa0'
down_revision = '1ec937c2466e'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TYPE state RENAME TO state_old")

    state_new = postgresql.ENUM('ACTIVE', 'HISTORICAL', name='state')
    state_new.create(op.get_bind(), checkfirst=True)

    op.execute("ALTER TABLE businesses ALTER COLUMN state TYPE state USING state::text::state")
    op.execute("ALTER TABLE businesses_version ALTER COLUMN state TYPE state USING state::text::state")
    op.execute("ALTER TABLE businesses_bak ALTER COLUMN state TYPE state USING state::text::state")

    op.execute("DROP TYPE state_old")


def downgrade():
    op.execute("ALTER TYPE state ADD VALUE 'LIQUIDATION'")
