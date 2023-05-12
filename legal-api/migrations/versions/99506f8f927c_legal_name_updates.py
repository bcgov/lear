"""legal_name_updates

Revision ID: 99506f8f927c
Revises: 0c792224fe11
Create Date: 2023-05-10 14:06:18.112289

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '99506f8f927c'
down_revision = '0c792224fe11'
branch_labels = None
depends_on = None



name_type_enum = postgresql.ENUM('OPERATING', name='alternate_names_type')
role_type_enum = postgresql.ENUM('applicant',
                                 'completing_party',
                                 'custodian',
                                 'director',
                                 'incorporator',
                                 'liquidator',
                                 'proprietor',
                                 'partner',
                                 name='entity_role_type')

def upgrade():

    # ==========================================================================================
    # legal_entities related updates
    # ==========================================================================================

    # remove FKs pointing at businesses table
    op.drop_constraint('documents_business_id_fkey', 'documents', type_='foreignkey')
    op.drop_constraint('documents_version_business_id_fkey', 'documents_version', type_='foreignkey')
    op.drop_constraint('request_tracker_business_id_fkey', 'request_tracker', type_='foreignkey')
    op.drop_constraint('resolutions_business_id_fkey', 'resolutions', type_='foreignkey')
    op.drop_constraint('aliases_business_id_fkey', 'aliases', type_='foreignkey')
    op.drop_constraint('filings_business_id_fkey', 'filings', type_='foreignkey')
    op.drop_constraint('comments_business_id_fkey', 'comments', type_='foreignkey')
    op.drop_constraint('offices_business_id_fkey', 'offices', type_='foreignkey')
    op.drop_constraint('party_roles_business_id_fkey', 'party_roles', type_='foreignkey')
    op.drop_constraint('addresses_business_id_fkey', 'addresses', type_='foreignkey')
    op.drop_constraint('share_classes_business_id_fkey', 'share_classes', type_='foreignkey')
    op.drop_constraint('dc_connections_business_id_fkey', 'dc_connections', type_='foreignkey')

    # remove indexes related to business_id columns
    op.drop_index(op.f('ix_addresses_business_id'), table_name='addresses')
    op.drop_index(op.f('ix_addresses_version_business_id'), table_name='addresses_version')
    op.drop_index(op.f('ix_comments_business_id'), table_name='comments')
    op.drop_index(op.f('ix_documents_business_id'), table_name='documents')
    op.drop_index(op.f('ix_documents_version_business_id'), table_name='documents_version')
    op.drop_index(op.f('ix_filings_business_id'), table_name='filings')
    op.drop_index(op.f('ix_offices_business_id'), table_name='offices')
    op.drop_index(op.f('ix_offices_version_business_id'), table_name='offices_version')
    op.drop_index(op.f('ix_party_roles_business_id'), table_name='party_roles')
    op.drop_index(op.f('ix_party_roles_version_business_id'), table_name='party_roles_version')
    op.drop_index(op.f('ix_request_tracker_business_id'), table_name='request_tracker')

    # migrate businesses table to legal_entities table
    op.drop_constraint('businesses_submitter_userid_fkey', 'businesses', type_='foreignkey')
    op.drop_constraint('businesses_state_filing_id_fkey', 'businesses', type_='foreignkey')

    op.drop_index(op.f('ix_businesses_identifier'), table_name='businesses')
    op.drop_index(op.f('ix_businesses_legal_name'), table_name='businesses')
    op.drop_index(op.f('ix_businesses_tax_id'), table_name='businesses')

    op.drop_index(op.f('ix_businesses_version_identifier'), table_name='businesses_version')
    op.drop_index(op.f('ix_businesses_version_legal_name'), table_name='businesses_version')
    op.drop_index(op.f('ix_businesses_version_tax_id'), table_name='businesses_version')
    op.drop_index(op.f('ix_businesses_version_operation_type'), table_name='businesses_version')
    op.drop_index(op.f('ix_businesses_version_transaction_id'), table_name='businesses_version')
    op.drop_index(op.f('ix_businesses_version_end_transaction_id'), table_name='businesses_version')

    op.rename_table('businesses', 'legal_entities')
    op.rename_table('businesses_version', 'legal_entities_version')

    op.alter_column('legal_entities', 'legal_type', new_column_name='entity_type',
                    existing_type=sa.String(length=10),
                    type_=sa.String(length=15), )

    op.alter_column('legal_entities_version', 'legal_type', new_column_name='entity_type',
                    existing_type=sa.String(length=10),
                    type_=sa.String(length=15))

    op.add_column('legal_entities', sa.Column('bn9', sa.String(length=9), nullable=True))
    op.add_column('legal_entities', sa.Column('first_name', sa.String(length=30), nullable=True))
    op.add_column('legal_entities', sa.Column('middle_initial', sa.String(length=30), nullable=True))
    op.add_column('legal_entities', sa.Column('last_name', sa.String(length=30), nullable=True))
    op.add_column('legal_entities', sa.Column('additional_name', sa.String(length=100), nullable=True))
    op.add_column('legal_entities', sa.Column('title', sa.String(length=1000), nullable=True))
    op.add_column('legal_entities', sa.Column('email', sa.String(length=254), nullable=True))
    op.add_column('legal_entities', sa.Column('delivery_address_id', sa.Integer(), nullable=True))
    op.add_column('legal_entities', sa.Column('mailing_address_id', sa.Integer(), nullable=True))

    op.add_column('legal_entities_version', sa.Column('bn9', sa.String(length=9), nullable=True))
    op.add_column('legal_entities_version', sa.Column('first_name', sa.String(length=30), nullable=True))
    op.add_column('legal_entities_version', sa.Column('middle_initial', sa.String(length=30), nullable=True))
    op.add_column('legal_entities_version', sa.Column('last_name', sa.String(length=30), nullable=True))
    op.add_column('legal_entities_version', sa.Column('additional_name', sa.String(length=100), nullable=True))
    op.add_column('legal_entities_version', sa.Column('title', sa.String(length=1000), nullable=True))
    op.add_column('legal_entities_version', sa.Column('email', sa.String(length=254), nullable=True))
    op.add_column('legal_entities_version', sa.Column('delivery_address_id', sa.Integer(), nullable=True))
    op.add_column('legal_entities_version', sa.Column('mailing_address_id', sa.Integer(), nullable=True))

    op.execute("ALTER TABLE legal_entities RENAME CONSTRAINT businesses_pkey TO legal_entities_pkey")
    op.execute("ALTER TABLE legal_entities_version RENAME CONSTRAINT businesses_version_pkey TO legal_entities_version_pkey")

    op.execute("ALTER SEQUENCE businesses_id_seq RENAME TO legal_entities_id_seq")
    op.execute("ALTER SEQUENCE business_identifier_coop RENAME TO legal_entity_identifier_coop")
    op.execute("ALTER SEQUENCE business_identifier_sp_gp RENAME TO legal_entity_identifier_sp_gp")

    op.create_foreign_key('legal_entities_submitter_userid_fkey', 'legal_entities', 'users', ['submitter_userid'], ['id'])
    op.create_foreign_key('legal_entities_state_filing_id_fkey', 'legal_entities', 'filings', ['state_filing_id'], ['id'])
    op.create_foreign_key('legal_entities_delivery_address_id_fkey', 'legal_entities', 'addresses', ['delivery_address_id'], ['id'])
    op.create_foreign_key('legal_entities_mailing_address_id_fkey', 'legal_entities', 'addresses', ['mailing_address_id'], ['id'])

    op.create_index(op.f('ix_legal_entities_identifier'), 'legal_entities', ['identifier'], unique=False)
    op.create_index(op.f('ix_legal_entities_legal_name'), 'legal_entities', ['legal_name'], unique=False)
    op.create_index(op.f('ix_legal_entities_tax_id'), 'legal_entities', ['tax_id'], unique=False)
    op.create_index(op.f('ix_legal_entities_entity_type'), 'legal_entities', ['entity_type'], unique=False)
    op.create_index(op.f('ix_legal_entities_first_name'), 'legal_entities', ['first_name'], unique=False)
    op.create_index(op.f('ix_legal_entities_middle_initial'), 'legal_entities', ['middle_initial'], unique=False)
    op.create_index(op.f('ix_legal_entities_last_name'), 'legal_entities', ['last_name'], unique=False)
    op.create_index(op.f('ix_legal_entities_email'), 'legal_entities', ['email'], unique=False)
    op.create_index(op.f('ix_legal_entities_delivery_address_id'), 'legal_entities', ['delivery_address_id'], unique=False)
    op.create_index(op.f('ix_legal_entities_mailing_address_id'), 'legal_entities', ['mailing_address_id'], unique=False)

    op.create_index(op.f('ix_legal_entities_version_identifier'), 'legal_entities_version', ['identifier'], unique=False)
    op.create_index(op.f('ix_legal_entities_version_legal_name'), 'legal_entities_version', ['legal_name'], unique=False)
    op.create_index(op.f('ix_legal_entities_version_tax_id'), 'legal_entities_version', ['tax_id'], unique=False)
    op.create_index(op.f('ix_legal_entities_version_entity_type'), 'legal_entities_version', ['entity_type'], unique=False)
    op.create_index(op.f('ix_legal_entities_version_operation_type'), 'legal_entities_version', ['operation_type'], unique=False)
    op.create_index(op.f('ix_legal_entities_version_transaction_id'), 'legal_entities_version', ['transaction_id'], unique=False)
    op.create_index(op.f('ix_legal_entities_version_end_transaction_id'), 'legal_entities_version', ['end_transaction_id'], unique=False)
    op.create_index(op.f('ix_legal_entities_version_first_name'), 'legal_entities_version', ['first_name'], unique=False)
    op.create_index(op.f('ix_legal_entities_version_middle_initial'), 'legal_entities_version', ['middle_initial'], unique=False)
    op.create_index(op.f('ix_legal_entities_version_last_name'), 'legal_entities_version', ['last_name'], unique=False)
    op.create_index(op.f('ix_legal_entities_version_email'), 'legal_entities_version', ['email'], unique=False)
    op.create_index(op.f('ix_legal_entities_version_delivery_address_id'), 'legal_entities_version', ['delivery_address_id'], unique=False)
    op.create_index(op.f('ix_legal_entities_version_mailing_address_id'), 'legal_entities_version', ['mailing_address_id'], unique=False)

    # Rename business_id columns to legal_entity_id for tables referencing legal_entities table.
    op.alter_column('documents', 'business_id', new_column_name='legal_entity_id')
    op.alter_column('documents_version', 'business_id', new_column_name='legal_entity_id')
    op.alter_column('request_tracker', 'business_id', new_column_name='legal_entity_id')
    op.alter_column('resolutions', 'business_id', new_column_name='legal_entity_id')
    op.alter_column('resolutions_version', 'business_id', new_column_name='legal_entity_id')
    op.alter_column('aliases', 'business_id', new_column_name='legal_entity_id')
    op.alter_column('aliases_version', 'business_id', new_column_name='legal_entity_id')
    op.alter_column('filings', 'business_id', new_column_name='legal_entity_id')
    op.alter_column('comments', 'business_id', new_column_name='legal_entity_id')
    op.alter_column('offices', 'business_id', new_column_name='legal_entity_id')
    op.alter_column('offices_version', 'business_id', new_column_name='legal_entity_id')
    op.alter_column('party_roles', 'business_id', new_column_name='legal_entity_id')
    op.alter_column('party_roles_version', 'business_id', new_column_name='legal_entity_id')
    op.alter_column('addresses', 'business_id', new_column_name='legal_entity_id')
    op.alter_column('addresses_version', 'business_id', new_column_name='legal_entity_id')
    op.alter_column('share_classes', 'business_id', new_column_name='legal_entity_id')
    op.alter_column('share_classes_version', 'business_id', new_column_name='legal_entity_id')
    op.alter_column('dc_connections', 'business_id', new_column_name='legal_entity_id')

    # Create FKs pointing at legal_entities table
    op.create_foreign_key('documents_legal_entity_id_fkey', 'documents', 'legal_entities', ['legal_entity_id'], ['id'])
    op.create_foreign_key('documents_version_legal_entity_id_fkey', 'documents_version', 'legal_entities', ['legal_entity_id'], ['id'])
    op.create_foreign_key('request_tracker_legal_entity_id_fkey', 'request_tracker', 'legal_entities', ['legal_entity_id'], ['id'])
    op.create_foreign_key('resolutions_legal_entity_id_fkey', 'resolutions', 'legal_entities', ['legal_entity_id'], ['id'])
    op.create_foreign_key('aliases_legal_entity_id_fkey', 'aliases', 'legal_entities', ['legal_entity_id'], ['id'])
    op.create_foreign_key('filings_legal_entity_id_fkey', 'filings', 'legal_entities', ['legal_entity_id'], ['id'])
    op.create_foreign_key('comments_legal_entity_id_fkey', 'comments', 'legal_entities', ['legal_entity_id'], ['id'])
    op.create_foreign_key('offices_legal_entity_id_fkey', 'offices', 'legal_entities', ['legal_entity_id'], ['id'])
    op.create_foreign_key('party_roles_legal_entity_id_fkey', 'party_roles', 'legal_entities', ['legal_entity_id'], ['id'])
    op.create_foreign_key('addresses_legal_entity_id_fkey', 'addresses', 'legal_entities', ['legal_entity_id'], ['id'])
    op.create_foreign_key('share_classes_legal_entity_id_fkey', 'share_classes', 'legal_entities', ['legal_entity_id'], ['id'])
    op.create_foreign_key('dc_connections_legal_entity_id_fkey', 'dc_connections', 'legal_entities', ['legal_entity_id'], ['id'])

    # Add indexes related to legal_entity_id columns for tables pointing at legal_entities table.
    op.create_index(op.f('ix_addresses_legal_entity_id'), 'addresses', ['legal_entity_id'], unique=False)
    op.create_index(op.f('ix_addresses_version_legal_entity_id'), 'addresses_version', ['legal_entity_id'], unique=False)
    op.create_index(op.f('ix_comments_legal_entity_id'), 'comments', ['legal_entity_id'], unique=False)
    op.create_index(op.f('ix_documents_legal_entity_id'), 'documents', ['legal_entity_id'], unique=False)
    op.create_index(op.f('ix_documents_version_legal_entity_id'), 'documents_version', ['legal_entity_id'], unique=False)
    op.create_index(op.f('ix_filings_legal_entity_id'), 'filings', ['legal_entity_id'], unique=False)
    op.create_index(op.f('ix_offices_legal_entity_id'), 'offices', ['legal_entity_id'], unique=False)
    op.create_index(op.f('ix_offices_version_legal_entity_id'), 'offices_version', ['legal_entity_id'], unique=False)
    op.create_index(op.f('ix_party_roles_legal_entity_id'), 'party_roles', ['legal_entity_id'], unique=False)
    op.create_index(op.f('ix_party_roles_version_legal_entity_id'), 'party_roles_version', ['legal_entity_id'], unique=False)
    op.create_index(op.f('ix_request_tracker_legal_entity_id'), 'request_tracker', ['legal_entity_id'], unique=False)

    # ==========================================================================================
    # alternate_names/alternate_names_version tables
    # ==========================================================================================

    name_type_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'alternate_names',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('identifier', sa.String(length=10), nullable=True),
        sa.Column('name', sa.String(length=1000), nullable=False),
        sa.Column('bn15', sa.String(length=15), nullable=True),
        sa.Column('legal_entity_id', sa.Integer(), autoincrement=False, nullable=True),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['legal_entity_id'], ['legal_entities.id'], ),
        sa.PrimaryKeyConstraint('id'))

    # enum added after creating table as DuplicateObject error would be thrown otherwise
    op.add_column('alternate_names', sa.Column('name_type', name_type_enum, nullable=False))

    op.create_table(
        'alternate_names_version',
        sa.Column('id', sa.Integer(), autoincrement=False, nullable=False),
        sa.Column('identifier', sa.String(length=10), nullable=True),
        sa.Column('name', sa.String(length=1000), nullable=False),
        sa.Column('bn15', sa.String(length=15), nullable=True),
        sa.Column('legal_entity_id', sa.Integer(), autoincrement=False, nullable=True),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('transaction_id', sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column('end_transaction_id', sa.BigInteger(), nullable=True),
        sa.Column('operation_type', sa.SmallInteger(), nullable=False),
        sa.PrimaryKeyConstraint('id', 'transaction_id'))

    # enum added after creating table as DuplicateObject error would be thrown otherwise
    op.add_column('alternate_names_version', sa.Column('name_type', name_type_enum, nullable=False))

    # ==========================================================================================
    # colin_entities/colin_entities_version tables
    # ==========================================================================================

    op.create_table(
        'colin_entities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_name', sa.String(length=150), nullable=False),
        sa.Column('identifier', sa.String(length=10), nullable=False),
        sa.Column('email', sa.String(length=254), nullable=True),
        sa.Column('delivery_address_id', sa.Integer(), autoincrement=False, nullable=True),
        sa.Column('mailing_address_id', sa.Integer(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['delivery_address_id'], ['addresses.id'], ),
        sa.ForeignKeyConstraint(['mailing_address_id'], ['addresses.id'], ),
        sa.PrimaryKeyConstraint('id'))

    op.create_index(op.f('ix_colin_entities_organization_name'), 'colin_entities', ['organization_name'], unique=False)
    op.create_index(op.f('ix_colin_entities_identifier'), 'colin_entities', ['identifier'], unique=False)
    op.create_index(op.f('ix_colin_entities_email'), 'colin_entities', ['email'], unique=False)
    op.create_index(op.f('ix_colin_entities_delivery_address_id'), 'colin_entities', ['delivery_address_id'], unique=False)
    op.create_index(op.f('ix_colin_entities_mailing_address_id'), 'colin_entities', ['mailing_address_id'], unique=False)

    op.create_table(
        'colin_entities_version',
        sa.Column('id', sa.Integer(), autoincrement=False, nullable=False),
        sa.Column('organization_name', sa.String(length=150), nullable=False),
        sa.Column('identifier', sa.String(length=10), nullable=False),
        sa.Column('email', sa.String(length=254), nullable=True),
        sa.Column('delivery_address_id', sa.Integer(), autoincrement=False, nullable=True),
        sa.Column('mailing_address_id', sa.Integer(), autoincrement=False, nullable=True),
        sa.Column('transaction_id', sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column('end_transaction_id', sa.BigInteger(), nullable=True),
        sa.Column('operation_type', sa.SmallInteger(), nullable=False),
        sa.PrimaryKeyConstraint('id', 'transaction_id'))

    op.create_index(op.f('ix_colin_entities_version_organization_name'), 'colin_entities_version', ['organization_name'], unique=False)
    op.create_index(op.f('ix_colin_entities_version_identifier'), 'colin_entities_version', ['identifier'], unique=False)
    op.create_index(op.f('ix_colin_entities_version_email'), 'colin_entities_version', ['email'], unique=False)
    op.create_index(op.f('ix_colin_entities_version_delivery_address_id'), 'colin_entities_version', ['delivery_address_id'], unique=False)
    op.create_index(op.f('ix_colin_entities_version_mailing_address_id'), 'colin_entities_version', ['mailing_address_id'], unique=False)
    op.create_index(op.f('ix_colin_entities_version_operation_type'), 'colin_entities_version', ['operation_type'], unique=False)
    op.create_index(op.f('ix_colin_entities_version_transaction_id'), 'colin_entities_version', ['transaction_id'], unique=False)
    op.create_index(op.f('ix_colin_entities_version_end_transaction_id'), 'colin_entities_version', ['end_transaction_id'], unique=False)

    # ==========================================================================================
    # resolutions/resolutions_version tables
    # ==========================================================================================

    op.add_column('resolutions', sa.Column('signing_legal_entity_id', sa.Integer(), nullable=True))
    op.create_foreign_key('resolutions_signing_legal_entity_id_fkey', 'resolutions', 'legal_entities', ['signing_legal_entity_id'], ['id'])

    op.add_column('resolutions_version', sa.Column('signing_legal_entity_id', sa.Integer(), nullable=True))

    # ==========================================================================================
    # entity_roles/entity_roles_version tables
    # ==========================================================================================

    role_type_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'entity_roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('legal_entity_id', sa.Integer(), autoincrement=False, nullable=False),
        sa.Column('related_entity_id', sa.Integer(), autoincrement=False, nullable=True),
        sa.Column('related_colin_entity_id', sa.Integer(), autoincrement=False, nullable=True),
        sa.Column('filing_id', sa.Integer(), autoincrement=False, nullable=True),
        sa.Column('appointment_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cessation_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivery_address_id', sa.Integer(), autoincrement=False, nullable=True),
        sa.Column('mailing_address_id', sa.Integer(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['legal_entity_id'], ['legal_entities.id'], ),
        sa.ForeignKeyConstraint(['related_entity_id'], ['legal_entities.id'], ),
        sa.ForeignKeyConstraint(['related_colin_entity_id'], ['colin_entities.id'], ),
        sa.ForeignKeyConstraint(['filing_id'], ['filings.id'], ),
        sa.ForeignKeyConstraint(['delivery_address_id'], ['addresses.id'], ),
        sa.ForeignKeyConstraint(['mailing_address_id'], ['addresses.id'], ),
        sa.PrimaryKeyConstraint('id'))
    op.add_column('entity_roles', sa.Column('role_type', role_type_enum, nullable=False))
    op.create_index(op.f('ix_entity_roles_legal_entity_id'), 'entity_roles', ['legal_entity_id'], unique=False)
    op.create_index(op.f('ix_entity_roles_related_entity_id'), 'entity_roles', ['related_entity_id'], unique=False)
    op.create_index(op.f('ix_entity_roles_related_colin_entity_id'), 'entity_roles', ['related_colin_entity_id'], unique=False)
    op.create_index(op.f('ix_entity_roles_filing_id'), 'entity_roles', ['filing_id'], unique=False)

    op.create_table(
        'entity_roles_version',
        sa.Column('id', sa.Integer(), autoincrement=False, nullable=False),
        sa.Column('legal_entity_id', sa.Integer(), autoincrement=False, nullable=False),
        sa.Column('related_entity_id', sa.Integer(), autoincrement=False, nullable=True),
        sa.Column('related_colin_entity_id', sa.Integer(), autoincrement=False, nullable=True),
        sa.Column('filing_id', sa.Integer(), autoincrement=False, nullable=True),
        sa.Column('appointment_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cessation_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivery_address_id', sa.Integer(), autoincrement=False, nullable=True),
        sa.Column('mailing_address_id', sa.Integer(), autoincrement=False, nullable=True),
        sa.Column('transaction_id', sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column('end_transaction_id', sa.BigInteger(), nullable=True),
        sa.Column('operation_type', sa.SmallInteger(), nullable=False),
        sa.PrimaryKeyConstraint('id', 'transaction_id'))
    op.add_column('entity_roles_version', sa.Column('role_type', role_type_enum, nullable=False))
    op.create_index(op.f('ix_entity_roles_version_legal_entity_id'), 'entity_roles_version', ['legal_entity_id'], unique=False)
    op.create_index(op.f('ix_entity_roles_version_related_entity_id'), 'entity_roles_version', ['related_entity_id'], unique=False)
    op.create_index(op.f('ix_entity_roles_version_related_colin_entity_id'), 'entity_roles_version', ['related_colin_entity_id'], unique=False)
    op.create_index(op.f('ix_entity_roles_version_filing_id'), 'entity_roles_version', ['filing_id'], unique=False)
    op.create_index(op.f('ix_entity_roles_version_operation_type'), 'entity_roles_version', ['operation_type'], unique=False)
    op.create_index(op.f('ix_entity_roles_version_transaction_id'), 'entity_roles_version', ['transaction_id'], unique=False)
    op.create_index(op.f('ix_entity_roles_version_end_transaction_id'), 'entity_roles_version', ['end_transaction_id'], unique=False)

    # ==========================================================================================
    # role_addresses/role_addresses_version tables
    # ==========================================================================================

    op.create_table(
        'role_addresses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('legal_entity_id', sa.Integer(), autoincrement=False, nullable=False),
        sa.Column('delivery_address_id', sa.Integer(), autoincrement=False, nullable=True),
        sa.Column('mailing_address_id', sa.Integer(), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(['legal_entity_id'], ['legal_entities.id'], ),
        sa.ForeignKeyConstraint(['delivery_address_id'], ['addresses.id'], ),
        sa.ForeignKeyConstraint(['mailing_address_id'], ['addresses.id'], ),
        sa.PrimaryKeyConstraint('id'))
    op.add_column('role_addresses', sa.Column('role_type', role_type_enum, nullable=False))

    op.create_table(
        'role_addresses_version',
        sa.Column('id', sa.Integer(), autoincrement=False, nullable=False),
        sa.Column('legal_entity_id', sa.Integer(), autoincrement=False, nullable=False),
        sa.Column('delivery_address_id', sa.Integer(), autoincrement=False, nullable=True),
        sa.Column('mailing_address_id', sa.Integer(), autoincrement=False, nullable=True),
        sa.Column('transaction_id', sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column('end_transaction_id', sa.BigInteger(), nullable=True),
        sa.Column('operation_type', sa.SmallInteger(), nullable=False),
        sa.PrimaryKeyConstraint('id', 'transaction_id'))
    op.add_column('role_addresses_version', sa.Column('role_type', role_type_enum, nullable=False))



def downgrade():


    # ==========================================================================================
    # alternate names
    # ==========================================================================================
    op.drop_table('alternate_names_version')
    op.drop_table('alternate_names')
    name_type_enum.drop(op.get_bind())

    op.drop_table('role_addresses_version')
    op.drop_table('role_addresses')
    op.drop_table('entity_roles_version')
    op.drop_table('entity_roles')
    role_type_enum.drop(op.get_bind())

    op.drop_table('colin_entities_version')
    op.drop_table('colin_entities')

    # ==========================================================================================
    # resolutions/resolutions_version tables
    # ==========================================================================================

    op.drop_constraint('resolutions_signing_legal_entity_id_fkey', 'resolutions', type_='foreignkey')
    op.drop_column('resolutions', 'signing_legal_entity_id')

    op.drop_column('resolutions_version', 'signing_legal_entity_id')

    # ==========================================================================================
    # legal_entities related updates
    # ==========================================================================================

    # remove FKs pointing at legal_entities table
    op.drop_constraint('documents_legal_entity_id_fkey', 'documents', type_='foreignkey')
    op.drop_constraint('documents_version_legal_entity_id_fkey', 'documents_version', type_='foreignkey')
    op.drop_constraint('request_tracker_legal_entity_id_fkey', 'request_tracker', type_='foreignkey')
    op.drop_constraint('resolutions_legal_entity_id_fkey', 'resolutions', type_='foreignkey')
    op.drop_constraint('aliases_legal_entity_id_fkey', 'aliases', type_='foreignkey')
    op.drop_constraint('filings_legal_entity_id_fkey', 'filings', type_='foreignkey')
    op.drop_constraint('comments_legal_entity_id_fkey', 'comments', type_='foreignkey')
    op.drop_constraint('offices_legal_entity_id_fkey', 'offices', type_='foreignkey')
    op.drop_constraint('party_roles_legal_entity_id_fkey', 'party_roles', type_='foreignkey')
    op.drop_constraint('addresses_legal_entity_id_fkey', 'addresses', type_='foreignkey')
    op.drop_constraint('share_classes_legal_entity_id_fkey', 'share_classes', type_='foreignkey')
    op.drop_constraint('dc_connections_legal_entity_id_fkey', 'dc_connections', type_='foreignkey')

    op.drop_index(op.f('ix_addresses_legal_entity_id'), table_name='addresses')
    op.drop_index(op.f('ix_addresses_version_legal_entity_id'), table_name='addresses_version')
    op.drop_index(op.f('ix_comments_legal_entity_id'), table_name='comments')
    op.drop_index(op.f('ix_documents_legal_entity_id'), table_name='documents')
    op.drop_index(op.f('ix_documents_version_legal_entity_id'), table_name='documents_version')
    op.drop_index(op.f('ix_filings_legal_entity_id'), table_name='filings')
    op.drop_index(op.f('ix_offices_legal_entity_id'), table_name='offices')
    op.drop_index(op.f('ix_offices_version_legal_entity_id'), table_name='offices_version')
    op.drop_index(op.f('ix_party_roles_legal_entity_id'), table_name='party_roles')
    op.drop_index(op.f('ix_party_roles_version_legal_entity_id'), table_name='party_roles_version')
    op.drop_index(op.f('ix_request_tracker_legal_entity_id'), table_name='request_tracker')

    # migrate legal_entities table to businesses table
    op.drop_constraint('legal_entities_submitter_userid_fkey', 'legal_entities', type_='foreignkey')
    op.drop_constraint('legal_entities_state_filing_id_fkey', 'legal_entities', type_='foreignkey')

    op.drop_index(op.f('ix_legal_entities_identifier'), table_name='legal_entities')
    op.drop_index(op.f('ix_legal_entities_legal_name'), table_name='legal_entities')
    op.drop_index(op.f('ix_legal_entities_tax_id'), table_name='legal_entities')
    op.drop_index(op.f('ix_legal_entities_entity_type'), table_name='legal_entities')
    op.drop_index(op.f('ix_legal_entities_first_name'), table_name='legal_entities')
    op.drop_index(op.f('ix_legal_entities_middle_initial'), table_name='legal_entities')
    op.drop_index(op.f('ix_legal_entities_last_name'), table_name='legal_entities')
    op.drop_index(op.f('ix_legal_entities_email'), table_name='legal_entities')
    op.drop_index(op.f('ix_legal_entities_delivery_address_id'), table_name='legal_entities')
    op.drop_index(op.f('ix_legal_entities_mailing_address_id'), table_name='legal_entities')

    op.drop_index(op.f('ix_legal_entities_version_identifier'), table_name='legal_entities_version')
    op.drop_index(op.f('ix_legal_entities_version_legal_name'), table_name='legal_entities_version')
    op.drop_index(op.f('ix_legal_entities_version_tax_id'), table_name='legal_entities_version')
    op.drop_index(op.f('ix_legal_entities_version_entity_type'), table_name='legal_entities_version')
    op.drop_index(op.f('ix_legal_entities_version_first_name'), table_name='legal_entities_version')
    op.drop_index(op.f('ix_legal_entities_version_middle_initial'), table_name='legal_entities_version')
    op.drop_index(op.f('ix_legal_entities_version_last_name'), table_name='legal_entities_version')
    op.drop_index(op.f('ix_legal_entities_version_email'), table_name='legal_entities_version')
    op.drop_index(op.f('ix_legal_entities_version_delivery_address_id'), table_name='legal_entities_version')
    op.drop_index(op.f('ix_legal_entities_version_mailing_address_id'), table_name='legal_entities_version')
    op.drop_index(op.f('ix_legal_entities_version_operation_type'), table_name='legal_entities_version')
    op.drop_index(op.f('ix_legal_entities_version_transaction_id'), table_name='legal_entities_version')
    op.drop_index(op.f('ix_legal_entities_version_end_transaction_id'), table_name='legal_entities_version')

    op.rename_table('legal_entities', 'businesses')
    op.rename_table('legal_entities_version', 'businesses_version')

    op.alter_column('businesses', 'entity_type', new_column_name='legal_type', existing_type=sa.String(length=15), type_=sa.String(length=10))
    op.alter_column('businesses_version', 'entity_type', new_column_name='legal_type', existing_type=sa.String(length=15), type_=sa.String(length=10))

    op.drop_column('businesses', 'bn9')
    op.drop_column('businesses', 'first_name')
    op.drop_column('businesses', 'middle_initial')
    op.drop_column('businesses', 'last_name')
    op.drop_column('businesses', 'additional_name')
    op.drop_column('businesses', 'title')
    op.drop_column('businesses', 'email')
    op.drop_column('businesses', 'delivery_address_id')
    op.drop_column('businesses', 'mailing_address_id')

    op.drop_column('businesses_version', 'bn9')
    op.drop_column('businesses_version', 'first_name')
    op.drop_column('businesses_version', 'middle_initial')
    op.drop_column('businesses_version', 'last_name')
    op.drop_column('businesses_version', 'additional_name')
    op.drop_column('businesses_version', 'title')
    op.drop_column('businesses_version', 'email')
    op.drop_column('businesses_version', 'delivery_address_id')
    op.drop_column('businesses_version', 'mailing_address_id')

    op.execute("ALTER TABLE businesses RENAME CONSTRAINT legal_entities_pkey TO businesses_pkey")
    op.execute("ALTER TABLE businesses_version RENAME CONSTRAINT legal_entities_version_pkey TO businesses_version_pkey")

    op.execute("ALTER SEQUENCE legal_entities_id_seq RENAME TO businesses_id_seq")
    op.execute("ALTER SEQUENCE legal_entity_identifier_coop RENAME TO business_identifier_coop")
    op.execute("ALTER SEQUENCE legal_entity_identifier_sp_gp RENAME TO business_identifier_sp_gp")

    op.create_foreign_key('businesses_submitter_userid_fkey', 'businesses', 'users', ['submitter_userid'], ['id'])
    op.create_foreign_key('businesses_state_filing_id_fkey', 'businesses', 'filings', ['state_filing_id'], ['id'])

    op.create_index(op.f('ix_businesses_identifier'), 'businesses', ['identifier'], unique=False)
    op.create_index(op.f('ix_businesses_legal_name'), 'businesses', ['legal_name'], unique=False)
    op.create_index(op.f('ix_businesses_tax_id'), 'businesses', ['tax_id'], unique=False)

    op.create_index(op.f('ix_businesses_version_identifier'), 'businesses_version', ['identifier'], unique=False)
    op.create_index(op.f('ix_businesses_version_legal_name'), 'businesses_version', ['legal_name'], unique=False)
    op.create_index(op.f('ix_businesses_version_tax_id'), 'businesses_version', ['tax_id'], unique=False)
    op.create_index(op.f('ix_businesses_version_operation_type'), 'businesses_version', ['operation_type'], unique=False)
    op.create_index(op.f('ix_businesses_version_transaction_id'), 'businesses_version', ['transaction_id'], unique=False)
    op.create_index(op.f('ix_businesses_version_end_transaction_id'), 'businesses_version', ['end_transaction_id'], unique=False)

    # Rename business_id columns to legal_entity_id for tables referencing legal_entities table.
    op.alter_column('documents', 'legal_entity_id', new_column_name='business_id')
    op.alter_column('documents_version', 'legal_entity_id', new_column_name='business_id')
    op.alter_column('request_tracker', 'legal_entity_id', new_column_name='business_id')
    op.alter_column('resolutions', 'legal_entity_id', new_column_name='business_id')
    op.alter_column('resolutions_version', 'legal_entity_id', new_column_name='business_id')
    op.alter_column('aliases', 'legal_entity_id', new_column_name='business_id')
    op.alter_column('aliases_version', 'legal_entity_id', new_column_name='business_id')
    op.alter_column('filings', 'legal_entity_id', new_column_name='business_id')
    op.alter_column('comments', 'legal_entity_id', new_column_name='business_id')
    op.alter_column('offices', 'legal_entity_id', new_column_name='business_id')
    op.alter_column('offices_version', 'legal_entity_id', new_column_name='business_id')
    op.alter_column('party_roles', 'legal_entity_id', new_column_name='business_id')
    op.alter_column('party_roles_version', 'legal_entity_id', new_column_name='business_id')
    op.alter_column('addresses', 'legal_entity_id', new_column_name='business_id')
    op.alter_column('addresses_version', 'legal_entity_id', new_column_name='business_id')
    op.alter_column('share_classes', 'legal_entity_id', new_column_name='business_id')
    op.alter_column('share_classes_version', 'legal_entity_id', new_column_name='business_id')
    op.alter_column('dc_connections', 'legal_entity_id', new_column_name='business_id')

    # Create FKs pointing at businesses table
    op.create_foreign_key('documents_business_id_fkey', 'documents', 'businesses', ['business_id'], ['id'])
    op.create_foreign_key('documents_version_business_id_fkey', 'documents_version', 'businesses', ['business_id'], ['id'])
    op.create_foreign_key('request_tracker_business_id_fkey', 'request_tracker', 'businesses', ['business_id'], ['id'])
    op.create_foreign_key('resolutions_business_id_fkey', 'resolutions', 'businesses', ['business_id'], ['id'])
    op.create_foreign_key('aliases_business_id_fkey', 'aliases', 'businesses', ['business_id'], ['id'])
    op.create_foreign_key('filings_business_id_fkey', 'filings', 'businesses', ['business_id'], ['id'])
    op.create_foreign_key('comments_business_id_fkey', 'comments', 'businesses', ['business_id'], ['id'])
    op.create_foreign_key('offices_business_id_fkey', 'offices', 'businesses', ['business_id'], ['id'])
    op.create_foreign_key('party_roles_business_id_fkey', 'party_roles', 'businesses', ['business_id'], ['id'])
    op.create_foreign_key('addresses_business_id_fkey', 'addresses', 'businesses', ['business_id'], ['id'])
    op.create_foreign_key('share_classes_business_id_fkey', 'share_classes', 'businesses', ['business_id'], ['id'])
    op.create_foreign_key('dc_connections_business_id_fkey', 'dc_connections', 'businesses', ['business_id'], ['id'])

    # Add indexes related to business_id columns for tables pointing at businesses table.
    op.create_index(op.f('ix_addresses_business_id'), 'addresses', ['business_id'], unique=False)
    op.create_index(op.f('ix_addresses_version_business_id'), 'addresses_version', ['business_id'], unique=False)
    op.create_index(op.f('ix_comments_business_id'), 'comments', ['business_id'], unique=False)
    op.create_index(op.f('ix_documents_business_id'), 'documents', ['business_id'], unique=False)
    op.create_index(op.f('ix_documents_version_business_id'), 'documents_version', ['business_id'], unique=False)
    op.create_index(op.f('ix_filings_business_id'), 'filings', ['business_id'], unique=False)
    op.create_index(op.f('ix_offices_business_id'), 'offices', ['business_id'], unique=False)
    op.create_index(op.f('ix_offices_version_business_id'), 'offices_version', ['business_id'], unique=False)
    op.create_index(op.f('ix_party_roles_business_id'), 'party_roles', ['business_id'], unique=False)
    op.create_index(op.f('ix_party_roles_version_business_id'), 'party_roles_version', ['business_id'], unique=False)
    op.create_index(op.f('ix_request_tracker_business_id'), 'request_tracker', ['business_id'], unique=False)
