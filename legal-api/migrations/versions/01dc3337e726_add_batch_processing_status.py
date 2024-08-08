"""add_batch_processing_status

Revision ID: 01dc3337e726
Revises: a31cb1eb4b6b
Create Date: 2024-08-08 08:57:36.395684

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '01dc3337e726'
down_revision = 'a31cb1eb4b6b'
branch_labels = None
depends_on = None

old_options = ('HOLD', 'PROCESSING', 'WITHDRAWN', 'COMPLETED', 'ERROR')
new_otions = sorted(old_options + ('QUEUED',))

old_type = sa.Enum(*old_options, name='batch_processing_status')
new_type = sa.Enum(*new_otions, name='batch_processing_status')

def upgrade():
    op.execute('ALTER TYPE batch_processing_status RENAME TO tmp_batch_processing_status')
    new_type.create(op.get_bind())
    op.execute('ALTER TABLE batch_processing ALTER COLUMN status TYPE batch_processing_status USING status::text::batch_processing_status')
    op.execute('DROP TYPE tmp_batch_processing_status')


def downgrade():
    # Need to convert any existing QUEUED statuses to PROCESSING
    op.execute('UPDATE batch_processing SET status = "PROCESSED" WHERE status = "QUEUED"')
    op.execute('ALTER TYPE batch_processing_status RENAME TO tmp_batch_processing_status')
    old_type.create(op.get_bind())
    op.execute('ALTER TABLE batch_processing ALTER COLUMN status TYPE batch_processing_status USING status::text::batch_processing_status')
    op.execute('DROP TYPE tmp_batch_processing_status')
