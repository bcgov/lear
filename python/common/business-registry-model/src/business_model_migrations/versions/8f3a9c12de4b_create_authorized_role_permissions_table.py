"""create_authorized_role_permissions_table

Revision ID: 8f3a9c12de4b
Revises: 7fb9cd3e81bf
Create Date: 2025-06-04 01:03:37.254302

"""
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '8f3a9c12de4b'
down_revision = '7fb9cd3e81bf'
branch_labels = None
depends_on = None


def upgrade():
    # Create authorized_roles table
    op.create_table(
        'authorized_roles',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('role_name', sa.String(50), nullable=False, unique=True),
        sa.Column('created_date', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('last_modified', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('created_by_id', sa.Integer, nullable=True),
        sa.Column('modified_by_id', sa.Integer, nullable=True)
    )

    # Create permissions table
    op.create_table(
        'permissions',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('permission_name', sa.String(100), nullable=False, unique=True),
        sa.Column('description', sa.String(255), nullable=True),
        sa.Column('created_date', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('last_modified', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('created_by_id', sa.Integer, nullable=True),
        sa.Column('modified_by_id', sa.Integer, nullable=True),
    )

    # Create authorized_role_permissions table
    op.create_table(
        'authorized_role_permissions',
        sa.Column('role_id', sa.Integer, sa.ForeignKey('authorized_roles.id'), primary_key=True),
        sa.Column('permission_id', sa.Integer, sa.ForeignKey('permissions.id'), primary_key=True),
        sa.Column('created_date', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('last_modified', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('created_by_id', sa.Integer, nullable=True),
        sa.Column('modified_by_id', sa.Integer, nullable=True),
    )

    now = datetime.now(timezone.utc)

    authorized_roles = sa.table(
        'authorized_roles',
        sa.column('role_name', sa.String),
        sa.column('created_date', sa.TIMESTAMP(timezone=True)),
        sa.column('last_modified', sa.TIMESTAMP(timezone=True)),
        sa.column('created_by_id', sa.Integer),
        sa.column('modified_by_id', sa.Integer)
    )

    authorized_role_data = [
        {'name': 'sbc_staff'},
        {'name': 'staff'},
        {'name': 'contact_centre_staff'},
        {'name': 'maximus_staff'},
        {'name': 'public_user'}
    ]

    authorized_roles_list = [
        {
            'role_name': role['name'],
            'created_date': now,
            'last_modified': now,
            'created_by_id': None,
            'modified_by_id': None
        }
        for role in authorized_role_data
    ]

    op.bulk_insert(authorized_roles, authorized_roles_list)

    permissions = sa.table(
        'permissions',
        sa.column('permission_name', sa.String),
        sa.column('created_date', sa.TIMESTAMP(timezone=True)),
        sa.column('description', sa.String),
        sa.column('last_modified', sa.TIMESTAMP(timezone=True)),
        sa.column('created_by_id', sa.Integer),
        sa.column('modified_by_id', sa.Integer)
    )

    permission_data = [
        {'name': 'ADDRESS_CHANGE_FILING', 'description': 'Authorized to access a Change of Address filing.'},
        {'name': 'ADD_ENTITY_NO_AUTHENTICATION', 'description': 'Authorized to affiliate business or NR without authentication.'},
        {'name': 'ADMIN_DISSOLUTION_FILING', 'description': 'Authorized to access an Admin Dissolution filing.'},
        {'name': 'AGM_CHG_LOCATION_FILING', 'description': 'Authorized to access an AGM Location Change filing.'},
        {'name': 'AGM_EXTENSION_FILING', 'description': 'Authorized to access an AGM Extension filing.'},  
        {'name': 'ALTERATION_FILING', 'description': 'Authorized to access an Alteration filing.'},        
        {'name': 'AMALGAMATION_FILING', 'description': 'Authorized to access an Amalgamation filing.'},    
        {'name': 'AML_OVERRIDES', 'description': 'Authorized to override misc Amalgamation rules.'},       
        {'name': 'ANNUAL_REPORT_FILING', 'description': 'Authorized to access an Annual Report filing.'},  
        {'name': 'BLANK_CERTIFY_STATE', 'description': 'Authorized to not prepopulate certify state.'},
        {'name': 'BLANK_COMPLETING_PARTY', 'description': 'Authorized to not prepopulate completing party.'},
        {'name': 'CONSENT_AMALGAMATION_OUT_FILING', 'description': 'Authorized to access Consent to Amalgamate Out filing.'},
        {'name': 'CONSENT_CONTINUATION_OUT_FILING', 'description': 'Authorized to access Consent to Continue Out filing.'},
        {'name': 'CONTINUATION_IN_FILING', 'description': 'Authorized to access Continuation In filing.'}, 
        {'name': 'CORRECTION_FILING', 'description': 'Authorized to access coop/corp/firm Correction filing.'},
        {'name': 'COURT_ORDER_FILING', 'description': 'Authorized to access Court Order filing.'},
        {'name': 'COURT_ORDER_POA', 'description': 'Authorized to see Court Order / POA component in filing.'},
        {'name': 'DELAY_DISSOLUTION_FILING', 'description': 'Authorized to access Delay of Dissolution filing.'},
        {'name': 'DETAIL_COMMENTS', 'description': 'Authorized to add detail comments in ledger.'},        
        {'name': 'DIGITAL_CREDENTIALS', 'description': 'Authorized to access Digital Credentials.'},       
        {'name': 'DIRECTOR_CHANGE_FILING', 'description': 'Authorized to access Change of Director filing.'},
        {'name': 'DOCUMENT_RECORDS', 'description': 'Authorized to use document records (DRS) in filing.'},    
        {'name': 'EDITABLE_CERTIFY_NAME', 'description': 'Authorized to edit certify name in filing.'},    
        {'name': 'EDITABLE_COMPLETING_PARTY', 'description': 'Authorized to edit completing party in filing.'},
        {'name': 'FILE_AND_PAY', 'description': 'Authorized to click File and Pay.'},
        {'name': 'FIRM_ADD_BUSINESS', 'description': 'Authorized to add business to firm (in Registration filing).'},
        {'name': 'FIRM_CHANGE_FILING', 'description': 'Authorized to access (firm) Change of Registration filing.'},
        {'name': 'FIRM_CONVERSION_FILING', 'description': 'Authorized to access (firm) Conversion filing.'},
        {'name': 'FIRM_DISSOLUTION_FILING', 'description': 'Authorized to access firm Dissolution filing.'},
        {'name': 'FIRM_EDITABLE_DBA', 'description': 'Authorized to edit DBA (in Change filing).'},        
        {'name': 'FIRM_EDITABLE_EMAIL_ADDRESS', 'description': 'Authorized to edit email address (in Registration filing).'},
        {'name': 'FIRM_NO_HELP_SECTION', 'description': 'Authorized to skip help section (in Change filing).'},
        {'name': 'FIRM_NO_MIN_START_DATE', 'description': 'Authorized to use any start date (in any firm filing).'},
        {'name': 'FIRM_REPLACE_PERSON', 'description': 'Authorized to replace person (in Change filing).'},    
        {'name': 'INCORPORATION_APPLICATION_FILING', 'description': 'Authorized to access Incorporation Application filing.'},
        {'name': 'MANAGE_BUSINESS', 'description': 'Authorized to manage business in BRD.'},
        {'name': 'MANAGE_NR', 'description': 'Authorized to use/open NR in BRD.'},
        {'name': 'MANAGE_OTHER_ORGANIZATION', 'description': 'Authorized to access and manage another account\'s BRD (view it).'},
        {'name': 'MANAGE_SOCIETY', 'description': 'Authorized to manage society in BRD.'},
        {'name': 'NOTICE_WITHDRAWAL_FILING', 'description': 'Authorized to access Notice of Withdrawal filing.'},
        {'name': 'NO_COMPLETING_PARTY_MESSAGE_BOX', 'description': 'Authorized to skip completing party message box.'},
        {'name': 'NO_CONTACT_INFO', 'description': 'Authorized to not see contact info (in dialogs, etc).'},
        {'name': 'OVERRIDE_NIGS', 'description': 'Authorized to override misc NIGS rules.'},
        {'name': 'REGISTRATION_FILING', 'description': 'Authorized to access Registration filing.'},       
        {'name': 'RESTORATION_REINSTATEMENT_FILING', 'description': 'Authorized to access Restoration filing (all 4 types).'},
        {'name': 'RESUME_DRAFT', 'description': 'Authorized to resume drafts of temp businesses in BRD.'}, 
        {'name': 'SAVE_DRAFT', 'description': 'Authorized to save a filing draft. See note.'},
        {'name': 'SBC_BREADCRUMBS', 'description': 'Authorized to see SBC Staff breadcrumbs.'},
        {'name': 'SEARCH_BUSINESS_NR', 'description': 'Authorized to search for businesses or NRs in BRD.'},
        {'name': 'SPECIAL_RESOLUTION_FILING', 'description': 'Authorized to access Special Resolution filing.'},
        {'name': 'STAFF_BREADCRUMBS', 'description': 'Authorized to see REGI Staff breadcrumbs.'},
        {'name': 'STAFF_COMMENTS', 'description': 'Authorized to see/add staff comments against business.'},
        {'name': 'STAFF_DASHBOARD', 'description': 'Authorized to see the staff version of business registry dashboard.'},
        {'name': 'STAFF_FILINGS', 'description': 'Authorized to access staff filings.'},
        {'name': 'STAFF_PAYMENT', 'description': 'Authorized to see staff payment component in filings.'}, 
        {'name': 'THIRD_PARTY_CERTIFY_STMT', 'description': 'Authorized to see third-party ("they are authorized...") instead of first-party ("I am authorized...") certify statement.'},
        {'name': 'TRANSITION_FILING', 'description': 'Authorized to access Transition filing.'},
        {'name': 'VOLUNTARY_DISSOLUTION_FILING', 'description': 'Authorized to access (non-firm) Voluntary Dissolution filing.'},
    ]

    
    permissions_list = [
        {
            'permission_name': permission['name'],
            'description': permission['description'],
            'created_date': now,
            'last_modified': now,
            'created_by_id': None,
            'modified_by_id': None
        }
        for permission in permission_data
    ]
    
    op.bulk_insert(permissions, permissions_list)

    # Map role-permission pairs
    bind = op.get_bind()
    role_map = {r['role_name']: r['id'] for r in bind.execute(sa.text("SELECT id, role_name FROM authorized_roles"))}
    permission_map = {a['permission_name']: a['id'] for a in bind.execute(sa.text("SELECT id, permission_name FROM permissions"))}

    authorized_role_permissions = sa.table('authorized_role_permissions',
        sa.column('role_id', sa.Integer),
        sa.column('permission_id', sa.Integer),
        sa.column('created_date', sa.TIMESTAMP(timezone=True)),
        sa.column('last_modified', sa.TIMESTAMP(timezone=True)),
        sa.column('created_by_id', sa.Integer),
        sa.column('modified_by_id', sa.Integer)
    )

    role_permission_pairs_data = [
        {'role': 'contact_centre_staff', 'permission': 'ADDRESS_CHANGE_FILING'},
        {'role': 'contact_centre_staff', 'permission': 'ALTERATION_FILING'},
        {'role': 'contact_centre_staff', 'permission': 'ANNUAL_REPORT_FILING'},
        {'role': 'contact_centre_staff', 'permission': 'BLANK_CERTIFY_STATE'},
        {'role': 'contact_centre_staff', 'permission': 'DIRECTOR_CHANGE_FILING'},
        {'role': 'contact_centre_staff', 'permission': 'DOCUMENT_RECORDS'},
        {'role': 'contact_centre_staff', 'permission': 'EDITABLE_CERTIFY_NAME'},
        {'role': 'contact_centre_staff', 'permission': 'FIRM_CHANGE_FILING'},
        {'role': 'contact_centre_staff', 'permission': 'FIRM_DISSOLUTION_FILING'},
        {'role': 'contact_centre_staff', 'permission': 'INCORPORATION_APPLICATION_FILING'},
        {'role': 'contact_centre_staff', 'permission': 'MANAGE_BUSINESS'},
        {'role': 'contact_centre_staff', 'permission': 'MANAGE_NR'},
        {'role': 'contact_centre_staff', 'permission': 'MANAGE_SOCIETY'},
        {'role': 'contact_centre_staff', 'permission': 'REGISTRATION_FILING'},
        {'role': 'contact_centre_staff', 'permission': 'RESUME_DRAFT'},
        {'role': 'contact_centre_staff', 'permission': 'SBC_BREADCRUMBS'},
        {'role': 'contact_centre_staff', 'permission': 'SEARCH_BUSINESS_NR'},
        {'role': 'contact_centre_staff', 'permission': 'STAFF_BREADCRUMBS'},
        {'role': 'contact_centre_staff', 'permission': 'THIRD_PARTY_CERTIFY_STMT'},
        {'role': 'contact_centre_staff', 'permission': 'VOLUNTARY_DISSOLUTION_FILING'},
        {'role': 'maximus_staff', 'permission': 'ADDRESS_CHANGE_FILING'},
        {'role': 'maximus_staff', 'permission': 'ALTERATION_FILING'},
        {'role': 'maximus_staff', 'permission': 'ANNUAL_REPORT_FILING'},
        {'role': 'maximus_staff', 'permission': 'BLANK_CERTIFY_STATE'},
        {'role': 'maximus_staff', 'permission': 'DIRECTOR_CHANGE_FILING'},
        {'role': 'maximus_staff', 'permission': 'DOCUMENT_RECORDS'},
        {'role': 'maximus_staff', 'permission': 'EDITABLE_CERTIFY_NAME'},
        {'role': 'maximus_staff', 'permission': 'FIRM_CHANGE_FILING'},
        {'role': 'maximus_staff', 'permission': 'FIRM_DISSOLUTION_FILING'},
        {'role': 'maximus_staff', 'permission': 'INCORPORATION_APPLICATION_FILING'},
        {'role': 'maximus_staff', 'permission': 'MANAGE_BUSINESS'},
        {'role': 'maximus_staff', 'permission': 'MANAGE_NR'},
        {'role': 'maximus_staff', 'permission': 'MANAGE_OTHER_ORGANIZATION'},
        {'role': 'maximus_staff', 'permission': 'MANAGE_SOCIETY'},
        {'role': 'maximus_staff', 'permission': 'REGISTRATION_FILING'},
        {'role': 'maximus_staff', 'permission': 'RESUME_DRAFT'},
        {'role': 'maximus_staff', 'permission': 'SBC_BREADCRUMBS'},
        {'role': 'maximus_staff', 'permission': 'SEARCH_BUSINESS_NR'},
        {'role': 'maximus_staff', 'permission': 'STAFF_BREADCRUMBS'},
        {'role': 'maximus_staff', 'permission': 'THIRD_PARTY_CERTIFY_STMT'},
        {'role': 'maximus_staff', 'permission': 'VOLUNTARY_DISSOLUTION_FILING'},
        {'role': 'public_user', 'permission': 'ADDRESS_CHANGE_FILING'},
        {'role': 'public_user', 'permission': 'AGM_CHG_LOCATION_FILING'},
        {'role': 'public_user', 'permission': 'AGM_EXTENSION_FILING'},
        {'role': 'public_user', 'permission': 'ALTERATION_FILING'},
        {'role': 'public_user', 'permission': 'AMALGAMATION_FILING'},
        {'role': 'public_user', 'permission': 'ANNUAL_REPORT_FILING'},
        {'role': 'public_user', 'permission': 'CONSENT_AMALGAMATION_OUT_FILING'},
        {'role': 'public_user', 'permission': 'CONSENT_CONTINUATION_OUT_FILING'},
        {'role': 'public_user', 'permission': 'CONTINUATION_IN_FILING'},
        {'role': 'public_user', 'permission': 'DELAY_DISSOLUTION_FILING'},
        {'role': 'public_user', 'permission': 'DIGITAL_CREDENTIALS'},
        {'role': 'public_user', 'permission': 'DIRECTOR_CHANGE_FILING'},
        {'role': 'public_user', 'permission': 'FILE_AND_PAY'},
        {'role': 'public_user', 'permission': 'FIRM_CHANGE_FILING'},
        {'role': 'public_user', 'permission': 'FIRM_DISSOLUTION_FILING'},
        {'role': 'public_user', 'permission': 'INCORPORATION_APPLICATION_FILING'},
        {'role': 'public_user', 'permission': 'MANAGE_BUSINESS'},
        {'role': 'public_user', 'permission': 'MANAGE_NR'},
        {'role': 'public_user', 'permission': 'MANAGE_SOCIETY'},
        {'role': 'public_user', 'permission': 'REGISTRATION_FILING'},
        {'role': 'public_user', 'permission': 'RESUME_DRAFT'},
        {'role': 'public_user', 'permission': 'SAVE_DRAFT'},
        {'role': 'public_user', 'permission': 'SEARCH_BUSINESS_NR'},
        {'role': 'public_user', 'permission': 'SPECIAL_RESOLUTION_FILING'},
        {'role': 'public_user', 'permission': 'VOLUNTARY_DISSOLUTION_FILING'},
        {'role': 'sbc_staff', 'permission': 'ADDRESS_CHANGE_FILING'},
        {'role': 'sbc_staff', 'permission': 'ADD_ENTITY_NO_AUTHENTICATION'},
        {'role': 'sbc_staff', 'permission': 'ALTERATION_FILING'},
        {'role': 'sbc_staff', 'permission': 'ANNUAL_REPORT_FILING'},
        {'role': 'sbc_staff', 'permission': 'BLANK_CERTIFY_STATE'},
        {'role': 'sbc_staff', 'permission': 'BLANK_COMPLETING_PARTY'},
        {'role': 'sbc_staff', 'permission': 'COURT_ORDER_POA'},
        {'role': 'sbc_staff', 'permission': 'DIRECTOR_CHANGE_FILING'},
        {'role': 'sbc_staff', 'permission': 'DOCUMENT_RECORDS'},
        {'role': 'sbc_staff', 'permission': 'EDITABLE_CERTIFY_NAME'},
        {'role': 'sbc_staff', 'permission': 'EDITABLE_COMPLETING_PARTY'},
        {'role': 'sbc_staff', 'permission': 'FILE_AND_PAY'},
        {'role': 'sbc_staff', 'permission': 'FIRM_CHANGE_FILING'},
        {'role': 'sbc_staff', 'permission': 'FIRM_DISSOLUTION_FILING'},
        {'role': 'sbc_staff', 'permission': 'FIRM_EDITABLE_EMAIL_ADDRESS'},
        {'role': 'sbc_staff', 'permission': 'INCORPORATION_APPLICATION_FILING'},
        {'role': 'sbc_staff', 'permission': 'MANAGE_BUSINESS'},
        {'role': 'sbc_staff', 'permission': 'MANAGE_NR'},
        {'role': 'sbc_staff', 'permission': 'MANAGE_OTHER_ORGANIZATION'},
        {'role': 'sbc_staff', 'permission': 'MANAGE_SOCIETY'},
        {'role': 'sbc_staff', 'permission': 'REGISTRATION_FILING'},
        {'role': 'sbc_staff', 'permission': 'RESUME_DRAFT'},
        {'role': 'sbc_staff', 'permission': 'SAVE_DRAFT'},
        {'role': 'sbc_staff', 'permission': 'SBC_BREADCRUMBS'},
        {'role': 'sbc_staff', 'permission': 'SEARCH_BUSINESS_NR'},
        {'role': 'sbc_staff', 'permission': 'STAFF_BREADCRUMBS'},
        {'role': 'sbc_staff', 'permission': 'STAFF_COMMENTS'},
        {'role': 'sbc_staff', 'permission': 'STAFF_DASHBOARD'},
        {'role': 'sbc_staff', 'permission': 'STAFF_PAYMENT'},
        {'role': 'sbc_staff', 'permission': 'THIRD_PARTY_CERTIFY_STMT'},
        {'role': 'sbc_staff', 'permission': 'VOLUNTARY_DISSOLUTION_FILING'},
        {'role': 'staff', 'permission': 'ADDRESS_CHANGE_FILING'},
        {'role': 'staff', 'permission': 'ADD_ENTITY_NO_AUTHENTICATION'},
        {'role': 'staff', 'permission': 'ADMIN_DISSOLUTION_FILING'},
        {'role': 'staff', 'permission': 'AGM_CHG_LOCATION_FILING'},
        {'role': 'staff', 'permission': 'AGM_EXTENSION_FILING'},
        {'role': 'staff', 'permission': 'ALTERATION_FILING'},
        {'role': 'staff', 'permission': 'AMALGAMATION_FILING'},
        {'role': 'staff', 'permission': 'AML_OVERRIDES'},
        {'role': 'staff', 'permission': 'ANNUAL_REPORT_FILING'},
        {'role': 'staff', 'permission': 'BLANK_CERTIFY_STATE'},
        {'role': 'staff', 'permission': 'BLANK_COMPLETING_PARTY'},
        {'role': 'staff', 'permission': 'CONSENT_AMALGAMATION_OUT_FILING'},
        {'role': 'staff', 'permission': 'CONSENT_CONTINUATION_OUT_FILING'},
        {'role': 'staff', 'permission': 'CONTINUATION_IN_FILING'},
        {'role': 'staff', 'permission': 'CORRECTION_FILING'},
        {'role': 'staff', 'permission': 'COURT_ORDER_FILING'},
        {'role': 'staff', 'permission': 'COURT_ORDER_POA'},
        {'role': 'staff', 'permission': 'DELAY_DISSOLUTION_FILING'},
        {'role': 'staff', 'permission': 'DETAIL_COMMENTS'},
        {'role': 'staff', 'permission': 'DIRECTOR_CHANGE_FILING'},
        {'role': 'staff', 'permission': 'DOCUMENT_RECORDS'},
        {'role': 'staff', 'permission': 'EDITABLE_CERTIFY_NAME'},
        {'role': 'staff', 'permission': 'EDITABLE_COMPLETING_PARTY'},
        {'role': 'staff', 'permission': 'FILE_AND_PAY'},
        {'role': 'staff', 'permission': 'FIRM_ADD_BUSINESS'},
        {'role': 'staff', 'permission': 'FIRM_CHANGE_FILING'},
        {'role': 'staff', 'permission': 'FIRM_CONVERSION_FILING'},
        {'role': 'staff', 'permission': 'FIRM_DISSOLUTION_FILING'},
        {'role': 'staff', 'permission': 'FIRM_EDITABLE_DBA'},
        {'role': 'staff', 'permission': 'FIRM_EDITABLE_EMAIL_ADDRESS'},
        {'role': 'staff', 'permission': 'FIRM_NO_HELP_SECTION'},
        {'role': 'staff', 'permission': 'FIRM_NO_MIN_START_DATE'},
        {'role': 'staff', 'permission': 'FIRM_REPLACE_PERSON'},
        {'role': 'staff', 'permission': 'INCORPORATION_APPLICATION_FILING'},
        {'role': 'staff', 'permission': 'MANAGE_BUSINESS'},
        {'role': 'staff', 'permission': 'MANAGE_NR'},
        {'role': 'staff', 'permission': 'MANAGE_OTHER_ORGANIZATION'},
        {'role': 'staff', 'permission': 'MANAGE_SOCIETY'},
        {'role': 'staff', 'permission': 'NOTICE_WITHDRAWAL_FILING'},
        {'role': 'staff', 'permission': 'NO_COMPLETING_PARTY_MESSAGE_BOX'},
        {'role': 'staff', 'permission': 'NO_CONTACT_INFO'},
        {'role': 'staff', 'permission': 'OVERRIDE_NIGS'},
        {'role': 'staff', 'permission': 'REGISTRATION_FILING'},
        {'role': 'staff', 'permission': 'RESTORATION_REINSTATEMENT_FILING'},
        {'role': 'staff', 'permission': 'RESUME_DRAFT'},
        {'role': 'staff', 'permission': 'SAVE_DRAFT'},
        {'role': 'staff', 'permission': 'SEARCH_BUSINESS_NR'},
        {'role': 'staff', 'permission': 'SPECIAL_RESOLUTION_FILING'},
        {'role': 'staff', 'permission': 'STAFF_BREADCRUMBS'},
        {'role': 'staff', 'permission': 'STAFF_COMMENTS'},
        {'role': 'staff', 'permission': 'STAFF_DASHBOARD'},
        {'role': 'staff', 'permission': 'STAFF_FILINGS'},
        {'role': 'staff', 'permission': 'STAFF_PAYMENT'},
        {'role': 'staff', 'permission': 'THIRD_PARTY_CERTIFY_STMT'},
        {'role': 'staff', 'permission': 'TRANSITION_FILING'},
        {'role': 'staff', 'permission': 'VOLUNTARY_DISSOLUTION_FILING'},
    ]

    role_permission_list = [
        {
            'role_id': role_map[pair['role']],
            'permission_id': permission_map[pair['permission']],
            'created_date': now,
            'last_modified': now,
            'created_by_id': None,
            'modified_by_id': None
        }
        for pair in role_permission_pairs_data
        if pair['role'] in role_map and pair['permission'] in permission_map
    ]

    op.bulk_insert(authorized_role_permissions, role_permission_list)

def downgrade():
    op.drop_table('authorized_role_permissions')
    op.drop_table('permissions')
    op.drop_table('authorized_roles')

