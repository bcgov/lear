"""ar_reminder_opt_out

Revision ID: edbd0f6ef10e
Revises: 7efd0c42babd
Create Date: 2026-02-17 22:21:38.643521

"""
from datetime import datetime, timezone
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'edbd0f6ef10e'
down_revision = '7efd0c42babd'
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
            'permission_name': 'AR_REMINDER_OPT_OUT',
            'description': 'Authorized to access Opt out ar reminder option.',
            'created_date': now,
            'last_modified': now,
            'created_by_id': None,
            'modified_by_id': None
        }]
    )

    bind = op.get_bind()

    roles = bind.execute(sa.text("SELECT id, role_name FROM authorized_roles where role_name in ('sbc_staff', 'staff', 'public_user')")).mappings().all()
    role_map = {r['role_name']: r['id'] for r in roles}

    permission = bind.execute(
        sa.text("SELECT id FROM permissions WHERE permission_name = 'AR_REMINDER_OPT_OUT'")
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
        sa.text("SELECT id FROM permissions WHERE permission_name = 'AR_REMINDER_OPT_OUT'")
    ).mappings().first()
    if permission:
        permission_id = permission['id']

        op.execute(
            sa.text("DELETE FROM authorized_role_permissions WHERE permission_id = :pid").bindparams(pid=permission_id)
        )

        op.execute(
            sa.text("DELETE FROM permissions WHERE id = :pid").bindparams(pid=permission_id)
        )
