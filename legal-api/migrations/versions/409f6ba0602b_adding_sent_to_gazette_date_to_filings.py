"""empty message

Revision ID: 409f6ba0602b
Revises: b6997f07700a
Create Date: 2021-10-18 09:24:33.473531

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '409f6ba0602b'
down_revision = 'b6997f07700a'
branch_labels = None
depends_on = None


def upgrade():    
    op.add_column('filings', sa.Column('sent_to_gazette_date', sa.DateTime(timezone=True), nullable=True))
    

def downgrade():    
    op.drop_column('filings', 'sent_to_gazette_date')
    