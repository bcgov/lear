"""add_review_imported_data_filing_permission

Revision ID: 78ce7f82c239
Revises: c4e7b2a95d18
Create Date: 2026-10-07 14:05:17.105621

"""
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '78ce7f82c239'
down_revision = 'c4e7b2a95d18'
branch_labels = None
depends_on = None

PERMISSION_NAME = 'REVIEW_IMPORTED_DATA_FILING'


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
            'permission_name': PERMISSION_NAME,
            'description': 'Authorized to access Review Imported Data filing.',
            'created_date': now,
            'last_modified': now,
            'created_by_id': None,
            'modified_by_id': None
        }]
    )

    bind = op.get_bind()

    role_ids = [
        r['id'] for r in
        bind.execute(sa.text('SELECT id FROM authorized_roles')).mappings().all()
    ]

    permission = bind.execute(
        sa.text('SELECT id FROM permissions WHERE permission_name = :name').bindparams(name=PERMISSION_NAME)
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
            for role_id in role_ids
        ]
    )


def downgrade():
    bind = op.get_bind()

    permission = bind.execute(
        sa.text('SELECT id FROM permissions WHERE permission_name = :name').bindparams(name=PERMISSION_NAME)
    ).mappings().first()
    if permission:
        permission_id = permission['id']

        op.execute(
            sa.text('DELETE FROM authorized_role_permissions WHERE permission_id = :pid').bindparams(pid=permission_id)
        )
        op.execute(
            sa.text('DELETE FROM permissions WHERE id = :pid').bindparams(pid=permission_id)
        )
