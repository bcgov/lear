"""empty message

Revision ID: bc62c64eeaab
Revises: b5ded56cab5b
Create Date: 2026-06-26 09:33:49.399745

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'bc62c64eeaab'
down_revision = 'b5ded56cab5b'
branch_labels = None
depends_on = None

enum_name = "commenttype"
enum_values = ["FILING", "STAFF"]
user_role_enum = sa.Enum(*enum_values, name=enum_name)

def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(f"CREATE TYPE {enum_name} AS ENUM ({', '.join([f"'{v}'" for v in enum_values])})")

    with op.batch_alter_table('comments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('comment_type', user_role_enum, nullable=True))

    op.execute("UPDATE comments SET comment_type = 'STAFF' WHERE comment_type IS NULL")

    with op.batch_alter_table('comments', schema=None) as batch_op:
        batch_op.alter_column('comment_type', existing_type=user_role_enum, nullable=False)


def downgrade():
    with op.batch_alter_table('comments', schema=None) as batch_op:
        batch_op.drop_column('comment_type')

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(f"DROP TYPE {enum_name}")
