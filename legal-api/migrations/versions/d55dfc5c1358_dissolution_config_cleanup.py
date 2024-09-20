"""dissolution_config_cleanup

Revision ID: d55dfc5c1358
Revises: 7d486343384b
Create Date: 2024-09-10 14:50:01.802155

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd55dfc5c1358'
down_revision = '7d486343384b'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""DELETE FROM configurations
               WHERE name IN ('DISSOLUTIONS_ON_HOLD', 'DISSOLUTIONS_SUMMARY_EMAIL')
               """)


def downgrade():
    op.execute("""INSERT INTO configurations (name, val, short_description, full_description) VALUES
               ('DISSOLUTIONS_ON_HOLD', 'False', 'Flag to put all dissolution processes on hold.', 'Flag to put all dissolution processes on hold.'),
               ('DISSOLUTIONS_SUMMARY_EMAIL', 'test12@no-reply.com', 'Email address used to send dissolution summary to BA inbox.', 'Email address used to send dissolution summary to BA inbox.')
               """)
