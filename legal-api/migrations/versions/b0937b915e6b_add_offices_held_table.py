"""“add_offices_held_table”

Revision ID: b0937b915e6b
Revises: ad21c1ed551e
Create Date: 2025-02-28 14:30:31.105670

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'b0937b915e6b'
down_revision = 'ad21c1ed551e'
branch_labels = None
depends_on = None

titles_enum = postgresql.ENUM('CEO', 'CFO', 'CHAIR', 'OTHER_OFFICES', 'TREASURER', 'VICE_PRESIDENT',
                              'PRESIDENT', 'SECRETARY', 'ASSISTANT_SECRETARY',
                              name='titles_enum')

def upgrade():
    titles_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'offices_held',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('party_role_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['party_role_id'], ['party_roles.id']),
        sa.PrimaryKeyConstraint('id'))

    op.add_column('offices_held', sa.Column('title', titles_enum, nullable=False))

    op.create_table(
        'offices_held_version',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('party_role_id', sa.Integer(), nullable=False),
        sa.Column('transaction_id', sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column('end_transaction_id', sa.BigInteger(), nullable=True),
        sa.Column('operation_type', sa.SmallInteger(), nullable=False),
        sa.ForeignKeyConstraint(['party_role_id'], ['party_roles.id']),
        sa.PrimaryKeyConstraint('id', 'transaction_id')
    )

    op.add_column('offices_held_version', sa.Column('title', titles_enum, nullable=False))


def downgrade():
    op.drop_table('offices_held_version')
    op.drop_table('offices_held')
    titles_enum.drop(op.get_bind(), checkfirst=True)


