"""empty message

Revision ID: 5238dd8fb805
Revises: 6e28f267db2a
Create Date: 2023-12-13 16:28:23.390151

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '5238dd8fb805'
down_revision = '6e28f267db2a'
branch_labels = None
depends_on = None

role_enum = postgresql.ENUM('AMALGAMATING', 'HOLDING', name='amalgamating_business_role')
amalgamation_type_enum = postgresql.ENUM('regular',
                                         'vertical',
                                         'horizontal',
                                         name='amalgamation_type')

def upgrade():
    
    
    # ==========================================================================================
    # amalgamating_business/amalgamation tables
    # ==========================================================================================
    
    
    op.create_table(
        
        'amalgamating_business',
        
        sa.Column('id', sa.Integer(), primary_key=True),
        
        sa.Column('business_id', sa.Integer(), nullable=False),
        
        sa.Column('amalgamation_id', sa.Integer(), nullable=False),
        
        sa.Column('foreign_jurisdiction', sa.String(length=10), nullable=True),
        
        sa.Column('foreign_name', sa.String(length=100), nullable=True),
        
        sa.Column('foreign_corp_num', sa.String(length=50), nullable=True),
        
        sa.ForeignKeyConstraint(['business_id'], ['business.id']),
        
        sa.ForeignKeyConstraint(['amalgamation_id'], ['amalgamation.id']),
        
        sa.PrimaryKeyConstraint('id'))
    
    # enum added after creating table as DuplicateObject error would be thrown otherwise
    op.add_column('amalgamating_business', sa.Column('role', role_enum, nullable=False))
    

    op.create_table(
        
        'amalgamation',
        
        sa.Column('id', sa.Integer(), autoincrement=False, nullable=False),
        
        sa.Column('business_id', sa.Integer(), autoincrement=False, nullable=True),
        
        sa.Column('filing_id', sa.Integer(), autoincrement=False, nullable=True),
        
        sa.Column('amalgamation_date', sa.TIMESTAMP(timezone=True), nullable=False),
        
        sa.Column('court_approval', sa.Boolean(), nullable=True),
        
        sa.ForeignKeyConstraint(['filing_id'], ['filings.id']),
        
        sa.ForeignKeyConstraint(['business_id'], ['business.id']),
        
        sa.PrimaryKeyConstraint('id'))
    
    # enum added after creating table as DuplicateObject error would be thrown otherwise
    op.add_column('amalgamation', sa.Column('amalgamation_type', amalgamation_type_enum, nullable=False))
        

def downgrade():
    
    op.drop_table('amalgamation')
    
    op.drop_table('amalgamating_business')
    
    amalgamation_type_enum.drop(op.get_bind())
    
    role_enum.drop(op.get_bind())
    
