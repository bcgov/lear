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
    # amalgamating_business/amalgamation tables
    # ==========================================================================================

    op.create_table(
        'amalgamation',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('legal_entity_id', sa.Integer(), nullable=False),
        sa.Column('filing_id', sa.Integer(), nullable=False),
        sa.Column('amalgamation_date', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('court_approval', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['filing_id'], ['filings.id']),
        sa.ForeignKeyConstraint(['legal_entity_id'], ['legal_entitites.id']),
        sa.PrimaryKeyConstraint('id'))

    # enum added after creating table as DuplicateObject error would be thrown otherwise
    op.add_column('amalgamation', sa.Column('amalgamation_type', amalgamation_type_enum, nullable=False))

    op.create_table(
        'amalgamating_business',
        sa.Column('id', sa.Integer(), primary_key=False),
        sa.Column('legal_entity_id', sa.Integer(), nullable=True),
        sa.Column('amalgamation_id', sa.Integer(), nullable=False),
        sa.Column('foreign_jurisdiction', sa.String(length=10), nullable=True),
        sa.Column('foreign_jurisdiction_region', sa.String(length=10), nullable=True),
        sa.Column('foreign_name', sa.String(length=100), nullable=True),
        sa.Column('foreign_corp_num', sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(['legal_entity_id'], ['legal_entitites.id']),
        sa.ForeignKeyConstraint(['amalgamation_id'], ['amalgamation.id']),
        sa.PrimaryKeyConstraint('id'))

    # enum added after creating table as DuplicateObject error would be thrown otherwise
    op.add_column('amalgamating_business', sa.Column('role', role_enum, nullable=False))


def downgrade():
    op.drop_table('amalgamating_business')
    op.drop_table('amalgamation')

    # Drop enum types from the database
    amalgamation_type_enum.drop(op.get_bind(), checkfirst=True)
    role_enum.drop(op.get_bind(), checkfirst=True)
