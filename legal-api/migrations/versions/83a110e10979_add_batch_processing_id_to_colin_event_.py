"""add_batch_processing_id_to_colin_event_ids

Revision ID: 83a110e10979
Revises: d55dfc5c1358
Create Date: 2024-10-07 15:34:55.319366

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '83a110e10979'
down_revision = 'd55dfc5c1358'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('colin_event_ids', sa.Column('batch_processing_id', sa.Integer(), nullable=True))
    op.add_column('colin_event_ids', sa.Column('batch_processing_step', sa.Enum('WARNING_LEVEL_1', 'WARNING_LEVEL_2', 'DISSOLUTION', name='batch_processing_step'), nullable=True))
    op.create_foreign_key('colin_event_ids_batch_processing_id_fkey', 'colin_event_ids', 'batch_processing', ['batch_processing_id'], ['id'])


def downgrade():
    op.drop_constraint('colin_event_ids_batch_processing_id_fkey', 'colin_event_ids', type_='foreignkey')
    op.drop_column('colin_event_ids', 'batch_processing_id')
    op.drop_column('colin_event_ids', 'batch_processing_step')
