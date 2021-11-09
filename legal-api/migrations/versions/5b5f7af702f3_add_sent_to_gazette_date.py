"""add_sent_to_gazette_date

Revision ID: 5b5f7af702f3
Revises: 3d8eb786f4c2
Create Date: 2021-11-05 14:59:54.099716

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5b5f7af702f3'
down_revision = '3d8eb786f4c2'
branch_labels = None
depends_on = None


def upgrade():    
    op.add_column('filings', sa.Column('sent_to_gazette_date', sa.DateTime(timezone=True), nullable=True))
    

def downgrade():    
    op.drop_column('filings', 'sent_to_gazette_date')
