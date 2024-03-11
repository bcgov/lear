"""amalgamation

Revision ID: 5238dd8fb805
Revises: 60d9c14c2b7f
Create Date: 2023-12-13 16:28:23.390151

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '5238dd8fb805'
down_revision = '60d9c14c2b7f'
branch_labels = None
depends_on = None

role_enum = postgresql.ENUM('amalgamating', 'holding', 'primary', name='amalgamating_business_role')
amalgamation_type_enum = postgresql.ENUM('regular',
                                         'vertical',
                                         'horizontal',
                                         name='amalgamation_type')


def upgrade():

    # add enum values
    role_enum.create(op.get_bind(), checkfirst=True)
    amalgamation_type_enum.create(op.get_bind(), checkfirst=True)

    # ==========================================================================================
    # amalgamating_businesses/amalgamations/amalgamations_history/amalgamating_businesses_history tables
    # ==========================================================================================

    op.create_table(
        'amalgamations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('legal_entity_id', sa.Integer(), nullable=False),
        sa.Column('filing_id', sa.Integer(), nullable=False),
        sa.Column('amalgamation_date', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('court_approval', sa.Boolean(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['filing_id'], ['filings.id']),
        sa.ForeignKeyConstraint(['legal_entity_id'], ['legal_entities.id']),
        sa.PrimaryKeyConstraint('id'),
        sqlite_autoincrement=True,
    )

    # enum added after creating table as DuplicateObject error would be thrown otherwise
    op.add_column('amalgamations', sa.Column('amalgamation_type', amalgamation_type_enum, nullable=False))

    op.create_table(
        'amalgamating_businesses',
        sa.Column('id', sa.Integer(), primary_key=False),
        sa.Column('legal_entity_id', sa.Integer(), nullable=True),
        sa.Column('amalgamation_id', sa.Integer(), nullable=False),
        sa.Column('foreign_jurisdiction', sa.String(length=10), nullable=True),
        sa.Column('foreign_jurisdiction_region', sa.String(length=10), nullable=True),
        sa.Column('foreign_name', sa.String(length=100), nullable=True),
        sa.Column('foreign_identifier', sa.String(length=50), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('filing_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['legal_entity_id'], ['legal_entities.id']),
        sa.ForeignKeyConstraint(['amalgamation_id'], ['amalgamations.id']),
        sa.ForeignKeyConstraint(['filing_id'], ['filings.id']),
        sa.PrimaryKeyConstraint('id'),
        sqlite_autoincrement=True,
    )

    # enum added after creating table as DuplicateObject error would be thrown otherwise
    op.add_column('amalgamating_businesses', sa.Column('role', role_enum, nullable=False))
    
    with op.batch_alter_table('amalgamating_businesses', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_amalgamating_businesses_filing_id'), ['filing_id'], unique=False)
    
    op.create_table(
        'amalgamations_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('legal_entity_id', sa.Integer(), nullable=False),
        sa.Column('filing_id', sa.Integer(), nullable=False),
        sa.Column('amalgamation_date', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('court_approval', sa.Boolean(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('changed', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['filing_id'], ['filings.id']),
        sa.ForeignKeyConstraint(['legal_entity_id'], ['legal_entities.id']),
        sa.PrimaryKeyConstraint('id', 'version'),
        sqlite_autoincrement=True,
    )
    
    # enum added after creating table as DuplicateObject error would be thrown otherwise
    op.add_column('amalgamations_history', sa.Column('amalgamation_type', amalgamation_type_enum, nullable=False))
    
    with op.batch_alter_table('amalgamations_history', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_amalgamations_version_history_legal_entity_id'), ['legal_entity_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_amalgamations_version_history_filing_id'), ['filing_id'], unique=False)

    
    op.create_table(
        'amalgamating_businesses_history',
        sa.Column('id', sa.Integer(), primary_key=False),
        sa.Column('legal_entity_id', sa.Integer(), nullable=True),
        sa.Column('amalgamation_id', sa.Integer(), nullable=False),
        sa.Column('foreign_jurisdiction', sa.String(length=10), nullable=True),
        sa.Column('foreign_jurisdiction_region', sa.String(length=10), nullable=True),
        sa.Column('foreign_name', sa.String(length=100), nullable=True),
        sa.Column('foreign_identifier', sa.String(length=50), nullable=True),
        sa.Column('filing_id', sa.Integer(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('changed', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['legal_entity_id'], ['legal_entities.id']),
        sa.ForeignKeyConstraint(['filing_id'], ['filings.id']),
        sa.PrimaryKeyConstraint('id', 'version')
    )
    
    # enum added after creating table as DuplicateObject error would be thrown otherwise
    op.add_column('amalgamating_businesses_history', sa.Column('role', role_enum, nullable=False))
    
    with op.batch_alter_table('amalgamating_businesses_history', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_amalgamating_businesses_history_legal_entity_id'), ['legal_entity_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_amalgamating_businesses_history_amalgamation_id'), ['amalgamation_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_amalgamating_businesses_history_filing_id'), ['filing_id'], unique=False)

def downgrade():
    op.drop_table('amalgamating_businesses')
    op.drop_table('amalgamations')
    op.drop_table('amalgamating_businesses_history')
    op.drop_table('amalgamations_history')

    # Drop enum types from the database
    amalgamation_type_enum.drop(op.get_bind(), checkfirst=True)
    role_enum.drop(op.get_bind(), checkfirst=True)
