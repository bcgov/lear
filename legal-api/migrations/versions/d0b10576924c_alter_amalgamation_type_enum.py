"""alter_amalgamation_type_enum

Revision ID: d0b10576924c
Revises: d9254d3cbbf4
Create Date: 2025-02-03 21:47:05.061172

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'd0b10576924c'
down_revision = 'd9254d3cbbf4'
branch_labels = None
depends_on = None


amalgamation_type_old_enum = postgresql.ENUM('regular',
                                         'vertical',
                                         'horizontal',
                                         name='amalgamation_type_old')


def upgrade():
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE amalgamation_type ADD VALUE 'unknown'")


def downgrade():
    op.execute("UPDATE amalgamations SET amalgamation_type = 'regular' WHERE amalgamation_type = 'unknown'")
    op.execute("UPDATE amalgamations_version SET amalgamation_type = 'regular' WHERE amalgamation_type = 'unknown'")

    amalgamation_type_old_enum.create(op.get_bind(), checkfirst=True)

    op.execute("""
        ALTER TABLE amalgamations
        ALTER COLUMN amalgamation_type
        TYPE amalgamation_type_old
        USING amalgamation_type::text::amalgamation_type_old
    """)
    op.execute("""
        ALTER TABLE amalgamations_version
        ALTER COLUMN amalgamation_type
        TYPE amalgamation_type_old
        USING amalgamation_type::text::amalgamation_type_old
    """)

    op.execute("DROP TYPE amalgamation_type")
    op.execute("ALTER TYPE amalgamation_type_old RENAME TO amalgamation_type")
