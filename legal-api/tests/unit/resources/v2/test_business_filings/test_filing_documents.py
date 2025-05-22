# Copyright © 2021 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests to assure the business-filing end-point - LEDGER SEARCH

Test-Suite to ensure that the /businesses/_id_/filings LEDGER SEARCH endpoint is working as expected.
"""
import copy
import json
import re
from datetime import datetime
from http import HTTPStatus

import pytest
from flask import current_app
from registry_schemas.example_data import (
    AGM_EXTENSION,
    AGM_LOCATION_CHANGE,
    AMALGAMATION_APPLICATION,
    ANNUAL_REPORT,
    CHANGE_OF_ADDRESS,
    CHANGE_OF_DIRECTORS,
    CHANGE_OF_REGISTRATION,
    CONTINUATION_IN,
    CONTINUATION_OUT,
    CORRECTION_AR,
    CORRECTION_CP_SPECIAL_RESOLUTION,
    CORRECTION_INCORPORATION,
    COURT_ORDER,
    DISSOLUTION,
    FILING_HEADER,
    FIRMS_CONVERSION,
    REGISTRATION,
    RESTORATION,
    SPECIAL_RESOLUTION,
)
from registry_schemas.example_data.schema_data import ALTERATION, INCORPORATION, CONTINUATION_IN

from legal_api.core import Filing
from legal_api.models import Business, RegistrationBootstrap
from legal_api.services.authz import STAFF_ROLE
from tests.unit.models import (  # noqa:E501,I001
    factory_business,
    factory_completed_filing,
    factory_filing,
)
from tests.unit.services.utils import create_header, helper_create_jwt

ADMIN_DISSOLUTION = copy.deepcopy(DISSOLUTION)
ADMIN_DISSOLUTION['dissolutionType'] = 'administrative'


def basic_test_helper():
    identifier = 'CP7654321'
    business = factory_business(identifier)

    filing_json = FILING_HEADER
    filing_json['specialResolution'] = SPECIAL_RESOLUTION
    filing_date = datetime.utcnow()
    filing = factory_completed_filing(business, filing_json, filing_date=filing_date)

    return business, filing


def test_not_authorized(session, client, jwt):
    """Assert the the call fails for unauthorized access."""
    business, filing = basic_test_helper()

    MISSING_ROLES = ['SOME RANDO ROLE', ]

    rv = client.get(f'/api/v2/businesses/{business.identifier}/filings/{filing.id}/documents',
                    headers=create_header(jwt, MISSING_ROLES, business.identifier))

    assert rv.status_code == HTTPStatus.UNAUTHORIZED
    assert rv.json.get('message')
    assert business.identifier in rv.json.get('message')


def test_missing_business(session, client, jwt):
    """Assert the the call fails for missing business."""
    business, filing = basic_test_helper()

    not_the_business_identifier = 'ABC123'

    rv = client.get(f'/api/v2/businesses/{not_the_business_identifier}/filings/{filing.id}/documents',
                    headers=create_header(jwt, [STAFF_ROLE, ], business.identifier))

    assert rv.status_code == HTTPStatus.NOT_FOUND
    assert rv.json.get('message')
    assert not_the_business_identifier in rv.json.get('message')


def test_missing_filing(session, client, jwt):
    """Assert the the call fails for missing business."""
    business, filing = basic_test_helper()

    wrong_filing_number = 999999999

    rv = client.get(f'/api/v2/businesses/{business.identifier}/filings/{wrong_filing_number}/documents',
                    headers=create_header(jwt, [STAFF_ROLE, ], business.identifier))

    assert rv.status_code == HTTPStatus.NOT_FOUND
    assert rv.json.get('message')
    assert str(wrong_filing_number) in rv.json.get('message')


def test_unpaid_filing(session, client, jwt):
    identifier = 'CP7654321'
    business = factory_business(identifier)

    filing_json = FILING_HEADER
    filing_json['specialResolution'] = SPECIAL_RESOLUTION
    filing_date = datetime.utcnow()
    filing = factory_filing(business, filing_json, filing_date=filing_date)

    rv = client.get(f'/api/v2/businesses/{business.identifier}/filings/{filing.id}/documents',
                    headers=create_header(jwt, [STAFF_ROLE], business.identifier))

    assert rv.status_code == HTTPStatus.NOT_FOUND
    assert rv.json == {}


base_url = 'https://LEGAL_API_BASE_URL'

ALTERATION_WITHOUT_NR = copy.deepcopy(ALTERATION)
del ALTERATION_WITHOUT_NR['nameRequest']['nrNumber']
del ALTERATION_WITHOUT_NR['nameRequest']['legalName']

ALTERATION_MEMORANDUM_RULES_IN_RESOLUTION = copy.deepcopy(ALTERATION)
ALTERATION_MEMORANDUM_RULES_IN_RESOLUTION['memorandumInResolution'] = True
ALTERATION_MEMORANDUM_RULES_IN_RESOLUTION['rulesInResolution'] = True

MOCK_NOTICE_OF_WITHDRAWAL = {}
MOCK_NOTICE_OF_WITHDRAWAL['courtOrder'] = copy.deepcopy(COURT_ORDER)
MOCK_NOTICE_OF_WITHDRAWAL['filingId'] = '123456'
MOCK_NOTICE_OF_WITHDRAWAL['hasTakenEffect'] = False
MOCK_NOTICE_OF_WITHDRAWAL['partOfPoa'] = False


@pytest.mark.parametrize('test_name, identifier, entity_type, filing_name_1, legal_filing_1, filing_name_2, legal_filing_2, status, expected_msg, expected_http_code, payment_completion_date', [
    ('special_res_paper', 'CP7654321', Business.LegalTypes.COOP.value,
     'specialResolution', SPECIAL_RESOLUTION, None, None, Filing.Status.PAPER_ONLY, {}, HTTPStatus.NOT_FOUND, None
     ),
    ('special_res_pending', 'CP7654321', Business.LegalTypes.COOP.value,
     'specialResolution', SPECIAL_RESOLUTION, None, None, Filing.Status.PENDING, {}, HTTPStatus.NOT_FOUND, None
     ),
    ('special_res_paid', 'CP7654321', Business.LegalTypes.COOP.value,
     'specialResolution', SPECIAL_RESOLUTION, None, None, Filing.Status.PAID,
     {'documents': {
         'legalFilings': [
             {'specialResolution': f'{base_url}/api/v2/businesses/CP7654321/filings/1/documents/specialResolution'},
         ],
         'receipt': f'{base_url}/api/v2/businesses/CP7654321/filings/1/documents/receipt',
     }
     },
     HTTPStatus.OK, '2017-10-01'
     ),
    ('special_res_completed', 'CP7654321', Business.LegalTypes.COOP.value,
     'specialResolution', SPECIAL_RESOLUTION, None, None, Filing.Status.COMPLETED,
     {'documents': {
         'certifiedRules': f'{base_url}/api/v2/businesses/CP7654321/filings/1/documents/certifiedRules',
         'legalFilings': [
             {'specialResolution': f'{base_url}/api/v2/businesses/CP7654321/filings/1/documents/specialResolution'},
         ],
         'receipt': f'{base_url}/api/v2/businesses/CP7654321/filings/1/documents/receipt',
                    'specialResolutionApplication': f'{base_url}/api/v2/businesses/CP7654321/filings/1/documents/specialResolutionApplication',
     }
     },
     HTTPStatus.OK, '2017-10-01'
     ),
    ('special_res_rules_memorandum_included_completed', 'CP7654321', Business.LegalTypes.COOP.value,
     'specialResolution', SPECIAL_RESOLUTION, 'alteration', ALTERATION_MEMORANDUM_RULES_IN_RESOLUTION, Filing.Status.COMPLETED,
     {'documents': {
         'certifiedRules': f'{base_url}/api/v2/businesses/CP7654321/filings/1/documents/certifiedRules',
         'legalFilings': [
             {'specialResolution': f'{base_url}/api/v2/businesses/CP7654321/filings/1/documents/specialResolution'}
         ],
         'receipt': f'{base_url}/api/v2/businesses/CP7654321/filings/1/documents/receipt',
                    'specialResolutionApplication': f'{base_url}/api/v2/businesses/CP7654321/filings/1/documents/specialResolutionApplication',
     }
     },
     HTTPStatus.OK, '2017-10-01'
     ),
    ('specres_court_completed', 'CP7654321', Business.LegalTypes.COOP.value,
     'specialResolution', SPECIAL_RESOLUTION, 'courtOrder', COURT_ORDER, Filing.Status.COMPLETED,
     {'documents': {
         'certifiedRules': f'{base_url}/api/v2/businesses/CP7654321/filings/1/documents/certifiedRules',
         'legalFilings': [
             {'courtOrder': f'{base_url}/api/v2/businesses/CP7654321/filings/1/documents/courtOrder'},
             {'specialResolution': f'{base_url}/api/v2/businesses/CP7654321/filings/1/documents/specialResolution'},
         ],
         'receipt': f'{base_url}/api/v2/businesses/CP7654321/filings/1/documents/receipt',
                    'specialResolutionApplication': f'{base_url}/api/v2/businesses/CP7654321/filings/1/documents/specialResolutionApplication',
     }
     },
     HTTPStatus.OK, '2017-10-01'
     ),
    ('special_res_correction', 'CP7654321', Business.LegalTypes.COOP.value,
     'correction', CORRECTION_CP_SPECIAL_RESOLUTION, None, None, Filing.Status.COMPLETED,
     {'documents': {
         'certificateOfNameCorrection': f'{base_url}/api/v2/businesses/CP7654321/filings/1/documents/certificateOfNameCorrection',
         'certifiedRules': f'{base_url}/api/v2/businesses/CP7654321/filings/1/documents/certifiedRules',
         'legalFilings': [
             {'correction': f'{base_url}/api/v2/businesses/CP7654321/filings/1/documents/correction'},
         ],
         'receipt': f'{base_url}/api/v2/businesses/CP7654321/filings/1/documents/receipt',
         'specialResolution': f'{base_url}/api/v2/businesses/CP7654321/filings/1/documents/specialResolution'
     }
     },
     HTTPStatus.OK, '2017-10-01'
     ),
    ('cp_ia_completed', 'CP7654321', Business.LegalTypes.COOP.value,
     'incorporationApplication', INCORPORATION, None, None, Filing.Status.COMPLETED,
     {'documents': {
         'receipt': f'{base_url}/api/v2/businesses/CP7654321/filings/1/documents/receipt',
                    'certificate': f'{base_url}/api/v2/businesses/CP7654321/filings/1/documents/certificate',
                    'certifiedMemorandum': f'{base_url}/api/v2/businesses/CP7654321/filings/1/documents/certifiedMemorandum',
                    'certifiedRules': f'{base_url}/api/v2/businesses/CP7654321/filings/1/documents/certifiedRules',
                    'legalFilings': [
                        {'incorporationApplication': f'{base_url}/api/v2/businesses/CP7654321/filings/1/documents/incorporationApplication'},
                    ]
     }
     },
     HTTPStatus.OK, '2017-10-01'
     ),
    ('ben_ia_completed', 'BC7654321', Business.LegalTypes.BCOMP.value,
     'incorporationApplication', INCORPORATION, None, None, Filing.Status.COMPLETED,
     {'documents': {'receipt': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt',
                    'certificate': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/certificate',
                    'noticeOfArticles': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles',
                    'legalFilings': [
                        {'incorporationApplication': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/incorporationApplication'},
                    ]
                    }
      },
     HTTPStatus.OK, '2017-10-01'
     ),
    ('ben_ia_completed', 'BC7654321', Business.LegalTypes.BCOMP.value,
     'incorporationApplication', INCORPORATION, None, None, Filing.Status.COMPLETED,
     {'documents': {'certificate': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/certificate',
                    'noticeOfArticles': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles',
                    'legalFilings': [
                        {'incorporationApplication': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/incorporationApplication'},
                    ]
                    }
      },
     HTTPStatus.OK, None
     ),
    ('ben_correction_completed', 'BC7654321', Business.LegalTypes.BCOMP.value,
     'correction', CORRECTION_INCORPORATION, None, None, Filing.Status.COMPLETED,
     {'documents': {'noticeOfArticles': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles',
                    'legalFilings': [
                        {'correction': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/correction'}
                    ]
                    }
      },
     HTTPStatus.OK, None
     ),
    ('bc_correction_completed', 'BC7654321', Business.LegalTypes.COMP.value,
     'correction', CORRECTION_INCORPORATION, None, None, Filing.Status.COMPLETED,
     {'documents': {'noticeOfArticles': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles',
                    'legalFilings': [
                        {'correction': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/correction'}
                    ]
                    }
      },
     HTTPStatus.OK, None
     ),
    ('ccc_correction_completed', 'BC7654321', Business.LegalTypes.BC_CCC.value,
     'correction', CORRECTION_INCORPORATION, None, None, Filing.Status.COMPLETED,
     {'documents': {'noticeOfArticles': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles',
                    'legalFilings': [
                        {'correction': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/correction'}
                    ]
                    }
      },
     HTTPStatus.OK, None
     ),
    ('ulc_correction_completed', 'BC7654321', Business.LegalTypes.BC_ULC_COMPANY.value,
     'correction', CORRECTION_INCORPORATION, None, None, Filing.Status.COMPLETED,
     {'documents': {'noticeOfArticles': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles',
                    'legalFilings': [
                        {'correction': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/correction'}
                    ]
                    }
      },
     HTTPStatus.OK, None
     ),
    ('ben_correction_completed', 'BC7654321', Business.LegalTypes.BCOMP.value,
     'correction', CORRECTION_INCORPORATION, None, None, Filing.Status.COMPLETED,
     {'documents': {'noticeOfArticles': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles',
                    'legalFilings': [
                        {'correction': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/correction'}
                    ]
                    }
      },
     HTTPStatus.OK, None
     ),
    ('ben_alteration_completed', 'BC7654321', Business.LegalTypes.BCOMP.value,
     'alteration', ALTERATION_WITHOUT_NR, None, None, Filing.Status.COMPLETED,
     {'documents': {'noticeOfArticles': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles',
                    'legalFilings': [
                        {'alteration': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/alteration'},
                    ]
                    }
      },
     HTTPStatus.OK, None
     ),
    ('bc_alteration_completed', 'BC7654321', Business.LegalTypes.COMP.value,
     'alteration', ALTERATION_WITHOUT_NR, None, None, Filing.Status.COMPLETED,
     {'documents': {'noticeOfArticles': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles',
                    'legalFilings': [
                        {'alteration': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/alteration'},
                    ]
                    }
      },
     HTTPStatus.OK, None
     ),
    ('cc_alteration_completed', 'BC7654321', Business.LegalTypes.BC_CCC.value,
     'alteration', ALTERATION_WITHOUT_NR, None, None, Filing.Status.COMPLETED,
     {'documents': {'noticeOfArticles': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles',
                    'legalFilings': [
                        {'alteration': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/alteration'},
                    ]
                    }
      },
     HTTPStatus.OK, None
     ),
    ('ulc_alteration_completed', 'BC7654321', Business.LegalTypes.BC_ULC_COMPANY.value,
     'alteration', ALTERATION_WITHOUT_NR, None, None, Filing.Status.COMPLETED,
     {'documents': {'noticeOfArticles': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles',
                    'legalFilings': [
                        {'alteration': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/alteration'},
                    ]
                    }
      },
     HTTPStatus.OK, None
     ),
    ('ben_alteration_with_nr_completed', 'BC7654321', Business.LegalTypes.BCOMP.value,
     'alteration', ALTERATION, None, None, Filing.Status.COMPLETED,
     {'documents': {'certificateOfNameChange': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/certificateOfNameChange',
                    'noticeOfArticles': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles',
                    'legalFilings': [
                        {'alteration': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/alteration'},
                    ]
                    }
      },
     HTTPStatus.OK, None
     ),
    ('ben_changeOfDirector', 'BC7654321', Business.LegalTypes.BCOMP.value,
     'changeOfDirectors', CHANGE_OF_DIRECTORS, None, None, Filing.Status.COMPLETED,
     {'documents': {'noticeOfArticles': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles',
                    'legalFilings': [
                        {'changeOfDirectors': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/changeOfDirectors'},
                    ]
                    }
      },
     HTTPStatus.OK, None
     ),
    ('bc_changeOfDirector', 'BC7654321', Business.LegalTypes.COMP.value,
     'changeOfDirectors', CHANGE_OF_DIRECTORS, None, None, Filing.Status.COMPLETED,
     {'documents': {'noticeOfArticles': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles',
                    'legalFilings': [
                        {
                            'changeOfDirectors': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/changeOfDirectors'},
                    ]
                    }
      },
     HTTPStatus.OK, None
     ),
    ('cc_changeOfDirector', 'BC7654321', Business.LegalTypes.BC_CCC.value,
     'changeOfDirectors', CHANGE_OF_DIRECTORS, None, None, Filing.Status.COMPLETED,
     {'documents': {'noticeOfArticles': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles',
                    'legalFilings': [
                        {
                            'changeOfDirectors': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/changeOfDirectors'},
                    ]
                    }
      },
     HTTPStatus.OK, None
     ),
    ('ulc_changeOfDirector', 'BC7654321', Business.LegalTypes.BC_ULC_COMPANY.value,
     'changeOfDirectors', CHANGE_OF_DIRECTORS, None, None, Filing.Status.COMPLETED,
     {'documents': {'noticeOfArticles': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles',
                    'legalFilings': [
                        {
                            'changeOfDirectors': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/changeOfDirectors'},
                    ]
                    }
      },
     HTTPStatus.OK, None
     ),
    ('cp_correction_ar', 'CP7654321', Business.LegalTypes.COOP.value,
     'correction', CORRECTION_AR, None, None, Filing.Status.COMPLETED,
     {'documents': {'legalFilings': [
         {'correction': f'{base_url}/api/v2/businesses/CP7654321/filings/1/documents/correction'},
     ]
     }
     },
     HTTPStatus.OK, None
     ),
    ('cp_changeOfDirector', 'CP7654321', Business.LegalTypes.COOP.value,
     'changeOfDirectors', CHANGE_OF_DIRECTORS, None, None, Filing.Status.COMPLETED,
     {'documents': {
         'legalFilings': [
             {'changeOfDirectors': f'{base_url}/api/v2/businesses/CP7654321/filings/1/documents/changeOfDirectors'},
         ]
     }
     },
     HTTPStatus.OK, None
     ),
    ('cp_dissolution_completed', 'CP7654321', Business.LegalTypes.COOP.value,
     'dissolution', DISSOLUTION, 'specialResolution', SPECIAL_RESOLUTION, Filing.Status.COMPLETED,
     {
         'documents': {
             'affidavit':
             f'{base_url}/api/v2/businesses/CP7654321/filings/1/documents/affidavit',
             'certificateOfDissolution':
             f'{base_url}/api/v2/businesses/CP7654321/filings/1/documents/certificateOfDissolution',
             'legalFilings': [
                 {'dissolution': f'{base_url}/api/v2/businesses/CP7654321/filings/1/documents/dissolution'},
                 {'specialResolution':
                     f'{base_url}/api/v2/businesses/CP7654321/filings/1/documents/specialResolution'}
             ],
             'receipt': f'{base_url}/api/v2/businesses/CP7654321/filings/1/documents/receipt',
         },
     },
     HTTPStatus.OK, '2017-10-01'
     ),
    ('cp_dissolution_paid', 'CP7654321', Business.LegalTypes.COOP.value,
     'dissolution', DISSOLUTION, None, None, Filing.Status.PAID,
     {
         'documents': {
             'receipt': f'{base_url}/api/v2/businesses/CP7654321/filings/1/documents/receipt',
             'legalFilings': [
                 {'dissolution': f'{base_url}/api/v2/businesses/CP7654321/filings/1/documents/dissolution'},
             ]
         }
     },
     HTTPStatus.OK, '2017-10-01'
     ),
    ('ben_dissolution_completed', 'BC7654321', 'BEN',
     'dissolution', DISSOLUTION, None, None, Filing.Status.COMPLETED,
     {
         'documents': {
             'receipt': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt',
             'certificateOfDissolution':
             f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/certificateOfDissolution',
                 'legalFilings': [
                     {'dissolution': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/dissolution'},
                 ]
         }
     },
     HTTPStatus.OK, '2017-10-01'
     ),
    ('ben_dissolution_paid', 'BC7654321', 'BEN',
     'dissolution', DISSOLUTION, None, None, Filing.Status.PAID,
     {
         'documents': {
             'receipt': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt',
             'legalFilings': [
                 {'dissolution': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/dissolution'},
             ]
         }
     },
     HTTPStatus.OK, '2017-10-01'
     ),
    ('bc_dissolution_completed', 'BC7654321', 'BC',
     'dissolution', DISSOLUTION, None, None, Filing.Status.COMPLETED,
     {
         'documents': {
             'receipt': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt',
             'certificateOfDissolution':
             f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/certificateOfDissolution',
                 'legalFilings': [
                     {'dissolution': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/dissolution'},
                 ]
         }
     },
     HTTPStatus.OK, '2017-10-01'
     ),
    ('cc_dissolution_completed', 'BC7654321', 'CC',
     'dissolution', DISSOLUTION, None, None, Filing.Status.COMPLETED,
     {
         'documents': {
             'receipt': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt',
             'certificateOfDissolution':
             f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/certificateOfDissolution',
                 'legalFilings': [
                     {'dissolution': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/dissolution'},
                 ]
         }
     },
     HTTPStatus.OK, '2017-10-01'
     ),
    ('sp_registration_paid', 'FM7654321', 'SP',
     'registration', REGISTRATION, None, None, Filing.Status.PAID,
     {
         'documents': {
             'receipt': f'{base_url}/api/v2/businesses/FM7654321/filings/1/documents/receipt'
         }
     },
     HTTPStatus.OK, '2017-10-01'
     ),
    ('sp_registration_completed', 'FM7654321', 'SP',
     'registration', REGISTRATION, None, None, Filing.Status.COMPLETED,
     {
         'documents': {
             'receipt': f'{base_url}/api/v2/businesses/FM7654321/filings/1/documents/receipt',
             'legalFilings': [
                 {'registration': f'{base_url}/api/v2/businesses/FM7654321/filings/1/documents/registration'},
             ]
         }
     },
     HTTPStatus.OK, '2017-10-01'
     ),
    ('gp_registration_paid', 'FM7654321', 'GP',
     'registration', REGISTRATION, None, None, Filing.Status.PAID,
     {
         'documents': {
             'receipt': f'{base_url}/api/v2/businesses/FM7654321/filings/1/documents/receipt'
         }
     },
     HTTPStatus.OK, '2017-10-01'
     ),
    ('gp_registration_completed', 'FM7654321', 'GP',
     'registration', REGISTRATION, None, None, Filing.Status.COMPLETED,
     {
         'documents': {
             'receipt': f'{base_url}/api/v2/businesses/FM7654321/filings/1/documents/receipt',
             'legalFilings': [
                 {'registration': f'{base_url}/api/v2/businesses/FM7654321/filings/1/documents/registration'},
             ]
         }
     },
     HTTPStatus.OK, '2017-10-01'
     ),
    ('sp_change_of_registration_paid', 'FM7654321', 'SP',
     'changeOfRegistration', CHANGE_OF_REGISTRATION, None, None, Filing.Status.PAID,
     {
         'documents': {
             'receipt': f'{base_url}/api/v2/businesses/FM7654321/filings/1/documents/receipt',
             'legalFilings': [
                 {'changeOfRegistration':
                  f'{base_url}/api/v2/businesses/FM7654321/filings/1/documents/changeOfRegistration'},
             ]
         }
     },
     HTTPStatus.OK, '2017-10-01'
     ),
    ('sp_change_of_registration_completed', 'FM7654321', 'SP',
     'changeOfRegistration', CHANGE_OF_REGISTRATION, None, None, Filing.Status.COMPLETED,
     {
         'documents': {
             'receipt': f'{base_url}/api/v2/businesses/FM7654321/filings/1/documents/receipt',
             'amendedRegistrationStatement':
                 f'{base_url}/api/v2/businesses/FM7654321/filings/1/documents/amendedRegistrationStatement',
             'legalFilings': [
                 {'changeOfRegistration':
                  f'{base_url}/api/v2/businesses/FM7654321/filings/1/documents/changeOfRegistration'},
             ]
         }
     },
     HTTPStatus.OK, '2017-10-01'
     ),
    ('gp_change_of_registration_paid', 'FM7654321', 'GP',
     'changeOfRegistration', CHANGE_OF_REGISTRATION, None, None, Filing.Status.PAID,
     {
         'documents': {
             'receipt': f'{base_url}/api/v2/businesses/FM7654321/filings/1/documents/receipt',
             'legalFilings': [
                 {'changeOfRegistration':
                  f'{base_url}/api/v2/businesses/FM7654321/filings/1/documents/changeOfRegistration'},
             ]
         }
     },
     HTTPStatus.OK, '2017-10-01'
     ),
    ('gp_change_of_registration_completed', 'FM7654321', 'GP',
     'changeOfRegistration', CHANGE_OF_REGISTRATION, None, None, Filing.Status.COMPLETED,
     {
         'documents': {
             'receipt': f'{base_url}/api/v2/businesses/FM7654321/filings/1/documents/receipt',
             'amendedRegistrationStatement':
                 f'{base_url}/api/v2/businesses/FM7654321/filings/1/documents/amendedRegistrationStatement',
             'legalFilings': [
                 {'changeOfRegistration':
                  f'{base_url}/api/v2/businesses/FM7654321/filings/1/documents/changeOfRegistration'},
             ]
         }
     },
     HTTPStatus.OK, '2017-10-01'
     ),
    ('sp_ia_completed', 'FM7654321', Business.LegalTypes.SOLE_PROP.value,
     'conversion', FIRMS_CONVERSION, None, None, Filing.Status.COMPLETED,
     {'documents': {}},
     HTTPStatus.OK, None
     ),
    ('gp_ia_completed', 'FM7654321', Business.LegalTypes.PARTNERSHIP.value,
     'conversion', FIRMS_CONVERSION, None, None, Filing.Status.COMPLETED,
     {'documents': {}},
     HTTPStatus.OK, None
     ),
    ('sp_dissolution_completed', 'FM7654321', 'SP',
     'dissolution', DISSOLUTION, None, None, Filing.Status.COMPLETED,
     {
         'documents': {
             'receipt': f'{base_url}/api/v2/businesses/FM7654321/filings/1/documents/receipt',
             'legalFilings': [
                 {'dissolution': f'{base_url}/api/v2/businesses/FM7654321/filings/1/documents/dissolution'},
             ]
         }
     },
     HTTPStatus.OK, '2017-10-01'
     ),
    ('sp_dissolution_paid', 'FM7654321', 'SP',
     'dissolution', DISSOLUTION, None, None, Filing.Status.PAID,
     {
         'documents': {
             'receipt': f'{base_url}/api/v2/businesses/FM7654321/filings/1/documents/receipt'
         }
     },
     HTTPStatus.OK, '2017-10-01'
     ),
    ('gp_dissolution_completed', 'FM7654321', 'GP',
     'dissolution', DISSOLUTION, None, None, Filing.Status.COMPLETED,
     {
         'documents': {
             'receipt': f'{base_url}/api/v2/businesses/FM7654321/filings/1/documents/receipt',
             'legalFilings': [
                 {'dissolution': f'{base_url}/api/v2/businesses/FM7654321/filings/1/documents/dissolution'},
             ]
         }
     },
     HTTPStatus.OK, '2017-10-01'
     ),
    ('gp_dissolution_paid', 'FM7654321', 'GP',
     'dissolution', DISSOLUTION, None, None, Filing.Status.PAID,
     {
         'documents': {
             'receipt': f'{base_url}/api/v2/businesses/FM7654321/filings/1/documents/receipt'
         }
     },
     HTTPStatus.OK, '2017-10-01'
     ),
    ('ulc_ia_paid', 'BC7654321', Business.LegalTypes.BC_ULC_COMPANY.value,
     'incorporationApplication', INCORPORATION, None, None, Filing.Status.PAID,
     {'documents': {'receipt': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt',
                    'legalFilings': [
                        {'incorporationApplication':
                         f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/incorporationApplication'},
                    ]
                    }
      },
     HTTPStatus.OK, '2017-10-01'
     ),
    ('ulc_ia_completed', 'BC7654321', Business.LegalTypes.BC_ULC_COMPANY.value,
     'incorporationApplication', INCORPORATION, None, None, Filing.Status.COMPLETED,
     {'documents': {'receipt': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt',
                    'certificate': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/certificate',
                    'noticeOfArticles': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles',
                    'legalFilings': [
                        {'incorporationApplication':
                         f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/incorporationApplication'},
                    ]
                    }
      },
     HTTPStatus.OK, '2017-10-01'
     ),
    ('cc_ia_paid', 'BC7654321', Business.LegalTypes.BC_CCC.value,
     'incorporationApplication', INCORPORATION, None, None, Filing.Status.PAID,
     {'documents': {'receipt': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt',
                    'legalFilings': [
                        {'incorporationApplication':
                         f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/incorporationApplication'},
                    ]
                    }
      },
     HTTPStatus.OK, '2017-10-01'
     ),
    ('cc_ia_completed', 'BC7654321', Business.LegalTypes.BC_CCC.value,
     'incorporationApplication', INCORPORATION, None, None, Filing.Status.COMPLETED,
     {'documents': {'receipt': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt',
                    'certificate': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/certificate',
                    'noticeOfArticles': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles',
                    'legalFilings': [
                        {'incorporationApplication':
                         f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/incorporationApplication'},
                    ]
                    }
      },
     HTTPStatus.OK, '2017-10-01'
     ),
    ('bc_ia_paid', 'BC7654321', Business.LegalTypes.COMP.value,
     'incorporationApplication', INCORPORATION, None, None, Filing.Status.PAID,
     {'documents': {'receipt': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt',
                    'legalFilings': [
                        {'incorporationApplication':
                         f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/incorporationApplication'},
                    ]
                    }
      },
     HTTPStatus.OK, '2017-10-01'
     ),
    ('bc_ia_completed', 'BC7654321', Business.LegalTypes.COMP.value,
     'incorporationApplication', INCORPORATION, None, None, Filing.Status.COMPLETED,
     {'documents': {'receipt': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt',
                    'certificate': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/certificate',
                    'noticeOfArticles': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles',
                    'legalFilings': [
                        {'incorporationApplication':
                         f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/incorporationApplication'},
                    ]
                    }
      },
     HTTPStatus.OK, '2017-10-01'
     ),
    ('bc_ia_completed', 'BC7654321', Business.LegalTypes.COMP.value,
     'incorporationApplication', INCORPORATION, None, None, Filing.Status.WITHDRAWN,
     {'documents': {'receipt': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt',
                    'legalFilings': [
                        {'incorporationApplication':
                         f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/incorporationApplication'},
                    ]
                    }
      },
     HTTPStatus.OK, '2017-10-01'
     ),
    ('bc_annual_report_completed', 'BC7654321', Business.LegalTypes.COMP.value,
     'annualReport', ANNUAL_REPORT, None, None, Filing.Status.COMPLETED,
     {'documents': {'receipt': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt',
                    'legalFilings': [
                        {'annualReport':
                         f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/annualReport'},
                    ]
                    }
      },
     HTTPStatus.OK, '2017-10-01'
     ),
    ('ccc_annual_report_completed', 'BC7654321', Business.LegalTypes.BC_CCC.value,
     'annualReport', ANNUAL_REPORT, None, None, Filing.Status.COMPLETED,
     {'documents': {'receipt': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt',
                    'legalFilings': [
                        {'annualReport':
                         f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/annualReport'},
                    ]
                    }
      },
     HTTPStatus.OK, '2017-10-01'
     ),
    ('ulc_annual_report_completed', 'BC7654321', Business.LegalTypes.BC_ULC_COMPANY.value,
     'annualReport', ANNUAL_REPORT, None, None, Filing.Status.COMPLETED,
     {'documents': {'receipt': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt',
                    'legalFilings': [
                        {'annualReport':
                         f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/annualReport'},
                    ]
                    }
      },
     HTTPStatus.OK, '2017-10-01'
     ),
    ('cp_annual_report_completed', 'CP7654321', Business.LegalTypes.COOP.value,
     'annualReport', ANNUAL_REPORT, None, None, Filing.Status.COMPLETED,
     {'documents': {'receipt': f'{base_url}/api/v2/businesses/CP7654321/filings/1/documents/receipt',
                    'legalFilings': [
                        {'annualReport':
                         f'{base_url}/api/v2/businesses/CP7654321/filings/1/documents/annualReport'},
                    ]
                    }
      },
     HTTPStatus.OK, '2017-10-01'
     ),
    ('ben_annual_report_completed', 'BC7654321', Business.LegalTypes.BCOMP.value,
     'annualReport', ANNUAL_REPORT, None, None, Filing.Status.COMPLETED,
     {'documents': {'receipt': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt',
                    'legalFilings': [
                        {'annualReport':
                         f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/annualReport'},
                    ]
                    }
      },
     HTTPStatus.OK, '2017-10-01'
     ),

    ('bc_annual_report_paid', 'BC7654321', Business.LegalTypes.COMP.value,
     'annualReport', ANNUAL_REPORT, None, None, Filing.Status.PAID,
     {'documents': {'receipt': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt',
                    'legalFilings': [
                        {'annualReport':
                         f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/annualReport'},
                    ]
                    }
      },
     HTTPStatus.OK, '2017-10-01'
     ),
    ('ccc_annual_report_paid', 'BC7654321', Business.LegalTypes.BC_CCC.value,
     'annualReport', ANNUAL_REPORT, None, None, Filing.Status.PAID,
     {'documents': {'receipt': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt',
                    'legalFilings': [
                        {'annualReport':
                         f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/annualReport'},
                    ]
                    }
      },
     HTTPStatus.OK, '2017-10-01'
     ),
    ('ulc_annual_report_paid', 'BC7654321', Business.LegalTypes.BC_ULC_COMPANY.value,
     'annualReport', ANNUAL_REPORT, None, None, Filing.Status.PAID,
     {'documents': {'receipt': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt',
                    'legalFilings': [
                        {'annualReport':
                         f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/annualReport'},
                    ]
                    }
      },
     HTTPStatus.OK, '2017-10-01'
     ),
    ('cp_annual_report_paid', 'CP7654321', Business.LegalTypes.COOP.value,
     'annualReport', ANNUAL_REPORT, None, None, Filing.Status.PAID,
     {'documents': {'receipt': f'{base_url}/api/v2/businesses/CP7654321/filings/1/documents/receipt',
                    'legalFilings': [
                        {'annualReport':
                         f'{base_url}/api/v2/businesses/CP7654321/filings/1/documents/annualReport'},
                    ]
                    }
      },
     HTTPStatus.OK, '2017-10-01'
     ),
    ('ben_annual_report_paid', 'BC7654321', Business.LegalTypes.BCOMP.value,
     'annualReport', ANNUAL_REPORT, None, None, Filing.Status.PAID,
     {'documents': {'receipt': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt',
                    'legalFilings': [
                        {'annualReport':
                         f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/annualReport'},
                    ]
                    }
      },
     HTTPStatus.OK, '2017-10-01'
     ),
    ('ben_agmExtension_completed', 'BC7654321',
     Business.LegalTypes.BCOMP.value, 'agmExtension', AGM_EXTENSION,
     None, None, Filing.Status.COMPLETED,
     {'documents': {
         'letterOfAgmExtension': f'{base_url}/api/v2/businesses/BC7654321/filings/documents/letterOfAgmExtension',
         'receipt': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt'
     }
     },
     HTTPStatus.OK, '2017-10-01'
     ),
    ('ben_agmLocationChange_paid', 'BC7654321',
     Business.LegalTypes.BCOMP.value, 'agmExtension', AGM_EXTENSION,
     None, None, Filing.Status.PAID,
     {'documents': {
         'receipt': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt'
     }
     },
     HTTPStatus.OK, '2017-10-01'
     ),
    ('ben_agmLocationChange_completed', 'BC7654321',
     Business.LegalTypes.BCOMP.value, 'agmLocationChange', AGM_LOCATION_CHANGE,
     None, None, Filing.Status.COMPLETED,
     {'documents': {
         'letterOfAgmLocationChange': f'{base_url}/api/v2/businesses/BC7654321/filings/documents/letterOfAgmLocationChange',
         'receipt': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt'
     }
     },
     HTTPStatus.OK, '2017-10-01'
     ),
    ('ben_agmLocationChange_paid', 'BC7654321',
     Business.LegalTypes.BCOMP.value, 'agmLocationChange', AGM_LOCATION_CHANGE,
     None, None, Filing.Status.PAID,
     {'documents': {
         'receipt': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt'
     }
     },
     HTTPStatus.OK, '2017-10-01'
     ),
    ('ben_amalgamation_completed', 'BC7654321',
     Business.LegalTypes.BCOMP.value, 'amalgamationApplication', AMALGAMATION_APPLICATION,
     None, None, Filing.Status.COMPLETED,
     {'documents': {
         'certificateOfAmalgamation': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/certificateOfAmalgamation',
         'legalFilings': [
             {
                 'amalgamationApplication': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/amalgamationApplication'
             }
         ],
         'noticeOfArticles': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles',
         'receipt': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt'
     }
     },
        HTTPStatus.OK, '2017-10-01'
     ),
    ('ben_amalgamation_paid', 'BC7654321',
     Business.LegalTypes.BCOMP.value, 'amalgamationApplication', AMALGAMATION_APPLICATION,
     None, None, Filing.Status.PAID,
     {'documents': {
         'legalFilings': [
             {
                 'amalgamationApplication': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/amalgamationApplication'
             }
         ],
         'receipt': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt'
     }
     },
        HTTPStatus.OK, '2017-10-01'
     ),
    ('ben_changeOfAddress', 'BC7654321', Business.LegalTypes.BCOMP.value,
     'changeOfAddress', CHANGE_OF_ADDRESS, None, None, Filing.Status.COMPLETED,
     {'documents': {'noticeOfArticles': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles',
                    'legalFilings': [
                        {'changeOfAddress': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/changeOfAddress'},
                    ]
                    }
      },
     HTTPStatus.OK, None
     ),
    ('bc_changeOfAddress', 'BC7654321', Business.LegalTypes.COMP.value,
     'changeOfAddress', CHANGE_OF_ADDRESS, None, None, Filing.Status.COMPLETED,
     {'documents': {'noticeOfArticles': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles',
                    'legalFilings': [
                        {
                            'changeOfAddress': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/changeOfAddress'},
                    ]
                    }
      },
     HTTPStatus.OK, None
     ),
    ('cc_changeOfAddress', 'BC7654321', Business.LegalTypes.BC_CCC.value,
     'changeOfAddress', CHANGE_OF_ADDRESS, None, None, Filing.Status.COMPLETED,
     {'documents': {'noticeOfArticles': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles',
                    'legalFilings': [
                        {
                            'changeOfAddress': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/changeOfAddress'},
                    ]
                    }
      },
     HTTPStatus.OK, None
     ),
    ('ulc_changeOfAddress', 'BC7654321', Business.LegalTypes.BC_ULC_COMPANY.value,
     'changeOfAddress', CHANGE_OF_ADDRESS, None, None, Filing.Status.COMPLETED,
     {'documents': {'noticeOfArticles': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles',
                    'legalFilings': [
                        {
                            'changeOfAddress': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/changeOfAddress'},
                    ]
                    }
      },
     HTTPStatus.OK, None
     ),
    ('bc_restoration_completed', 'BC7654321', Business.LegalTypes.COMP.value,
     'restoration', RESTORATION, None, None, Filing.Status.COMPLETED,
     {'documents': {'receipt': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt',
                    'certificateOfRestoration': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/certificateOfRestoration',
                    'noticeOfArticles': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles',
                    'legalFilings': [
                        {
                            'restoration': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/restoration'},
                    ]
                    }
      },
     HTTPStatus.OK, '2017-10-01'
     ),
    ('bc_restoration_paid', 'BC7654321', Business.LegalTypes.COMP.value,
     'restoration', RESTORATION, None, None, Filing.Status.PAID,
     {'documents': {'receipt': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt',
                    'legalFilings': [
                        {
                            'restoration': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/restoration'},
                    ]
                    }
      },
     HTTPStatus.OK, '2017-10-01'
     ),
    ('ben_restoration_completed', 'BC7654321', Business.LegalTypes.BCOMP.value,
     'restoration', RESTORATION, None, None, Filing.Status.COMPLETED,
     {'documents': {'receipt': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt',
                    'certificateOfRestoration': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/certificateOfRestoration',
                    'noticeOfArticles': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles',
                    'legalFilings': [
                        {
                            'restoration': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/restoration'},
                    ]
                    }
      },
     HTTPStatus.OK, '2017-10-01'
     ),
    ('ben_restoration_paid', 'BC7654321', Business.LegalTypes.BCOMP.value,
     'restoration', RESTORATION, None, None, Filing.Status.PAID,
     {'documents': {'receipt': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt',
                    'legalFilings': [
                        {
                            'restoration': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/restoration'},
                    ]
                    }
      },
     HTTPStatus.OK, '2017-10-01'
     ),
    ('ulc_restoration_completed', 'BC7654321', Business.LegalTypes.BC_ULC_COMPANY.value,
     'restoration', RESTORATION, None, None, Filing.Status.COMPLETED,
     {'documents': {'receipt': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt',
                    'certificateOfRestoration': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/certificateOfRestoration',
                    'noticeOfArticles': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles',
                    'legalFilings': [
                        {
                            'restoration': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/restoration'},
                    ]
                    }
      },
     HTTPStatus.OK, '2017-10-01'
     ),
    ('ulc_restoration_paid', 'BC7654321', Business.LegalTypes.BC_ULC_COMPANY.value,
     'restoration', RESTORATION, None, None, Filing.Status.PAID,
     {'documents': {'receipt': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt',
                    'legalFilings': [
                        {
                            'restoration': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/restoration'},
                    ]
                    }
      },
     HTTPStatus.OK, '2017-10-01'
     ),
    ('cc_restoration_completed', 'BC7654321', Business.LegalTypes.BC_CCC.value,
     'restoration', RESTORATION, None, None, Filing.Status.COMPLETED,
     {'documents': {'receipt': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt',
                    'certificateOfRestoration': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/certificateOfRestoration',
                    'noticeOfArticles': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles',
                    'legalFilings': [
                        {
                            'restoration': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/restoration'},
                    ]
                    }
      },
     HTTPStatus.OK, '2017-10-01'
     ),
    ('cc_restoration_paid', 'BC7654321', Business.LegalTypes.BC_CCC.value,
     'restoration', RESTORATION, None, None, Filing.Status.PAID,
     {'documents': {'receipt': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt',
                    'legalFilings': [
                        {
                            'restoration': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/restoration'},
                    ]
                    }
      },
     HTTPStatus.OK, '2017-10-01'
     ),

    ('bc_continuationOut_complete', 'BC7654321', Business.LegalTypes.COMP.value,
     'continuationOut', CONTINUATION_OUT, None, None, Filing.Status.COMPLETED,
     {'documents': {
         'receipt': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt'
     }
     },
     HTTPStatus.OK, '2017-10-1'
     ),
    ('ulc_continuationOut_complete', 'BC7654321', Business.LegalTypes.BC_ULC_COMPANY.value,
     'continuationOut', CONTINUATION_OUT, None, None, Filing.Status.COMPLETED,
     {'documents': {
         'receipt': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt'
     }
     },
     HTTPStatus.OK, '2017-10-1'
     ),
    ('cc_continuationOut_complete', 'BC7654321', Business.LegalTypes.BC_CCC.value,
     'continuationOut', CONTINUATION_OUT, None, None, Filing.Status.COMPLETED,
     {'documents': {
         'receipt': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt'
     }
     },
     HTTPStatus.OK, '2017-10-1'
     ),
    ('ben_continuationOut_complete', 'BC7654321', Business.LegalTypes.BCOMP.value, 'continuationOut', CONTINUATION_OUT, None, None, Filing.Status.COMPLETED,
     {'documents': {
         'receipt': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt'
     }
     },
     HTTPStatus.OK, '2017-10-1'
     ),
    ('bc_continuationOut_paid', 'BC7654321', Business.LegalTypes.COMP.value,
     'continuationOut', CONTINUATION_OUT, None, None, Filing.Status.PAID,
     {'documents': {
         'receipt': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt'
     }
     },
     HTTPStatus.OK, '2017-10-1'
     ),
    ('ulc_continuationOut_paid', 'BC7654321', Business.LegalTypes.BC_ULC_COMPANY.value,
     'continuationOut', CONTINUATION_OUT, None, None, Filing.Status.PAID,
     {'documents': {
         'receipt': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt'
     }
     },
     HTTPStatus.OK, '2017-10-1'
     ),
    ('cc_continuationOut_paid', 'BC7654321', Business.LegalTypes.BC_CCC.value,
     'continuationOut', CONTINUATION_OUT, None, None, Filing.Status.PAID,
     {'documents': {
         'receipt': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt'
     }
     },
     HTTPStatus.OK, '2017-10-1'
     ),
    ('ben_continuationOut_paid', 'BC7654321', Business.LegalTypes.BCOMP.value, 'continuationOut', CONTINUATION_OUT, None, None, Filing.Status.PAID,
     {'documents': {
         'receipt': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt'
     }
     },
     HTTPStatus.OK, '2017-10-1'
     ),
    ('cben_cont_in_completed', 'C7654321', Business.LegalTypes.BCOMP_CONTINUE_IN.value,
     'continuationIn', CONTINUATION_IN, None, None, Filing.Status.COMPLETED,
     {'documents': {'receipt': f'{base_url}/api/v2/businesses/C7654321/filings/1/documents/receipt',
                    'certificateOfContinuation': f'{base_url}/api/v2/businesses/C7654321/filings/1/documents/certificateOfContinuation',
                    'noticeOfArticles': f'{base_url}/api/v2/businesses/C7654321/filings/1/documents/noticeOfArticles',
                    'legalFilings': [
                        {'continuationIn': f'{base_url}/api/v2/businesses/C7654321/filings/1/documents/continuationIn'},
                    ]
                    }
      },
     HTTPStatus.OK, '2024-06-06'
     ),
    ('cben_cont_in_completed', 'C7654321', Business.LegalTypes.BCOMP_CONTINUE_IN.value,
     'continuationIn', CONTINUATION_IN, None, None, Filing.Status.COMPLETED,
     {'documents': {'certificateOfContinuation': f'{base_url}/api/v2/businesses/C7654321/filings/1/documents/certificateOfContinuation',
                    'noticeOfArticles': f'{base_url}/api/v2/businesses/C7654321/filings/1/documents/noticeOfArticles',
                    'legalFilings': [
                        {'continuationIn': f'{base_url}/api/v2/businesses/C7654321/filings/1/documents/continuationIn'},
                    ]
                    }
      },
     HTTPStatus.OK, None
     ),
    ('c_cont_in_completed', 'C7654322', Business.LegalTypes.CONTINUE_IN.value,
     'continuationIn', CONTINUATION_IN, None, None, Filing.Status.COMPLETED,
     {'documents': {'receipt': f'{base_url}/api/v2/businesses/C7654322/filings/1/documents/receipt',
                    'certificateOfContinuation': f'{base_url}/api/v2/businesses/C7654322/filings/1/documents/certificateOfContinuation',
                    'noticeOfArticles': f'{base_url}/api/v2/businesses/C7654322/filings/1/documents/noticeOfArticles',
                    'legalFilings': [
                        {'continuationIn': f'{base_url}/api/v2/businesses/C7654322/filings/1/documents/continuationIn'},
                    ]
                    }
      },
     HTTPStatus.OK, '2024-06-06'
     ),
    ('c_cont_in_completed', 'C7654322', Business.LegalTypes.CONTINUE_IN.value,
     'continuationIn', CONTINUATION_IN, None, None, Filing.Status.COMPLETED,
     {'documents': {'certificateOfContinuation': f'{base_url}/api/v2/businesses/C7654322/filings/1/documents/certificateOfContinuation',
                    'noticeOfArticles': f'{base_url}/api/v2/businesses/C7654322/filings/1/documents/noticeOfArticles',
                    'legalFilings': [
                        {'continuationIn': f'{base_url}/api/v2/businesses/C7654322/filings/1/documents/continuationIn'},
                    ]
                    }
      },
     HTTPStatus.OK, None
     ),
    ('cul_cont_in_completed', 'C7654323', Business.LegalTypes.ULC_CONTINUE_IN.value,
     'continuationIn', CONTINUATION_IN, None, None, Filing.Status.COMPLETED,
     {'documents': {'receipt': f'{base_url}/api/v2/businesses/C7654323/filings/1/documents/receipt',
                    'certificateOfContinuation': f'{base_url}/api/v2/businesses/C7654323/filings/1/documents/certificateOfContinuation',
                    'noticeOfArticles': f'{base_url}/api/v2/businesses/C7654323/filings/1/documents/noticeOfArticles',
                    'legalFilings': [
                        {'continuationIn': f'{base_url}/api/v2/businesses/C7654323/filings/1/documents/continuationIn'},
                    ]
                    }
      },
     HTTPStatus.OK, '2024-06-06'
     ),
    ('cul_cont_in_completed', 'C7654323', Business.LegalTypes.ULC_CONTINUE_IN.value,
     'continuationIn', CONTINUATION_IN, None, None, Filing.Status.COMPLETED,
     {'documents': {'certificateOfContinuation': f'{base_url}/api/v2/businesses/C7654323/filings/1/documents/certificateOfContinuation',
                    'noticeOfArticles': f'{base_url}/api/v2/businesses/C7654323/filings/1/documents/noticeOfArticles',
                    'legalFilings': [
                        {'continuationIn': f'{base_url}/api/v2/businesses/C7654323/filings/1/documents/continuationIn'},
                    ]
                    }
      },
     HTTPStatus.OK, None
     ),
    ('ccc_cont_in_completed', 'C7654324', Business.LegalTypes.CCC_CONTINUE_IN.value,
     'continuationIn', CONTINUATION_IN, None, None, Filing.Status.COMPLETED,
     {'documents': {'receipt': f'{base_url}/api/v2/businesses/C7654324/filings/1/documents/receipt',
                    'certificateOfContinuation': f'{base_url}/api/v2/businesses/C7654324/filings/1/documents/certificateOfContinuation',
                    'noticeOfArticles': f'{base_url}/api/v2/businesses/C7654324/filings/1/documents/noticeOfArticles',
                    'legalFilings': [
                        {'continuationIn': f'{base_url}/api/v2/businesses/C7654324/filings/1/documents/continuationIn'},
                    ]
                    }
      },
     HTTPStatus.OK, '2024-06-06'
     ),
    ('ccc_cont_in_completed', 'C7654324', Business.LegalTypes.CCC_CONTINUE_IN.value,
     'continuationIn', CONTINUATION_IN, None, None, Filing.Status.COMPLETED,
     {'documents': {'certificateOfContinuation': f'{base_url}/api/v2/businesses/C7654324/filings/1/documents/certificateOfContinuation',
                    'noticeOfArticles': f'{base_url}/api/v2/businesses/C7654324/filings/1/documents/noticeOfArticles',
                    'legalFilings': [
                        {'continuationIn': f'{base_url}/api/v2/businesses/C7654324/filings/1/documents/continuationIn'},
                    ]
                    }
      },
     HTTPStatus.OK, None
     ),
    ('bc_notice_of_withdrawal_completed', 'BC7654321', Business.LegalTypes.COMP.value,
     'noticeOfWithdrawal', MOCK_NOTICE_OF_WITHDRAWAL, None, None, Filing.Status.COMPLETED,
     {'documents': {'receipt': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt',
                    'legalFilings': [
                        {'noticeOfWithdrawal': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfWithdrawal'},
                    ]
                    }
      },
     HTTPStatus.OK, '2024-09-25'
     ),
    ('ben_notice_of_withdrawal_completed', 'BC7654321', Business.LegalTypes.BCOMP.value,
     'noticeOfWithdrawal', MOCK_NOTICE_OF_WITHDRAWAL, None, None, Filing.Status.COMPLETED,
     {'documents': {'receipt': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt',
                    'legalFilings': [
                        {'noticeOfWithdrawal': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfWithdrawal'},
                    ]
                    }
      },
     HTTPStatus.OK, '2024-09-25'
     ),
    ('cc_notice_of_withdrawal_completed', 'BC7654321', Business.LegalTypes.BC_CCC.value,
     'noticeOfWithdrawal', MOCK_NOTICE_OF_WITHDRAWAL, None, None, Filing.Status.COMPLETED,
     {'documents': {'receipt': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt',
                    'legalFilings': [
                        {'noticeOfWithdrawal': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfWithdrawal'},
                    ]
                    }
      },
     HTTPStatus.OK, '2024-09-25'
     ),
    ('ulc_notice_of_withdrawal_completed', 'BC7654321', Business.LegalTypes.BC_ULC_COMPANY.value,
     'noticeOfWithdrawal', MOCK_NOTICE_OF_WITHDRAWAL, None, None, Filing.Status.COMPLETED,
     {'documents': {'receipt': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt',
                    'legalFilings': [
                        {'noticeOfWithdrawal': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfWithdrawal'},
                    ]
                    }
      },
     HTTPStatus.OK, '2024-09-25'
     ),
    ('c_notice_of_withdrawal_completed', 'C7654321', Business.LegalTypes.CONTINUE_IN.value,
     'noticeOfWithdrawal', MOCK_NOTICE_OF_WITHDRAWAL, None, None, Filing.Status.COMPLETED,
     {'documents': {'receipt': f'{base_url}/api/v2/businesses/C7654321/filings/1/documents/receipt',
                    'legalFilings': [
                        {'noticeOfWithdrawal': f'{base_url}/api/v2/businesses/C7654321/filings/1/documents/noticeOfWithdrawal'},
                    ]
                    }
      },
     HTTPStatus.OK, '2024-09-25'
     ),
    ('ccc_notice_of_withdrawal_completed', 'C7654321', Business.LegalTypes.CCC_CONTINUE_IN.value,
     'noticeOfWithdrawal', MOCK_NOTICE_OF_WITHDRAWAL, None, None, Filing.Status.COMPLETED,
     {'documents': {'receipt': f'{base_url}/api/v2/businesses/C7654321/filings/1/documents/receipt',
                    'legalFilings': [
                        {'noticeOfWithdrawal': f'{base_url}/api/v2/businesses/C7654321/filings/1/documents/noticeOfWithdrawal'},
                    ]
                    }
      },
     HTTPStatus.OK, '2024-09-25'
     ),
    ('cben_notice_of_withdrawal_completed', 'C7654321', Business.LegalTypes.BCOMP_CONTINUE_IN.value,
     'noticeOfWithdrawal', MOCK_NOTICE_OF_WITHDRAWAL, None, None, Filing.Status.COMPLETED,
     {'documents': {'receipt': f'{base_url}/api/v2/businesses/C7654321/filings/1/documents/receipt',
                    'legalFilings': [
                        {'noticeOfWithdrawal': f'{base_url}/api/v2/businesses/C7654321/filings/1/documents/noticeOfWithdrawal'},
                    ]
                    }
      },
     HTTPStatus.OK, '2024-09-25'
     ),
    ('cul_notice_of_withdrawal_completed', 'C7654321', Business.LegalTypes.ULC_CONTINUE_IN.value,
     'noticeOfWithdrawal', MOCK_NOTICE_OF_WITHDRAWAL, None, None, Filing.Status.COMPLETED,
     {'documents': {'receipt': f'{base_url}/api/v2/businesses/C7654321/filings/1/documents/receipt',
                    'legalFilings': [
                        {'noticeOfWithdrawal': f'{base_url}/api/v2/businesses/C7654321/filings/1/documents/noticeOfWithdrawal'},
                    ]
                    }
      },
     HTTPStatus.OK, '2024-09-25'
     ),
    ('bc_notice_of_withdrawal_paid', 'BC7654321', Business.LegalTypes.COMP.value,
     'noticeOfWithdrawal', MOCK_NOTICE_OF_WITHDRAWAL, None, None, Filing.Status.PAID,
     {'documents': {'receipt': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt',
                    'legalFilings': [
                        {'noticeOfWithdrawal': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfWithdrawal'},
                    ]
                    }
      },
     HTTPStatus.OK, '2024-09-26'
     ),
    ('ben_notice_of_withdrawal_paid', 'BC7654321', Business.LegalTypes.BCOMP.value,
     'noticeOfWithdrawal', MOCK_NOTICE_OF_WITHDRAWAL, None, None, Filing.Status.PAID,
     {'documents': {'receipt': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt',
                    'legalFilings': [
                        {'noticeOfWithdrawal': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfWithdrawal'},
                    ]
                    }
      },
     HTTPStatus.OK, '2024-09-26'
     ),
    ('cc_notice_of_withdrawal_paid', 'BC7654321', Business.LegalTypes.BC_CCC.value,
     'noticeOfWithdrawal', MOCK_NOTICE_OF_WITHDRAWAL, None, None, Filing.Status.PAID,
     {'documents': {'receipt': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt',
                    'legalFilings': [
                        {'noticeOfWithdrawal': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfWithdrawal'},
                    ]
                    }
      },
     HTTPStatus.OK, '2024-09-26'
     ),
    ('ulc_notice_of_withdrawal_paid', 'BC7654321', Business.LegalTypes.BC_ULC_COMPANY.value,
     'noticeOfWithdrawal', MOCK_NOTICE_OF_WITHDRAWAL, None, None, Filing.Status.PAID,
     {'documents': {'receipt': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt',
                    'legalFilings': [
                        {'noticeOfWithdrawal': f'{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfWithdrawal'},
                    ]
                    }
      },
     HTTPStatus.OK, '2024-09-26'
     ),
    ('c_notice_of_withdrawal_paid', 'C7654321', Business.LegalTypes.CONTINUE_IN.value,
     'noticeOfWithdrawal', MOCK_NOTICE_OF_WITHDRAWAL, None, None, Filing.Status.PAID,
     {'documents': {'receipt': f'{base_url}/api/v2/businesses/C7654321/filings/1/documents/receipt',
                    'legalFilings': [
                        {'noticeOfWithdrawal': f'{base_url}/api/v2/businesses/C7654321/filings/1/documents/noticeOfWithdrawal'},
                    ]
                    }
      },
     HTTPStatus.OK, '2024-09-26'
     ),
    ('ccc_notice_of_withdrawal_paid', 'C7654321', Business.LegalTypes.CCC_CONTINUE_IN.value,
     'noticeOfWithdrawal', MOCK_NOTICE_OF_WITHDRAWAL, None, None, Filing.Status.PAID,
     {'documents': {'receipt': f'{base_url}/api/v2/businesses/C7654321/filings/1/documents/receipt',
                    'legalFilings': [
                        {'noticeOfWithdrawal': f'{base_url}/api/v2/businesses/C7654321/filings/1/documents/noticeOfWithdrawal'},
                    ]
                    }
      },
     HTTPStatus.OK, '2024-09-26'
     ),
    ('cben_notice_of_withdrawal_paid', 'C7654321', Business.LegalTypes.BCOMP_CONTINUE_IN.value,
     'noticeOfWithdrawal', MOCK_NOTICE_OF_WITHDRAWAL, None, None, Filing.Status.PAID,
     {'documents': {'receipt': f'{base_url}/api/v2/businesses/C7654321/filings/1/documents/receipt',
                    'legalFilings': [
                        {'noticeOfWithdrawal': f'{base_url}/api/v2/businesses/C7654321/filings/1/documents/noticeOfWithdrawal'},
                    ]
                    }
      },
     HTTPStatus.OK, '2024-09-26'
     ),
    ('cul_notice_of_withdrawal_paid', 'C7654321', Business.LegalTypes.ULC_CONTINUE_IN.value,
     'noticeOfWithdrawal', MOCK_NOTICE_OF_WITHDRAWAL, None, None, Filing.Status.PAID,
     {'documents': {'receipt': f'{base_url}/api/v2/businesses/C7654321/filings/1/documents/receipt',
                    'legalFilings': [
                        {'noticeOfWithdrawal': f'{base_url}/api/v2/businesses/C7654321/filings/1/documents/noticeOfWithdrawal'},
                    ]
                    }
      },
     HTTPStatus.OK, '2024-09-26'
     )
])
def test_document_list_for_various_filing_states(session, mocker, client, jwt,
                                                 test_name,
                                                 identifier,
                                                 entity_type,
                                                 filing_name_1, legal_filing_1,
                                                 filing_name_2, legal_filing_2,
                                                 status, expected_msg, expected_http_code,
                                                 payment_completion_date):
    """Test document list based on filing states."""
    # Setup
    # identifier = 'CP7654321'
    business = factory_business(identifier, entity_type=entity_type)

    filing_json = copy.deepcopy(FILING_HEADER)
    filing_json['filing']['header']['name'] = filing_name_1
    filing_json['filing']['business']['legalType'] = entity_type
    if filing_name_1 == 'incorporationApplication':
        legal_filing_1['nameRequest']['legalType'] = entity_type
    filing_json['filing'][filing_name_1] = legal_filing_1

    if legal_filing_2:
        filing_json['filing'][filing_name_2] = legal_filing_2

    filing_date = datetime.utcnow()
    filing = factory_filing(business, filing_json, filing_date=filing_date)
    filing.skip_status_listener = True
    filing._status = status
    filing._payment_completion_date = payment_completion_date
    filing.save()

    if status == 'COMPLETED':
        lf = [list(x.keys()) for x in filing.legal_filings()]
        legal_filings = [item for sublist in lf for item in sublist]
        meta_data = {'legalFilings': legal_filings}
        filing._meta_data = filer_action(filing_name_1, filing_json, meta_data, business)
        filing.save()

        if filing_name_1 == 'continuationIn':
            affidavit_file_key = meta_data['continuationIn']['affidavitFileKey']
            expected_msg['documents']['staticDocuments'] = [
                {
                    'name': 'Unlimited Liability Corporation Information',
                    'url': f'{base_url}/api/v2/businesses/{identifier}/filings/1/documents/static/{affidavit_file_key}'
                }
            ]
            for file in meta_data['continuationIn']['authorizationFiles']:
                file_key = file.get('fileKey')
                expected_msg['documents']['staticDocuments'].append({
                    'name': file.get('fileName'),
                    'url': f'{base_url}/api/v2/businesses/{identifier}/filings/1/documents/static/{file_key}'
                })

    mocker.patch('legal_api.core.filing.has_roles', return_value=True)
    rv = client.get(f'/api/v2/businesses/{business.identifier}/filings/{filing.id}/documents',
                    headers=create_header(jwt, [STAFF_ROLE], business.identifier))

    # remove the filing ID
    rv_data = json.loads(re.sub("/\d+/", "/", rv.data.decode("utf-8")).replace("\n", ""))
    expected = json.loads(re.sub("/\d+/", "/", json.dumps(expected_msg)))

    assert rv.status_code == expected_http_code
    assert rv_data == expected


def filer_action(filing_name, filing_json, meta_data, business):
    """Helper function for test_document_list_for_various_filing_states."""
    if filing_name == 'alteration' and \
            (legal_name := filing_json['filing']['alteration'].get('nameRequest', {}).get('legalName')):
        meta_data['alteration'] = {}
        meta_data['alteration']['fromLegalName'] = business.legal_name
        meta_data['alteration']['toLegalName'] = legal_name

    if filing_name == 'continuationIn':
        continuation_in = filing_json['filing']['continuationIn']
        meta_data['continuationIn'] = {}
        meta_data['continuationIn']['affidavitFileKey'] = continuation_in['foreignJurisdiction']['affidavitFileKey']
        meta_data['continuationIn']['authorizationFiles'] = continuation_in['authorization']['files']

    if filing_name == 'correction' and business.legal_type == 'CP':
        meta_data['correction'] = {}
        if (legal_name := filing_json['filing']['correction'].get('nameRequest', {}).get('legalName')):
            meta_data['correction']['fromLegalName'] = business.legal_name
            meta_data['correction']['toLegalName'] = legal_name

        if filing_json['filing']['correction'].get('rulesFileKey'):
            meta_data['correction']['uploadNewRules'] = True

        if filing_json['filing']['correction'].get('memorandumFileKey'):
            meta_data['correction']['uploadNewMemorandum'] = True

        if filing_json['filing']['correction'].get('resolution'):
            meta_data['correction']['hasResolution'] = True

    if filing_name == 'specialResolution' and business.legal_type == 'CP':
        meta_data['alteration'] = {}
        meta_data['alteration']['uploadNewRules'] = True

    return meta_data


@pytest.mark.parametrize('test_name, temp_identifier, identifier, entity_type, filing_name, legal_filing, status, expected_msg, expected_http_code', [
    ('ben_ia_paid', 'Tb31yQIuBw', None, Business.LegalTypes.BCOMP.value,
     'incorporationApplication', INCORPORATION, Filing.Status.PAID,
     {'documents': {'receipt': f'{base_url}/api/v2/businesses/Tb31yQIuBw/filings/1/documents/receipt',
                    'legalFilings': [
                        {'incorporationApplication': f'{base_url}/api/v2/businesses/Tb31yQIuBw/filings/1/documents/incorporationApplication'},
                    ]}},
     HTTPStatus.OK
     ),
    ('ben_ia_paid', 'Tb31yQIuBw', None, Business.LegalTypes.BCOMP.value,
     'incorporationApplication', INCORPORATION, Filing.Status.WITHDRAWN,
     {'documents': {'receipt': f'{base_url}/api/v2/businesses/Tb31yQIuBw/filings/1/documents/receipt',
                    'legalFilings': [
                        {'incorporationApplication': f'{base_url}/api/v2/businesses/Tb31yQIuBw/filings/1/documents/incorporationApplication'},
                    ]}},
     HTTPStatus.OK
     ),
    ('ben_ia_completed', 'Tb31yQIuBw', 'BC7654321', Business.LegalTypes.BCOMP.value,
     'incorporationApplication', INCORPORATION, Filing.Status.COMPLETED,
     {'documents': {}}, HTTPStatus.OK
     ),
    ('ben_amalgamation_paid', 'Tb31yQIuBw', None,
     Business.LegalTypes.BCOMP.value, 'amalgamationApplication', AMALGAMATION_APPLICATION, Filing.Status.PAID,
     {'documents': {
         'legalFilings': [
             {'amalgamationApplication': f'{base_url}/api/v2/businesses/Tb31yQIuBw/filings/1/documents/amalgamationApplication'}
         ],
         'receipt': f'{base_url}/api/v2/businesses/Tb31yQIuBw/filings/1/documents/receipt'
     }
     }, HTTPStatus.OK
     ),
    ('ben_amalgamation_completed', 'Tb31yQIuBw', 'BC7654321',
     Business.LegalTypes.BCOMP.value, 'amalgamationApplication', AMALGAMATION_APPLICATION, Filing.Status.COMPLETED,
     {'documents': {}}, HTTPStatus.OK
     ),
    ('cben_ci_paid', 'Tb31yQIuBw', None, Business.LegalTypes.BCOMP_CONTINUE_IN.value,
     'continuationIn', CONTINUATION_IN, Filing.Status.PAID,
     {'documents': {'receipt': f'{base_url}/api/v2/businesses/Tb31yQIuBw/filings/1/documents/receipt',
                    'legalFilings': [
                        {'continuationIn': f'{base_url}/api/v2/businesses/Tb31yQIuBw/filings/1/documents/continuationIn'},
                    ]}},
     HTTPStatus.OK
     ),
    ('cben_ci_completed', 'Tb31yQIuBw', 'BC7654321', Business.LegalTypes.BCOMP_CONTINUE_IN.value,
     'continuationIn', CONTINUATION_IN, Filing.Status.COMPLETED,
     {'documents': {}}, HTTPStatus.OK
     ),
    ('sp_registration_paid', 'Tb31yQIuBw', None, Business.LegalTypes.SOLE_PROP.value,
     'registration', REGISTRATION, Filing.Status.PAID,
     {
         'documents': {
             'receipt': f'{base_url}/api/v2/businesses/Tb31yQIuBw/filings/1/documents/receipt'
         }
     },
        HTTPStatus.OK
     ),
    ('sp_registration_completed', 'Tb31yQIuBw', 'FM7654321', Business.LegalTypes.SOLE_PROP.value,
     'registration', REGISTRATION, Filing.Status.COMPLETED,
     {'documents': {}}, HTTPStatus.OK
     ),
])
def test_temp_document_list_for_various_filing_states(mocker, session, client, jwt,
                                                      test_name,
                                                      temp_identifier,
                                                      identifier,
                                                      entity_type,
                                                      filing_name, legal_filing,
                                                      status, expected_msg, expected_http_code):
    """Test document list based on filing states with temp identifier."""
    # Setup
    filing_json = copy.deepcopy(FILING_HEADER)
    filing_json['filing']['header']['name'] = filing_name
    filing_json['filing']['business']['legalType'] = entity_type
    if filing_name == 'incorporationApplication':
        legal_filing['nameRequest']['legalType'] = entity_type
    filing_json['filing'][filing_name] = legal_filing

    filing_date = datetime.utcnow()

    temp_reg = RegistrationBootstrap()
    temp_reg._identifier = temp_identifier
    temp_reg.save()

    business = None
    if status == 'COMPLETED':
        business = factory_business(identifier, entity_type=entity_type)
    filing = factory_filing(business, filing_json, filing_date=filing_date)
    filing.skip_status_listener = True
    filing._status = status
    filing._payment_completion_date = '2017-10-01'
    filing.temp_reg = temp_identifier
    filing.save()

    mocker.patch('legal_api.core.filing.has_roles', return_value=True)
    rv = client.get(f'/api/v2/businesses/{temp_identifier}/filings/{filing.id}/documents',
                    headers=create_header(jwt, [STAFF_ROLE], temp_identifier))

    # remove the filing ID
    rv_data = json.loads(re.sub("/\d+/", "/", rv.data.decode("utf-8")).replace("\n", ""))
    expected = json.loads(re.sub("/\d+/", "/", json.dumps(expected_msg)))

    assert rv.status_code == expected_http_code
    assert rv_data == expected


def test_get_receipt(session, client, jwt, requests_mock):
    """Assert that a receipt is generated."""
    from legal_api.resources.v2.business.business_filings.business_documents import _get_receipt

    # Setup
    identifier = 'CP7654321'
    business = factory_business(identifier)
    filing_name = 'incorporationApplication'
    payment_id = '12345'

    filing_json = copy.deepcopy(FILING_HEADER)
    filing_json['filing']['header']['name'] = filing_name
    filing_json['filing'][filing_name] = INCORPORATION
    filing_json['filing'].pop('business')

    filing_date = datetime.utcnow()
    filing = factory_filing(business, filing_json, filing_date=filing_date)
    filing.skip_status_listener = True
    filing._status = 'PAID'
    filing._payment_token = payment_id
    filing.save()
    filing_core = Filing()
    filing_core._storage = filing

    requests_mock.post(f"{current_app.config.get('PAYMENT_SVC_URL')}/{payment_id}/receipts",
                       json={'foo': 'bar'},
                       status_code=HTTPStatus.CREATED)

    token = helper_create_jwt(jwt, roles=[STAFF_ROLE], username='username')

    content, status_code = _get_receipt(business, filing_core, token)

    assert status_code == HTTPStatus.CREATED
    assert requests_mock.called_once


def test_get_receipt_request_mock(session, client, jwt, requests_mock):
    """Assert that a receipt is generated."""
    from legal_api.resources.v2.business.business_filings.business_documents import _get_receipt

    # Setup
    identifier = 'CP7654321'
    business = factory_business(identifier)
    filing_name = 'incorporationApplication'
    payment_id = '12345'

    filing_json = copy.deepcopy(FILING_HEADER)
    filing_json['filing']['header']['name'] = filing_name
    filing_json['filing'][filing_name] = INCORPORATION
    filing_json['filing'].pop('business')

    filing_date = datetime.utcnow()
    filing = factory_filing(business, filing_json, filing_date=filing_date)
    filing.skip_status_listener = True
    filing._status = 'PAID'
    filing._payment_token = payment_id
    filing._payment_completion_date = filing_date
    filing.save()

    requests_mock.post(f"{current_app.config.get('PAYMENT_SVC_URL')}/{payment_id}/receipts",
                       json={'foo': 'bar'},
                       status_code=HTTPStatus.CREATED)

    rv = client.get(f'/api/v2/businesses/{identifier}/filings/{filing.id}/documents/receipt',
                    headers=create_header(jwt,
                                          [STAFF_ROLE],
                                          identifier,
                                          **{'accept': 'application/pdf'})
                    )

    assert rv.status_code == HTTPStatus.CREATED
    assert requests_mock.called_once


def test_get_receipt_no_receipt_ca(session, client, jwt, requests_mock):
    """Assert that a receipt is generated."""
    from legal_api.resources.v2.business.business_filings.business_documents import _get_receipt

    # Setup
    identifier = 'CP7654321'
    business = factory_business(identifier)
    filing_name = 'incorporationApplication'
    payment_id = '12345'

    filing_json = copy.deepcopy(FILING_HEADER)
    filing_json['filing']['header']['name'] = filing_name
    filing_json['filing'][filing_name] = INCORPORATION
    filing_json['filing'].pop('business')

    filing_date = datetime.utcnow()
    filing = factory_filing(business, filing_json, filing_date=filing_date)
    filing.skip_status_listener = True
    filing._status = 'PAID'
    filing._payment_token = payment_id
    filing._payment_completion_date = filing_date
    filing.save()

    requests_mock.post(f"{current_app.config.get('PAYMENT_SVC_URL')}/{payment_id}/receipts",
                       json={'foo': 'bar'},
                       status_code=HTTPStatus.CREATED)

    requests_mock.get(
        f"{current_app.config.get('AUTH_SVC_URL')}/orgs/123456/products?include_hidden=true",
        json=[{"code": "CA_SEARCH", "subscriptionStatus": "ACTIVE"}],
    )

    rv = client.get(f'/api/v2/businesses/{identifier}/filings/{filing.id}/documents',
                    headers=create_header(jwt,
                                          [],
                                          identifier,
                                          **{'accept': 'application/pdf', 'Account-Id': '123456'})
                    )

    assert rv.status_code == HTTPStatus.OK
    assert not rv.json.get('documents').get('receipt', False)


@pytest.mark.parametrize('test_name, temp_identifier, entity_type, expected_msg, expected_http_code', [
    ('now_ia_paid', 'Tb31yQIuBw', Business.LegalTypes.BCOMP.value,
     {'documents': {'receipt': f'{base_url}/api/v2/businesses/Tb31yQIuBw/filings/1/documents/receipt',
                    'legalFilings': [
                        {'noticeOfWithdrawal': f'{base_url}/api/v2/businesses/Tb31yQIuBw/filings/1/documents/noticeOfWithdrawal'},
                    ]}},
     HTTPStatus.OK
     )
])
def test_temp_document_list_for_now(mocker, session, client, jwt,
                                    test_name,
                                    temp_identifier,
                                    entity_type,
                                    expected_msg, expected_http_code):
    """Test document list for noticeOfWithdrawal states with temp identifier."""
    # Setup

    withdrawn_filing_json = copy.deepcopy(FILING_HEADER)
    withdrawn_filing_json['filing']['header']['name'] = 'incorporationApplication'
    withdrawn_filing_json['filing']['business']['legalType'] = entity_type
    withdrawn_filing_json['filing']['incorporationApplication'] = INCORPORATION

    filing_json = copy.deepcopy(FILING_HEADER)
    filing_json['filing']['header']['name'] = 'noticeOfWithdrawal'
    filing_json['filing']['business']['legalType'] = entity_type
    filing_json['filing']['noticeOfWithdrawal'] = MOCK_NOTICE_OF_WITHDRAWAL

    filing_date = datetime.utcnow()

    temp_reg = RegistrationBootstrap()
    temp_reg._identifier = temp_identifier
    temp_reg.save()

    business = None
    withdrawn_filing = factory_filing(business, withdrawn_filing_json, filing_date=filing_date)
    withdrawn_filing.temp_reg = temp_identifier
    withdrawn_filing.save()
    filing = factory_filing(business, filing_json, filing_date=filing_date)
    filing.skip_status_listener = True
    filing._status = Filing.Status.PAID
    filing._payment_completion_date = '2017-10-01'
    filing.temp_reg = None
    filing.withdrawn_filing_id = withdrawn_filing.id
    filing.save()

    mocker.patch('legal_api.core.filing.has_roles', return_value=True)
    rv = client.get(f'/api/v2/businesses/{temp_identifier}/filings/{filing.id}/documents',
                    headers=create_header(jwt, [STAFF_ROLE], temp_identifier))

    # remove the filing ID
    rv_data = json.loads(re.sub("/\d+/", "/", rv.data.decode("utf-8")).replace("\n", ""))
    expected = json.loads(re.sub("/\d+/", "/", json.dumps(expected_msg)))

    assert rv.status_code == expected_http_code
    assert rv_data == expected

    filing._status = Filing.Status.COMPLETED
    filing.save()

    mocker.patch('legal_api.core.filing.has_roles', return_value=True)
    rv = client.get(f'/api/v2/businesses/{temp_identifier}/filings/{filing.id}/documents',
                    headers=create_header(jwt, [STAFF_ROLE], temp_identifier))

    # remove the filing ID
    rv_data = json.loads(re.sub("/\d+/", "/", rv.data.decode("utf-8")).replace("\n", ""))
    expected = json.loads(re.sub("/\d+/", "/", json.dumps(expected_msg)))

    assert rv.status_code == expected_http_code
    assert rv_data == expected
