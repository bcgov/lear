"""add party class model

Revision ID: 1dd76abf128a
Revises: 957a67bde783
Create Date: 2025-06-06 15:52:44.732128

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import MetaData, Table

# revision identifiers, used by Alembic.
revision = '1dd76abf128a'
down_revision = '957a67bde783'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('party_class',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('class_type', sa.Enum('ATTORNEY', 'AGENT', 'DIRECTOR', 'OFFICER', name='partyclasstype'), nullable=False),
    sa.Column('short_description', sa.String(length=512), nullable=True),
    sa.Column('full_description', sa.String(length=1024), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('class_type')
    )

    op.create_table('party_class_version',
    sa.Column('id', sa.Integer(), autoincrement=False, nullable=False),
    sa.Column('class_type', sa.Enum('ATTORNEY', 'AGENT', 'DIRECTOR', 'OFFICER', name='partyclasstype'), autoincrement=False, nullable=False),
    sa.Column('short_description', sa.String(length=512), autoincrement=False, nullable=True),
    sa.Column('full_description', sa.String(length=1024), autoincrement=False, nullable=True),
    sa.Column('transaction_id', sa.BigInteger(), autoincrement=False, nullable=False),
    sa.Column('end_transaction_id', sa.BigInteger(), nullable=True),
    sa.Column('operation_type', sa.SmallInteger(), nullable=False),
    sa.PrimaryKeyConstraint('id', 'transaction_id')
    )
    op.create_index(op.f('ix_party_class_version_end_transaction_id'), 'party_class_version', ['end_transaction_id'], unique=False)
    op.create_index(op.f('ix_party_class_version_operation_type'), 'party_class_version', ['operation_type'], unique=False)
    op.create_index(op.f('ix_party_class_version_transaction_id'), 'party_class_version', ['transaction_id'], unique=False)
    

    op.add_column('party_roles', sa.Column('party_class_type', sa.Enum('ATTORNEY', 'AGENT', 'DIRECTOR', 'OFFICER', name='partyclasstype'), nullable=True))
    
    op.create_foreign_key(None, 'party_roles', 'party_class', ['party_class_type'], ['class_type'])
    op.add_column('party_roles_version', sa.Column('party_class_type', sa.Enum('ATTORNEY', 'AGENT', 'DIRECTOR', 'OFFICER', name='partyclasstype'), autoincrement=False, nullable=True))
    

    # add default party classes
    bind = op.get_bind()
    meta = MetaData()
    party_class_table = Table('party_class', meta, autoload_with=bind)

    op.bulk_insert(
        party_class_table,
        [
            {
                'class_type': 'ATTORNEY',
                'short_description': 'TBD',
                'full_description': 'TBD'
            },
            {
                'class_type': 'AGENT',
                'short_description': 'TBD',
                'full_description': 'TBD'
            },
            {
                'class_type': 'DIRECTOR',
                'short_description': 'TBD',
                'full_description': 'TBD'
            },
            {
                'class_type': 'OFFICER',
                'short_description': 'TBD',
                'full_description': 'TBD'
            }
        ]
    )


def downgrade():
    op.drop_column('party_roles_version', 'party_class_type')
    
    op.drop_constraint(None, 'party_roles', type_='foreignkey')
    op.drop_column('party_roles', 'party_class_type')
    
    op.drop_table('party_class_version')
    op.drop_table('party_class')
    # ### end Alembic commands ###
