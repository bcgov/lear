"""misc_configurations_table_updates

Revision ID: 508c7466b2af
Revises: 8bd6dc383c96
Create Date: 2024-05-15 17:12:22.298255

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '508c7466b2af'
down_revision = '8bd6dc383c96'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""UPDATE configurations
               SET val = 600
               WHERE name = 'MAX_DISSOLUTIONS_ALLOWED'
               """)
    op.execute("""UPDATE configurations
               SET name = 'DISSOLUTIONS_STAGE_1_SCHEDULE',
                   val = '0 0 * * 2-4'
               WHERE name = 'NEW_DISSOLUTIONS_SCHEDULE'
               """)
    op.execute("""INSERT INTO configurations (name, val, short_description, full_description) VALUES
               ('DISSOLUTIONS_STAGE_2_SCHEDULE', '0 0 * * 1', 'Schedule for running stage 2 of dissolution process.', 'Schedule for running stage 2 of dissolution process.'),
               ('DISSOLUTIONS_STAGE_3_SCHEDULE', '0 0 * * 1', 'Schedule for running stage 3 of dissolution process.', 'Schedule for running stage 3 of dissolution process.'),
               ('DISSOLUTIONS_SUMMARY_EMAIL', '', 'Email address used to send dissolution summary to BA inbox.', 'Email address used to send dissolution summary to BA inbox.')
               """)



def downgrade():
    op.execute("""UPDATE configurations
               SET val = 2000
               WHERE name = 'MAX_DISSOLUTIONS_ALLOWED'
               """)
    op.execute("""UPDATE configurations
               SET name = 'NEW_DISSOLUTIONS_SCHEDULE',
                   val = '0 0 * * *'
               WHERE name = 'DISSOLUTIONS_STAGE_1_SCHEDULE'
               """)
    op.execute("""DELETE FROM configurations
               WHERE name IN ('DISSOLUTIONS_STAGE_2_SCHEDULE', 'DISSOLUTIONS_STAGE_3_SCHEDULE', 'DISSOLUTIONS_SUMMARY_EMAIL')
               """)
