"""add_sbc_finance_staff_role

Revision ID: 7ab9e063925f
Revises: a230afde0a28
Create Date: 2026-11-20 09:29:53.000000

"""
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '7ab9e063925f'
down_revision = 'a230afde0a28'
branch_labels = None
depends_on = None

PERMISSION_NAMES = [
    'DOCUMENT_RECORDS',
    'MANAGE_BUSINESS',
    'MANAGE_NR',
    'MANAGE_OTHER_ORGANIZATION',
    'MANAGE_SOCIETY',
    'SEARCH_BUSINESS_NR',
    'STAFF_BREADCRUMBS',
]


def upgrade():
    now = datetime.now(UTC)

    authorized_roles = sa.table(
        'authorized_roles',
        sa.column('role_name', sa.String),
        sa.column('created_date', sa.TIMESTAMP(timezone=True)),
        sa.column('last_modified', sa.TIMESTAMP(timezone=True)),
        sa.column('created_by_id', sa.Integer),
        sa.column('modified_by_id', sa.Integer)
    )

    op.bulk_insert(
        authorized_roles,
        [{
            'role_name': 'sbc_finance_staff',
            'created_date': now,
            'last_modified': now,
            'created_by_id': None,
            'modified_by_id': None
        }]
    )

    bind = op.get_bind()

    role_id = bind.execute(
        sa.text("SELECT id FROM authorized_roles WHERE role_name = 'sbc_finance_staff'")
    ).mappings().first()['id']

    permission_map = {p[1]: p[0] for p in bind.execute(sa.text('SELECT id, permission_name FROM permissions'))}
    permission_ids = [permission_map[name] for name in PERMISSION_NAMES]

    authorized_role_permissions = sa.table(
        'authorized_role_permissions',
        sa.column('role_id', sa.Integer),
        sa.column('permission_id', sa.Integer),
        sa.column('created_date', sa.TIMESTAMP(timezone=True)),
        sa.column('last_modified', sa.TIMESTAMP(timezone=True)),
        sa.column('created_by_id', sa.Integer),
        sa.column('modified_by_id', sa.Integer)
    )

    op.bulk_insert(
        authorized_role_permissions,
        [
            {
                'role_id': role_id,
                'permission_id': permission_id,
                'created_date': now,
                'last_modified': now,
                'created_by_id': None,
                'modified_by_id': None
            }
            for permission_id in permission_ids
        ]
    )


def downgrade():
    op.execute(
        "DELETE FROM authorized_role_permissions WHERE role_id = "
        "(SELECT id FROM authorized_roles WHERE role_name = 'sbc_finance_staff')"
    )
    op.execute("DELETE FROM authorized_roles WHERE role_name = 'sbc_finance_staff'")