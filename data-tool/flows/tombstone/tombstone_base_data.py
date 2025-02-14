# ======== business ========
BUSINESS = {
    'identifier': None,
    'legal_name': None,
    'legal_type': None,
    'founding_date': None,  # timestamptz
    'state': None,
    'tax_id': None,
    'fiscal_year_end_date': None,  # timestamptz
    'last_ledger_timestamp': None, # timestamptz
    'admin_freeze': False,
    'send_ar_ind': True,
    'last_ar_year': None,
    'last_ar_date': None,
    'last_ar_reminder_year': None
    # 'no_dissolution' : False  # db sets default value
}


# ======== user ========
USER = {
    'username': None,
    'firstname': None,
    'middlename': None,
    'lastname': None,
    'email': None,
    'creation_date': None
}


# ======== comment ========
COMMENT = {
    'comment': None,
    'timestamp': None,
    # FK
    'business_id': None,
    'staff_id': None,
    'filing_id': None
}


# ======== address ========
ADDRESS = {
    'address_type': None,  # mailing or delivery
    'street': None,
    'street_additional': None,
    'city': None,
    'region': None,
    'country': None,
    'postal_code': None,
    'delivery_instructions': None,
    # FK
    'business_id': None,
    'office_id': None,
}


# ======== office (composite) ========
# insert: office -> address
OFFICE = {
    'offices': {
        'office_type': None,
        # FK
        'business_id': None,
    },
    'addresses': [
       # ADDRESS (0~1)
    ]
}


# ======== party (composite) ========
# insert: address -> party -> party_role
# party_role
PARTY_ROLE = {
    'role': None,
    'appointment_date': None,  # timestamptz
    'cessation_date': None,  # timestamptz
    # FK
    'business_id': None,
    'party_id': None,
}

PARTY = {
    'addresses': [
        # ADDRESS (0~1)
    ],
    'parties': {
        'party_type': None,
        'first_name': None,
        'middle_initial': None,
        'last_name': None,
        'title': None,
        'organization_name': None,
        'email': None,
        # FK
        'delivery_address_id': None,
        'mailing_address_id': None,

    },
    'party_roles': [
        # PARTY_ROLE (1~n)
    ]
}


# ======== share structure (composite) ========
# insert: share_class -> share_series(if any)
# share_series
SHARE_SERIES = {
    'name': None,
    'priority': 1,
    'max_share_flag': False,
    'max_shares': None,  # integer
    'special_rights_flag': False,
    # FK
    'share_class_id': None,
}

SHARE_CLASSES = {
    'share_classes': {
        'name': None,
        'priority': 1,
        'max_share_flag': False,
        'max_shares': None,  # integer
        'par_value_flag': False,
        'par_value': None,  # float
        'currency': None,
        'special_rights_flag': False,
        # FK
        'business_id': None
    },
    'share_series': [
        # SHARE_SERIES (0~n)
    ]
}


# ======== alias ========
ALIAS = {
    'alias': None,
    'type': None,
    # FK
    'business_id': None
}


# ======== resolution ========
RESOLUTION = {
    'resolution_date': None,  # date
    'type': None,
    # FK
    'business_id': None,
}


# ======== jurisdiction ========
JURISDICTION = {
    'country': None,
    'region': None,
    'identifier': None,
    'legal_name': None,
    'tax_id': None,
    'incorporation_date': None,  # date
    'expro_identifier': None,
    'expro_legal_name': None,
}


# ======== filing ========
FILING_JSON = {
    'filing': {
        'header': {}
    }
}

FILING = {
    'filings': {
        'filing_date': None,  # timestamptz
        'filing_json': FILING_JSON,
        'filing_type': None,
        'filing_sub_type': None,
        'status': 'COMPLETED',
        'completion_date': None,  # timestamptz
        'effective_date': None,  # timestamptz
        'meta_data': None,
        # default values for now
        'paper_only': True,
        'source': 'COLIN',
        'colin_only': False,
        'deletion_locked': False,
        'hide_in_ledger': False, # TODO: double check when doing cleanup - dissolution (invol, admin)
        # TODO: new columns for NoW
        # FK
        'business_id': None,
        'transaction_id': None,
        'submitter_id': None,
        # others
        'submitter_roles': None,
    },
    'jurisdiction': None,  # optional
    'amalgamations': None,  # optional
    'comments': None,  # optional
    'colin_event_ids': None
}

FILING_COMBINED = {
    'filings': [FILING],
    'update_business_info': {
        # business info to update
    },
    'state_filing_index': -1,
}

AMALGAMATION = {
    'amalgamations': {
        'amalgamation_date': None,
        'court_approval': None,
        'amalgamation_type': None,
        # FK
        'business_id': None,
        'filing_id': None,
    },
    'amalgamating_businesses': []
}

AMALGAMTING_BUSINESS = {
    'foreign_jurisdiction': None,
    'foreign_name': None,
    'foreign_identifier': None,
    'role': None,
    'foreign_jurisdiction_region': None,
    # FK
    'business_id': None,
    'amalgamation_id': None,
}

# ======== tombstone example ========
TOMBSTONE = {
    'businesses': BUSINESS,
    'offices': [OFFICE],
    'parties': [PARTY],
    'share_classes': [SHARE_CLASSES],
    'aliases': [ALIAS],
    'resolutions': [RESOLUTION],
    'filings': [FILING],
    'updates': {
        'businesses': BUSINESS,
        'state_filing_index': -1
    }
}
