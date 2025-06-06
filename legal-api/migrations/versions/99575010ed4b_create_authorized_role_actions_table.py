"""create_authorized_role_actions_table

Revision ID: 99575010ed4b
Revises: 957a67bde783
Create Date: 2025-06-04 01:03:37.254302

"""
from datetime import datetime, timezone
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '99575010ed4b'
down_revision = '957a67bde783'
branch_labels = None
depends_on = None


def upgrade():
    # Create user_roles table
    op.create_table(
        'user_roles',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('role_name', sa.String(50), nullable=False, unique=True),
        sa.Column('created_date', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('last_modified', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('created_by_id', sa.Integer, nullable=True),
        sa.Column('modified_by_id', sa.Integer, nullable=True)
    )

    # Create actions table
    op.create_table(
        'actions',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('action_name', sa.String(100), nullable=False, unique=True),
        sa.Column('description', sa.String(255), nullable=True),
        sa.Column('created_date', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('last_modified', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('created_by_id', sa.Integer, nullable=True),
        sa.Column('modified_by_id', sa.Integer, nullable=True),
    )

    # Create authorized_role_actions table
    op.create_table(
        'authorized_role_actions',
        sa.Column('role_id', sa.Integer, sa.ForeignKey('user_roles.id'), primary_key=True),
        sa.Column('action_id', sa.Integer, sa.ForeignKey('actions.id'), primary_key=True),
        sa.Column('created_date', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('last_modified', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('created_by_id', sa.Integer, nullable=True),
        sa.Column('modified_by_id', sa.Integer, nullable=True),
    )

    now = datetime.now(timezone.utc)

    user_roles = sa.table(
        'user_roles',
        sa.column('role_name', sa.String),
        sa.column('created_date', sa.TIMESTAMP(timezone=True)),
        sa.column('last_modified', sa.TIMESTAMP(timezone=True)),
        sa.column('created_by_id', sa.Integer),
        sa.column('modified_by_id', sa.Integer)
    )

    user_role_data = [
        {'name': 'contact_centre_staff'},
        {'name': 'maximus_staff'},
        {'name': 'public_user'},
        {'name': 'sbc_staff'},
        {'name': 'staff'}
    ]

    user_roles_list = [
        {
            'role_name': role['name'],
            'created_date': now,
            'last_modified': now,
            'created_by_id': None,
            'modified_by_id': None
        }
        for role in user_role_data
    ]

    op.bulk_insert(user_roles, user_roles_list)

    actions = sa.table(
        'actions',
        sa.column('action_name', sa.String),
        sa.column('created_date', sa.TIMESTAMP(timezone=True)),
        sa.column('description', sa.String),
        sa.column('last_modified', sa.TIMESTAMP(timezone=True)),
        sa.column('created_by_id', sa.Integer),
        sa.column('modified_by_id', sa.Integer)
    )

    action_data = [
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

    
    actions_list = [
        {
            'action_name': action['name'],
            'description': action['description'],
            'created_date': now,
            'last_modified': now,
            'created_by_id': None,
            'modified_by_id': None
        }
        for action in action_data
    ]
    
    op.bulk_insert(actions, actions_list)

    # Map role-action pairs
    bind = op.get_bind()
    role_map = {r['role_name']: r['id'] for r in bind.execute(sa.text("SELECT id, role_name FROM user_roles"))}
    action_map = {a['action_name']: a['id'] for a in bind.execute(sa.text("SELECT id, action_name FROM actions"))}

    authorized_role_actions = sa.table('authorized_role_actions',
        sa.column('role_id', sa.Integer),
        sa.column('action_id', sa.Integer),
        sa.column('created_date', sa.TIMESTAMP(timezone=True)),
        sa.column('last_modified', sa.TIMESTAMP(timezone=True)),
        sa.column('created_by_id', sa.Integer),
        sa.column('modified_by_id', sa.Integer)
    )

    role_action_pairs_data = [
        {'role': 'contact_centre_staff', 'action': 'ADDRESS_CHANGE_FILING'},
        {'role': 'contact_centre_staff', 'action': 'ALTERATION_FILING'},
        {'role': 'contact_centre_staff', 'action': 'ANNUAL_REPORT_FILING'},
        {'role': 'contact_centre_staff', 'action': 'BLANK_CERTIFY_STATE'},
        {'role': 'contact_centre_staff', 'action': 'DIRECTOR_CHANGE_FILING'},
        {'role': 'contact_centre_staff', 'action': 'DOCUMENT_RECORDS'},
        {'role': 'contact_centre_staff', 'action': 'EDITABLE_CERTIFY_NAME'},
        {'role': 'contact_centre_staff', 'action': 'FIRM_CHANGE_FILING'},
        {'role': 'contact_centre_staff', 'action': 'FIRM_DISSOLUTION_FILING'},
        {'role': 'contact_centre_staff', 'action': 'INCORPORATION_APPLICATION_FILING'},
        {'role': 'contact_centre_staff', 'action': 'MANAGE_BUSINESS'},
        {'role': 'contact_centre_staff', 'action': 'MANAGE_NR'},
        {'role': 'contact_centre_staff', 'action': 'MANAGE_SOCIETY'},
        {'role': 'contact_centre_staff', 'action': 'REGISTRATION_FILING'},
        {'role': 'contact_centre_staff', 'action': 'RESUME_DRAFT'},
        {'role': 'contact_centre_staff', 'action': 'SBC_BREADCRUMBS'},
        {'role': 'contact_centre_staff', 'action': 'SEARCH_BUSINESS_NR'},
        {'role': 'contact_centre_staff', 'action': 'STAFF_BREADCRUMBS'},
        {'role': 'contact_centre_staff', 'action': 'THIRD_PARTY_CERTIFY_STMT'},
        {'role': 'contact_centre_staff', 'action': 'VOLUNTARY_DISSOLUTION_FILING'},
        {'role': 'maximus_staff', 'action': 'ADDRESS_CHANGE_FILING'},
        {'role': 'maximus_staff', 'action': 'ALTERATION_FILING'},
        {'role': 'maximus_staff', 'action': 'ANNUAL_REPORT_FILING'},
        {'role': 'maximus_staff', 'action': 'BLANK_CERTIFY_STATE'},
        {'role': 'maximus_staff', 'action': 'DIRECTOR_CHANGE_FILING'},
        {'role': 'maximus_staff', 'action': 'DOCUMENT_RECORDS'},
        {'role': 'maximus_staff', 'action': 'EDITABLE_CERTIFY_NAME'},
        {'role': 'maximus_staff', 'action': 'FIRM_CHANGE_FILING'},
        {'role': 'maximus_staff', 'action': 'FIRM_DISSOLUTION_FILING'},
        {'role': 'maximus_staff', 'action': 'INCORPORATION_APPLICATION_FILING'},
        {'role': 'maximus_staff', 'action': 'MANAGE_BUSINESS'},
        {'role': 'maximus_staff', 'action': 'MANAGE_NR'},
        {'role': 'maximus_staff', 'action': 'MANAGE_OTHER_ORGANIZATION'},
        {'role': 'maximus_staff', 'action': 'MANAGE_SOCIETY'},
        {'role': 'maximus_staff', 'action': 'REGISTRATION_FILING'},
        {'role': 'maximus_staff', 'action': 'RESUME_DRAFT'},
        {'role': 'maximus_staff', 'action': 'SBC_BREADCRUMBS'},
        {'role': 'maximus_staff', 'action': 'SEARCH_BUSINESS_NR'},
        {'role': 'maximus_staff', 'action': 'STAFF_BREADCRUMBS'},
        {'role': 'maximus_staff', 'action': 'THIRD_PARTY_CERTIFY_STMT'},
        {'role': 'maximus_staff', 'action': 'VOLUNTARY_DISSOLUTION_FILING'},
        {'role': 'public_user', 'action': 'ADDRESS_CHANGE_FILING'},
        {'role': 'public_user', 'action': 'AGM_CHG_LOCATION_FILING'},
        {'role': 'public_user', 'action': 'AGM_EXTENSION_FILING'},
        {'role': 'public_user', 'action': 'ALTERATION_FILING'},
        {'role': 'public_user', 'action': 'AMALGAMATION_FILING'},
        {'role': 'public_user', 'action': 'ANNUAL_REPORT_FILING'},
        {'role': 'public_user', 'action': 'CONSENT_AMALGAMATION_OUT_FILING'},
        {'role': 'public_user', 'action': 'CONSENT_CONTINUATION_OUT_FILING'},
        {'role': 'public_user', 'action': 'CONTINUATION_IN_FILING'},
        {'role': 'public_user', 'action': 'DELAY_DISSOLUTION_FILING'},
        {'role': 'public_user', 'action': 'DIGITAL_CREDENTIALS'},
        {'role': 'public_user', 'action': 'DIRECTOR_CHANGE_FILING'},
        {'role': 'public_user', 'action': 'FILE_AND_PAY'},
        {'role': 'public_user', 'action': 'FIRM_CHANGE_FILING'},
        {'role': 'public_user', 'action': 'FIRM_DISSOLUTION_FILING'},
        {'role': 'public_user', 'action': 'INCORPORATION_APPLICATION_FILING'},
        {'role': 'public_user', 'action': 'MANAGE_BUSINESS'},
        {'role': 'public_user', 'action': 'MANAGE_NR'},
        {'role': 'public_user', 'action': 'MANAGE_SOCIETY'},
        {'role': 'public_user', 'action': 'REGISTRATION_FILING'},
        {'role': 'public_user', 'action': 'RESUME_DRAFT'},
        {'role': 'public_user', 'action': 'SAVE_DRAFT'},
        {'role': 'public_user', 'action': 'SEARCH_BUSINESS_NR'},
        {'role': 'public_user', 'action': 'SPECIAL_RESOLUTION_FILING'},
        {'role': 'public_user', 'action': 'VOLUNTARY_DISSOLUTION_FILING'},
        {'role': 'sbc_staff', 'action': 'ADDRESS_CHANGE_FILING'},
        {'role': 'sbc_staff', 'action': 'ADD_ENTITY_NO_AUTHENTICATION'},
        {'role': 'sbc_staff', 'action': 'ALTERATION_FILING'},
        {'role': 'sbc_staff', 'action': 'ANNUAL_REPORT_FILING'},
        {'role': 'sbc_staff', 'action': 'BLANK_CERTIFY_STATE'},
        {'role': 'sbc_staff', 'action': 'BLANK_COMPLETING_PARTY'},
        {'role': 'sbc_staff', 'action': 'COURT_ORDER_POA'},
        {'role': 'sbc_staff', 'action': 'DIRECTOR_CHANGE_FILING'},
        {'role': 'sbc_staff', 'action': 'DOCUMENT_RECORDS'},
        {'role': 'sbc_staff', 'action': 'EDITABLE_CERTIFY_NAME'},
        {'role': 'sbc_staff', 'action': 'EDITABLE_COMPLETING_PARTY'},
        {'role': 'sbc_staff', 'action': 'FILE_AND_PAY'},
        {'role': 'sbc_staff', 'action': 'FIRM_CHANGE_FILING'},
        {'role': 'sbc_staff', 'action': 'FIRM_DISSOLUTION_FILING'},
        {'role': 'sbc_staff', 'action': 'FIRM_EDITABLE_EMAIL_ADDRESS'},
        {'role': 'sbc_staff', 'action': 'INCORPORATION_APPLICATION_FILING'},
        {'role': 'sbc_staff', 'action': 'MANAGE_BUSINESS'},
        {'role': 'sbc_staff', 'action': 'MANAGE_NR'},
        {'role': 'sbc_staff', 'action': 'MANAGE_OTHER_ORGANIZATION'},
        {'role': 'sbc_staff', 'action': 'MANAGE_SOCIETY'},
        {'role': 'sbc_staff', 'action': 'REGISTRATION_FILING'},
        {'role': 'sbc_staff', 'action': 'RESUME_DRAFT'},
        {'role': 'sbc_staff', 'action': 'SAVE_DRAFT'},
        {'role': 'sbc_staff', 'action': 'SBC_BREADCRUMBS'},
        {'role': 'sbc_staff', 'action': 'SEARCH_BUSINESS_NR'},
        {'role': 'sbc_staff', 'action': 'STAFF_BREADCRUMBS'},
        {'role': 'sbc_staff', 'action': 'STAFF_COMMENTS'},
        {'role': 'sbc_staff', 'action': 'STAFF_DASHBOARD'},
        {'role': 'sbc_staff', 'action': 'STAFF_PAYMENT'},
        {'role': 'sbc_staff', 'action': 'THIRD_PARTY_CERTIFY_STMT'},
        {'role': 'sbc_staff', 'action': 'VOLUNTARY_DISSOLUTION_FILING'},
        {'role': 'staff', 'action': 'ADDRESS_CHANGE_FILING'},
        {'role': 'staff', 'action': 'ADD_ENTITY_NO_AUTHENTICATION'},
        {'role': 'staff', 'action': 'ADMIN_DISSOLUTION_FILING'},
        {'role': 'staff', 'action': 'AGM_CHG_LOCATION_FILING'},
        {'role': 'staff', 'action': 'AGM_EXTENSION_FILING'},
        {'role': 'staff', 'action': 'ALTERATION_FILING'},
        {'role': 'staff', 'action': 'AMALGAMATION_FILING'},
        {'role': 'staff', 'action': 'AML_OVERRIDES'},
        {'role': 'staff', 'action': 'ANNUAL_REPORT_FILING'},
        {'role': 'staff', 'action': 'BLANK_CERTIFY_STATE'},
        {'role': 'staff', 'action': 'BLANK_COMPLETING_PARTY'},
        {'role': 'staff', 'action': 'CONSENT_AMALGAMATION_OUT_FILING'},
        {'role': 'staff', 'action': 'CONSENT_CONTINUATION_OUT_FILING'},
        {'role': 'staff', 'action': 'CONTINUATION_IN_FILING'},
        {'role': 'staff', 'action': 'CORRECTION_FILING'},
        {'role': 'staff', 'action': 'COURT_ORDER_FILING'},
        {'role': 'staff', 'action': 'COURT_ORDER_POA'},
        {'role': 'staff', 'action': 'DELAY_DISSOLUTION_FILING'},
        {'role': 'staff', 'action': 'DETAIL_COMMENTS'},
        {'role': 'staff', 'action': 'DIRECTOR_CHANGE_FILING'},
        {'role': 'staff', 'action': 'DOCUMENT_RECORDS'},
        {'role': 'staff', 'action': 'EDITABLE_CERTIFY_NAME'},
        {'role': 'staff', 'action': 'EDITABLE_COMPLETING_PARTY'},
        {'role': 'staff', 'action': 'FILE_AND_PAY'},
        {'role': 'staff', 'action': 'FIRM_ADD_BUSINESS'},
        {'role': 'staff', 'action': 'FIRM_CHANGE_FILING'},
        {'role': 'staff', 'action': 'FIRM_CONVERSION_FILING'},
        {'role': 'staff', 'action': 'FIRM_DISSOLUTION_FILING'},
        {'role': 'staff', 'action': 'FIRM_EDITABLE_DBA'},
        {'role': 'staff', 'action': 'FIRM_EDITABLE_EMAIL_ADDRESS'},
        {'role': 'staff', 'action': 'FIRM_NO_HELP_SECTION'},
        {'role': 'staff', 'action': 'FIRM_NO_MIN_START_DATE'},
        {'role': 'staff', 'action': 'FIRM_REPLACE_PERSON'},
        {'role': 'staff', 'action': 'INCORPORATION_APPLICATION_FILING'},
        {'role': 'staff', 'action': 'MANAGE_BUSINESS'},
        {'role': 'staff', 'action': 'MANAGE_NR'},
        {'role': 'staff', 'action': 'MANAGE_OTHER_ORGANIZATION'},
        {'role': 'staff', 'action': 'MANAGE_SOCIETY'},
        {'role': 'staff', 'action': 'NOTICE_WITHDRAWAL_FILING'},
        {'role': 'staff', 'action': 'NO_COMPLETING_PARTY_MESSAGE_BOX'},
        {'role': 'staff', 'action': 'NO_CONTACT_INFO'},
        {'role': 'staff', 'action': 'OVERRIDE_NIGS'},
        {'role': 'staff', 'action': 'REGISTRATION_FILING'},
        {'role': 'staff', 'action': 'RESTORATION_REINSTATEMENT_FILING'},
        {'role': 'staff', 'action': 'RESUME_DRAFT'},
        {'role': 'staff', 'action': 'SAVE_DRAFT'},
        {'role': 'staff', 'action': 'SEARCH_BUSINESS_NR'},
        {'role': 'staff', 'action': 'SPECIAL_RESOLUTION_FILING'},
        {'role': 'staff', 'action': 'STAFF_BREADCRUMBS'},
        {'role': 'staff', 'action': 'STAFF_COMMENTS'},
        {'role': 'staff', 'action': 'STAFF_DASHBOARD'},
        {'role': 'staff', 'action': 'STAFF_FILINGS'},
        {'role': 'staff', 'action': 'STAFF_PAYMENT'},
        {'role': 'staff', 'action': 'THIRD_PARTY_CERTIFY_STMT'},
        {'role': 'staff', 'action': 'TRANSITION_FILING'},
        {'role': 'staff', 'action': 'VOLUNTARY_DISSOLUTION_FILING'},
    ]

    role_action_list = [
        {
            'role_id': role_map[pair['role']],
            'action_id': action_map[pair['action']],
            'created_date': now,
            'last_modified': now,
            'created_by_id': None,
            'modified_by_id': None
        }
        for pair in role_action_pairs_data
        if pair['role'] in role_map and pair['action'] in action_map
    ]

    op.bulk_insert(authorized_role_actions, role_action_list)

def downgrade():
    op.drop_table('authorized_role_actions')
    op.drop_table('actions')
    op.drop_table('user_roles')
