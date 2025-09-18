"""add_officer_change_filing_permission

Revision ID: 9883916ba68f
Revises: b42a474558f0
Create Date: 2025-09-11 12:29:13.950563

"""
from datetime import datetime, timezone
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9883916ba68f'
down_revision = 'b42a474558f0'
branch_labels = None
depends_on = None


def upgrade():
    now = datetime.now(timezone.utc)

    permissions = sa.table(
        'permissions',
        sa.column('id', sa.Integer),
        sa.column('permission_name', sa.String),
        sa.column('description', sa.String),
        sa.column('created_date', sa.TIMESTAMP(timezone=True)),
        sa.column('last_modified', sa.TIMESTAMP(timezone=True)),
        sa.column('created_by_id', sa.Integer),
        sa.column('modified_by_id', sa.Integer)
    )

    op.bulk_insert(
        permissions,
        [{
            'permission_name': 'OFFICER_CHANGE_FILING',
            'description': 'Authorized to access Change of Officer filing.',
            'created_date': now,
            'last_modified': now,
            'created_by_id': None,
            'modified_by_id': None
        }]
    )

    bind = op.get_bind()

    roles = bind.execute(sa.text("SELECT id, role_name FROM authorized_roles")).mappings().all()
    role_map = {r['role_name']: r['id'] for r in roles}

    permission = bind.execute(
        sa.text("SELECT id FROM permissions WHERE permission_name = 'OFFICER_CHANGE_FILING'")
    ).mappings().first()
    permission_id = permission['id']

    authorized_role_permissions = sa.table(
        'authorized_role_permissions',
        sa.column('role_id', sa.Integer),
        sa.column('permission_id', sa.Integer),
        sa.column('created_date', sa.TIMESTAMP(timezone=True)),
        sa.column('last_modified', sa.TIMESTAMP(timezone=True)),
        sa.column('created_by_id', sa.Integer),
        sa.column('modified_by_id', sa.Integer)
    )

    role_permission_list = [
        {
            'role_id': role_id,
            'permission_id': permission_id,
            'created_date': now,
            'last_modified': now,
            'created_by_id': None,
            'modified_by_id': None
        }
        for role_id in role_map.values()
    ]

    op.bulk_insert(authorized_role_permissions, role_permission_list)


def downgrade():
    bind = op.get_bind()

    permission = bind.execute(
        sa.text("SELECT id FROM permissions WHERE permission_name = 'OFFICER_CHANGE_FILING'")
    ).mappings().first()
    if permission:
        permission_id = permission['id']

        op.execute(
            sa.text("DELETE FROM authorized_role_permissions WHERE permission_id = :pid").bindparams(pid=permission_id)
        )

        op.execute(
            sa.text("DELETE FROM permissions WHERE id = :pid").bindparams(pid=permission_id)
        )
