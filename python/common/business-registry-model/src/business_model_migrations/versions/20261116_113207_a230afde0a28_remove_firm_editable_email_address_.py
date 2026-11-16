"""remove_firm_editable_email_address_permission

Revision ID: a230afde0a28
Revises: d5aae4f4e64d
Create Date: 2026-11-16 11:32:07.427742

"""
from datetime import UTC, datetime

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a230afde0a28'
down_revision = 'd5aae4f4e64d'
branch_labels = None
depends_on = None

PERMISSION_NAME = 'FIRM_EDITABLE_EMAIL_ADDRESS'
PERMISSION_DESCRIPTION = 'Authorized to edit email address (in Registration filing).'
ROLES_WITH_PERMISSION = ['sbc_staff', 'staff']


def upgrade():
    # Remove role mappings first (FK to permissions)
    op.execute(
        sa.text("""
            DELETE FROM authorized_role_permissions
            WHERE permission_id = (
                SELECT id FROM permissions WHERE permission_name = :name
            )
        """).bindparams(name=PERMISSION_NAME)
    )

    # Then remove the permission itself
    op.execute(
        sa.text("DELETE FROM permissions WHERE permission_name = :name")
        .bindparams(name=PERMISSION_NAME)
    )


def downgrade():
    now = datetime.now(UTC)
    bind = op.get_bind()

    bind.execute(
        sa.text("""
            INSERT INTO permissions
                (permission_name, description, created_date, last_modified)
            VALUES (:name, :description, :now, :now)
        """),
        {'name': PERMISSION_NAME, 'description': PERMISSION_DESCRIPTION, 'now': now},
    )

    for role in ROLES_WITH_PERMISSION:
        bind.execute(
            sa.text("""
                INSERT INTO authorized_role_permissions
                    (role_id, permission_id, created_date, last_modified)
                SELECT r.id, p.id, :now, :now
                FROM authorized_roles r, permissions p
                WHERE r.role_name = :role AND p.permission_name = :name
            """),
            {'role': role, 'name': PERMISSION_NAME, 'now': now},
        )
