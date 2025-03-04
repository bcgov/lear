"""modify_data_type_for_max_shares

Revision ID: f1d010259785
Revises: b0937b915e6b
Create Date: 2025-02-28 22:29:38.543965

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'f1d010259785'
down_revision = 'b0937b915e6b'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('ALTER TABLE share_classes ALTER COLUMN max_shares TYPE NUMERIC(20) USING max_shares::NUMERIC(20);')
    op.execute('ALTER TABLE share_series ALTER COLUMN max_shares TYPE NUMERIC(20) USING max_shares::NUMERIC(20);')

    op.execute('ALTER TABLE share_classes_version ALTER COLUMN max_shares TYPE NUMERIC(20) USING max_shares::NUMERIC(20);')
    op.execute('ALTER TABLE share_series_version ALTER COLUMN max_shares TYPE NUMERIC(20) USING max_shares::NUMERIC(20);')


def downgrade():
    op.execute("UPDATE share_classes SET max_shares = 2147483647 WHERE max_shares > 2147483647;")
    op.execute("UPDATE share_classes SET max_shares = -2147483648 WHERE max_shares < -2147483648;")
    op.execute("UPDATE share_classes_version SET max_shares = 2147483647 WHERE max_shares > 2147483647;")
    op.execute("UPDATE share_classes_version SET max_shares = -2147483648 WHERE max_shares < -2147483648;")

    op.execute("UPDATE share_series SET max_shares = 2147483647 WHERE max_shares > 2147483647;")
    op.execute("UPDATE share_series SET max_shares = -2147483648 WHERE max_shares < -2147483648;")
    op.execute("UPDATE share_series_version SET max_shares = 2147483647 WHERE max_shares > 2147483647;")
    op.execute("UPDATE share_series_version SET max_shares = -2147483648 WHERE max_shares < -2147483648;")

    op.execute("ALTER TABLE share_classes ALTER COLUMN max_shares TYPE INTEGER USING max_shares::INTEGER;")
    op.execute("ALTER TABLE share_series ALTER COLUMN max_shares TYPE INTEGER USING max_shares::INTEGER;")
    op.execute("ALTER TABLE share_classes_version ALTER COLUMN max_shares TYPE INTEGER USING max_shares::INTEGER;")
    op.execute("ALTER TABLE share_series_version ALTER COLUMN max_shares TYPE INTEGER USING max_shares::INTEGER;")


