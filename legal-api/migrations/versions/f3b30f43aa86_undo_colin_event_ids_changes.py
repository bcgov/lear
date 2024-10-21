"""Undo colin_event_ids changes.

Revision ID: f3b30f43aa86
Revises: 698885b80fc0
Create Date: 2024-10-21 11:09:24.413272

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f3b30f43aa86'
down_revision = '698885b80fc0'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint('colin_event_ids_batch_processing_id_fkey', 'colin_event_ids', type_='foreignkey')
    op.drop_column('colin_event_ids', 'batch_processing_id')
    op.drop_column('colin_event_ids', 'batch_processing_step')

def downgrade():
    op.add_column('colin_event_ids', sa.Column('batch_processing_id', sa.Integer(), nullable=True))
    op.add_column('colin_event_ids', sa.Column('batch_processing_step', sa.Enum(name='batch_processing_step'), nullable=True))
    op.create_foreign_key('colin_event_ids_batch_processing_id_fkey', 'colin_event_ids', 'batch_processing', ['batch_processing_id'], ['id'])
