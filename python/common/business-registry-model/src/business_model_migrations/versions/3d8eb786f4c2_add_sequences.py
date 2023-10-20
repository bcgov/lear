"""add_coop_sequence

Revision ID: 3d8eb786f4c2
Revises: b6997f07700a
Create Date: 2021-10-24 14:45:58.533628

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3d8eb786f4c2'
down_revision = '2b08acebfed5'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE SEQUENCE legal_entity_identifier_coop START 1002395")
    op.execute("CREATE SEQUENCE legal_entity_identifier_sp_gp START 1002395")
    op.execute("CREATE SEQUENCE legal_entity_identifier_person START 0000001")


def downgrade():
    op.execute("DROP SEQUENCE legal_entity_identifier_coop")
    op.execute("DROP SEQUENCE legal_entity_identifier_sp_gp")
    op.execute("DROP SEQUENCE legal_entity_identifier_person")
