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
from datetime import date, datetime
from http import HTTPStatus
from typing import Final, Tuple

import datedelta
import pytest
from dateutil.parser import parse
from flask import current_app
from registry_schemas.example_data import (
    AGM_EXTENSION,
    AGM_LOCATION_CHANGE,
    ALTERATION_FILING_TEMPLATE,
    AMALGAMATION_APPLICATION,
    ANNUAL_REPORT,
    CHANGE_OF_ADDRESS,
    CHANGE_OF_DIRECTORS,
    CHANGE_OF_REGISTRATION,
    CONTINUATION_OUT,
    CORRECTION_AR,
    CORRECTION_CP_SPECIAL_RESOLUTION,
    CORRECTION_INCORPORATION,
    COURT_ORDER,
    DISSOLUTION,
    FILING_HEADER,
    FILING_TEMPLATE,
    FIRMS_CONVERSION,
    INCORPORATION_FILING_TEMPLATE,
    REGISTRATION,
    RESTORATION,
    SPECIAL_RESOLUTION,
    TRANSITION_FILING_TEMPLATE,
)
from registry_schemas.example_data.schema_data import ALTERATION, INCORPORATION

from legal_api.core import FILINGS, Filing, FilingMeta
from legal_api.models import Comment
from legal_api.models import Filing as FilingStorage
from legal_api.models import LegalEntity, UserRoles
from legal_api.resources.v2.business.business_filings.business_filings import ListFilingResource
from legal_api.services.authz import BASIC_USER, STAFF_ROLE
from legal_api.utils.legislation_datetime import LegislationDatetime
from tests import api_v2, integration_payment
from tests.unit import nested_session
from tests.unit.core.test_filing_ledger import load_ledger
from tests.unit.models import (  # noqa:E501,I001
    factory_completed_filing,
    factory_filing,
    factory_legal_entity,
    factory_legal_entity_mailing_address,
    factory_user,
)
from tests.unit.services.utils import create_header, helper_create_jwt

ADMIN_DISSOLUTION = copy.deepcopy(DISSOLUTION)
ADMIN_DISSOLUTION["dissolutionType"] = "administrative"


def basic_test_helper():
    identifier = "CP7654321"
    legal_entity = factory_legal_entity(identifier)

    filing_json = FILING_HEADER
    filing_json["specialResolution"] = SPECIAL_RESOLUTION
    filing_date = datetime.utcnow()
    filing = factory_completed_filing(legal_entity, filing_json, filing_date=filing_date)

    return legal_entity, filing

#TODO: Can be tested/fixed after Output endpoints are fixed
def test_not_authorized(session, client, jwt):
    """Assert the the call fails for unauthorized access."""
    with nested_session(session):
        legal_entity, filing = basic_test_helper()

        MISSING_ROLES = [
            "SOME RANDO ROLE",
        ]

        rv = client.get(
            f"/api/v2/businesses/{legal_entity.identifier}/filings/{filing.id}/documents",
            headers=create_header(jwt, MISSING_ROLES, legal_entity.identifier),
        )

        assert rv.status_code == HTTPStatus.UNAUTHORIZED
        assert rv.json.get("message")
        assert legal_entity.identifier in rv.json.get("message")


def test_missing_business(session, client, jwt):
    """Assert the the call fails for missing business."""
    with nested_session(session):
        legal_entity, filing = basic_test_helper()

        not_the_business_identifier = "ABC123"

        rv = client.get(
            f"/api/v2/businesses/{not_the_business_identifier}/filings/{filing.id}/documents",
            headers=create_header(
                jwt,
                [
                    STAFF_ROLE,
                ],
                legal_entity.identifier,
            ),
        )

        assert rv.status_code == HTTPStatus.NOT_FOUND
        assert rv.json.get("message")
        assert not_the_business_identifier in rv.json.get("message")


def test_missing_filing(session, client, jwt):
    """Assert the the call fails for missing business."""
    with nested_session(session):
        legal_entity, filing = basic_test_helper()

        wrong_filing_number = 999999999

        rv = client.get(
            f"/api/v2/businesses/{legal_entity.identifier}/filings/{wrong_filing_number}/documents",
            headers=create_header(
                jwt,
                [
                    STAFF_ROLE,
                ],
                legal_entity.identifier,
            ),
        )

        assert rv.status_code == HTTPStatus.NOT_FOUND
        assert rv.json.get("message")
        assert str(wrong_filing_number) in rv.json.get("message")


def test_unpaid_filing(session, client, jwt):
    with nested_session(session):
        identifier = "CP7654321"
        legal_entity = factory_legal_entity(identifier)

        filing_json = FILING_HEADER
        filing_json["specialResolution"] = SPECIAL_RESOLUTION
        filing_date = datetime.utcnow()
        filing = factory_filing(legal_entity, filing_json, filing_date=filing_date)

        rv = client.get(
            f"/api/v2/businesses/{legal_entity.identifier}/filings/{filing.id}/documents",
            headers=create_header(jwt, [STAFF_ROLE], legal_entity.identifier),
        )

        assert rv.status_code == HTTPStatus.NOT_FOUND
        assert rv.json == {}


base_url = "https://LEGAL_API_BASE_URL"

ALTERATION_WITHOUT_NR = copy.deepcopy(ALTERATION)
del ALTERATION_WITHOUT_NR["nameRequest"]["nrNumber"]
del ALTERATION_WITHOUT_NR["nameRequest"]["legalName"]

ALTERATION_MEMORANDUM_RULES_IN_RESOLUTION = copy.deepcopy(ALTERATION)
ALTERATION_MEMORANDUM_RULES_IN_RESOLUTION["memorandumInResolution"] = True
ALTERATION_MEMORANDUM_RULES_IN_RESOLUTION["rulesInResolution"] = True


@pytest.mark.parametrize(
    "test_name, identifier, entity_type, filing_name_1, legal_filing_1, filing_name_2, legal_filing_2, status,\
    expected_msg, expected_http_code, payment_completion_date",
    [
        (
            "special_res_paper",
            "CP7654321",
            LegalEntity.EntityTypes.COOP.value,
            "specialResolution",
            SPECIAL_RESOLUTION,
            None,
            None,
            Filing.Status.PAPER_ONLY,
            {},
            HTTPStatus.NOT_FOUND,
            None,
        ),
        (
            "special_res_pending",
            "CP7654321",
            LegalEntity.EntityTypes.COOP.value,
            "specialResolution",
            SPECIAL_RESOLUTION,
            None,
            None,
            Filing.Status.PENDING,
            {},
            HTTPStatus.NOT_FOUND,
            None,
        ),
        (
            "special_res_paid",
            "CP7654321",
            LegalEntity.EntityTypes.COOP.value,
            "specialResolution",
            SPECIAL_RESOLUTION,
            None,
            None,
            Filing.Status.PAID,
            {
                "documents": {
                    "legalFilings": [
                        {
                            "specialResolution": f"{base_url}/api/v2/businesses/CP7654321/filings/1/documents/specialResolution"  # noqa: E501;
                        },
                    ],
                    "receipt": f"{base_url}/api/v2/businesses/CP7654321/filings/1/documents/receipt",
                }
            },
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "special_res_completed",
            "CP7654321",
            LegalEntity.EntityTypes.COOP.value,
            "specialResolution",
            SPECIAL_RESOLUTION,
            None,
            None,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "certifiedMemorandum": f"{base_url}/api/v2/businesses/CP7654321/filings/1/documents/certifiedMemorandum",  # noqa: E501;
                    "certifiedRules": f"{base_url}/api/v2/businesses/CP7654321/filings/1/documents/certifiedRules",
                    "legalFilings": [
                        {
                            "specialResolution": f"{base_url}/api/v2/businesses/CP7654321/filings/1/documents/specialResolution"  # noqa: E501;
                        },
                    ],
                    "receipt": f"{base_url}/api/v2/businesses/CP7654321/filings/1/documents/receipt",
                    "specialResolutionApplication": f"{base_url}/api/v2/businesses/CP7654321/filings/1/documents/specialResolutionApplication",  # noqa: E501;
                }
            },
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "special_res_rules_memorandum_included_completed",
            "CP7654321",
            LegalEntity.EntityTypes.COOP.value,
            "specialResolution",
            SPECIAL_RESOLUTION,
            "alteration",
            ALTERATION_MEMORANDUM_RULES_IN_RESOLUTION,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "legalFilings": [
                        {
                            "specialResolution": f"{base_url}/api/v2/businesses/CP7654321/filings/1/documents/specialResolution"  # noqa: E501;
                        }
                    ],
                    "receipt": f"{base_url}/api/v2/businesses/CP7654321/filings/1/documents/receipt",
                    "specialResolutionApplication": f"{base_url}/api/v2/businesses/CP7654321/filings/1/documents/specialResolutionApplication",  # noqa: E501;
                }
            },
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "specres_court_completed",
            "CP7654321",
            LegalEntity.EntityTypes.COOP.value,
            "specialResolution",
            SPECIAL_RESOLUTION,
            "courtOrder",
            COURT_ORDER,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "certifiedRules": f"{base_url}/api/v2/businesses/CP7654321/filings/1/documents/certifiedRules",
                    "certifiedMemorandum": f"{base_url}/api/v2/businesses/CP7654321/filings/1/documents/certifiedMemorandum",  # noqa: E501;
                    "legalFilings": [
                        {"courtOrder": f"{base_url}/api/v2/businesses/CP7654321/filings/1/documents/courtOrder"},
                        {
                            "specialResolution": f"{base_url}/api/v2/businesses/CP7654321/filings/1/documents/specialResolution"  # noqa: E501;
                        },
                    ],
                    "receipt": f"{base_url}/api/v2/businesses/CP7654321/filings/1/documents/receipt",
                    "specialResolutionApplication": f"{base_url}/api/v2/businesses/CP7654321/filings/1/documents/specialResolutionApplication",  # noqa: E501;
                }
            },
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "special_res_correction",
            "CP7654321",
            LegalEntity.EntityTypes.COOP.value,
            "correction",
            CORRECTION_CP_SPECIAL_RESOLUTION,
            None,
            None,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "certificateOfNameChange": f"{base_url}/api/v2/businesses/CP7654321/filings/1/documents/certificateOfNameChange",  # noqa: E501;
                    "certifiedRules": f"{base_url}/api/v2/businesses/CP7654321/filings/1/documents/certifiedRules",
                    "legalFilings": [
                        {"correction": f"{base_url}/api/v2/businesses/CP7654321/filings/1/documents/correction"},
                    ],
                    "receipt": f"{base_url}/api/v2/businesses/CP7654321/filings/1/documents/receipt",
                    "specialResolution": f"{base_url}/api/v2/businesses/CP7654321/filings/1/documents/specialResolution",  # noqa: E501;
                }
            },
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "cp_ia_completed",
            "CP7654321",
            LegalEntity.EntityTypes.COOP.value,
            "incorporationApplication",
            INCORPORATION,
            None,
            None,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "receipt": f"{base_url}/api/v2/businesses/CP7654321/filings/1/documents/receipt",
                    "certificate": f"{base_url}/api/v2/businesses/CP7654321/filings/1/documents/certificate",
                    "certifiedMemorandum": f"{base_url}/api/v2/businesses/CP7654321/filings/1/documents/certifiedMemorandum",  # noqa: E501;
                    "certifiedRules": f"{base_url}/api/v2/businesses/CP7654321/filings/1/documents/certifiedRules",
                    "legalFilings": [
                        {
                            "incorporationApplication": f"{base_url}/api/v2/businesses/CP7654321/filings/1/documents/incorporationApplication"  # noqa: E501;
                        },
                    ],
                }
            },
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "ben_ia_completed",
            "BC7654321",
            LegalEntity.EntityTypes.BCOMP.value,
            "incorporationApplication",
            INCORPORATION,
            None,
            None,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "receipt": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt",
                    "certificate": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/certificate",
                    "noticeOfArticles": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles",
                    "legalFilings": [
                        {
                            "incorporationApplication": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/incorporationApplication"  # noqa: E501;
                        },
                    ],
                }
            },
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "ben_ia_completed",
            "BC7654321",
            LegalEntity.EntityTypes.BCOMP.value,
            "incorporationApplication",
            INCORPORATION,
            None,
            None,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "certificate": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/certificate",
                    "noticeOfArticles": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles",
                    "legalFilings": [
                        {
                            "incorporationApplication": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/incorporationApplication"  # noqa: E501;
                        },
                    ],
                }
            },
            HTTPStatus.OK,
            None,
        ),
        (
            "ben_correction_completed",
            "BC7654321",
            LegalEntity.EntityTypes.BCOMP.value,
            "correction",
            CORRECTION_INCORPORATION,
            None,
            None,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "noticeOfArticles": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles",
                    "legalFilings": [
                        {"correction": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/correction"}
                    ],
                }
            },
            HTTPStatus.OK,
            None,
        ),
        (
            "bc_correction_completed",
            "BC7654321",
            LegalEntity.EntityTypes.COMP.value,
            "correction",
            CORRECTION_INCORPORATION,
            None,
            None,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "noticeOfArticles": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles",
                    "legalFilings": [
                        {"correction": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/correction"}
                    ],
                }
            },
            HTTPStatus.OK,
            None,
        ),
        (
            "ccc_correction_completed",
            "BC7654321",
            LegalEntity.EntityTypes.BC_CCC.value,
            "correction",
            CORRECTION_INCORPORATION,
            None,
            None,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "noticeOfArticles": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles",
                    "legalFilings": [
                        {"correction": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/correction"}
                    ],
                }
            },
            HTTPStatus.OK,
            None,
        ),
        (
            "ulc_correction_completed",
            "BC7654321",
            LegalEntity.EntityTypes.BC_ULC_COMPANY.value,
            "correction",
            CORRECTION_INCORPORATION,
            None,
            None,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "noticeOfArticles": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles",
                    "legalFilings": [
                        {"correction": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/correction"}
                    ],
                }
            },
            HTTPStatus.OK,
            None,
        ),
        (
            "ben_correction_completed",
            "BC7654321",
            LegalEntity.EntityTypes.BCOMP.value,
            "correction",
            CORRECTION_INCORPORATION,
            None,
            None,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "noticeOfArticles": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles",
                    "legalFilings": [
                        {"correction": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/correction"}
                    ],
                }
            },
            HTTPStatus.OK,
            None,
        ),
        (
            "ben_alteration_completed",
            "BC7654321",
            LegalEntity.EntityTypes.BCOMP.value,
            "alteration",
            ALTERATION_WITHOUT_NR,
            None,
            None,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "noticeOfArticles": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles",
                    "legalFilings": [
                        {"alteration": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/alteration"},
                    ],
                }
            },
            HTTPStatus.OK,
            None,
        ),
        (
            "bc_alteration_completed",
            "BC7654321",
            LegalEntity.EntityTypes.COMP.value,
            "alteration",
            ALTERATION_WITHOUT_NR,
            None,
            None,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "noticeOfArticles": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles",
                    "legalFilings": [
                        {"alteration": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/alteration"},
                    ],
                }
            },
            HTTPStatus.OK,
            None,
        ),
        (
            "cc_alteration_completed",
            "BC7654321",
            LegalEntity.EntityTypes.BC_CCC.value,
            "alteration",
            ALTERATION_WITHOUT_NR,
            None,
            None,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "noticeOfArticles": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles",
                    "legalFilings": [
                        {"alteration": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/alteration"},
                    ],
                }
            },
            HTTPStatus.OK,
            None,
        ),
        (
            "ulc_alteration_completed",
            "BC7654321",
            LegalEntity.EntityTypes.BC_ULC_COMPANY.value,
            "alteration",
            ALTERATION_WITHOUT_NR,
            None,
            None,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "noticeOfArticles": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles",
                    "legalFilings": [
                        {"alteration": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/alteration"},
                    ],
                }
            },
            HTTPStatus.OK,
            None,
        ),
        (
            "ben_alteration_with_nr_completed",
            "BC7654321",
            LegalEntity.EntityTypes.BCOMP.value,
            "alteration",
            ALTERATION,
            None,
            None,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "certificateOfNameChange": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/certificateOfNameChange",  # noqa: E501;
                    "noticeOfArticles": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles",
                    "legalFilings": [
                        {"alteration": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/alteration"},
                    ],
                }
            },
            HTTPStatus.OK,
            None,
        ),
        (
            "ben_changeOfDirector",
            "BC7654321",
            LegalEntity.EntityTypes.BCOMP.value,
            "changeOfDirectors",
            CHANGE_OF_DIRECTORS,
            None,
            None,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "noticeOfArticles": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles",
                    "legalFilings": [
                        {
                            "changeOfDirectors": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/changeOfDirectors"  # noqa: E501;
                        },
                    ],
                }
            },
            HTTPStatus.OK,
            None,
        ),
        (
            "bc_changeOfDirector",
            "BC7654321",
            LegalEntity.EntityTypes.COMP.value,
            "changeOfDirectors",
            CHANGE_OF_DIRECTORS,
            None,
            None,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "noticeOfArticles": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles",
                    "legalFilings": [
                        {
                            "changeOfDirectors": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/changeOfDirectors"  # noqa: E501;
                        },
                    ],
                }
            },
            HTTPStatus.OK,
            None,
        ),
        (
            "cc_changeOfDirector",
            "BC7654321",
            LegalEntity.EntityTypes.BC_CCC.value,
            "changeOfDirectors",
            CHANGE_OF_DIRECTORS,
            None,
            None,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "noticeOfArticles": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles",
                    "legalFilings": [
                        {
                            "changeOfDirectors": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/changeOfDirectors"  # noqa: E501;
                        },
                    ],
                }
            },
            HTTPStatus.OK,
            None,
        ),
        (
            "ulc_changeOfDirector",
            "BC7654321",
            LegalEntity.EntityTypes.BC_ULC_COMPANY.value,
            "changeOfDirectors",
            CHANGE_OF_DIRECTORS,
            None,
            None,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "noticeOfArticles": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles",
                    "legalFilings": [
                        {
                            "changeOfDirectors": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/changeOfDirectors"  # noqa: E501;
                        },
                    ],
                }
            },
            HTTPStatus.OK,
            None,
        ),
        (
            "cp_correction_ar",
            "CP7654321",
            LegalEntity.EntityTypes.COOP.value,
            "correction",
            CORRECTION_AR,
            None,
            None,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "legalFilings": [
                        {"correction": f"{base_url}/api/v2/businesses/CP7654321/filings/1/documents/correction"},
                    ]
                }
            },
            HTTPStatus.OK,
            None,
        ),
        (
            "cp_changeOfDirector",
            "CP7654321",
            LegalEntity.EntityTypes.COOP.value,
            "changeOfDirectors",
            CHANGE_OF_DIRECTORS,
            None,
            None,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "legalFilings": [
                        {
                            "changeOfDirectors": f"{base_url}/api/v2/businesses/CP7654321/filings/1/documents/changeOfDirectors"  # noqa: E501;
                        },
                    ]
                }
            },
            HTTPStatus.OK,
            None,
        ),
        (
            "cp_dissolution_completed",
            "CP7654321",
            LegalEntity.EntityTypes.COOP.value,
            "dissolution",
            DISSOLUTION,
            "specialResolution",
            SPECIAL_RESOLUTION,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "affidavit": f"{base_url}/api/v2/businesses/CP7654321/filings/1/documents/affidavit",
                    "certificateOfDissolution": f"{base_url}/api/v2/businesses/CP7654321/filings/1/documents/certificateOfDissolution",  # noqa: E501;
                    "certifiedMemorandum": f"{base_url}/api/v2/businesses/CP7654321/filings/1/documents/certifiedMemorandum",  # noqa: E501;
                    "certifiedRules": f"{base_url}/api/v2/businesses/CP7654321/filings/1/documents/certifiedRules",
                    "legalFilings": [
                        {"dissolution": f"{base_url}/api/v2/businesses/CP7654321/filings/1/documents/dissolution"},
                        {
                            "specialResolution": f"{base_url}/api/v2/businesses/CP7654321/filings/1/documents/specialResolution"  # noqa: E501;
                        },
                    ],
                    "receipt": f"{base_url}/api/v2/businesses/CP7654321/filings/1/documents/receipt",
                },
            },
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "cp_dissolution_paid",
            "CP7654321",
            LegalEntity.EntityTypes.COOP.value,
            "dissolution",
            DISSOLUTION,
            None,
            None,
            Filing.Status.PAID,
            {
                "documents": {
                    "receipt": f"{base_url}/api/v2/businesses/CP7654321/filings/1/documents/receipt",
                    "legalFilings": [
                        {"dissolution": f"{base_url}/api/v2/businesses/CP7654321/filings/1/documents/dissolution"},
                    ],
                }
            },
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "ben_dissolution_completed",
            "BC7654321",
            "BEN",
            "dissolution",
            DISSOLUTION,
            None,
            None,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "receipt": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt",
                    "certificateOfDissolution": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/certificateOfDissolution",  # noqa: E501;
                    "legalFilings": [
                        {"dissolution": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/dissolution"},
                    ],
                }
            },
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "ben_dissolution_paid",
            "BC7654321",
            "BEN",
            "dissolution",
            DISSOLUTION,
            None,
            None,
            Filing.Status.PAID,
            {
                "documents": {
                    "receipt": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt",
                    "legalFilings": [
                        {"dissolution": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/dissolution"},
                    ],
                }
            },
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "bc_dissolution_completed",
            "BC7654321",
            "BC",
            "dissolution",
            DISSOLUTION,
            None,
            None,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "receipt": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt",
                    "certificateOfDissolution": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/certificateOfDissolution",  # noqa: E501;
                    "legalFilings": [
                        {"dissolution": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/dissolution"},
                    ],
                }
            },
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "cc_dissolution_completed",
            "BC7654321",
            "CC",
            "dissolution",
            DISSOLUTION,
            None,
            None,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "receipt": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt",
                    "certificateOfDissolution": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/certificateOfDissolution",  # noqa: E501;
                    "legalFilings": [
                        {"dissolution": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/dissolution"},
                    ],
                }
            },
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "ulc_dissolution_completed",
            "BC7654321",
            "LLC",
            "dissolution",
            DISSOLUTION,
            None,
            None,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "receipt": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt",
                    "certificateOfDissolution": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/certificateOfDissolution",  # noqa: E501;
                    "legalFilings": [
                        {"dissolution": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/dissolution"},
                    ],
                }
            },
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "llc_dissolution_completed",
            "BC7654321",
            "LLC",
            "dissolution",
            DISSOLUTION,
            None,
            None,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "receipt": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt",
                    "certificateOfDissolution": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/certificateOfDissolution",  # noqa: E501;
                    "legalFilings": [
                        {"dissolution": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/dissolution"},
                    ],
                }
            },
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "dissolution_completed_no_certificate_of_dissolution",
            "BC7654321",
            "LLC",
            "dissolution",
            ADMIN_DISSOLUTION,
            None,
            None,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "receipt": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt",
                    "legalFilings": [
                        {"dissolution": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/dissolution"},
                    ],
                }
            },
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "sp_registration_paid",
            "FM7654321",
            "SP",
            "registration",
            REGISTRATION,
            None,
            None,
            Filing.Status.PAID,
            {"documents": {"receipt": f"{base_url}/api/v2/businesses/FM7654321/filings/1/documents/receipt"}},
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "sp_registration_completed",
            "FM7654321",
            "SP",
            "registration",
            REGISTRATION,
            None,
            None,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "receipt": f"{base_url}/api/v2/businesses/FM7654321/filings/1/documents/receipt",
                    "legalFilings": [
                        {"registration": f"{base_url}/api/v2/businesses/FM7654321/filings/1/documents/registration"},
                    ],
                }
            },
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "gp_registration_paid",
            "FM7654321",
            "GP",
            "registration",
            REGISTRATION,
            None,
            None,
            Filing.Status.PAID,
            {"documents": {"receipt": f"{base_url}/api/v2/businesses/FM7654321/filings/1/documents/receipt"}},
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "gp_registration_completed",
            "FM7654321",
            "GP",
            "registration",
            REGISTRATION,
            None,
            None,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "receipt": f"{base_url}/api/v2/businesses/FM7654321/filings/1/documents/receipt",
                    "legalFilings": [
                        {"registration": f"{base_url}/api/v2/businesses/FM7654321/filings/1/documents/registration"},
                    ],
                }
            },
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "sp_change_of_registration_paid",
            "FM7654321",
            "SP",
            "changeOfRegistration",
            CHANGE_OF_REGISTRATION,
            None,
            None,
            Filing.Status.PAID,
            {
                "documents": {
                    "receipt": f"{base_url}/api/v2/businesses/FM7654321/filings/1/documents/receipt",
                    "legalFilings": [
                        {
                            "changeOfRegistration": f"{base_url}/api/v2/businesses/FM7654321/filings/1/documents/changeOfRegistration"  # noqa: E501;
                        },
                    ],
                }
            },
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "sp_change_of_registration_completed",
            "FM7654321",
            "SP",
            "changeOfRegistration",
            CHANGE_OF_REGISTRATION,
            None,
            None,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "receipt": f"{base_url}/api/v2/businesses/FM7654321/filings/1/documents/receipt",
                    "amendedRegistrationStatement": f"{base_url}/api/v2/businesses/FM7654321/filings/1/documents/amendedRegistrationStatement",  # noqa: E501;
                    "legalFilings": [
                        {
                            "changeOfRegistration": f"{base_url}/api/v2/businesses/FM7654321/filings/1/documents/changeOfRegistration"  # noqa: E501;
                        },
                    ],
                }
            },
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "gp_change_of_registration_paid",
            "FM7654321",
            "GP",
            "changeOfRegistration",
            CHANGE_OF_REGISTRATION,
            None,
            None,
            Filing.Status.PAID,
            {
                "documents": {
                    "receipt": f"{base_url}/api/v2/businesses/FM7654321/filings/1/documents/receipt",
                    "legalFilings": [
                        {
                            "changeOfRegistration": f"{base_url}/api/v2/businesses/FM7654321/filings/1/documents/changeOfRegistration"  # noqa: E501;
                        },
                    ],
                }
            },
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "gp_change_of_registration_completed",
            "FM7654321",
            "GP",
            "changeOfRegistration",
            CHANGE_OF_REGISTRATION,
            None,
            None,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "receipt": f"{base_url}/api/v2/businesses/FM7654321/filings/1/documents/receipt",
                    "amendedRegistrationStatement": f"{base_url}/api/v2/businesses/FM7654321/filings/1/documents/amendedRegistrationStatement",  # noqa: E501;
                    "legalFilings": [
                        {
                            "changeOfRegistration": f"{base_url}/api/v2/businesses/FM7654321/filings/1/documents/changeOfRegistration"  # noqa: E501;
                        },
                    ],
                }
            },
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "sp_ia_completed",
            "FM7654321",
            LegalEntity.EntityTypes.SOLE_PROP.value,
            "conversion",
            FIRMS_CONVERSION,
            None,
            None,
            Filing.Status.COMPLETED,
            {"documents": {}},
            HTTPStatus.OK,
            None,
        ),
        (
            "gp_ia_completed",
            "FM7654321",
            LegalEntity.EntityTypes.PARTNERSHIP.value,
            "conversion",
            FIRMS_CONVERSION,
            None,
            None,
            Filing.Status.COMPLETED,
            {"documents": {}},
            HTTPStatus.OK,
            None,
        ),
        (
            "sp_dissolution_completed",
            "FM7654321",
            "SP",
            "dissolution",
            DISSOLUTION,
            None,
            None,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "receipt": f"{base_url}/api/v2/businesses/FM7654321/filings/1/documents/receipt",
                    "legalFilings": [
                        {"dissolution": f"{base_url}/api/v2/businesses/FM7654321/filings/1/documents/dissolution"},
                    ],
                }
            },
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "sp_dissolution_paid",
            "FM7654321",
            "SP",
            "dissolution",
            DISSOLUTION,
            None,
            None,
            Filing.Status.PAID,
            {"documents": {"receipt": f"{base_url}/api/v2/businesses/FM7654321/filings/1/documents/receipt"}},
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "gp_dissolution_completed",
            "FM7654321",
            "GP",
            "dissolution",
            DISSOLUTION,
            None,
            None,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "receipt": f"{base_url}/api/v2/businesses/FM7654321/filings/1/documents/receipt",
                    "legalFilings": [
                        {"dissolution": f"{base_url}/api/v2/businesses/FM7654321/filings/1/documents/dissolution"},
                    ],
                }
            },
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "gp_dissolution_paid",
            "FM7654321",
            "GP",
            "dissolution",
            DISSOLUTION,
            None,
            None,
            Filing.Status.PAID,
            {"documents": {"receipt": f"{base_url}/api/v2/businesses/FM7654321/filings/1/documents/receipt"}},
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "ulc_ia_paid",
            "BC7654321",
            LegalEntity.EntityTypes.BC_ULC_COMPANY.value,
            "incorporationApplication",
            INCORPORATION,
            None,
            None,
            Filing.Status.PAID,
            {
                "documents": {
                    "receipt": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt",
                    "legalFilings": [
                        {
                            "incorporationApplication": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/incorporationApplication"  # noqa: E501;
                        },
                    ],
                }
            },
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "ulc_ia_completed",
            "BC7654321",
            LegalEntity.EntityTypes.BC_ULC_COMPANY.value,
            "incorporationApplication",
            INCORPORATION,
            None,
            None,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "receipt": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt",
                    "certificate": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/certificate",
                    "noticeOfArticles": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles",
                    "legalFilings": [
                        {
                            "incorporationApplication": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/incorporationApplication"  # noqa: E501;
                        },
                    ],
                }
            },
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "cc_ia_paid",
            "BC7654321",
            LegalEntity.EntityTypes.BC_CCC.value,
            "incorporationApplication",
            INCORPORATION,
            None,
            None,
            Filing.Status.PAID,
            {
                "documents": {
                    "receipt": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt",
                    "legalFilings": [
                        {
                            "incorporationApplication": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/incorporationApplication"  # noqa: E501;
                        },
                    ],
                }
            },
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "cc_ia_completed",
            "BC7654321",
            LegalEntity.EntityTypes.BC_CCC.value,
            "incorporationApplication",
            INCORPORATION,
            None,
            None,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "receipt": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt",
                    "certificate": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/certificate",
                    "noticeOfArticles": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles",
                    "legalFilings": [
                        {
                            "incorporationApplication": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/incorporationApplication"  # noqa: E501;
                        },
                    ],
                }
            },
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "bc_ia_paid",
            "BC7654321",
            LegalEntity.EntityTypes.COMP.value,
            "incorporationApplication",
            INCORPORATION,
            None,
            None,
            Filing.Status.PAID,
            {
                "documents": {
                    "receipt": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt",
                    "legalFilings": [
                        {
                            "incorporationApplication": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/incorporationApplication"  # noqa: E501;
                        },
                    ],
                }
            },
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "bc_ia_completed",
            "BC7654321",
            LegalEntity.EntityTypes.COMP.value,
            "incorporationApplication",
            INCORPORATION,
            None,
            None,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "receipt": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt",
                    "certificate": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/certificate",
                    "noticeOfArticles": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles",
                    "legalFilings": [
                        {
                            "incorporationApplication": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/incorporationApplication"  # noqa: E501;
                        },
                    ],
                }
            },
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "bc_annual_report_completed",
            "BC7654321",
            LegalEntity.EntityTypes.COMP.value,
            "annualReport",
            ANNUAL_REPORT,
            None,
            None,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "receipt": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt",
                    "legalFilings": [
                        {"annualReport": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/annualReport"},
                    ],
                }
            },
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "ccc_annual_report_completed",
            "BC7654321",
            LegalEntity.EntityTypes.BC_CCC.value,
            "annualReport",
            ANNUAL_REPORT,
            None,
            None,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "receipt": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt",
                    "legalFilings": [
                        {"annualReport": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/annualReport"},
                    ],
                }
            },
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "ulc_annual_report_completed",
            "BC7654321",
            LegalEntity.EntityTypes.BC_ULC_COMPANY.value,
            "annualReport",
            ANNUAL_REPORT,
            None,
            None,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "receipt": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt",
                    "legalFilings": [
                        {"annualReport": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/annualReport"},
                    ],
                }
            },
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "cp_annual_report_completed",
            "CP7654321",
            LegalEntity.EntityTypes.COOP.value,
            "annualReport",
            ANNUAL_REPORT,
            None,
            None,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "receipt": f"{base_url}/api/v2/businesses/CP7654321/filings/1/documents/receipt",
                    "legalFilings": [
                        {"annualReport": f"{base_url}/api/v2/businesses/CP7654321/filings/1/documents/annualReport"},
                    ],
                }
            },
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "ben_annual_report_completed",
            "BC7654321",
            LegalEntity.EntityTypes.BCOMP.value,
            "annualReport",
            ANNUAL_REPORT,
            None,
            None,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "receipt": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt",
                    "legalFilings": [
                        {"annualReport": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/annualReport"},
                    ],
                }
            },
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "bc_annual_report_paid",
            "BC7654321",
            LegalEntity.EntityTypes.COMP.value,
            "annualReport",
            ANNUAL_REPORT,
            None,
            None,
            Filing.Status.PAID,
            {
                "documents": {
                    "receipt": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt",
                    "legalFilings": [
                        {"annualReport": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/annualReport"},
                    ],
                }
            },
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "ccc_annual_report_paid",
            "BC7654321",
            LegalEntity.EntityTypes.BC_CCC.value,
            "annualReport",
            ANNUAL_REPORT,
            None,
            None,
            Filing.Status.PAID,
            {
                "documents": {
                    "receipt": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt",
                    "legalFilings": [
                        {"annualReport": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/annualReport"},
                    ],
                }
            },
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "ulc_annual_report_paid",
            "BC7654321",
            LegalEntity.EntityTypes.BC_ULC_COMPANY.value,
            "annualReport",
            ANNUAL_REPORT,
            None,
            None,
            Filing.Status.PAID,
            {
                "documents": {
                    "receipt": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt",
                    "legalFilings": [
                        {"annualReport": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/annualReport"},
                    ],
                }
            },
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "cp_annual_report_paid",
            "CP7654321",
            LegalEntity.EntityTypes.COOP.value,
            "annualReport",
            ANNUAL_REPORT,
            None,
            None,
            Filing.Status.PAID,
            {
                "documents": {
                    "receipt": f"{base_url}/api/v2/businesses/CP7654321/filings/1/documents/receipt",
                    "legalFilings": [
                        {"annualReport": f"{base_url}/api/v2/businesses/CP7654321/filings/1/documents/annualReport"},
                    ],
                }
            },
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "ben_annual_report_paid",
            "BC7654321",
            LegalEntity.EntityTypes.BCOMP.value,
            "annualReport",
            ANNUAL_REPORT,
            None,
            None,
            Filing.Status.PAID,
            {
                "documents": {
                    "receipt": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt",
                    "legalFilings": [
                        {"annualReport": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/annualReport"},
                    ],
                }
            },
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "ben_agmExtension_completed",
            "BC7654321",
            LegalEntity.EntityTypes.BCOMP.value,
            "agmExtension",
            AGM_EXTENSION,
            None,
            None,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "letterOfAgmExtension": "https://LEGAL_API_BASE_URL/api/v2/businesses\
                        /BC7654321/filings/documents/letterOfAgmExtension",
                    "receipt": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt",
                }
            },
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "ben_agmLocationChange_paid",
            "BC7654321",
            LegalEntity.EntityTypes.BCOMP.value,
            "agmExtension",
            AGM_EXTENSION,
            None,
            None,
            Filing.Status.PAID,
            {"documents": {"receipt": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt"}},
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "ben_agmLocationChange_completed",
            "BC7654321",
            LegalEntity.EntityTypes.BCOMP.value,
            "agmLocationChange",
            AGM_LOCATION_CHANGE,
            None,
            None,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "letterOfAgmLocationChange": "https://LEGAL_API_BASE_URL/api/v2/businesses\
                        /BC7654321/filings/documents/letterOfAgmLocationChange",
                    "receipt": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt",
                }
            },
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "ben_agmLocationChange_paid",
            "BC7654321",
            LegalEntity.EntityTypes.BCOMP.value,
            "agmLocationChange",
            AGM_LOCATION_CHANGE,
            None,
            None,
            Filing.Status.PAID,
            {"documents": {"receipt": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt"}},
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "ben_amalgamation_completed",
            "BC7654321",
            LegalEntity.EntityTypes.BCOMP.value,
            "amalgamationApplication",
            AMALGAMATION_APPLICATION,
            None,
            None,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "certificateOfAmalgamation": f"{base_url}/api/v2/businesses\
                        /BC7654321/filings/1/documents/certificateOfAmalgamation",
                    "legalFilings": [
                        {
                            "amalgamationApplication": f"{base_url}/api/v2/businesses\
                                /BC7654321/filings/1/documents/amalgamationApplication"
                        }
                    ],
                    "noticeOfArticles": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles",
                    "receipt": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt",
                }
            },
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "ben_amalgamation_paid",
            "BC7654321",
            LegalEntity.EntityTypes.BCOMP.value,
            "amalgamationApplication",
            AMALGAMATION_APPLICATION,
            None,
            None,
            Filing.Status.PAID,
            {
                "documents": {
                    "legalFilings": [
                        {
                            "amalgamationApplication": f"{base_url}/api/v2/businesses\
                                /BC7654321/filings/1/documents/amalgamationApplication"
                        }
                    ],
                    "receipt": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt",
                }
            },
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "ben_changeOfAddress",
            "BC7654321",
            LegalEntity.EntityTypes.BCOMP.value,
            "changeOfAddress",
            CHANGE_OF_ADDRESS,
            None,
            None,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "noticeOfArticles": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles",
                    "legalFilings": [
                        {
                            "changeOfAddress": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/changeOfAddress"  # noqa: E501;
                        }
                    ],
                }
            },
            HTTPStatus.OK,
            None,
        ),
        (
            "bc_changeOfAddress",
            "BC7654321",
            LegalEntity.EntityTypes.COMP.value,
            "changeOfAddress",
            CHANGE_OF_ADDRESS,
            None,
            None,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "noticeOfArticles": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles",
                    "legalFilings": [
                        {
                            "changeOfAddress": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/changeOfAddress"  # noqa: E501;
                        },
                    ],
                }
            },
            HTTPStatus.OK,
            None,
        ),
        (
            "cc_changeOfAddress",
            "BC7654321",
            LegalEntity.EntityTypes.BC_CCC.value,
            "changeOfAddress",
            CHANGE_OF_ADDRESS,
            None,
            None,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "noticeOfArticles": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles",
                    "legalFilings": [
                        {
                            "changeOfAddress": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/changeOfAddress"  # noqa: E501;
                        },
                    ],
                }
            },
            HTTPStatus.OK,
            None,
        ),
        (
            "ulc_changeOfAddress",
            "BC7654321",
            LegalEntity.EntityTypes.BC_ULC_COMPANY.value,
            "changeOfAddress",
            CHANGE_OF_ADDRESS,
            None,
            None,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "noticeOfArticles": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles",
                    "legalFilings": [
                        {
                            "changeOfAddress": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/changeOfAddress"  # noqa: E501;
                        },
                    ],
                }
            },
            HTTPStatus.OK,
            None,
        ),
        (
            "bc_restoration_completed",
            "BC7654321",
            LegalEntity.EntityTypes.COMP.value,
            "restoration",
            RESTORATION,
            None,
            None,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "receipt": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt",
                    "certificateOfRestoration": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/certificateOfRestoration",  # noqa: E501;
                    "noticeOfArticles": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles",
                    "legalFilings": [
                        {"restoration": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/restoration"},
                    ],
                }
            },
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "bc_restoration_paid",
            "BC7654321",
            LegalEntity.EntityTypes.COMP.value,
            "restoration",
            RESTORATION,
            None,
            None,
            Filing.Status.PAID,
            {
                "documents": {
                    "receipt": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt",
                    "legalFilings": [
                        {"restoration": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/restoration"},
                    ],
                }
            },
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "ben_restoration_completed",
            "BC7654321",
            LegalEntity.EntityTypes.BCOMP.value,
            "restoration",
            RESTORATION,
            None,
            None,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "receipt": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt",
                    "certificateOfRestoration": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/certificateOfRestoration",  # noqa: E501;
                    "noticeOfArticles": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles",
                    "legalFilings": [
                        {"restoration": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/restoration"},
                    ],
                }
            },
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "ben_restoration_paid",
            "BC7654321",
            LegalEntity.EntityTypes.BCOMP.value,
            "restoration",
            RESTORATION,
            None,
            None,
            Filing.Status.PAID,
            {
                "documents": {
                    "receipt": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt",
                    "legalFilings": [
                        {"restoration": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/restoration"},
                    ],
                }
            },
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "ulc_restoration_completed",
            "BC7654321",
            LegalEntity.EntityTypes.BC_ULC_COMPANY.value,
            "restoration",
            RESTORATION,
            None,
            None,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "receipt": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt",
                    "certificateOfRestoration": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/certificateOfRestoration",  # noqa: E501;
                    "noticeOfArticles": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles",
                    "legalFilings": [
                        {"restoration": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/restoration"},
                    ],
                }
            },
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "ulc_restoration_paid",
            "BC7654321",
            LegalEntity.EntityTypes.BC_ULC_COMPANY.value,
            "restoration",
            RESTORATION,
            None,
            None,
            Filing.Status.PAID,
            {
                "documents": {
                    "receipt": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt",
                    "legalFilings": [
                        {"restoration": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/restoration"},
                    ],
                }
            },
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "cc_restoration_completed",
            "BC7654321",
            LegalEntity.EntityTypes.BC_CCC.value,
            "restoration",
            RESTORATION,
            None,
            None,
            Filing.Status.COMPLETED,
            {
                "documents": {
                    "receipt": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt",
                    "certificateOfRestoration": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/certificateOfRestoration",  # noqa: E501;
                    "noticeOfArticles": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/noticeOfArticles",
                    "legalFilings": [
                        {"restoration": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/restoration"},
                    ],
                }
            },
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "cc_restoration_paid",
            "BC7654321",
            LegalEntity.EntityTypes.BC_CCC.value,
            "restoration",
            RESTORATION,
            None,
            None,
            Filing.Status.PAID,
            {
                "documents": {
                    "receipt": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt",
                    "legalFilings": [
                        {"restoration": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/restoration"},
                    ],
                }
            },
            HTTPStatus.OK,
            "2017-10-01",
        ),
        (
            "bc_continuationOut_complete",
            "BC7654321",
            LegalEntity.EntityTypes.COMP.value,
            "continuationOut",
            CONTINUATION_OUT,
            None,
            None,
            Filing.Status.COMPLETED,
            {"documents": {"receipt": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt"}},
            HTTPStatus.OK,
            "2017-10-1",
        ),
        (
            "ulc_continuationOut_complete",
            "BC7654321",
            LegalEntity.EntityTypes.BC_ULC_COMPANY.value,
            "continuationOut",
            CONTINUATION_OUT,
            None,
            None,
            Filing.Status.COMPLETED,
            {"documents": {"receipt": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt"}},
            HTTPStatus.OK,
            "2017-10-1",
        ),
        (
            "cc_continuationOut_complete",
            "BC7654321",
            LegalEntity.EntityTypes.BC_CCC.value,
            "continuationOut",
            CONTINUATION_OUT,
            None,
            None,
            Filing.Status.COMPLETED,
            {"documents": {"receipt": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt"}},
            HTTPStatus.OK,
            "2017-10-1",
        ),
        (
            "ben_continuationOut_complete",
            "BC7654321",
            LegalEntity.EntityTypes.BCOMP.value,
            "continuationOut",
            CONTINUATION_OUT,
            None,
            None,
            Filing.Status.COMPLETED,
            {"documents": {"receipt": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt"}},
            HTTPStatus.OK,
            "2017-10-1",
        ),
        (
            "bc_continuationOut_paid",
            "BC7654321",
            LegalEntity.EntityTypes.COMP.value,
            "continuationOut",
            CONTINUATION_OUT,
            None,
            None,
            Filing.Status.PAID,
            {"documents": {"receipt": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt"}},
            HTTPStatus.OK,
            "2017-10-1",
        ),
        (
            "ulc_continuationOut_paid",
            "BC7654321",
            LegalEntity.EntityTypes.BC_ULC_COMPANY.value,
            "continuationOut",
            CONTINUATION_OUT,
            None,
            None,
            Filing.Status.PAID,
            {"documents": {"receipt": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt"}},
            HTTPStatus.OK,
            "2017-10-1",
        ),
        (
            "cc_continuationOut_paid",
            "BC7654321",
            LegalEntity.EntityTypes.BC_CCC.value,
            "continuationOut",
            CONTINUATION_OUT,
            None,
            None,
            Filing.Status.PAID,
            {"documents": {"receipt": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt"}},
            HTTPStatus.OK,
            "2017-10-1",
        ),
        (
            "ben_continuationOut_paid",
            "BC7654321",
            LegalEntity.EntityTypes.BCOMP.value,
            "continuationOut",
            CONTINUATION_OUT,
            None,
            None,
            Filing.Status.PAID,
            {"documents": {"receipt": f"{base_url}/api/v2/businesses/BC7654321/filings/1/documents/receipt"}},
            HTTPStatus.OK,
            "2017-10-1",
        ),
    ],
)
def test_document_list_for_various_filing_states(
    session,
    client,
    jwt,
    test_name,
    identifier,
    entity_type,
    filing_name_1,
    legal_filing_1,
    filing_name_2,
    legal_filing_2,
    status,
    expected_msg,
    expected_http_code,
    payment_completion_date,
):
    """Test document list based on filing states."""
    with nested_session(session):
        # Setup
        # identifier = 'CP7654321'
        legal_entity = factory_legal_entity(identifier, _entity_type=entity_type)

        filing_json = copy.deepcopy(FILING_HEADER)
        filing_json["filing"]["header"]["name"] = filing_name_1
        filing_json["filing"]["business"]["legalType"] = entity_type
        if filing_name_1 == "incorporationApplication":
            legal_filing_1["nameRequest"]["legalType"] = entity_type
        filing_json["filing"][filing_name_1] = legal_filing_1

        if legal_filing_2:
            filing_json["filing"][filing_name_2] = legal_filing_2

        filing_date = datetime.utcnow()
        filing = factory_filing(legal_entity, filing_json, filing_date=filing_date)
        filing.skip_status_listener = True
        filing._status = status
        filing._payment_completion_date = payment_completion_date
        filing.save()

        if status == "COMPLETED":
            lf = [list(x.keys()) for x in filing.legal_filings()]
            legal_filings = [item for sublist in lf for item in sublist]
            meta_data = {"legalFilings": legal_filings}

            if filing_name_1 == "alteration" and (
                legal_name := filing_json["filing"]["alteration"].get("nameRequest", {}).get("legalName")
            ):
                meta_data["alteration"] = {}
                meta_data["alteration"]["fromBusinessName"] = legal_entity.legal_name
                meta_data["alteration"]["toBusinessName"] = legal_name

        # usually done by the filer.
        if (
            filing_name_1 == "correction"
            and legal_entity.legal_type == "CP"
            and (legal_name := filing_json["filing"]["correction"].get("nameRequest", {}).get("legalName"))
        ):
            meta_data["correction"] = {}
            meta_data["correction"]["fromBusinessName"] = legal_entity.legal_name
            meta_data["correction"]["toBusinessName"] = legal_name

        filing._meta_data = meta_data
        filing.save()

        rv = client.get(
            f"/api/v2/businesses/{legal_entity.identifier}/filings/{filing.id}/documents",
            headers=create_header(jwt, [STAFF_ROLE], legal_entity.identifier),
        )

        # remove the filing ID
        rv_data = json.loads(re.sub("/\d+/", "/", rv.data.decode("utf-8")).replace("\n", ""))  # noqa: W605;
        expected = json.loads(re.sub("/\d+/", "/", json.dumps(expected_msg)))  # noqa: W605;

        assert rv.status_code == expected_http_code
        assert rv_data == expected


def filer_action(filing_name, filing_json, meta_data, business):
    """Helper function for test_document_list_for_various_filing_states."""
    if filing_name == "alteration" and (
        legal_name := filing_json["filing"]["alteration"].get("nameRequest", {}).get("legalName")
    ):
        meta_data["alteration"] = {}
        meta_data["alteration"]["fromLegalName"] = business.legal_name
        meta_data["alteration"]["toLegalName"] = legal_name

    if filing_name == "correction" and business.legal_type == "CP":
        meta_data["correction"] = {}
        if legal_name := filing_json["filing"]["correction"].get("nameRequest", {}).get("legalName"):
            meta_data["correction"]["fromLegalName"] = business.legal_name
            meta_data["correction"]["toLegalName"] = legal_name

        if filing_json["filing"]["correction"].get("rulesFileKey"):
            meta_data["correction"]["uploadNewRules"] = True

        if filing_json["filing"]["correction"].get("memorandumFileKey"):
            meta_data["correction"]["uploadNewMemorandum"] = True

        if filing_json["filing"]["correction"].get("resolution"):
            meta_data["correction"]["hasResolution"] = True

    if filing_name == "specialResolution" and business.legal_type == "CP":
        meta_data["alteration"] = {}
        meta_data["alteration"]["uploadNewRules"] = True

    return meta_data


def test_get_receipt(session, client, jwt, requests_mock):
    """Assert that a receipt is generated."""
    with nested_session(session):
        from legal_api.resources.v2.business.business_filings.business_documents import _get_receipt

        # Setup
        identifier = "CP7654321"
        legal_entity = factory_legal_entity(identifier)
        filing_name = "incorporationApplication"
        payment_id = "12345"

        filing_json = copy.deepcopy(FILING_HEADER)
        filing_json["filing"]["header"]["name"] = filing_name
        filing_json["filing"][filing_name] = INCORPORATION
        filing_json["filing"].pop("business")

        filing_date = datetime.utcnow()
        filing = factory_filing(legal_entity, filing_json, filing_date=filing_date)
        filing.skip_status_listener = True
        filing._status = "PAID"
        filing._payment_token = payment_id
        filing.save()
        filing_core = Filing()
        filing_core._storage = filing

        requests_mock.post(
            f"{current_app.config.get('PAYMENT_SVC_URL')}/{payment_id}/receipts",
            json={"foo": "bar"},
            status_code=HTTPStatus.CREATED,
        )

        token = helper_create_jwt(jwt, roles=[STAFF_ROLE], username="username")

        content, status_code = _get_receipt(legal_entity, filing_core, token)

        assert status_code == HTTPStatus.CREATED
        assert requests_mock.called_once


def test_get_receipt_request_mock(session, client, jwt, requests_mock):
    """Assert that a receipt is generated."""
    with nested_session(session):
        from legal_api.resources.v2.business.business_filings.business_documents import _get_receipt

        # Setup
        identifier = "CP7654321"
        legal_entity = factory_legal_entity(identifier)
        filing_name = "incorporationApplication"
        payment_id = "12345"

        filing_json = copy.deepcopy(FILING_HEADER)
        filing_json["filing"]["header"]["name"] = filing_name
        filing_json["filing"][filing_name] = INCORPORATION
        filing_json["filing"].pop("business")

        filing_date = datetime.utcnow()
        filing = factory_filing(legal_entity, filing_json, filing_date=filing_date)
        filing.skip_status_listener = True
        filing._status = "PAID"
        filing._payment_token = payment_id
        filing.save()

        requests_mock.post(
            f"{current_app.config.get('PAYMENT_SVC_URL')}/{payment_id}/receipts",
            json={"foo": "bar"},
            status_code=HTTPStatus.CREATED,
        )

        rv = client.get(
            f"/api/v2/businesses/{identifier}/filings/{filing.id}/documents/receipt",
            headers=create_header(jwt, [STAFF_ROLE], identifier, **{"accept": "application/pdf"}),
        )

        assert rv.status_code == HTTPStatus.CREATED
        assert requests_mock.called_once
