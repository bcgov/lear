"""furnishings

Revision ID: 01b28a2bb730
Revises: 3083d361616e
Create Date: 2024-06-12 20:10:44.723041

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '01b28a2bb730'
down_revision = '3083d361616e'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('furnishings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('furnishing_type', sa.Enum('EMAIL', 'MAIL', 'GAZETTE', name='furnishing_type'), nullable=False),
        sa.Column('furnishing_name', sa.Enum(
            'DISSOLUTION_COMMENCEMENT_NO_AR',
            'DISSOLUTION_COMMENCEMENT_NO_TR',
            'DISSOLUTION_COMMENCEMENT_NO_AR_XPRO',
            'DISSOLUTION_COMMENCEMENT_NO_TR_XPRO',
            'INTENT_TO_DISSOLVE',
            'INTENT_TO_DISSOLVE_XPRO',
            'CORP_DISSOLVED',
            'CORP_DISSOLVED_XPRO',
            name='furnishing_name'
            ),
            nullable=False
        ),
        sa.Column('batch_id', sa.Integer(), nullable=False),
        sa.Column('grouping_identifier', sa.Integer(), nullable=True),
        sa.Column('business_id', sa.Integer(), nullable=False),
        sa.Column('business_identifier', sa.VARCHAR(10), nullable=False),
        sa.Column('processed_date', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('status', sa.Enum('QUEUED', 'PROCESSED', 'FAILED', name='furnishing_status'), nullable=False),
        sa.Column('notes', sa.VARCHAR(length=150), nullable=True),
        sa.Column('meta_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_date', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('last_modified', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('email', sa.VARCHAR(length=254), nullable=True),
        sa.Column('last_name', sa.VARCHAR(length=30), nullable=True),
        sa.Column('first_name', sa.VARCHAR(length=30), nullable=True),                
        sa.Column('middle_name', sa.VARCHAR(length=30), nullable=True),
        sa.Column('address_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['address_id'], ['addresses.id']),
        sa.ForeignKeyConstraint(['batch_id'], ['batches.id']),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id']),
        sa.PrimaryKeyConstraint('id')
    )

    op.execute("CREATE SEQUENCE grouping_identifier START 1;")


def downgrade():
    op.drop_table('furnishings')
    op.execute("DROP TYPE furnishing_type;")
    op.execute("DROP TYPE furnishing_name;")
    op.execute("DROP TYPE furnishing_status;")
    op.execute("DROP SEQUENCE grouping_identifier;")
