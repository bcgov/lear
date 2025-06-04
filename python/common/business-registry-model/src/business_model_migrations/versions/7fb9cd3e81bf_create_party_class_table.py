"""create-party-class-table-and-relationship

Revision ID: 7fb9cd3e81bf
Revises: 5de1cfc78599
Create Date: 2025-06-03 13:10:28.750570

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '7fb9cd3e81bf'
down_revision = '5de1cfc78599'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('party_class',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('class_type', sa.Enum('ATTORNEY', 'AGENT', 'DIRECTOR', 'OFFICER', name='partyclasstype'), nullable=False),
    sa.Column('short_description', sa.String(length=512), nullable=False),
    sa.Column('full_description', sa.String(length=1024), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('class_type')
    )

    op.create_table('party_class_version',
    sa.Column('id', sa.Integer(), autoincrement=False, nullable=False),
    sa.Column('class_type', sa.Enum('ATTORNEY', 'AGENT', 'DIRECTOR', 'OFFICER', name='partyclasstype'), nullable=False),
    sa.Column('short_description', sa.String(length=512), autoincrement=False, nullable=False),
    sa.Column('full_description', sa.String(length=1024), autoincrement=False, nullable=False),
    sa.Column('transaction_id', sa.BigInteger(), autoincrement=False, nullable=False),
    sa.Column('end_transaction_id', sa.BigInteger(), nullable=True),
    sa.Column('operation_type', sa.SmallInteger(), nullable=False),
    sa.PrimaryKeyConstraint('id', 'transaction_id')
    )
    op.create_index(op.f('ix_party_class_version_end_transaction_id'), 'party_class_version', ['end_transaction_id'], unique=False)
    op.create_index(op.f('ix_party_class_version_operation_type'), 'party_class_version', ['operation_type'], unique=False)
    op.create_index(op.f('ix_party_class_version_transaction_id'), 'party_class_version', ['transaction_id'], unique=False)
    
    with op.batch_alter_table('party_roles', schema=None) as batch_op:
        batch_op.add_column(sa.Column('party_class_type', sa.Enum('ATTORNEY', 'AGENT', 'DIRECTOR', 'OFFICER', name='partyclasstype'), nullable=True))
        batch_op.create_foreign_key(None, 'party_class', ['party_class_type'], ['class_type'])

    with op.batch_alter_table('party_roles_version', schema=None) as batch_op:
        batch_op.add_column(sa.Column('party_class_type', sa.Enum('ATTORNEY', 'AGENT', 'DIRECTOR', 'OFFICER', name='partyclasstype'), nullable=True))    

    # ### end Alembic commands ###


def downgrade():
    with op.batch_alter_table('party_roles_version', schema=None) as batch_op:
        batch_op.drop_column('party_class_type')

    with op.batch_alter_table('party_roles', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_column('party_class_type')

    op.drop_table('party_class')
    op.drop_table('party_class_version')
    # ### end Alembic commands ###
