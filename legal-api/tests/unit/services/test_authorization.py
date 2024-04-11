# Copyright © 2019 Province of British Columbia
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

"""Tests to assure the Authorization Services.

Test-Suite to ensure that the Authorization Service is working as expected.
"""
import copy
import random
from datetime import datetime as _datetime
from enum import Enum
from http import HTTPStatus
from unittest.mock import MagicMock, PropertyMock, patch

import jwt as pyjwt
import pytest
from flask import jsonify
from registry_schemas.example_data import (
    AGM_EXTENSION,
    AGM_LOCATION_CHANGE,
    ALTERATION_FILING_TEMPLATE,
    ANNUAL_REPORT,
    CHANGE_OF_REGISTRATION_TEMPLATE,
    CONSENT_CONTINUATION_OUT,
    CONTINUATION_IN,
    CONTINUATION_OUT,
    CORRECTION_AR,
    DISSOLUTION,
    FILING_TEMPLATE,
    PUT_BACK_ON,
    RESTORATION,
)

from legal_api.models import Address, AmalgamatingBusiness, EntityRole, Filing, User
from legal_api.models.legal_entity import LegalEntity
from legal_api.services.authz import (
    BASIC_USER,
    COLIN_SVC_ROLE,
    PUBLIC_USER,
    STAFF_ROLE,
    are_digital_credentials_allowed,
    authorized,
    get_allowable_actions,
    get_allowed,
    get_allowed_filings,
    is_allowed,
    is_self_registered_owner_operator,
)
from legal_api.services.warnings.business.business_checks import WarningType
from tests import integration_authorization, not_github_ci
from tests.unit.models import (
    factory_completed_filing,
    factory_filing,
    factory_incomplete_statuses,
    factory_legal_entity,
    factory_party_role,
    factory_user,
)

from .utils import helper_create_jwt


def test_jwt_manager_initialized(jwt):
    """Assert that the jwt_manager is created as part of the fixtures."""
    assert jwt


@not_github_ci
def test_jwt_manager_correct_test_config(app_request, jwt):
    """Assert that the test configuration for the JWT is working as expected."""
    with app_request.app_context():
        message = "This is a protected end-point"
        protected_route = "/fake_jwt_route"

        @app_request.route(protected_route)
        @jwt.has_one_of_roles([STAFF_ROLE])
        def get():
            return jsonify(message=message)

        # assert that JWT is setup correctly for a known role
        token = helper_create_jwt(jwt, [STAFF_ROLE])
        headers = {"Authorization": "Bearer " + token}
        rv = app_request.test_client().get(protected_route, headers=headers)
        assert rv.status_code == HTTPStatus.OK

        # assert the JWT fails for an unknown role
        token = helper_create_jwt(jwt, ["SHOULD-FAIL"])
        headers = {"Authorization": "Bearer " + token}
        rv = app_request.test_client().get(protected_route, headers=headers)
        assert rv.status_code == HTTPStatus.UNAUTHORIZED


TEST_AUTHZ_DATA = [
    (
        "staff_role",  # test name
        "CP1234567",  # business identifier
        "happy-staff",  # username
        [STAFF_ROLE],  # roles
        ["view", "edit"],  # allowed actions
        ["edit"],  # requested action
        HTTPStatus.OK,
    ),  # expected response
    ("colin svc role", "CP1234567", "CP1234567", [COLIN_SVC_ROLE], ["view", "edit"], ["edit"], HTTPStatus.OK),
    ("authorized_user", "CP0001237", "CP1234567", [BASIC_USER], ["view", "edit"], ["edit"], HTTPStatus.OK),
    (
        "unauthorized_user",
        "CP1234567",
        "Not-Match-Identifier",
        [BASIC_USER],
        None,
        ["edit"],
        HTTPStatus.METHOD_NOT_ALLOWED,
    ),
    ("missing_action", "CP1234567", "Not-Match-Identifier", [BASIC_USER], None, None, HTTPStatus.METHOD_NOT_ALLOWED),
    (
        "invalid_action",
        "CP1234567",
        "Not-Match-Identifier",
        [BASIC_USER],
        None,
        ["scrum"],
        HTTPStatus.METHOD_NOT_ALLOWED,
    ),
    (
        "add_comment_not_allowed",
        "CP0001237",
        "CP1234567",
        [BASIC_USER],
        None,
        ["add_comment"],
        HTTPStatus.METHOD_NOT_ALLOWED,
    ),
]


class FilingKey(str, Enum):
    """Define an enum for expected allowable filing keys."""

    ADMN_FRZE = "ADMN_FRZE"
    IA_CP = "IA_CP"
    IA_BC = "IA_BC"
    IA_BEN = "IA_BEN"
    IA_CC = "IA_CC"
    IA_ULC = "IA_ULC"
    REG_SP = "REG_SP"
    REG_GP = "REG_GP"
    CORRCTN = "CORRCTN"
    CORRCTN_FIRMS = "CORRCTN_FIRMS"
    AR_CP = "AR_CP"
    AR_CORPS = "AR_CORPS"
    COA_CP = "COA_CP"
    COA_CORPS = "COA_CORPS"
    COD_CP = "COD_CP"
    COD_CORPS = "COD_CORPS"
    COURT_ORDER = "COURT_ORDER"
    VOL_DISS = "VOL_DISS"
    ADM_DISS = "ADM_DISS"
    VOL_DISS_FIRMS = "VOL_DISS_FIRMS"
    ADM_DISS_FIRMS = "ADM_DISS_FIRMS"
    REGISTRARS_NOTATION = "REGISTRARS_NOTATION"
    REGISTRARS_ORDER = "REGISTRARS_ORDER"
    SPECIAL_RESOLUTION = "SPECIAL_RESOLUTION"
    AGM_EXTENSION = "AGM_EXTENSION"
    AGM_LOCATION_CHANGE = "AGM_LOCATION_CHANGE"
    ALTERATION = "ALTERATION"
    CONSENT_CONTINUATION_OUT = "CONSENT_CONTINUATION_OUT"
    CONTINUATION_OUT = "CONTINUATION_OUT"
    TRANSITION = "TRANSITION"
    CHANGE_OF_REGISTRATION = "CHANGE_OF_REGISTRATION"
    CONV_FIRMS = "CONV_FIRM"
    RESTRN_FULL_CORPS = "RESTRN_FULL_CORPS"
    RESTRN_LTD_CORPS = "RESTRN_LTD_CORPS"
    RESTRN_LTD_EXT_CORPS = "RESTRN_LTD_EXT_CORPS"
    RESTRN_LTD_EXT_LLC = "RESTRN_LTD_EXT_LLC"
    RESTRN_LTD_TO_FULL_CORPS = "RESTRN_LTD_TO_FULL_CORPS"
    RESTRN_LTD_TO_FULL_LLC = "RESTRN_LTD_TO_FULL_LLC"
    PUT_BACK_ON = "PUT_BACK_ON"
    AMALGAMATION_REGULAR = "AMALGAMATION_REGULAR"
    AMALGAMATION_VERTICAL = "AMALGAMATION_VERTICAL"
    AMALGAMATION_HORIZONTAL = "AMALGAMATION_HORIZONTAL"


EXPECTED_DATA = {
    FilingKey.ADMN_FRZE: {"displayName": "Admin Freeze", "feeCode": "NOFEE", "name": "adminFreeze"},
    FilingKey.AR_CP: {"displayName": "Annual Report", "feeCode": "OTANN", "name": "annualReport"},
    FilingKey.AR_CORPS: {"displayName": "Annual Report", "feeCode": "BCANN", "name": "annualReport"},
    FilingKey.COA_CP: {"displayName": "Address Change", "feeCode": "OTADD", "name": "changeOfAddress"},
    FilingKey.COA_CORPS: {"displayName": "Address Change", "feeCode": "BCADD", "name": "changeOfAddress"},
    FilingKey.COD_CP: {"displayName": "Director Change", "feeCode": "OTCDR", "name": "changeOfDirectors"},
    FilingKey.COD_CORPS: {"displayName": "Director Change", "feeCode": "BCCDR", "name": "changeOfDirectors"},
    FilingKey.CORRCTN: {"displayName": "Register Correction Application", "feeCode": "CRCTN", "name": "correction"},
    FilingKey.CORRCTN_FIRMS: {
        "displayName": "Register Correction Application",
        "feeCode": "FMCORR",
        "name": "correction",
    },
    FilingKey.COURT_ORDER: {"displayName": "Court Order", "feeCode": "NOFEE", "name": "courtOrder"},
    FilingKey.VOL_DISS: {
        "displayName": "Voluntary Dissolution",
        "feeCode": "DIS_VOL",
        "name": "dissolution",
        "type": "voluntary",
    },
    FilingKey.ADM_DISS: {
        "displayName": "Administrative Dissolution",
        "feeCode": "DIS_ADM",
        "name": "dissolution",
        "type": "administrative",
    },
    FilingKey.VOL_DISS_FIRMS: {
        "displayName": "Statement of Dissolution",
        "feeCode": "DIS_VOL",
        "name": "dissolution",
        "type": "voluntary",
    },
    FilingKey.ADM_DISS_FIRMS: {
        "displayName": "Statement of Dissolution",
        "feeCode": "DIS_ADM",
        "name": "dissolution",
        "type": "administrative",
    },
    FilingKey.REGISTRARS_NOTATION: {
        "displayName": "Registrar's Notation",
        "feeCode": "NOFEE",
        "name": "registrarsNotation",
    },
    FilingKey.REGISTRARS_ORDER: {"displayName": "Registrar's Order", "feeCode": "NOFEE", "name": "registrarsOrder"},
    FilingKey.SPECIAL_RESOLUTION: {
        "displayName": "Special Resolution",
        "feeCode": "SPRLN",
        "name": "specialResolution",
    },
    FilingKey.AGM_EXTENSION: {"displayName": "Request for AGM Extension", "feeCode": "AGMDT", "name": "agmExtension"},
    FilingKey.AGM_LOCATION_CHANGE: {
        "displayName": "AGM Location Change",
        "feeCode": "AGMLC",
        "name": "agmLocationChange",
    },
    FilingKey.ALTERATION: {"displayName": "Alteration", "feeCode": "ALTER", "name": "alteration"},
    FilingKey.CONSENT_CONTINUATION_OUT: {
        "displayName": "6-Month Consent to Continue Out",
        "feeCode": "CONTO",
        "name": "consentContinuationOut",
    },
    FilingKey.CONTINUATION_OUT: {"displayName": "Continuation Out", "feeCode": "COUTI", "name": "continuationOut"},
    FilingKey.TRANSITION: {"displayName": "Transition Application", "feeCode": "TRANS", "name": "transition"},
    FilingKey.IA_CP: {
        "displayName": "Incorporation Application",
        "feeCode": "OTINC",
        "name": "incorporationApplication",
    },
    FilingKey.IA_BC: {
        "displayName": "BC Limited Company Incorporation Application",
        "feeCode": "BCINC",
        "name": "incorporationApplication",
    },
    FilingKey.IA_BEN: {
        "displayName": "BC Benefit Company Incorporation Application",
        "feeCode": "BCINC",
        "name": "incorporationApplication",
    },
    FilingKey.IA_CC: {
        "displayName": "BC Community Contribution Company Incorporation Application",
        "feeCode": "BCINC",
        "name": "incorporationApplication",
    },
    FilingKey.IA_ULC: {
        "displayName": "BC Unlimited Liability Company Incorporation Application",
        "feeCode": "BCINC",
        "name": "incorporationApplication",
    },
    FilingKey.REG_SP: {
        "displayName": "BC Sole Proprietorship Registration",
        "feeCode": "FRREG",
        "name": "registration",
    },
    FilingKey.REG_GP: {
        "displayName": "BC General Partnership Registration",
        "feeCode": "FRREG",
        "name": "registration",
    },
    FilingKey.CHANGE_OF_REGISTRATION: {
        "displayName": "Change of Registration Application",
        "feeCode": "FMCHANGE",
        "name": "changeOfRegistration",
    },
    FilingKey.CONV_FIRMS: {"displayName": "Record Conversion", "feeCode": "FMCONV", "name": "conversion"},
    FilingKey.RESTRN_FULL_CORPS: {
        "displayName": "Full Restoration Application",
        "feeCode": "RESTF",
        "name": "restoration",
        "type": "fullRestoration",
    },
    FilingKey.RESTRN_LTD_CORPS: {
        "displayName": "Limited Restoration Application",
        "feeCode": "RESTL",
        "name": "restoration",
        "type": "limitedRestoration",
    },
    FilingKey.RESTRN_LTD_EXT_CORPS: {
        "displayName": "Limited Restoration Extension Application",
        "feeCode": "RESXL",
        "name": "restoration",
        "type": "limitedRestorationExtension",
    },
    FilingKey.RESTRN_LTD_TO_FULL_CORPS: {
        "displayName": "Conversion to Full Restoration Application",
        "feeCode": "RESXF",
        "name": "restoration",
        "type": "limitedRestorationToFull",
    },
    FilingKey.RESTRN_LTD_EXT_LLC: {
        "displayName": "Limited Restoration Extension Application",
        "feeCode": None,
        "name": "restoration",
        "type": "limitedRestorationExtension",
    },
    FilingKey.RESTRN_LTD_TO_FULL_LLC: {
        "displayName": "Conversion to Full Restoration Application",
        "feeCode": None,
        "name": "restoration",
        "type": "limitedRestorationToFull",
    },
    FilingKey.PUT_BACK_ON: {"displayName": "Correction - Put Back On", "feeCode": "NOFEE", "name": "putBackOn"},
    FilingKey.AMALGAMATION_REGULAR: {
        "name": "amalgamationApplication",
        "type": "regular",
        "displayName": "Amalgamation Application (Regular)",
        "feeCode": "AMALR",
    },
    FilingKey.AMALGAMATION_VERTICAL: {
        "name": "amalgamationApplication",
        "type": "vertical",
        "displayName": "Amalgamation Application Short-form (Vertical)",
        "feeCode": "AMALV",
    },
    FilingKey.AMALGAMATION_HORIZONTAL: {
        "name": "amalgamationApplication",
        "type": "horizontal",
        "displayName": "Amalgamation Application Short-form (Horizontal)",
        "feeCode": "AMALH",
    },
}

BLOCKER_FILING_STATUSES = factory_incomplete_statuses()
BLOCKER_FILING_STATUSES_AND_ADDITIONAL = factory_incomplete_statuses(["unknown_status_1", "unknown_status_2"])
BLOCKER_DISSOLUTION_STATUSES_FOR_AMALG = [Filing.Status.PENDING.value, Filing.Status.PAID.value]
BLOCKER_FILING_TYPES = ["alteration", "correction"]

AGM_EXTENSION_FILING_TEMPLATE = copy.deepcopy(FILING_TEMPLATE)
AGM_EXTENSION_FILING_TEMPLATE["filing"]["agmExtension"] = AGM_EXTENSION

AGM_LOCATION_CHANGE_FILING_TEMPLATE = copy.deepcopy(FILING_TEMPLATE)
AGM_LOCATION_CHANGE_FILING_TEMPLATE["filing"]["agmLocationChange"] = AGM_LOCATION_CHANGE

RESTORATION_FILING_TEMPLATE = copy.deepcopy(FILING_TEMPLATE)
RESTORATION_FILING_TEMPLATE["filing"]["restoration"] = RESTORATION

DISSOLUTION_FILING_TEMPLATE = copy.deepcopy(FILING_TEMPLATE)
DISSOLUTION_FILING_TEMPLATE["filing"]["dissolution"] = DISSOLUTION

PUT_BACK_ON_FILING_TEMPLATE = copy.deepcopy(FILING_TEMPLATE)
PUT_BACK_ON_FILING_TEMPLATE["filing"]["putBackOn"] = PUT_BACK_ON

CONTINUATION_IN_TEMPLATE = copy.deepcopy(FILING_TEMPLATE)
CONTINUATION_IN_TEMPLATE["filing"]["continuationIn"] = CONTINUATION_IN

CONTINUATION_OUT_TEMPLATE = copy.deepcopy(FILING_TEMPLATE)
CONTINUATION_OUT_TEMPLATE["filing"]["continuationOut"] = CONTINUATION_OUT

CONSENT_CONTINUATION_OUT_TEMPLATE = copy.deepcopy(FILING_TEMPLATE)
CONSENT_CONTINUATION_OUT_TEMPLATE["filing"]["consentContinuationOut"] = CONSENT_CONTINUATION_OUT

FILING_DATA = {
    "agmExtension": AGM_EXTENSION_FILING_TEMPLATE,
    "agmLocationChange": AGM_LOCATION_CHANGE_FILING_TEMPLATE,
    "alteration": ALTERATION_FILING_TEMPLATE,
    "correction": CORRECTION_AR,
    "changeOfRegistration": CHANGE_OF_REGISTRATION_TEMPLATE,
    "restoration.limitedRestoration": RESTORATION_FILING_TEMPLATE,
    "restoration.fullRestoration": RESTORATION_FILING_TEMPLATE,
    "restoration.limitedRestorationExtension": RESTORATION_FILING_TEMPLATE,
    "dissolution": DISSOLUTION_FILING_TEMPLATE,
    "putBackOn": PUT_BACK_ON_FILING_TEMPLATE,
    "continuationIn": CONTINUATION_IN_TEMPLATE,
    "continuationOut": CONTINUATION_OUT_TEMPLATE,
    "consentContinuationOut": CONSENT_CONTINUATION_OUT_TEMPLATE,
}

MISSING_BUSINESS_INFO_WARNINGS = [
    {
        "warningType": WarningType.MISSING_REQUIRED_BUSINESS_INFO,
        "code": "NO_BUSINESS_OFFICE",
        "message": "A business office is required.",
    }
]


def expected_lookup(filing_keys: list):
    results = []
    for filing_key in filing_keys:
        results.append(EXPECTED_DATA[filing_key])
    return results


@not_github_ci
@pytest.mark.parametrize(
    "test_name,identifier,username,roles,allowed_actions,requested_actions,expected", TEST_AUTHZ_DATA
)
def test_authorized_user(
    monkeypatch, app_request, jwt, test_name, identifier, username, roles, allowed_actions, requested_actions, expected
):
    """Assert that the type of user authorization is correct, based on the expected outcome."""
    from requests import Response

    print(test_name)

    # mocks, the get and json calls for requests.Response
    def mock_get(*args, **kwargs):  # pylint: disable=unused-argument; mocks of library methods
        resp = Response()
        resp.status_code = 200
        return resp

    def mock_json(self, **kwargs):  # pylint: disable=unused-argument; mocks of library methods
        return {"roles": allowed_actions}

    monkeypatch.setattr("requests.sessions.Session.get", mock_get)
    monkeypatch.setattr("requests.Response.json", mock_json)

    # setup
    @app_request.route("/fake_jwt_route/<string:identifier>")
    @jwt.requires_auth
    def get_fake(identifier: str):
        if not authorized(identifier, jwt, ["view"]):
            return jsonify(message="failed"), HTTPStatus.METHOD_NOT_ALLOWED
        return jsonify(message="success"), HTTPStatus.OK

    token = helper_create_jwt(jwt, roles=roles, username=username)
    headers = {"Authorization": "Bearer " + token}

    # test it
    rv = app_request.test_client().get(f"/fake_jwt_route/{identifier}", headers=headers)

    # check it
    assert rv.status_code == expected


TEST_INTEG_AUTHZ_DATA = [
    (
        "staff_role",  # test name
        "CP1234567",  # business identifier
        "happy-staff",  # username
        [STAFF_ROLE],  # roles
        ["view", "edit"],  # allowed actions
        ["edit"],  # requested action
        HTTPStatus.OK,
    ),  # expected response
    ("colin svc role", "CP1234567", "CP1234567", [COLIN_SVC_ROLE], ["view", "edit"], ["edit"], HTTPStatus.OK),
    (
        "unauthorized_user",
        "CP1234567",
        "Not-Match-Identifier",
        [BASIC_USER],
        None,
        ["edit"],
        HTTPStatus.METHOD_NOT_ALLOWED,
    ),
    ("missing_action", "CP1234567", "Not-Match-Identifier", [BASIC_USER], None, None, HTTPStatus.METHOD_NOT_ALLOWED),
    (
        "invalid_action",
        "CP1234567",
        "Not-Match-Identifier",
        [BASIC_USER],
        None,
        ["scrum"],
        HTTPStatus.METHOD_NOT_ALLOWED,
    ),
    (
        "add_comment_not_allowed",
        "CP0001237",
        "CP1234567",
        [BASIC_USER],
        None,
        ["add_comment"],
        HTTPStatus.METHOD_NOT_ALLOWED,
    ),
]


@integration_authorization
@pytest.mark.parametrize(
    "test_name,identifier,username,roles,allowed_actions,requested_actions,expected", TEST_INTEG_AUTHZ_DATA
)
def test_authorized_user_integ(
    monkeypatch, app, jwt, test_name, identifier, username, roles, allowed_actions, requested_actions, expected
):
    """Assert that the type of user authorization is correct, based on the expected outcome."""
    import flask  # noqa: F401; import actually used in mock

    # setup
    token = helper_create_jwt(jwt, roles=roles, username=username)
    headers = {"Authorization": "Bearer " + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers["Authorization"]

    with app.test_request_context():
        monkeypatch.setattr("flask.request.headers.get", mock_auth)

        rv = authorized(identifier, jwt, ["view"])

    # check it
    if expected == HTTPStatus.OK:
        assert rv
    else:
        assert not rv


def test_authorized_missing_args():
    """Assert that the missing args return False."""
    identifier = "a corp"
    jwt = "fake"
    action = "fake"

    rv = authorized(identifier, jwt, None)
    assert not rv

    rv = authorized(identifier, None, action)
    assert not rv

    rv = authorized(None, jwt, action)
    assert not rv


def test_authorized_bad_url(monkeypatch, app, jwt):
    """Assert that an invalid auth service URL returns False."""
    import flask  # noqa: F401; import actually used in mock

    # setup
    identifier = "CP1234567"
    username = "username"
    roles = [BASIC_USER]
    token = helper_create_jwt(jwt, roles=roles, username=username)
    headers = {"Authorization": "Bearer " + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers["Authorization"]

    with app.test_request_context():
        monkeypatch.setattr("flask.request.headers.get", mock_auth)
        auth_svc_url = app.config["AUTH_SVC_URL"]
        app.config["AUTH_SVC_URL"] = "http://no.way.this.works/dribble"

        rv = authorized(identifier, jwt, ["view"])

        app.config["AUTH_SVC_URL"] = auth_svc_url

    assert not rv


def test_authorized_invalid_roles(monkeypatch, app, jwt):
    """Assert that an invalid role returns False."""
    import flask  # noqa: F401 ; import actually used in mock

    # setup noqa: I003
    identifier = "CP1234567"
    username = "username"
    roles = ["NONE"]
    token = helper_create_jwt(jwt, roles=roles, username=username)
    headers = {"Authorization": "Bearer " + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers["Authorization"]

    with app.test_request_context():
        monkeypatch.setattr("flask.request.headers.get", mock_auth)
        rv = authorized(identifier, jwt, ["view"])

    assert not rv


@pytest.mark.parametrize(
    "test_name,state,entity_types,username,roles,expected",
    [
        # active business
        (
            "staff_active_cp",
            LegalEntity.State.ACTIVE,
            ["CP"],
            "staff",
            [STAFF_ROLE],
            [
                "adminFreeze",
                "annualReport",
                "changeOfAddress",
                "changeOfDirectors",
                "correction",
                "courtOrder",
                {"dissolution": ["voluntary", "administrative"]},
                "incorporationApplication",
                "registrarsNotation",
                "registrarsOrder",
                "specialResolution",
            ],
        ),
        (
            "staff_active_corps",
            LegalEntity.State.ACTIVE,
            ["BC", "BEN", "CC", "ULC"],
            "staff",
            [STAFF_ROLE],
            [
                "adminFreeze",
                "agmExtension",
                "agmLocationChange",
                "alteration",
                {"amalgamationApplication": ["regular", "vertical", "horizontal"]},
                "annualReport",
                "changeOfAddress",
                "changeOfDirectors",
                "consentContinuationOut",
                "continuationOut",
                "correction",
                "courtOrder",
                {"dissolution": ["voluntary", "administrative"]},
                "incorporationApplication",
                "registrarsNotation",
                "registrarsOrder",
                "transition",
                {"restoration": ["limitedRestorationExtension", "limitedRestorationToFull"]},
            ],
        ),
        ("staff_active_llc", LegalEntity.State.ACTIVE, ["LLC"], "staff", [STAFF_ROLE], []),
        (
            "staff_active_firms",
            LegalEntity.State.ACTIVE,
            ["SP", "GP"],
            "staff",
            [STAFF_ROLE],
            [
                "adminFreeze",
                "changeOfRegistration",
                "conversion",
                "correction",
                "courtOrder",
                {"dissolution": ["voluntary", "administrative"]},
                "registrarsNotation",
                "registrarsOrder",
                "registration",
            ],
        ),
        (
            "user_active_cp",
            LegalEntity.State.ACTIVE,
            ["CP"],
            "general",
            [BASIC_USER],
            [
                "annualReport",
                "changeOfAddress",
                "changeOfDirectors",
                {"dissolution": ["voluntary"]},
                "incorporationApplication",
                "specialResolution",
            ],
        ),
        (
            "user_active_corps",
            LegalEntity.State.ACTIVE,
            ["BC", "BEN", "CC", "ULC"],
            "general",
            [BASIC_USER],
            [
                "agmExtension",
                "agmLocationChange",
                "alteration",
                {"amalgamationApplication": ["regular", "vertical", "horizontal"]},
                "annualReport",
                "changeOfAddress",
                "changeOfDirectors",
                "consentContinuationOut",
                {"dissolution": ["voluntary"]},
                "incorporationApplication",
                "transition",
            ],
        ),
        ("user_active_llc", LegalEntity.State.ACTIVE, ["LLC"], "general", [BASIC_USER], []),
        (
            "user_active_firms",
            LegalEntity.State.ACTIVE,
            ["SP", "GP"],
            "general",
            [BASIC_USER],
            ["changeOfRegistration", {"dissolution": ["voluntary"]}, "registration"],
        ),
        # historical business
        (
            "staff_historical_cp",
            LegalEntity.State.HISTORICAL,
            ["CP"],
            "staff",
            [STAFF_ROLE],
            ["courtOrder", "putBackOn", "registrarsNotation", "registrarsOrder"],
        ),
        (
            "staff_historical_corps",
            LegalEntity.State.HISTORICAL,
            ["BC", "BEN", "CC", "ULC"],
            "staff",
            [STAFF_ROLE],
            [
                "courtOrder",
                "putBackOn",
                "registrarsNotation",
                "registrarsOrder",
                {"restoration": ["fullRestoration", "limitedRestoration"]},
            ],
        ),
        ("staff_historical_llc", LegalEntity.State.HISTORICAL, ["LLC"], "staff", [STAFF_ROLE], []),
        (
            "staff_historical_firms",
            LegalEntity.State.HISTORICAL,
            ["SP", "GP"],
            "staff",
            [STAFF_ROLE],
            ["courtOrder", "putBackOn", "registrarsNotation", "registrarsOrder"],
        ),
        ("user_historical", LegalEntity.State.HISTORICAL, ["BC", "BEN", "CC", "ULC", "LLC"], "staff", [BASIC_USER], []),
    ],
)
def test_get_allowed(monkeypatch, app, jwt, test_name, state, entity_types, username, roles, expected):
    """Assert that get allowed returns valid filings."""
    token = helper_create_jwt(jwt, roles=roles, username=username)
    headers = {"Authorization": "Bearer " + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers[one]

    with app.test_request_context():
        monkeypatch.setattr("flask.request.headers.get", mock_auth)
        for entity_type in entity_types:
            filing_types = get_allowed(state, entity_type, jwt)
            assert filing_types == expected


@pytest.mark.parametrize(
    "test_name,state,filing_type,sub_filing_type,legal_types,username,roles,expected",
    [
        # active business
        (
            "staff_active_allowed",
            LegalEntity.State.ACTIVE,
            "agmExtension",
            None,
            ["BC", "BEN", "ULC", "CC"],
            "staff",
            [STAFF_ROLE],
            True,
        ),
        ("staff_active", LegalEntity.State.ACTIVE, "agmExtension", None, ["CP", "LLC"], "staff", [STAFF_ROLE], False),
        (
            "staff_active_allowed",
            LegalEntity.State.ACTIVE,
            "agmLocationChange",
            None,
            ["BC", "BEN", "ULC", "CC"],
            "staff",
            [STAFF_ROLE],
            True,
        ),
        (
            "staff_active",
            LegalEntity.State.ACTIVE,
            "agmLocationChange",
            None,
            ["CP", "LLC"],
            "staff",
            [STAFF_ROLE],
            False,
        ),
        (
            "staff_active_allowed",
            LegalEntity.State.ACTIVE,
            "alteration",
            None,
            ["BC", "BEN", "ULC", "CC"],
            "staff",
            [STAFF_ROLE],
            True,
        ),
        ("staff_active", LegalEntity.State.ACTIVE, "alteration", None, ["CP", "LLC"], "staff", [STAFF_ROLE], False),
        (
            "staff_active_allowed",
            LegalEntity.State.ACTIVE,
            "annualReport",
            None,
            ["CP", "BEN", "BC", "CC", "ULC"],
            "staff",
            [STAFF_ROLE],
            True,
        ),
        ("staff_active", LegalEntity.State.ACTIVE, "annualReport", None, ["LLC"], "staff", [STAFF_ROLE], False),
        (
            "staff_active_allowed",
            LegalEntity.State.ACTIVE,
            "changeOfAddress",
            None,
            ["CP", "BEN", "BC", "CC", "ULC"],
            "staff",
            [STAFF_ROLE],
            True,
        ),
        ("staff_active", LegalEntity.State.ACTIVE, "changeOfAddress", None, ["LLC"], "staff", [STAFF_ROLE], False),
        (
            "staff_active_allowed",
            LegalEntity.State.ACTIVE,
            "changeOfDirectors",
            None,
            ["CP", "BEN", "BC", "CC", "ULC"],
            "staff",
            [STAFF_ROLE],
            True,
        ),
        ("staff_active", LegalEntity.State.ACTIVE, "changeOfDirectors", None, ["LLC"], "staff", [STAFF_ROLE], False),
        (
            "staff_active_allowed",
            LegalEntity.State.ACTIVE,
            "consentContinuationOut",
            None,
            ["BC", "BEN", "ULC", "CC"],
            "staff",
            [STAFF_ROLE],
            True,
        ),
        (
            "staff_active",
            LegalEntity.State.ACTIVE,
            "consentContinuationOut",
            None,
            ["CP", "LLC"],
            "staff",
            [STAFF_ROLE],
            False,
        ),
        (
            "staff_active_allowed",
            LegalEntity.State.ACTIVE,
            "continuationOut",
            None,
            ["BC", "BEN", "ULC", "CC"],
            "staff",
            [STAFF_ROLE],
            False,
        ),
        (
            "staff_active",
            LegalEntity.State.ACTIVE,
            "continuationOut",
            None,
            ["CP", "LLC"],
            "staff",
            [STAFF_ROLE],
            False,
        ),
        (
            "staff_active_allowed",
            LegalEntity.State.ACTIVE,
            "correction",
            None,
            ["CP", "BEN", "BC", "CC", "ULC", "SP", "GP"],
            "staff",
            [STAFF_ROLE],
            True,
        ),
        ("staff_active", LegalEntity.State.ACTIVE, "correction", None, ["LLC"], "staff", [STAFF_ROLE], False),
        (
            "staff_active_allowed",
            LegalEntity.State.ACTIVE,
            "courtOrder",
            None,
            ["SP", "GP", "CP", "BC", "BEN", "CC", "ULC"],
            "staff",
            [STAFF_ROLE],
            True,
        ),
        ("staff_active_allowed", LegalEntity.State.ACTIVE, "courtOrder", None, ["LLC"], "staff", [STAFF_ROLE], False),
        (
            "staff_active_allowed",
            LegalEntity.State.ACTIVE,
            "dissolution",
            "voluntary",
            ["CP", "BC", "BEN", "CC", "ULC", "SP", "GP"],
            "staff",
            [STAFF_ROLE],
            True,
        ),
        (
            "staff_active_allowed",
            LegalEntity.State.ACTIVE,
            "dissolution",
            "administrative",
            ["CP", "BC", "BEN", "CC", "ULC", "SP", "GP"],
            "staff",
            [STAFF_ROLE],
            True,
        ),
        (
            "staff_active_allowed",
            LegalEntity.State.ACTIVE,
            "incorporationApplication",
            None,
            ["CP", "BC", "BEN", "ULC", "CC"],
            "staff",
            [STAFF_ROLE],
            False,
        ),
        (
            "staff_active",
            LegalEntity.State.ACTIVE,
            "restoration",
            "limitedRestorationExtension",
            ["BC", "BEN", "CC", "ULC"],
            "staff",
            [STAFF_ROLE],
            False,
        ),
        (
            "staff_active",
            LegalEntity.State.ACTIVE,
            "restoration",
            "limitedRestorationToFull",
            ["BC", "BEN", "CC", "ULC"],
            "staff",
            [STAFF_ROLE],
            False,
        ),
        (
            "staff_active",
            LegalEntity.State.ACTIVE,
            "restoration",
            "fullRestoration",
            ["CP", "BC", "BEN", "CC", "ULC", "LLC"],
            "staff",
            [STAFF_ROLE],
            False,
        ),
        (
            "staff_active",
            LegalEntity.State.ACTIVE,
            "restoration",
            "limitedRestoration",
            ["CP", "BC", "BEN", "CC", "ULC", "LLC"],
            "staff",
            [STAFF_ROLE],
            False,
        ),
        (
            "staff_active_allowed",
            LegalEntity.State.ACTIVE,
            "specialResolution",
            None,
            ["CP"],
            "staff",
            [STAFF_ROLE],
            True,
        ),
        (
            "staff_active",
            LegalEntity.State.ACTIVE,
            "specialResolution",
            None,
            ["BC", "BEN", "CC", "ULC", "LLC"],
            "staff",
            [STAFF_ROLE],
            False,
        ),
        (
            "staff_active_allowed",
            LegalEntity.State.ACTIVE,
            "transition",
            None,
            ["BC", "BEN", "CC", "ULC"],
            "staff",
            [STAFF_ROLE],
            True,
        ),
        ("staff_active", LegalEntity.State.ACTIVE, "transition", None, ["CP", "LLC"], "staff", [STAFF_ROLE], False),
        (
            "staff_active_allowed",
            LegalEntity.State.ACTIVE,
            "registrarsNotation",
            None,
            ["CP", "BC", "BEN", "CC", "ULC"],
            "staff",
            [STAFF_ROLE],
            True,
        ),
        (
            "staff_active_allowed",
            LegalEntity.State.ACTIVE,
            "registrarsOrder",
            None,
            ["SP", "GP", "CP", "BC", "BEN", "CC", "ULC"],
            "staff",
            [STAFF_ROLE],
            True,
        ),
        (
            "staff_active_allowed",
            LegalEntity.State.ACTIVE,
            "registration",
            None,
            ["SP", "GP"],
            "staff",
            [STAFF_ROLE],
            False,
        ),
        (
            "staff_active_allowed",
            LegalEntity.State.ACTIVE,
            "changeOfRegistration",
            None,
            ["SP", "GP"],
            "staff",
            [STAFF_ROLE],
            True,
        ),
        (
            "user_active_allowed",
            LegalEntity.State.ACTIVE,
            "agmExtension",
            None,
            ["BC", "BEN", "ULC", "CC"],
            "general",
            [BASIC_USER],
            True,
        ),
        ("user_active", LegalEntity.State.ACTIVE, "agmExtension", None, ["CP", "LLC"], "general", [BASIC_USER], False),
        (
            "user_active_allowed",
            LegalEntity.State.ACTIVE,
            "agmLocationChange",
            None,
            ["BC", "BEN", "ULC", "CC"],
            "general",
            [BASIC_USER],
            True,
        ),
        (
            "user_active",
            LegalEntity.State.ACTIVE,
            "agmLocationChange",
            None,
            ["CP", "LLC"],
            "general",
            [BASIC_USER],
            False,
        ),
        (
            "user_active_allowed",
            LegalEntity.State.ACTIVE,
            "alteration",
            None,
            ["BC", "BEN", "ULC", "CC"],
            "general",
            [BASIC_USER],
            True,
        ),
        ("user_active", LegalEntity.State.ACTIVE, "alteration", None, ["CP", "LLC"], "general", [BASIC_USER], False),
        (
            "user_active_allowed",
            LegalEntity.State.ACTIVE,
            "annualReport",
            None,
            ["CP", "BEN", "BC", "CC", "ULC"],
            "general",
            [BASIC_USER],
            True,
        ),
        ("user_active", LegalEntity.State.ACTIVE, "annualReport", None, ["LLC"], "general", [BASIC_USER], False),
        (
            "user_active_allowed",
            LegalEntity.State.ACTIVE,
            "changeOfAddress",
            None,
            ["CP", "BEN", "BC", "CC", "ULC"],
            "general",
            [BASIC_USER],
            True,
        ),
        ("user_active", LegalEntity.State.ACTIVE, "changeOfAddress", None, ["LLC"], "general", [BASIC_USER], False),
        (
            "user_active_allowed",
            LegalEntity.State.ACTIVE,
            "changeOfDirectors",
            None,
            ["CP", "BEN", "BC", "CC", "ULC"],
            "general",
            [BASIC_USER],
            True,
        ),
        ("user_active", LegalEntity.State.ACTIVE, "changeOfDirectors", None, ["LLC"], "general", [BASIC_USER], False),
        (
            "user_active",
            LegalEntity.State.ACTIVE,
            "correction",
            None,
            ["CP", "BC", "BEN", "CC", "ULC", "LLC"],
            "general",
            [BASIC_USER],
            False,
        ),
        (
            "user_active",
            LegalEntity.State.ACTIVE,
            "courtOrder",
            None,
            ["CP", "BC", "BEN", "CC", "ULC", "LLC"],
            "general",
            [BASIC_USER],
            False,
        ),
        (
            "user_active_allowed",
            LegalEntity.State.ACTIVE,
            "continuationOut",
            None,
            ["BC", "BEN", "ULC", "CC"],
            "general",
            [BASIC_USER],
            False,
        ),
        (
            "user_active",
            LegalEntity.State.ACTIVE,
            "continuationOut",
            None,
            ["CP", "LLC"],
            "general",
            [BASIC_USER],
            False,
        ),
        (
            "user_active_allowed",
            LegalEntity.State.ACTIVE,
            "dissolution",
            "voluntary",
            ["CP", "BC", "BEN", "CC", "ULC", "SP", "GP"],
            "general",
            [BASIC_USER],
            True,
        ),
        (
            "user_active_allowed",
            LegalEntity.State.ACTIVE,
            "incorporationApplication",
            None,
            ["CP", "BC", "BEN", "ULC", "CC"],
            "general",
            [BASIC_USER],
            False,
        ),
        (
            "user_active_allowed",
            LegalEntity.State.ACTIVE,
            "registration",
            None,
            ["SP", "GP"],
            "general",
            [BASIC_USER],
            False,
        ),
        (
            "user_active_allowed",
            LegalEntity.State.ACTIVE,
            "changeOfRegistration",
            None,
            ["SP", "GP"],
            "general",
            [BASIC_USER],
            True,
        ),
        (
            "user_active",
            LegalEntity.State.ACTIVE,
            "restoration",
            "fullRestoration",
            ["CP", "BC", "BEN", "CC", "ULC", "LLC"],
            "general",
            [BASIC_USER],
            False,
        ),
        (
            "user_active",
            LegalEntity.State.ACTIVE,
            "restoration",
            "limitedRestoration",
            ["CP", "BC", "BEN", "CC", "ULC", "LLC"],
            "general",
            [BASIC_USER],
            False,
        ),
        (
            "user_active_allowed",
            LegalEntity.State.ACTIVE,
            "specialResolution",
            None,
            ["CP"],
            "general",
            [BASIC_USER],
            True,
        ),
        (
            "user_active",
            LegalEntity.State.ACTIVE,
            "specialResolution",
            None,
            ["BC", "BEN", "CC", "ULC", "LLC"],
            "general",
            [BASIC_USER],
            False,
        ),
        (
            "user_active_allowed",
            LegalEntity.State.ACTIVE,
            "transition",
            None,
            ["BC", "BEN", "CC", "ULC"],
            "general",
            [BASIC_USER],
            True,
        ),
        ("user_active", LegalEntity.State.ACTIVE, "transition", None, ["CP", "LLC"], "general", [BASIC_USER], False),
        (
            "user_active",
            LegalEntity.State.ACTIVE,
            "registrarsNotation",
            None,
            ["CP", "BC", "BEN", "CC", "ULC", "LLC"],
            "general",
            [BASIC_USER],
            False,
        ),
        (
            "user_active",
            LegalEntity.State.ACTIVE,
            "registrarsOrder",
            None,
            ["CP", "BC", "BEN", "CC", "ULC", "LLC"],
            "general",
            [BASIC_USER],
            False,
        ),
        (
            "user_active",
            LegalEntity.State.ACTIVE,
            "consentContinuationOut",
            None,
            ["BC", "BEN", "ULC", "CC"],
            "general",
            [BASIC_USER],
            True,
        ),
        # historical business
        (
            "staff_historical",
            LegalEntity.State.HISTORICAL,
            "alteration",
            None,
            ["SP", "GP", "CP", "BC", "BEN", "CC", "ULC"],
            "staff",
            [STAFF_ROLE],
            False,
        ),
        (
            "staff_historical",
            LegalEntity.State.HISTORICAL,
            "annualReport",
            None,
            ["CP", "BC", "BEN", "CC", "ULC", "LLC"],
            "staff",
            [STAFF_ROLE],
            False,
        ),
        (
            "staff_historical",
            LegalEntity.State.HISTORICAL,
            "changeOfAddress",
            None,
            ["CP", "BC", "BEN", "CC", "ULC", "LLC"],
            "staff",
            [STAFF_ROLE],
            False,
        ),
        (
            "staff_historical",
            LegalEntity.State.HISTORICAL,
            "changeOfDirectors",
            None,
            ["CP", "BC", "BEN", "CC", "ULC", "LLC"],
            "staff",
            [STAFF_ROLE],
            False,
        ),
        (
            "staff_historical",
            LegalEntity.State.HISTORICAL,
            "correction",
            None,
            ["CP", "BC", "BEN", "CC", "ULC", "LLC"],
            "staff",
            [STAFF_ROLE],
            False,
        ),
        (
            "staff_historical_allowed",
            LegalEntity.State.HISTORICAL,
            "courtOrder",
            None,
            ["SP", "GP", "CP", "BC", "BEN", "CC", "ULC"],
            "staff",
            [STAFF_ROLE],
            True,
        ),
        (
            "staff_historical",
            LegalEntity.State.HISTORICAL,
            "dissolution",
            None,
            ["CP", "BC", "BEN", "CC", "ULC", "LLC", "SP", "GP"],
            "staff",
            [STAFF_ROLE],
            False,
        ),
        (
            "staff_historical",
            LegalEntity.State.HISTORICAL,
            "incorporationApplication",
            None,
            ["CP", "BC", "BEN", "CC", "ULC", "LLC"],
            "staff",
            [STAFF_ROLE],
            False,
        ),
        (
            "staff_historical_alloweds",
            LegalEntity.State.HISTORICAL,
            "restoration",
            "fullRestoration",
            ["BC", "BEN", "CC", "ULC"],
            "staff",
            [STAFF_ROLE],
            True,
        ),
        (
            "staff_historical_allowed",
            LegalEntity.State.HISTORICAL,
            "restoration",
            "limitedRestoration",
            ["BC", "BEN", "CC", "ULC"],
            "staff",
            [STAFF_ROLE],
            True,
        ),
        (
            "staff_historical",
            LegalEntity.State.HISTORICAL,
            "restoration",
            "fullRestoration",
            ["CP"],
            "staff",
            [STAFF_ROLE],
            False,
        ),
        (
            "staff_historical",
            LegalEntity.State.HISTORICAL,
            "restoration",
            "limitedRestoration",
            ["CP"],
            "staff",
            [STAFF_ROLE],
            False,
        ),
        (
            "staff_historical",
            LegalEntity.State.HISTORICAL,
            "specialResolution",
            None,
            ["CP", "BC", "BEN", "CC", "ULC", "LLC"],
            "staff",
            [STAFF_ROLE],
            False,
        ),
        (
            "staff_historical",
            LegalEntity.State.HISTORICAL,
            "transition",
            None,
            ["CP", "BC", "BEN", "CC", "ULC", "LLC"],
            "staff",
            [STAFF_ROLE],
            False,
        ),
        (
            "staff_historical_allowed",
            LegalEntity.State.HISTORICAL,
            "registrarsNotation",
            None,
            ["SP", "GP", "CP", "BC", "BEN", "CC", "ULC"],
            "staff",
            [STAFF_ROLE],
            True,
        ),
        (
            "staff_historical_allowed",
            LegalEntity.State.HISTORICAL,
            "registrarsOrder",
            None,
            ["SP", "GP", "CP", "BC", "BEN", "CC", "ULC"],
            "staff",
            [STAFF_ROLE],
            True,
        ),
        (
            "staff_historical",
            LegalEntity.State.HISTORICAL,
            "registration",
            None,
            ["SP", "GP"],
            "staff",
            [STAFF_ROLE],
            False,
        ),
        (
            "staff_historical",
            LegalEntity.State.HISTORICAL,
            "changeOfRegistration",
            None,
            ["SP", "GP"],
            "staff",
            [STAFF_ROLE],
            False,
        ),
        (
            "staff_historical",
            LegalEntity.State.HISTORICAL,
            "consentContinuationOut",
            None,
            ["BC", "BEN", "ULC", "CC"],
            "staff",
            [STAFF_ROLE],
            False,
        ),
        (
            "user_historical",
            LegalEntity.State.HISTORICAL,
            "alteration",
            None,
            ["CP", "BC", "BEN", "CC", "ULC", "LLC"],
            "general",
            [BASIC_USER],
            False,
        ),
        (
            "user_historical",
            LegalEntity.State.HISTORICAL,
            "annualReport",
            None,
            ["CP", "BC", "BEN", "CC", "ULC", "LLC"],
            "general",
            [BASIC_USER],
            False,
        ),
        (
            "user_historical",
            LegalEntity.State.HISTORICAL,
            "changeOfAddress",
            None,
            ["CP", "BC", "BEN", "CC", "ULC", "LLC"],
            "general",
            [BASIC_USER],
            False,
        ),
        (
            "user_historical",
            LegalEntity.State.HISTORICAL,
            "changeOfDirectors",
            None,
            ["CP", "BC", "BEN", "CC", "ULC", "LLC"],
            "general",
            [BASIC_USER],
            False,
        ),
        (
            "user_historical",
            LegalEntity.State.HISTORICAL,
            "correction",
            None,
            ["CP", "BC", "BEN", "CC", "ULC", "LLC"],
            "general",
            [BASIC_USER],
            False,
        ),
        (
            "user_historical",
            LegalEntity.State.HISTORICAL,
            "courtOrder",
            None,
            ["CP", "BC", "BEN", "CC", "ULC", "LLC"],
            "general",
            [BASIC_USER],
            False,
        ),
        (
            "user_historical",
            LegalEntity.State.HISTORICAL,
            "dissolution",
            None,
            ["CP", "BC", "BEN", "CC", "ULC", "LLC", "SP", "GP", "SP", "GP"],
            "general",
            [BASIC_USER],
            False,
        ),
        (
            "user_historical",
            LegalEntity.State.HISTORICAL,
            "incorporationApplication",
            None,
            ["CP", "BC", "BEN", "CC", "ULC", "LLC"],
            "general",
            [BASIC_USER],
            False,
        ),
        (
            "user_historical",
            LegalEntity.State.HISTORICAL,
            "restoration",
            "fullRestoration",
            ["BC", "BEN", "CC", "ULC"],
            "general",
            [BASIC_USER],
            False,
        ),
        (
            "user_historical",
            LegalEntity.State.HISTORICAL,
            "restoration",
            "limitedRestoration",
            ["BC", "BEN", "CC", "ULC"],
            "general",
            [BASIC_USER],
            False,
        ),
        (
            "user_historical",
            LegalEntity.State.HISTORICAL,
            "specialResolution",
            None,
            ["CP", "BC", "BEN", "CC", "ULC", "LLC"],
            "general",
            [BASIC_USER],
            False,
        ),
        (
            "user_historical",
            LegalEntity.State.HISTORICAL,
            "transition",
            None,
            ["CP", "BC", "BEN", "CC", "ULC", "LLC"],
            "general",
            [BASIC_USER],
            False,
        ),
        (
            "user_historical",
            LegalEntity.State.HISTORICAL,
            "registrarsNotation",
            None,
            ["CP", "BC", "BEN", "CC", "ULC", "LLC"],
            "general",
            [BASIC_USER],
            False,
        ),
        (
            "user_historical",
            LegalEntity.State.HISTORICAL,
            "registrarsOrder",
            None,
            ["CP", "BC", "BEN", "CC", "ULC", "LLC"],
            "general",
            [BASIC_USER],
            False,
        ),
        (
            "user_historical",
            LegalEntity.State.HISTORICAL,
            "registration",
            None,
            ["SP", "GP"],
            "general",
            [BASIC_USER],
            False,
        ),
        (
            "user_historical",
            LegalEntity.State.HISTORICAL,
            "changeOfRegistration",
            None,
            ["SP", "GP"],
            "general",
            [BASIC_USER],
            False,
        ),
        (
            "user_historical",
            LegalEntity.State.HISTORICAL,
            "consentContinuationOut",
            None,
            ["BC", "BEN", "ULC", "CC"],
            "general",
            [BASIC_USER],
            False,
        ),
    ],
)
def test_is_allowed(
    monkeypatch,
    app,
    session,
    jwt,
    test_name,
    state,
    filing_type,
    sub_filing_type,
    legal_types,
    username,
    roles,
    expected,
):
    """Assert that get allowed returns valid filings."""
    token = helper_create_jwt(jwt, roles=roles, username=username)
    headers = {"Authorization": "Bearer " + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers[one]

    with app.test_request_context():
        monkeypatch.setattr("flask.request.headers.get", mock_auth)
        for legal_type in legal_types:
            business = create_business(legal_type, state)
            filing_types = is_allowed(business, state, filing_type, legal_type, jwt, sub_filing_type, None)
            assert filing_types == expected


@pytest.mark.parametrize(
    "test_name,business_exists,state,legal_types,username,roles,expected",
    [
        # active business - staff user
        (
            "staff_active_cp",
            True,
            LegalEntity.State.ACTIVE,
            ["CP"],
            "staff",
            [STAFF_ROLE],
            expected_lookup(
                [
                    FilingKey.ADMN_FRZE,
                    FilingKey.AR_CP,
                    FilingKey.COA_CP,
                    FilingKey.COD_CP,
                    FilingKey.CORRCTN,
                    FilingKey.COURT_ORDER,
                    FilingKey.VOL_DISS,
                    FilingKey.ADM_DISS,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                    FilingKey.SPECIAL_RESOLUTION,
                ]
            ),
        ),
        (
            "staff_active_corps",
            True,
            LegalEntity.State.ACTIVE,
            ["BC", "BEN", "CC", "ULC"],
            "staff",
            [STAFF_ROLE],
            expected_lookup(
                [
                    FilingKey.ADMN_FRZE,
                    FilingKey.AGM_EXTENSION,
                    FilingKey.AGM_LOCATION_CHANGE,
                    FilingKey.ALTERATION,
                    FilingKey.AMALGAMATION_REGULAR,
                    FilingKey.AMALGAMATION_VERTICAL,
                    FilingKey.AMALGAMATION_HORIZONTAL,
                    FilingKey.AR_CORPS,
                    FilingKey.COA_CORPS,
                    FilingKey.COD_CORPS,
                    FilingKey.CONSENT_CONTINUATION_OUT,
                    FilingKey.CORRCTN,
                    FilingKey.COURT_ORDER,
                    FilingKey.VOL_DISS,
                    FilingKey.ADM_DISS,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                    FilingKey.TRANSITION,
                ]
            ),
        ),
        ("staff_active_llc", True, LegalEntity.State.ACTIVE, ["LLC"], "staff", [STAFF_ROLE], []),
        (
            "staff_active_firms",
            True,
            LegalEntity.State.ACTIVE,
            ["SP", "GP"],
            "staff",
            [STAFF_ROLE],
            expected_lookup(
                [
                    FilingKey.ADMN_FRZE,
                    FilingKey.CHANGE_OF_REGISTRATION,
                    FilingKey.CONV_FIRMS,
                    FilingKey.CORRCTN_FIRMS,
                    FilingKey.COURT_ORDER,
                    FilingKey.VOL_DISS_FIRMS,
                    FilingKey.ADM_DISS_FIRMS,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                ]
            ),
        ),
        # active business - general user
        (
            "general_user_cp",
            True,
            LegalEntity.State.ACTIVE,
            ["CP"],
            "general",
            [BASIC_USER],
            expected_lookup(
                [FilingKey.AR_CP, FilingKey.COA_CP, FilingKey.COD_CP, FilingKey.VOL_DISS, FilingKey.SPECIAL_RESOLUTION]
            ),
        ),
        (
            "general_user_corps",
            True,
            LegalEntity.State.ACTIVE,
            ["BC", "BEN", "CC", "ULC"],
            "general",
            [BASIC_USER],
            expected_lookup(
                [
                    FilingKey.AGM_EXTENSION,
                    FilingKey.AGM_LOCATION_CHANGE,
                    FilingKey.ALTERATION,
                    FilingKey.AMALGAMATION_REGULAR,
                    FilingKey.AMALGAMATION_VERTICAL,
                    FilingKey.AMALGAMATION_HORIZONTAL,
                    FilingKey.AR_CORPS,
                    FilingKey.COA_CORPS,
                    FilingKey.COD_CORPS,
                    FilingKey.CONSENT_CONTINUATION_OUT,
                    FilingKey.VOL_DISS,
                    FilingKey.TRANSITION,
                ]
            ),
        ),
        ("general_user_llc", True, LegalEntity.State.ACTIVE, ["LLC"], "general", [BASIC_USER], []),
        (
            "general_user_firms",
            True,
            LegalEntity.State.ACTIVE,
            ["SP", "GP"],
            "general",
            [BASIC_USER],
            expected_lookup([FilingKey.CHANGE_OF_REGISTRATION, FilingKey.VOL_DISS_FIRMS]),
        ),
        # historical business - staff user
        (
            "staff_historical_cp",
            True,
            LegalEntity.State.HISTORICAL,
            ["CP"],
            "staff",
            [STAFF_ROLE],
            expected_lookup(
                [
                    FilingKey.COURT_ORDER,
                    FilingKey.PUT_BACK_ON,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                ]
            ),
        ),
        (
            "staff_historical_corps",
            True,
            LegalEntity.State.HISTORICAL,
            ["BC", "BEN", "CC", "ULC"],
            "staff",
            [STAFF_ROLE],
            expected_lookup(
                [
                    FilingKey.COURT_ORDER,
                    FilingKey.PUT_BACK_ON,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                    FilingKey.RESTRN_FULL_CORPS,
                    FilingKey.RESTRN_LTD_CORPS,
                ]
            ),
        ),
        ("staff_historical_llc", True, LegalEntity.State.HISTORICAL, ["LLC"], "staff", [STAFF_ROLE], []),
        (
            "staff_historical_firms",
            True,
            LegalEntity.State.HISTORICAL,
            ["SP", "GP"],
            "staff",
            [STAFF_ROLE],
            expected_lookup(
                [
                    FilingKey.COURT_ORDER,
                    FilingKey.PUT_BACK_ON,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                ]
            ),
        ),
        # historical business - general user
        ("general_user_historical_cp", True, LegalEntity.State.HISTORICAL, ["CP"], "general", [BASIC_USER], []),
        (
            "general_user_historical_corps",
            True,
            LegalEntity.State.HISTORICAL,
            ["BC", "BEN", "CC", "ULC"],
            "general",
            [BASIC_USER],
            [],
        ),
        ("general_user_historical_llc", True, LegalEntity.State.HISTORICAL, ["LLC"], "general", [BASIC_USER], []),
        (
            "general_user_historical_firms",
            True,
            LegalEntity.State.HISTORICAL,
            ["SP", "GP"],
            "general",
            [BASIC_USER],
            [],
        ),
    ],
)
def test_get_allowed_actions(
    monkeypatch, app, session, jwt, test_name, business_exists, state, legal_types, username, roles, expected
):
    """Assert that get_allowed_actions returns the expected allowable filing info."""
    token = helper_create_jwt(jwt, roles=roles, username=username)
    headers = {"Authorization": "Bearer " + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers[one]

    with app.test_request_context():
        monkeypatch.setattr("flask.request.headers.get", mock_auth)

        for legal_type in legal_types:
            legal_entity = None
            if business_exists:
                legal_entity = create_business(legal_type, state)
            result = get_allowable_actions(jwt, legal_entity)
            assert result
            assert result["filing"]["filingSubmissionLink"]
            assert result["filing"]["filingTypes"] == expected


@pytest.mark.parametrize(
    "test_name,business_exists,state,legal_types,username,roles,expected",
    [
        # no business - staff user
        (
            "staff_no_business_cp",
            False,
            LegalEntity.State.ACTIVE,
            ["CP"],
            "staff",
            [STAFF_ROLE],
            expected_lookup([FilingKey.IA_CP]),
        ),
        (
            "staff_no_business_bc",
            False,
            LegalEntity.State.ACTIVE,
            ["BC"],
            "staff",
            [STAFF_ROLE],
            expected_lookup(
                [
                    FilingKey.AMALGAMATION_REGULAR,
                    FilingKey.AMALGAMATION_VERTICAL,
                    FilingKey.AMALGAMATION_HORIZONTAL,
                    FilingKey.IA_BC,
                ]
            ),
        ),
        (
            "staff_no_business_ben",
            False,
            LegalEntity.State.ACTIVE,
            ["BEN"],
            "staff",
            [STAFF_ROLE],
            expected_lookup(
                [
                    FilingKey.AMALGAMATION_REGULAR,
                    FilingKey.AMALGAMATION_VERTICAL,
                    FilingKey.AMALGAMATION_HORIZONTAL,
                    FilingKey.IA_BEN,
                ]
            ),
        ),
        (
            "staff_no_business_cc",
            False,
            LegalEntity.State.ACTIVE,
            ["CC"],
            "staff",
            [STAFF_ROLE],
            expected_lookup(
                [
                    FilingKey.AMALGAMATION_REGULAR,
                    FilingKey.AMALGAMATION_VERTICAL,
                    FilingKey.AMALGAMATION_HORIZONTAL,
                    FilingKey.IA_CC,
                ]
            ),
        ),
        (
            "staff_no_business_ulc",
            False,
            LegalEntity.State.ACTIVE,
            ["ULC"],
            "staff",
            [STAFF_ROLE],
            expected_lookup(
                [
                    FilingKey.AMALGAMATION_REGULAR,
                    FilingKey.AMALGAMATION_VERTICAL,
                    FilingKey.AMALGAMATION_HORIZONTAL,
                    FilingKey.IA_ULC,
                ]
            ),
        ),
        ("staff_no_business_llc", False, LegalEntity.State.ACTIVE, ["LLC"], "staff", [STAFF_ROLE], []),
        (
            "staff_no_business_sp",
            False,
            LegalEntity.State.ACTIVE,
            ["SP"],
            "staff",
            [STAFF_ROLE],
            expected_lookup([FilingKey.REG_SP]),
        ),
        (
            "staff_no_business_gp",
            False,
            LegalEntity.State.ACTIVE,
            ["GP"],
            "staff",
            [STAFF_ROLE],
            expected_lookup([FilingKey.REG_GP]),
        ),
        # no business - general user
        (
            "general_user_no_business_cp",
            False,
            LegalEntity.State.ACTIVE,
            ["CP"],
            "general",
            [BASIC_USER],
            expected_lookup([FilingKey.IA_CP]),
        ),
        (
            "general_user_no_business_bc",
            False,
            LegalEntity.State.ACTIVE,
            ["BC"],
            "general",
            [BASIC_USER],
            expected_lookup(
                [
                    FilingKey.AMALGAMATION_REGULAR,
                    FilingKey.AMALGAMATION_VERTICAL,
                    FilingKey.AMALGAMATION_HORIZONTAL,
                    FilingKey.IA_BC,
                ]
            ),
        ),
        (
            "general_user_no_business_ben",
            False,
            LegalEntity.State.ACTIVE,
            ["BEN"],
            "general",
            [BASIC_USER],
            expected_lookup(
                [
                    FilingKey.AMALGAMATION_REGULAR,
                    FilingKey.AMALGAMATION_VERTICAL,
                    FilingKey.AMALGAMATION_HORIZONTAL,
                    FilingKey.IA_BEN,
                ]
            ),
        ),
        (
            "general_user_no_business_cc",
            False,
            LegalEntity.State.ACTIVE,
            ["CC"],
            "general",
            [BASIC_USER],
            expected_lookup(
                [
                    FilingKey.AMALGAMATION_REGULAR,
                    FilingKey.AMALGAMATION_VERTICAL,
                    FilingKey.AMALGAMATION_HORIZONTAL,
                    FilingKey.IA_CC,
                ]
            ),
        ),
        (
            "general_user_no_business_ulc",
            False,
            LegalEntity.State.ACTIVE,
            ["ULC"],
            "general",
            [BASIC_USER],
            expected_lookup(
                [
                    FilingKey.AMALGAMATION_REGULAR,
                    FilingKey.AMALGAMATION_VERTICAL,
                    FilingKey.AMALGAMATION_HORIZONTAL,
                    FilingKey.IA_ULC,
                ]
            ),
        ),
        ("general_user_no_business_llc", False, LegalEntity.State.ACTIVE, ["LLC"], "general", [BASIC_USER], []),
        (
            "general_user_no_business_sp",
            False,
            LegalEntity.State.ACTIVE,
            ["SP"],
            "general",
            [BASIC_USER],
            expected_lookup([FilingKey.REG_SP]),
        ),
        (
            "general_user_no_business_gp",
            False,
            LegalEntity.State.ACTIVE,
            ["GP"],
            "general",
            [BASIC_USER],
            expected_lookup([FilingKey.REG_GP]),
        ),
        # active business - staff user
        (
            "staff_active_cp",
            True,
            LegalEntity.State.ACTIVE,
            ["CP"],
            "staff",
            [STAFF_ROLE],
            expected_lookup(
                [
                    FilingKey.ADMN_FRZE,
                    FilingKey.AR_CP,
                    FilingKey.COA_CP,
                    FilingKey.COD_CP,
                    FilingKey.CORRCTN,
                    FilingKey.COURT_ORDER,
                    FilingKey.VOL_DISS,
                    FilingKey.ADM_DISS,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                    FilingKey.SPECIAL_RESOLUTION,
                ]
            ),
        ),
        (
            "staff_active_corps",
            True,
            LegalEntity.State.ACTIVE,
            ["BC", "BEN", "CC", "ULC"],
            "staff",
            [STAFF_ROLE],
            expected_lookup(
                [
                    FilingKey.ADMN_FRZE,
                    FilingKey.AGM_EXTENSION,
                    FilingKey.AGM_LOCATION_CHANGE,
                    FilingKey.ALTERATION,
                    FilingKey.AMALGAMATION_REGULAR,
                    FilingKey.AMALGAMATION_VERTICAL,
                    FilingKey.AMALGAMATION_HORIZONTAL,
                    FilingKey.AR_CORPS,
                    FilingKey.COA_CORPS,
                    FilingKey.COD_CORPS,
                    FilingKey.CONSENT_CONTINUATION_OUT,
                    FilingKey.CORRCTN,
                    FilingKey.COURT_ORDER,
                    FilingKey.VOL_DISS,
                    FilingKey.ADM_DISS,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                    FilingKey.TRANSITION,
                ]
            ),
        ),
        ("staff_active_llc", True, LegalEntity.State.ACTIVE, ["LLC"], "staff", [STAFF_ROLE], []),
        (
            "staff_active_firms",
            True,
            LegalEntity.State.ACTIVE,
            ["SP", "GP"],
            "staff",
            [STAFF_ROLE],
            expected_lookup(
                [
                    FilingKey.ADMN_FRZE,
                    FilingKey.CHANGE_OF_REGISTRATION,
                    FilingKey.CONV_FIRMS,
                    FilingKey.CORRCTN_FIRMS,
                    FilingKey.COURT_ORDER,
                    FilingKey.VOL_DISS_FIRMS,
                    FilingKey.ADM_DISS_FIRMS,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                ]
            ),
        ),
        # active business - general user
        (
            "general_user_cp",
            True,
            LegalEntity.State.ACTIVE,
            ["CP"],
            "general",
            [BASIC_USER],
            expected_lookup(
                [FilingKey.AR_CP, FilingKey.COA_CP, FilingKey.COD_CP, FilingKey.VOL_DISS, FilingKey.SPECIAL_RESOLUTION]
            ),
        ),
        (
            "general_user_corps",
            True,
            LegalEntity.State.ACTIVE,
            ["BC", "BEN", "CC", "ULC"],
            "general",
            [BASIC_USER],
            expected_lookup(
                [
                    FilingKey.AGM_EXTENSION,
                    FilingKey.AGM_LOCATION_CHANGE,
                    FilingKey.ALTERATION,
                    FilingKey.AMALGAMATION_REGULAR,
                    FilingKey.AMALGAMATION_VERTICAL,
                    FilingKey.AMALGAMATION_HORIZONTAL,
                    FilingKey.AR_CORPS,
                    FilingKey.COA_CORPS,
                    FilingKey.COD_CORPS,
                    FilingKey.CONSENT_CONTINUATION_OUT,
                    FilingKey.VOL_DISS,
                    FilingKey.TRANSITION,
                ]
            ),
        ),
        ("general_user_llc", True, LegalEntity.State.ACTIVE, ["LLC"], "general", [BASIC_USER], []),
        (
            "general_user_firms",
            True,
            LegalEntity.State.ACTIVE,
            ["SP", "GP"],
            "general",
            [BASIC_USER],
            expected_lookup([FilingKey.CHANGE_OF_REGISTRATION, FilingKey.VOL_DISS_FIRMS]),
        ),
        # historical business - staff user
        (
            "staff_historical_cp",
            True,
            LegalEntity.State.HISTORICAL,
            ["CP"],
            "staff",
            [STAFF_ROLE],
            expected_lookup(
                [
                    FilingKey.COURT_ORDER,
                    FilingKey.PUT_BACK_ON,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                ]
            ),
        ),
        (
            "staff_historical_corps",
            True,
            LegalEntity.State.HISTORICAL,
            ["BC", "BEN", "CC", "ULC"],
            "staff",
            [STAFF_ROLE],
            expected_lookup(
                [
                    FilingKey.COURT_ORDER,
                    FilingKey.PUT_BACK_ON,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                    FilingKey.RESTRN_FULL_CORPS,
                    FilingKey.RESTRN_LTD_CORPS,
                ]
            ),
        ),
        ("staff_historical_llc", True, LegalEntity.State.HISTORICAL, ["LLC"], "staff", [STAFF_ROLE], []),
        (
            "staff_historical_firms",
            True,
            LegalEntity.State.HISTORICAL,
            ["SP", "GP"],
            "staff",
            [STAFF_ROLE],
            expected_lookup(
                [
                    FilingKey.COURT_ORDER,
                    FilingKey.PUT_BACK_ON,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                ]
            ),
        ),
        # historical business - general user
        ("general_user_historical_cp", True, LegalEntity.State.HISTORICAL, ["CP"], "general", [BASIC_USER], []),
        (
            "general_user_historical_corps",
            True,
            LegalEntity.State.HISTORICAL,
            ["BC", "BEN", "CC", "ULC"],
            "general",
            [BASIC_USER],
            [],
        ),
        ("general_user_historical_llc", True, LegalEntity.State.HISTORICAL, ["LLC"], "general", [BASIC_USER], []),
        (
            "general_user_historical_firms",
            True,
            LegalEntity.State.HISTORICAL,
            ["SP", "GP"],
            "general",
            [BASIC_USER],
            [],
        ),
    ],
)
def test_get_allowed_filings(
    monkeypatch, app, session, jwt, test_name, business_exists, state, legal_types, username, roles, expected
):
    """Assert that get allowed returns valid filings."""
    token = helper_create_jwt(jwt, roles=roles, username=username)
    headers = {"Authorization": "Bearer " + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers[one]

    with app.test_request_context():
        monkeypatch.setattr("flask.request.headers.get", mock_auth)

        for legal_type in legal_types:
            legal_entity = None
            if business_exists:
                legal_entity = create_business(legal_type, state)
            filing_types = get_allowed_filings(legal_entity, state, legal_type, jwt)
            assert filing_types == expected


@pytest.mark.parametrize(
    "test_name,business_exists,state,legal_types,username,roles,expected",
    [
        # active business - staff user
        (
            "staff_active_cp",
            True,
            LegalEntity.State.ACTIVE,
            ["CP"],
            "staff",
            [STAFF_ROLE],
            expected_lookup(
                [
                    FilingKey.ADMN_FRZE,
                    FilingKey.COURT_ORDER,
                    FilingKey.ADM_DISS,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                ]
            ),
        ),
        (
            "staff_active_corps",
            True,
            LegalEntity.State.ACTIVE,
            ["BC", "BEN", "CC", "ULC"],
            "staff",
            [STAFF_ROLE],
            expected_lookup(
                [
                    FilingKey.ADMN_FRZE,
                    FilingKey.COURT_ORDER,
                    FilingKey.ADM_DISS,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                    FilingKey.TRANSITION,
                ]
            ),
        ),
        ("staff_active_llc", True, LegalEntity.State.ACTIVE, ["LLC"], "staff", [STAFF_ROLE], []),
        (
            "staff_active_firms",
            True,
            LegalEntity.State.ACTIVE,
            ["SP", "GP"],
            "staff",
            [STAFF_ROLE],
            expected_lookup(
                [
                    FilingKey.ADMN_FRZE,
                    FilingKey.CONV_FIRMS,
                    FilingKey.COURT_ORDER,
                    FilingKey.ADM_DISS_FIRMS,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                ]
            ),
        ),
        # active business - general user
        ("general_user_cp", True, LegalEntity.State.ACTIVE, ["CP"], "general", [BASIC_USER], []),
        (
            "general_user_corps",
            True,
            LegalEntity.State.ACTIVE,
            ["BC", "BEN", "CC", "ULC"],
            "general",
            [BASIC_USER],
            expected_lookup([FilingKey.TRANSITION]),
        ),
        ("general_user_llc", True, LegalEntity.State.ACTIVE, ["LLC"], "general", [BASIC_USER], []),
        ("general_user_firms", True, LegalEntity.State.ACTIVE, ["SP", "GP"], "general", [BASIC_USER], []),
        # historical business - staff user
        (
            "staff_historical_cp",
            True,
            LegalEntity.State.HISTORICAL,
            ["CP"],
            "staff",
            [STAFF_ROLE],
            expected_lookup(
                [
                    FilingKey.COURT_ORDER,
                    FilingKey.PUT_BACK_ON,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                ]
            ),
        ),
        (
            "staff_historical_corps",
            True,
            LegalEntity.State.HISTORICAL,
            ["BC", "BEN", "CC", "ULC"],
            "staff",
            [STAFF_ROLE],
            expected_lookup(
                [
                    FilingKey.COURT_ORDER,
                    FilingKey.PUT_BACK_ON,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                    FilingKey.RESTRN_FULL_CORPS,
                    FilingKey.RESTRN_LTD_CORPS,
                ]
            ),
        ),
        ("staff_historical_llc", True, LegalEntity.State.HISTORICAL, ["LLC"], "staff", [STAFF_ROLE], []),
        (
            "staff_historical_firms",
            True,
            LegalEntity.State.HISTORICAL,
            ["SP", "GP"],
            "staff",
            [STAFF_ROLE],
            expected_lookup(
                [
                    FilingKey.COURT_ORDER,
                    FilingKey.PUT_BACK_ON,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                ]
            ),
        ),
        # historical business - general user
        ("general_user_historical_cp", True, LegalEntity.State.HISTORICAL, ["CP"], "general", [BASIC_USER], []),
        (
            "general_user_historical_corps",
            True,
            LegalEntity.State.HISTORICAL,
            ["BC", "BEN", "CC", "ULC"],
            "general",
            [BASIC_USER],
            [],
        ),
        ("general_user_historical_llc", True, LegalEntity.State.HISTORICAL, ["LLC"], "general", [BASIC_USER], []),
        (
            "general_user_historical_firms",
            True,
            LegalEntity.State.HISTORICAL,
            ["SP", "GP"],
            "general",
            [BASIC_USER],
            [],
        ),
    ],
)
def test_get_allowed_filings_blocker_admin_freeze(
    monkeypatch, app, session, jwt, test_name, business_exists, state, legal_types, username, roles, expected
):
    """Assert that get allowed returns valid filings when business is frozen."""
    token = helper_create_jwt(jwt, roles=roles, username=username)
    headers = {"Authorization": "Bearer " + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers[one]

    with app.test_request_context():
        monkeypatch.setattr("flask.request.headers.get", mock_auth)

        for legal_type in legal_types:
            legal_entity = None
            if business_exists:
                identifier = (f"BC{random.SystemRandom().getrandbits(0x58)}")[:9]
                legal_entity = factory_legal_entity(
                    identifier=identifier, entity_type=legal_type, state=state, admin_freeze=True
                )
            filing_types = get_allowed_filings(legal_entity, state, legal_type, jwt)
            assert filing_types == expected


@pytest.mark.parametrize(
    "test_name,business_exists,state,legal_types,username,roles,expected",
    [
        # historical business - staff user
        (
            "staff_historical_cp",
            True,
            LegalEntity.State.HISTORICAL,
            ["CP"],
            "staff",
            [STAFF_ROLE],
            expected_lookup(
                [
                    FilingKey.COURT_ORDER,
                    FilingKey.PUT_BACK_ON,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                ]
            ),
        ),
        (
            "staff_historical_corps",
            True,
            LegalEntity.State.HISTORICAL,
            ["BC", "BEN", "CC", "ULC"],
            "staff",
            [STAFF_ROLE],
            expected_lookup(
                [
                    FilingKey.COURT_ORDER,
                    FilingKey.PUT_BACK_ON,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                ]
            ),
        ),
        ("staff_historical_llc", True, LegalEntity.State.HISTORICAL, ["LLC"], "staff", [STAFF_ROLE], []),
        (
            "staff_historical_firms",
            True,
            LegalEntity.State.HISTORICAL,
            ["SP", "GP"],
            "staff",
            [STAFF_ROLE],
            expected_lookup(
                [
                    FilingKey.COURT_ORDER,
                    FilingKey.PUT_BACK_ON,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                ]
            ),
        ),
        # historical business - general user
        ("general_user_historical_cp", True, LegalEntity.State.HISTORICAL, ["CP"], "general", [BASIC_USER], []),
        (
            "general_user_historical_corps",
            True,
            LegalEntity.State.HISTORICAL,
            ["BC", "BEN", "CC", "ULC"],
            "general",
            [BASIC_USER],
            [],
        ),
        ("general_user_historical_llc", True, LegalEntity.State.HISTORICAL, ["LLC"], "general", [BASIC_USER], []),
        (
            "general_user_historical_firms",
            True,
            LegalEntity.State.HISTORICAL,
            ["SP", "GP"],
            "general",
            [BASIC_USER],
            [],
        ),
    ],
)
def test_get_allowed_filings_blocker_for_amalgamating_business(
    monkeypatch, app, session, jwt, test_name, business_exists, state, legal_types, username, roles, expected
):
    """Assert that get allowed returns valid filings when business is not in good standing."""
    token = helper_create_jwt(jwt, roles=roles, username=username)
    headers = {"Authorization": "Bearer " + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers[one]

    with app.test_request_context():
        monkeypatch.setattr("flask.request.headers.get", mock_auth)

        for legal_type in legal_types:
            business = None
            identifier = (f"BC{random.SystemRandom().getrandbits(0x58)}")[:9]
            business = factory_legal_entity(identifier=identifier, entity_type=legal_type, state=state)

            with patch.object(type(business), "amalgamating_businesses", new_callable=PropertyMock):
                filing_types = get_allowed_filings(business, state, legal_type, jwt)
                assert filing_types == expected


@pytest.mark.parametrize(
    "test_name,business_exists,state,legal_types,username,roles,expected",
    [
        # active business - staff user
        (
            "staff_active_cp",
            True,
            LegalEntity.State.ACTIVE,
            ["CP"],
            "staff",
            [STAFF_ROLE],
            expected_lookup(
                [
                    FilingKey.ADMN_FRZE,
                    FilingKey.AR_CP,
                    FilingKey.COA_CP,
                    FilingKey.COD_CP,
                    FilingKey.CORRCTN,
                    FilingKey.COURT_ORDER,
                    FilingKey.ADM_DISS,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                    FilingKey.SPECIAL_RESOLUTION,
                ]
            ),
        ),
        (
            "staff_active_corps",
            True,
            LegalEntity.State.ACTIVE,
            ["BC", "BEN", "CC", "ULC"],
            "staff",
            [STAFF_ROLE],
            expected_lookup(
                [
                    FilingKey.ADMN_FRZE,
                    FilingKey.ALTERATION,
                    FilingKey.AR_CORPS,
                    FilingKey.COA_CORPS,
                    FilingKey.COD_CORPS,
                    FilingKey.CORRCTN,
                    FilingKey.COURT_ORDER,
                    FilingKey.ADM_DISS,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                    FilingKey.TRANSITION,
                ]
            ),
        ),
        ("staff_active_llc", True, LegalEntity.State.ACTIVE, ["LLC"], "staff", [STAFF_ROLE], []),
        (
            "staff_active_firms",
            True,
            LegalEntity.State.ACTIVE,
            ["SP", "GP"],
            "staff",
            [STAFF_ROLE],
            expected_lookup(
                [
                    FilingKey.ADMN_FRZE,
                    FilingKey.CHANGE_OF_REGISTRATION,
                    FilingKey.CONV_FIRMS,
                    FilingKey.CORRCTN_FIRMS,
                    FilingKey.COURT_ORDER,
                    FilingKey.ADM_DISS_FIRMS,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                ]
            ),
        ),
        # active business - general user
        (
            "general_user_cp",
            True,
            LegalEntity.State.ACTIVE,
            ["CP"],
            "general",
            [BASIC_USER],
            expected_lookup([FilingKey.AR_CP, FilingKey.COA_CP, FilingKey.COD_CP, FilingKey.SPECIAL_RESOLUTION]),
        ),
        (
            "general_user_corps",
            True,
            LegalEntity.State.ACTIVE,
            ["BC", "BEN", "CC", "ULC"],
            "general",
            [BASIC_USER],
            expected_lookup(
                [
                    FilingKey.ALTERATION,
                    FilingKey.AR_CORPS,
                    FilingKey.COA_CORPS,
                    FilingKey.COD_CORPS,
                    FilingKey.TRANSITION,
                ]
            ),
        ),
        ("general_user_llc", True, LegalEntity.State.ACTIVE, ["LLC"], "general", [BASIC_USER], []),
        (
            "general_user_firms",
            True,
            LegalEntity.State.ACTIVE,
            ["SP", "GP"],
            "general",
            [BASIC_USER],
            expected_lookup([FilingKey.CHANGE_OF_REGISTRATION]),
        ),
        # historical business - staff user
        (
            "staff_historical_cp",
            True,
            LegalEntity.State.HISTORICAL,
            ["CP"],
            "staff",
            [STAFF_ROLE],
            expected_lookup(
                [
                    FilingKey.COURT_ORDER,
                    FilingKey.PUT_BACK_ON,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                ]
            ),
        ),
        (
            "staff_historical_corps",
            True,
            LegalEntity.State.HISTORICAL,
            ["BC", "BEN", "CC", "ULC"],
            "staff",
            [STAFF_ROLE],
            expected_lookup(
                [
                    FilingKey.COURT_ORDER,
                    FilingKey.PUT_BACK_ON,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                    FilingKey.RESTRN_FULL_CORPS,
                    FilingKey.RESTRN_LTD_CORPS,
                ]
            ),
        ),
        ("staff_historical_llc", True, LegalEntity.State.HISTORICAL, ["LLC"], "staff", [STAFF_ROLE], []),
        (
            "staff_historical_firms",
            True,
            LegalEntity.State.HISTORICAL,
            ["SP", "GP"],
            "staff",
            [STAFF_ROLE],
            expected_lookup(
                [
                    FilingKey.COURT_ORDER,
                    FilingKey.PUT_BACK_ON,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                ]
            ),
        ),
        # historical business - general user
        ("general_user_historical_cp", True, LegalEntity.State.HISTORICAL, ["CP"], "general", [BASIC_USER], []),
        (
            "general_user_historical_corps",
            True,
            LegalEntity.State.HISTORICAL,
            ["BC", "BEN", "CC", "ULC"],
            "general",
            [BASIC_USER],
            [],
        ),
        ("general_user_historical_llc", True, LegalEntity.State.HISTORICAL, ["LLC"], "general", [BASIC_USER], []),
        (
            "general_user_historical_firms",
            True,
            LegalEntity.State.HISTORICAL,
            ["SP", "GP"],
            "general",
            [BASIC_USER],
            [],
        ),
    ],
)
def test_get_allowed_filings_blocker_not_in_good_standing(
    monkeypatch, app, session, jwt, test_name, business_exists, state, legal_types, username, roles, expected
):
    """Assert that get allowed returns valid filings when business is not in good standing."""
    token = helper_create_jwt(jwt, roles=roles, username=username)
    headers = {"Authorization": "Bearer " + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers[one]

    with app.test_request_context():
        monkeypatch.setattr("flask.request.headers.get", mock_auth)

        for legal_type in legal_types:
            business = None
            identifier = (f"BC{random.SystemRandom().getrandbits(0x58)}")[:9]
            business = factory_legal_entity(identifier=identifier, entity_type=legal_type, state=state)
            with patch.object(type(business), "good_standing", new_callable=PropertyMock) as mock_good_standing:
                mock_good_standing.return_value = False
                filing_types = get_allowed_filings(business, state, legal_type, jwt)
                assert filing_types == expected


@pytest.mark.parametrize(
    "test_name,state,legal_types,username,roles,filing_statuses,expected",
    [
        # active business - staff user
        (
            "staff_active_cp",
            LegalEntity.State.ACTIVE,
            ["CP"],
            "staff",
            [STAFF_ROLE],
            BLOCKER_FILING_STATUSES,
            expected_lookup(
                [FilingKey.ADMN_FRZE, FilingKey.COURT_ORDER, FilingKey.REGISTRARS_NOTATION, FilingKey.REGISTRARS_ORDER]
            ),
        ),
        (
            "staff_active_corps",
            LegalEntity.State.ACTIVE,
            ["BC", "BEN", "CC", "ULC"],
            "staff",
            [STAFF_ROLE],
            BLOCKER_FILING_STATUSES,
            expected_lookup(
                [
                    FilingKey.ADMN_FRZE,
                    FilingKey.AMALGAMATION_REGULAR,
                    FilingKey.AMALGAMATION_VERTICAL,
                    FilingKey.AMALGAMATION_HORIZONTAL,
                    FilingKey.COURT_ORDER,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                    FilingKey.TRANSITION,
                ]
            ),
        ),
        ("staff_active_llc", LegalEntity.State.ACTIVE, ["LLC"], "staff", [STAFF_ROLE], BLOCKER_FILING_STATUSES, []),
        (
            "staff_active_firms",
            LegalEntity.State.ACTIVE,
            ["SP", "GP"],
            "staff",
            [STAFF_ROLE],
            BLOCKER_FILING_STATUSES,
            expected_lookup(
                [
                    FilingKey.ADMN_FRZE,
                    FilingKey.CONV_FIRMS,
                    FilingKey.COURT_ORDER,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                ]
            ),
        ),
        # active business - general user
        ("general_user_cp", LegalEntity.State.ACTIVE, ["CP"], "general", [BASIC_USER], BLOCKER_FILING_STATUSES, []),
        (
            "general_user_corps",
            LegalEntity.State.ACTIVE,
            ["BC", "BEN", "CC", "ULC"],
            "general",
            [BASIC_USER],
            BLOCKER_FILING_STATUSES,
            expected_lookup(
                [
                    FilingKey.AMALGAMATION_REGULAR,
                    FilingKey.AMALGAMATION_VERTICAL,
                    FilingKey.AMALGAMATION_HORIZONTAL,
                    FilingKey.TRANSITION,
                ]
            ),
        ),
        ("general_user_llc", LegalEntity.State.ACTIVE, ["LLC"], "general", [BASIC_USER], BLOCKER_FILING_STATUSES, []),
        (
            "general_user_firms",
            LegalEntity.State.ACTIVE,
            ["SP", "GP"],
            "general",
            [BASIC_USER],
            BLOCKER_FILING_STATUSES,
            [],
        ),
        # historical business - staff user
        (
            "staff_historical_cp",
            LegalEntity.State.HISTORICAL,
            ["CP"],
            "staff",
            [STAFF_ROLE],
            BLOCKER_FILING_STATUSES,
            expected_lookup(
                [
                    FilingKey.COURT_ORDER,
                    FilingKey.PUT_BACK_ON,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                ]
            ),
        ),
        (
            "staff_historical_corps",
            LegalEntity.State.HISTORICAL,
            ["BC", "BEN", "CC", "ULC"],
            "staff",
            [STAFF_ROLE],
            BLOCKER_FILING_STATUSES,
            expected_lookup(
                [
                    FilingKey.COURT_ORDER,
                    FilingKey.PUT_BACK_ON,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                    FilingKey.RESTRN_FULL_CORPS,
                    FilingKey.RESTRN_LTD_CORPS,
                ]
            ),
        ),
        (
            "staff_historical_llc",
            LegalEntity.State.HISTORICAL,
            ["LLC"],
            "staff",
            [STAFF_ROLE],
            BLOCKER_FILING_STATUSES,
            [],
        ),
        (
            "staff_historical_firms",
            LegalEntity.State.HISTORICAL,
            ["SP", "GP"],
            "staff",
            [STAFF_ROLE],
            BLOCKER_FILING_STATUSES,
            expected_lookup(
                [
                    FilingKey.COURT_ORDER,
                    FilingKey.PUT_BACK_ON,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                ]
            ),
        ),
        # historical business - general user
        (
            "general_user_historical_cp",
            LegalEntity.State.HISTORICAL,
            ["CP"],
            "general",
            [BASIC_USER],
            BLOCKER_FILING_STATUSES,
            [],
        ),
        (
            "general_user_historical_corps",
            LegalEntity.State.HISTORICAL,
            ["BC", "BEN", "CC", "ULC"],
            "general",
            [BASIC_USER],
            BLOCKER_FILING_STATUSES,
            [],
        ),
        (
            "general_user_historical_llc",
            LegalEntity.State.HISTORICAL,
            ["LLC"],
            "general",
            [BASIC_USER],
            BLOCKER_FILING_STATUSES,
            [],
        ),
        (
            "general_user_historical_firms",
            LegalEntity.State.HISTORICAL,
            ["SP", "GP"],
            "general",
            [BASIC_USER],
            BLOCKER_FILING_STATUSES,
            [],
        ),
    ],
)
def test_allowed_filings_blocker_filing_incomplete(
    monkeypatch, app, session, jwt, test_name, state, legal_types, username, roles, filing_statuses, expected
):
    """Assert that get allowed returns valid filings when business has blocker filings.

    A blocker filing in this instance is any filing that has a status of DRAFT, PENDING, PENDING CORRECTION,
    ERROR or PAID.
    """
    token = helper_create_jwt(jwt, roles=roles, username=username)
    headers = {"Authorization": "Bearer " + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers[one]

    with app.test_request_context():
        monkeypatch.setattr("flask.request.headers.get", mock_auth)

        for legal_type in legal_types:
            for filing_status in filing_statuses:
                legal_entity = create_business(legal_type, state)
                create_incomplete_filing(
                    legal_entity=legal_entity, filing_name="unknownFiling", filing_status=filing_status
                )
                filing_types = get_allowed_filings(legal_entity, state, legal_type, jwt)
                assert filing_types == expected


@pytest.mark.parametrize(
    "test_name,state,legal_types,username,roles,filing_types,filing_statuses,expected",
    [
        # active business - staff user
        (
            "staff_active_cp",
            LegalEntity.State.ACTIVE,
            ["CP"],
            "staff",
            [STAFF_ROLE],
            BLOCKER_FILING_TYPES,
            BLOCKER_FILING_STATUSES_AND_ADDITIONAL,
            expected_lookup(
                [FilingKey.ADMN_FRZE, FilingKey.COURT_ORDER, FilingKey.REGISTRARS_NOTATION, FilingKey.REGISTRARS_ORDER]
            ),
        ),
        (
            "staff_active_corps",
            LegalEntity.State.ACTIVE,
            ["BC", "BEN", "CC", "ULC"],
            "staff",
            [STAFF_ROLE],
            BLOCKER_FILING_TYPES,
            BLOCKER_FILING_STATUSES_AND_ADDITIONAL,
            expected_lookup(
                [
                    FilingKey.ADMN_FRZE,
                    FilingKey.AMALGAMATION_REGULAR,
                    FilingKey.AMALGAMATION_VERTICAL,
                    FilingKey.AMALGAMATION_HORIZONTAL,
                    FilingKey.COURT_ORDER,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                    FilingKey.TRANSITION,
                ]
            ),
        ),
        (
            "staff_active_llc",
            LegalEntity.State.ACTIVE,
            ["LLC"],
            "staff",
            [STAFF_ROLE],
            BLOCKER_FILING_TYPES,
            BLOCKER_FILING_STATUSES_AND_ADDITIONAL,
            [],
        ),
        (
            "staff_active_firms",
            LegalEntity.State.ACTIVE,
            ["SP", "GP"],
            "staff",
            [STAFF_ROLE],
            BLOCKER_FILING_TYPES,
            BLOCKER_FILING_STATUSES_AND_ADDITIONAL,
            expected_lookup(
                [
                    FilingKey.ADMN_FRZE,
                    FilingKey.CONV_FIRMS,
                    FilingKey.COURT_ORDER,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                ]
            ),
        ),
        # active business - general user
        (
            "general_user_cp",
            LegalEntity.State.ACTIVE,
            ["CP"],
            "general",
            [BASIC_USER],
            BLOCKER_FILING_TYPES,
            BLOCKER_FILING_STATUSES_AND_ADDITIONAL,
            [],
        ),
        (
            "general_user_corps",
            LegalEntity.State.ACTIVE,
            ["BC", "BEN", "CC", "ULC"],
            "general",
            [BASIC_USER],
            BLOCKER_FILING_TYPES,
            BLOCKER_FILING_STATUSES_AND_ADDITIONAL,
            expected_lookup(
                [
                    FilingKey.AMALGAMATION_REGULAR,
                    FilingKey.AMALGAMATION_VERTICAL,
                    FilingKey.AMALGAMATION_HORIZONTAL,
                    FilingKey.TRANSITION,
                ]
            ),
        ),
        (
            "general_user_llc",
            LegalEntity.State.ACTIVE,
            ["LLC"],
            "general",
            [BASIC_USER],
            BLOCKER_FILING_TYPES,
            BLOCKER_FILING_STATUSES_AND_ADDITIONAL,
            [],
        ),
        (
            "general_user_firms",
            LegalEntity.State.ACTIVE,
            ["SP", "GP"],
            "general",
            [BASIC_USER],
            BLOCKER_FILING_TYPES,
            BLOCKER_FILING_STATUSES_AND_ADDITIONAL,
            [],
        ),
        # historical business - staff user
        (
            "staff_historical_cp",
            LegalEntity.State.HISTORICAL,
            ["CP"],
            "staff",
            [STAFF_ROLE],
            BLOCKER_FILING_TYPES,
            BLOCKER_FILING_STATUSES_AND_ADDITIONAL,
            expected_lookup(
                [
                    FilingKey.COURT_ORDER,
                    FilingKey.PUT_BACK_ON,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                ]
            ),
        ),
        (
            "staff_historical_corps",
            LegalEntity.State.HISTORICAL,
            ["BC", "BEN", "CC", "ULC"],
            "staff",
            [STAFF_ROLE],
            BLOCKER_FILING_TYPES,
            BLOCKER_FILING_STATUSES_AND_ADDITIONAL,
            expected_lookup(
                [
                    FilingKey.COURT_ORDER,
                    FilingKey.PUT_BACK_ON,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                    FilingKey.RESTRN_FULL_CORPS,
                    FilingKey.RESTRN_LTD_CORPS,
                ]
            ),
        ),
        (
            "staff_historical_llc",
            LegalEntity.State.HISTORICAL,
            ["LLC"],
            "staff",
            [STAFF_ROLE],
            BLOCKER_FILING_TYPES,
            BLOCKER_FILING_STATUSES_AND_ADDITIONAL,
            [],
        ),
        (
            "staff_historical_firms",
            LegalEntity.State.HISTORICAL,
            ["SP", "GP"],
            "staff",
            [STAFF_ROLE],
            BLOCKER_FILING_TYPES,
            BLOCKER_FILING_STATUSES_AND_ADDITIONAL,
            expected_lookup(
                [
                    FilingKey.COURT_ORDER,
                    FilingKey.PUT_BACK_ON,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                ]
            ),
        ),
        # historical business - general user
        (
            "general_user_historical_cp",
            LegalEntity.State.HISTORICAL,
            ["CP"],
            "general",
            [BASIC_USER],
            BLOCKER_FILING_TYPES,
            BLOCKER_FILING_STATUSES_AND_ADDITIONAL,
            [],
        ),
        (
            "general_user_historical_corps",
            LegalEntity.State.HISTORICAL,
            ["BC", "BEN", "CC", "ULC"],
            "general",
            [BASIC_USER],
            BLOCKER_FILING_TYPES,
            BLOCKER_FILING_STATUSES_AND_ADDITIONAL,
            [],
        ),
        (
            "general_user_historical_llc",
            LegalEntity.State.HISTORICAL,
            ["LLC"],
            "general",
            [BASIC_USER],
            BLOCKER_FILING_TYPES,
            BLOCKER_FILING_STATUSES_AND_ADDITIONAL,
            [],
        ),
        (
            "general_user_historical_firms",
            LegalEntity.State.HISTORICAL,
            ["SP", "GP"],
            "general",
            [BASIC_USER],
            BLOCKER_FILING_TYPES,
            BLOCKER_FILING_STATUSES_AND_ADDITIONAL,
            [],
        ),
    ],
)
def test_allowed_filings_blocker_filing_specific_incomplete(
    monkeypatch,
    app,
    session,
    jwt,
    test_name,
    state,
    legal_types,
    username,
    roles,
    filing_types,
    filing_statuses,
    expected,
):
    """Assert that get allowed returns valid filings when business has blocker filings.

    A blocker filing in this instance is any filing incomplete filing where filing type is an alteration or a
    correction.  Note that this should also test unexpected incomplete status values.
    """
    token = helper_create_jwt(jwt, roles=roles, username=username)
    headers = {"Authorization": "Bearer " + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers[one]

    with app.test_request_context():
        monkeypatch.setattr("flask.request.headers.get", mock_auth)

        for legal_type in legal_types:
            for filing_status in filing_statuses:
                for filing_type in filing_types:
                    legal_entity = create_business(legal_type, state)
                    filing_dict = FILING_DATA.get(filing_type, None)
                    create_incomplete_filing(
                        legal_entity=legal_entity,
                        filing_name=filing_type,
                        filing_status=filing_status,
                        filing_dict=filing_dict,
                        filing_type=filing_type,
                    )
                    allowed_filing_types = get_allowed_filings(legal_entity, state, legal_type, jwt)
                    assert allowed_filing_types == expected


@pytest.mark.parametrize(
    "test_name,state,legal_types,username,roles,filing_types,filing_statuses,is_fed,expected",
    [
        # active business - staff user
        (
            "staff_active_corps",
            LegalEntity.State.ACTIVE,
            ["BC", "BEN", "CC", "ULC"],
            "staff",
            [STAFF_ROLE],
            ["dissolution.voluntary", "dissolution.administrative"],
            BLOCKER_DISSOLUTION_STATUSES_FOR_AMALG,
            True,
            expected_lookup(
                [
                    FilingKey.ADMN_FRZE,
                    FilingKey.COURT_ORDER,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                    FilingKey.TRANSITION,
                ]
            ),
        ),
        # active business - general user
        (
            "general_user_corps",
            LegalEntity.State.ACTIVE,
            ["BC", "BEN", "CC", "ULC"],
            "general",
            [BASIC_USER],
            ["dissolution.voluntary", "dissolution.administrative"],
            BLOCKER_DISSOLUTION_STATUSES_FOR_AMALG,
            True,
            expected_lookup([FilingKey.TRANSITION]),
        ),
    ],
)
def test_allowed_filings_blocker_filing_amalgamations(
    monkeypatch,
    app,
    session,
    jwt,
    test_name,
    state,
    legal_types,
    username,
    roles,
    filing_types,
    filing_statuses,
    is_fed,
    expected,
):
    """Assert that get allowed returns valid filings when amalgamating business has blocker filings.

    A blocker filing in this instance is a pending future effective dissolution filing.
    """
    token = helper_create_jwt(jwt, roles=roles, username=username)
    headers = {"Authorization": "Bearer " + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers[one]

    with app.test_request_context():
        monkeypatch.setattr("flask.request.headers.get", mock_auth)

        for legal_type in legal_types:
            for filing_status in filing_statuses:
                for filing in filing_types:
                    filing_type, filing_sub_type = filing.split(".")
                    business = create_business(legal_type, state)
                    filing_dict = FILING_DATA.get(filing_type, None)
                    create_incomplete_filing(
                        legal_entity=business,
                        filing_name=filing_type,
                        filing_status=filing_status,
                        filing_dict=filing_dict,
                        filing_type=filing_type,
                        filing_sub_type=filing_sub_type,
                        is_future_effective=is_fed,
                    )
                    allowed_filing_types = get_allowed_filings(business, state, legal_type, jwt)
                    assert allowed_filing_types == expected


@pytest.mark.parametrize(
    "test_name,state,legal_types,username,roles,expected",
    [
        # active business - staff user
        (
            "staff_active_cp",
            LegalEntity.State.ACTIVE,
            ["CP"],
            "staff",
            [STAFF_ROLE],
            expected_lookup(
                [
                    FilingKey.ADMN_FRZE,
                    FilingKey.AR_CP,
                    FilingKey.COA_CP,
                    FilingKey.COD_CP,
                    FilingKey.CORRCTN,
                    FilingKey.COURT_ORDER,
                    FilingKey.VOL_DISS,
                    FilingKey.ADM_DISS,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                    FilingKey.SPECIAL_RESOLUTION,
                ]
            ),
        ),
        (
            "staff_active_corps",
            LegalEntity.State.ACTIVE,
            ["BC", "BEN", "CC", "ULC"],
            "staff",
            [STAFF_ROLE],
            expected_lookup(
                [
                    FilingKey.ADMN_FRZE,
                    FilingKey.AGM_EXTENSION,
                    FilingKey.AGM_LOCATION_CHANGE,
                    FilingKey.ALTERATION,
                    FilingKey.AMALGAMATION_REGULAR,
                    FilingKey.AMALGAMATION_VERTICAL,
                    FilingKey.AMALGAMATION_HORIZONTAL,
                    FilingKey.AR_CORPS,
                    FilingKey.COA_CORPS,
                    FilingKey.COD_CORPS,
                    FilingKey.CONSENT_CONTINUATION_OUT,
                    FilingKey.CORRCTN,
                    FilingKey.COURT_ORDER,
                    FilingKey.VOL_DISS,
                    FilingKey.ADM_DISS,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                    FilingKey.TRANSITION,
                ]
            ),
        ),
        ("staff_active_llc", LegalEntity.State.ACTIVE, ["LLC"], "staff", [STAFF_ROLE], []),
        (
            "staff_active_firms",
            LegalEntity.State.ACTIVE,
            ["SP", "GP"],
            "staff",
            [STAFF_ROLE],
            expected_lookup(
                [
                    FilingKey.ADMN_FRZE,
                    FilingKey.CONV_FIRMS,
                    FilingKey.COURT_ORDER,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                ]
            ),
        ),
        # active business - general user
        (
            "general_user_cp",
            LegalEntity.State.ACTIVE,
            ["CP"],
            "general",
            [BASIC_USER],
            expected_lookup(
                [FilingKey.AR_CP, FilingKey.COA_CP, FilingKey.COD_CP, FilingKey.VOL_DISS, FilingKey.SPECIAL_RESOLUTION]
            ),
        ),
        (
            "general_user_corps",
            LegalEntity.State.ACTIVE,
            ["BC", "BEN", "CC", "ULC"],
            "general",
            [BASIC_USER],
            expected_lookup(
                [
                    FilingKey.AGM_EXTENSION,
                    FilingKey.AGM_LOCATION_CHANGE,
                    FilingKey.ALTERATION,
                    FilingKey.AMALGAMATION_REGULAR,
                    FilingKey.AMALGAMATION_VERTICAL,
                    FilingKey.AMALGAMATION_HORIZONTAL,
                    FilingKey.AR_CORPS,
                    FilingKey.COA_CORPS,
                    FilingKey.COD_CORPS,
                    FilingKey.CONSENT_CONTINUATION_OUT,
                    FilingKey.VOL_DISS,
                    FilingKey.TRANSITION,
                ]
            ),
        ),
        ("general_user_llc", LegalEntity.State.ACTIVE, ["LLC"], "general", [BASIC_USER], []),
        ("general_user_firms", LegalEntity.State.ACTIVE, ["SP", "GP"], "general", [BASIC_USER], []),
        # historical business - staff user
        (
            "staff_historical_cp",
            LegalEntity.State.HISTORICAL,
            ["CP"],
            "staff",
            [STAFF_ROLE],
            expected_lookup(
                [
                    FilingKey.COURT_ORDER,
                    FilingKey.PUT_BACK_ON,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                ]
            ),
        ),
        (
            "staff_historical_corps",
            LegalEntity.State.HISTORICAL,
            ["BC", "BEN", "CC", "ULC"],
            "staff",
            [STAFF_ROLE],
            expected_lookup(
                [
                    FilingKey.COURT_ORDER,
                    FilingKey.PUT_BACK_ON,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                    FilingKey.RESTRN_FULL_CORPS,
                    FilingKey.RESTRN_LTD_CORPS,
                ]
            ),
        ),
        ("staff_historical_llc", LegalEntity.State.HISTORICAL, ["LLC"], "staff", [STAFF_ROLE], []),
        (
            "staff_historical_firms",
            LegalEntity.State.HISTORICAL,
            ["SP", "GP"],
            "staff",
            [STAFF_ROLE],
            expected_lookup(
                [
                    FilingKey.COURT_ORDER,
                    FilingKey.PUT_BACK_ON,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                ]
            ),
        ),
        # historical business - general user
        ("general_user_historical_cp", LegalEntity.State.HISTORICAL, ["CP"], "general", [BASIC_USER], []),
        (
            "general_user_historical_corps",
            LegalEntity.State.HISTORICAL,
            ["BC", "BEN", "CC", "ULC"],
            "general",
            [BASIC_USER],
            [],
        ),
        ("general_user_historical_llc", LegalEntity.State.HISTORICAL, ["LLC"], "general", [BASIC_USER], []),
        ("general_user_historical_firms", LegalEntity.State.HISTORICAL, ["SP", "GP"], "general", [BASIC_USER], []),
    ],
)
def test_allowed_filings_warnings(
    monkeypatch, app, session, jwt, test_name, state, legal_types, username, roles, expected
):
    """Assert that get allowed returns valid filings when business has warnings."""
    token = helper_create_jwt(jwt, roles=roles, username=username)
    headers = {"Authorization": "Bearer " + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers[one]

    with app.test_request_context():
        monkeypatch.setattr("flask.request.headers.get", mock_auth)
        for legal_type in legal_types:
            legal_entity = create_business(legal_type, state)
            if legal_type in ("SP", "GP") and state == LegalEntity.State.ACTIVE:
                legal_entity.warnings = MISSING_BUSINESS_INFO_WARNINGS
            filing_types = get_allowed_filings(legal_entity, state, legal_type, jwt)
            assert filing_types == expected


@pytest.mark.parametrize(
    "test_name,state,legal_types,username,roles,state_filing_types,state_filing_sub_types,expected",
    [
        # active business - staff user
        (
            "staff_active_cp_unaffected",
            LegalEntity.State.ACTIVE,
            ["CP"],
            "staff",
            [STAFF_ROLE],
            ["restoration", "restoration", None, "restoration"],
            ["limitedRestoration", "limitedRestorationExtension", None, "fullRestoration"],
            expected_lookup(
                [
                    FilingKey.ADMN_FRZE,
                    FilingKey.AR_CP,
                    FilingKey.COA_CP,
                    FilingKey.COD_CP,
                    FilingKey.CORRCTN,
                    FilingKey.COURT_ORDER,
                    FilingKey.VOL_DISS,
                    FilingKey.ADM_DISS,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                    FilingKey.SPECIAL_RESOLUTION,
                ]
            ),
        ),
        (
            "staff_active_corps_valid_state_filing_success",
            LegalEntity.State.ACTIVE,
            ["BC", "BEN", "CC", "ULC"],
            "staff",
            [STAFF_ROLE],
            ["restoration", "restoration"],
            ["limitedRestoration", "limitedRestorationExtension"],
            expected_lookup(
                [
                    FilingKey.ADMN_FRZE,
                    FilingKey.AGM_EXTENSION,
                    FilingKey.AGM_LOCATION_CHANGE,
                    FilingKey.ALTERATION,
                    FilingKey.AMALGAMATION_REGULAR,
                    FilingKey.AMALGAMATION_VERTICAL,
                    FilingKey.AMALGAMATION_HORIZONTAL,
                    FilingKey.AR_CORPS,
                    FilingKey.COA_CORPS,
                    FilingKey.COD_CORPS,
                    FilingKey.CONSENT_CONTINUATION_OUT,
                    FilingKey.CORRCTN,
                    FilingKey.COURT_ORDER,
                    FilingKey.VOL_DISS,
                    FilingKey.ADM_DISS,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                    FilingKey.TRANSITION,
                    FilingKey.RESTRN_LTD_EXT_CORPS,
                    FilingKey.RESTRN_LTD_TO_FULL_CORPS,
                ]
            ),
        ),
        (
            "staff_active_corps_valid_state_filing_fail",
            LegalEntity.State.ACTIVE,
            ["BC", "BEN", "CC", "ULC"],
            "staff",
            [STAFF_ROLE],
            [None, "restoration"],
            [None, "fullRestoration"],
            expected_lookup(
                [
                    FilingKey.ADMN_FRZE,
                    FilingKey.AGM_EXTENSION,
                    FilingKey.AGM_LOCATION_CHANGE,
                    FilingKey.ALTERATION,
                    FilingKey.AMALGAMATION_REGULAR,
                    FilingKey.AMALGAMATION_VERTICAL,
                    FilingKey.AMALGAMATION_HORIZONTAL,
                    FilingKey.AR_CORPS,
                    FilingKey.COA_CORPS,
                    FilingKey.COD_CORPS,
                    FilingKey.CONSENT_CONTINUATION_OUT,
                    FilingKey.CORRCTN,
                    FilingKey.COURT_ORDER,
                    FilingKey.VOL_DISS,
                    FilingKey.ADM_DISS,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                    FilingKey.TRANSITION,
                ]
            ),
        ),
        (
            "staff_active_llc_valid_state_filing_success",
            LegalEntity.State.ACTIVE,
            ["LLC"],
            "staff",
            [STAFF_ROLE],
            ["restoration", "restoration"],
            ["limitedRestoration", "limitedRestorationExtension"],
            [],
        ),
        (
            "staff_active_llc_valid_state_filing_fail",
            LegalEntity.State.ACTIVE,
            ["LLC"],
            "staff",
            [STAFF_ROLE],
            [None, "restoration"],
            [None, "fullRestoration"],
            [],
        ),
        (
            "staff_active_firms_unaffected",
            LegalEntity.State.ACTIVE,
            ["SP", "GP"],
            "staff",
            [STAFF_ROLE],
            ["putBackOn", None],
            [None, None],
            expected_lookup(
                [
                    FilingKey.ADMN_FRZE,
                    FilingKey.CHANGE_OF_REGISTRATION,
                    FilingKey.CONV_FIRMS,
                    FilingKey.CORRCTN_FIRMS,
                    FilingKey.COURT_ORDER,
                    FilingKey.VOL_DISS_FIRMS,
                    FilingKey.ADM_DISS_FIRMS,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                ]
            ),
        ),
        # active business - general user
        (
            "general_user_cp_unaffected",
            LegalEntity.State.ACTIVE,
            ["CP"],
            "general",
            [BASIC_USER],
            ["restoration", "restoration", None, "restoration"],
            ["limitedRestoration", "limitedRestorationExtension", None, "fullRestoration"],
            expected_lookup(
                [FilingKey.AR_CP, FilingKey.COA_CP, FilingKey.COD_CP, FilingKey.VOL_DISS, FilingKey.SPECIAL_RESOLUTION]
            ),
        ),
        (
            "general_user_corps_unaffected",
            LegalEntity.State.ACTIVE,
            ["BC", "BEN", "CC", "ULC"],
            "general",
            [BASIC_USER],
            ["restoration", "restoration", None, "restoration"],
            ["limitedRestoration", "limitedRestorationExtension", None, "fullRestoration"],
            expected_lookup(
                [
                    FilingKey.AGM_EXTENSION,
                    FilingKey.AGM_LOCATION_CHANGE,
                    FilingKey.ALTERATION,
                    FilingKey.AMALGAMATION_REGULAR,
                    FilingKey.AMALGAMATION_VERTICAL,
                    FilingKey.AMALGAMATION_HORIZONTAL,
                    FilingKey.AR_CORPS,
                    FilingKey.COA_CORPS,
                    FilingKey.COD_CORPS,
                    FilingKey.CONSENT_CONTINUATION_OUT,
                    FilingKey.VOL_DISS,
                    FilingKey.TRANSITION,
                ]
            ),
        ),
        (
            "general_user_llc_unaffected",
            LegalEntity.State.ACTIVE,
            ["LLC"],
            "general",
            [BASIC_USER],
            ["restoration", "restoration", None, "restoration"],
            ["limitedRestoration", "limitedRestorationExtension", None, "fullRestoration"],
            [],
        ),
        (
            "general_user_firms_unaffected",
            LegalEntity.State.ACTIVE,
            ["SP", "GP"],
            "general",
            [BASIC_USER],
            ["putBackOn", None],
            [None, None],
            expected_lookup([FilingKey.CHANGE_OF_REGISTRATION, FilingKey.VOL_DISS_FIRMS]),
        ),
        # historical business - staff user
        (
            "staff_historical_cp_unaffected",
            LegalEntity.State.HISTORICAL,
            ["CP"],
            "staff",
            [STAFF_ROLE],
            ["dissolution", None],
            [None, None],
            expected_lookup(
                [
                    FilingKey.COURT_ORDER,
                    FilingKey.PUT_BACK_ON,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                ]
            ),
        ),
        (
            "staff_historical_cp_invalid_state_filing_fail",
            LegalEntity.State.HISTORICAL,
            ["CP"],
            "staff",
            [STAFF_ROLE],
            ["continuationIn"],
            [None],
            expected_lookup(
                [
                    FilingKey.COURT_ORDER,
                    FilingKey.PUT_BACK_ON,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                ]
            ),
        ),
        (
            "staff_historical_corps_unaffected",
            LegalEntity.State.HISTORICAL,
            ["BC", "BEN", "CC", "ULC"],
            "staff",
            [STAFF_ROLE],
            ["dissolution", None],
            [None, None],
            expected_lookup(
                [
                    FilingKey.COURT_ORDER,
                    FilingKey.PUT_BACK_ON,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                    FilingKey.RESTRN_FULL_CORPS,
                    FilingKey.RESTRN_LTD_CORPS,
                ]
            ),
        ),
        (
            "staff_historical_corps_invalid_state_filing_fail",
            LegalEntity.State.HISTORICAL,
            ["BC", "BEN", "CC", "ULC"],
            "staff",
            [STAFF_ROLE],
            ["continuationIn", "continuationOut"],
            [None, None],
            expected_lookup(
                [
                    FilingKey.COURT_ORDER,
                    FilingKey.PUT_BACK_ON,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                ]
            ),
        ),
        (
            "staff_historical_llc_unaffected",
            LegalEntity.State.HISTORICAL,
            ["LLC"],
            "staff",
            [STAFF_ROLE],
            ["dissolution", None],
            [None, None],
            [],
        ),
        (
            "staff_historical_firms_unaffected",
            LegalEntity.State.HISTORICAL,
            ["SP", "GP"],
            "staff",
            [STAFF_ROLE],
            ["dissolution", None],
            [None, None],
            expected_lookup(
                [
                    FilingKey.COURT_ORDER,
                    FilingKey.PUT_BACK_ON,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                ]
            ),
        ),
        # historical business - general user
        (
            "general_user_historical_cp_unaffected",
            LegalEntity.State.HISTORICAL,
            ["CP"],
            "general",
            [BASIC_USER],
            ["dissolution", "continuationIn", None],
            [None, None, None],
            [],
        ),
        (
            "general_user_historical_corps_unaffected",
            LegalEntity.State.HISTORICAL,
            ["BC", "BEN", "CC", "ULC"],
            "general",
            [BASIC_USER],
            ["dissolution", "continuationIn", "continuationOut", None],
            [None, None, None, None],
            [],
        ),
        (
            "general_user_historical_llc_unaffected",
            LegalEntity.State.HISTORICAL,
            ["LLC"],
            "general",
            [BASIC_USER],
            ["dissolution", None],
            [None, None],
            [],
        ),
        (
            "general_user_historical_firms_unaffected",
            LegalEntity.State.HISTORICAL,
            ["SP", "GP"],
            "general",
            [BASIC_USER],
            ["dissolution", None],
            [None, None],
            [],
        ),
    ],
)
def test_allowed_filings_state_filing_check(
    monkeypatch,
    app,
    session,
    jwt,
    test_name,
    state,
    legal_types,
    username,
    roles,
    state_filing_types,
    state_filing_sub_types,
    expected,
):
    """Assert that get allowed returns valid filings when validStateFilings or invalidStateFilings blocker is defined.

    A filing with validStateFiling defined should only return a target filing if the business state filing matches
    one of the state filing types defined in validStateFiling.

    A filing with invalidStateFiling defined should only return a target filing if the business state filing does
    not match one of the state filing types defined in invalidStateFiling.
    """
    token = helper_create_jwt(jwt, roles=roles, username=username)
    headers = {"Authorization": "Bearer " + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers[one]

    with app.test_request_context():
        monkeypatch.setattr("flask.request.headers.get", mock_auth)

        for legal_type in legal_types:
            for idx, state_filing_type in enumerate(state_filing_types):
                legal_entity = create_business(legal_type, state)
                state_filing_sub_type = state_filing_sub_types[idx]
                if state_filing_type:
                    state_filing = create_filing(legal_entity, state_filing_type, state_filing_sub_type)
                    legal_entity.state_filing_id = state_filing.id
                    legal_entity.save()
                allowed_filing_types = get_allowed_filings(legal_entity, state, legal_type, jwt)
                assert allowed_filing_types == expected


@pytest.mark.parametrize(
    "test_name,state,filing_type,sub_filing_type,legal_types,username,roles,filing_status,expected",
    [
        (
            "staff_user_active_allowed",
            LegalEntity.State.ACTIVE,
            "changeOfRegistration",
            None,
            ["SP", "GP"],
            "general",
            [STAFF_ROLE],
            Filing.Status.DRAFT.value,
            True,
        ),
        (
            "staff_user_active_allowed",
            LegalEntity.State.ACTIVE,
            "alteration",
            None,
            ["BEN", "BC", "ULC", "CC"],
            "general",
            [STAFF_ROLE],
            Filing.Status.DRAFT.value,
            True,
        ),
        (
            "staff_user_active",
            LegalEntity.State.ACTIVE,
            "changeOfRegistration",
            None,
            ["SP", "GP"],
            "general",
            [STAFF_ROLE],
            Filing.Status.PENDING.value,
            False,
        ),
        (
            "staff_active_allowed",
            LegalEntity.State.ACTIVE,
            "alteration",
            None,
            ["BEN", "BC", "ULC", "CC"],
            "general",
            [STAFF_ROLE],
            Filing.Status.PENDING.value,
            False,
        ),
        (
            "user_active_allowed",
            LegalEntity.State.ACTIVE,
            "changeOfRegistration",
            None,
            ["SP", "GP"],
            "general",
            [BASIC_USER],
            Filing.Status.DRAFT.value,
            True,
        ),
        (
            "user_active_allowed",
            LegalEntity.State.ACTIVE,
            "alteration",
            None,
            ["BEN", "BC", "ULC", "CC"],
            "general",
            [BASIC_USER],
            Filing.Status.DRAFT.value,
            True,
        ),
        (
            "user_active",
            LegalEntity.State.ACTIVE,
            "changeOfRegistration",
            None,
            ["SP", "GP"],
            "general",
            [BASIC_USER],
            Filing.Status.PENDING.value,
            False,
        ),
        (
            "user_active_allowed",
            LegalEntity.State.ACTIVE,
            "alteration",
            None,
            ["BEN", "BC", "ULC", "CC"],
            "general",
            [BASIC_USER],
            Filing.Status.PENDING.value,
            False,
        ),
    ],
)
def test_is_allowed_ignore_draft_filing(
    monkeypatch,
    app,
    session,
    jwt,
    test_name,
    state,
    filing_type,
    sub_filing_type,
    legal_types,
    username,
    roles,
    filing_status,
    expected,
):
    """Assert that get allowed returns valid filings when filing status is draft."""
    token = helper_create_jwt(jwt, roles=roles, username=username)
    headers = {"Authorization": "Bearer " + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers[one]

    with app.test_request_context():
        monkeypatch.setattr("flask.request.headers.get", mock_auth)
        for legal_type in legal_types:
            legal_entity = create_business(legal_type, state)
            filing_dict = FILING_DATA.get(filing_type, None)
            filing = create_incomplete_filing(
                legal_entity=legal_entity,
                filing_name=filing_type,
                filing_status=filing_status,
                filing_dict=filing_dict,
                filing_type=filing_type,
            )
            filing_types = is_allowed(legal_entity, state, filing_type, legal_type, jwt, sub_filing_type, filing.id)
            assert filing_types == expected


@pytest.mark.parametrize(
    "test_name,state,legal_types,username,roles,filing_types,filing_sub_types,is_completed,expected",
    [
        # active business - staff user
        (
            "staff_active_corps_completed_filing_success",
            LegalEntity.State.ACTIVE,
            ["BC", "BEN", "CC", "ULC"],
            "staff",
            [STAFF_ROLE],
            ["consentContinuationOut", "consentContinuationOut"],
            [None, None],
            [True, True],
            expected_lookup(
                [
                    FilingKey.ADMN_FRZE,
                    FilingKey.AGM_EXTENSION,
                    FilingKey.AGM_LOCATION_CHANGE,
                    FilingKey.ALTERATION,
                    FilingKey.AMALGAMATION_REGULAR,
                    FilingKey.AMALGAMATION_VERTICAL,
                    FilingKey.AMALGAMATION_HORIZONTAL,
                    FilingKey.AR_CORPS,
                    FilingKey.COA_CORPS,
                    FilingKey.COD_CORPS,
                    FilingKey.CONSENT_CONTINUATION_OUT,
                    FilingKey.CONTINUATION_OUT,
                    FilingKey.CORRCTN,
                    FilingKey.COURT_ORDER,
                    FilingKey.VOL_DISS,
                    FilingKey.ADM_DISS,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                    FilingKey.TRANSITION,
                ]
            ),
        ),
        (
            "staff_active_corps_completed_filing_success",
            LegalEntity.State.ACTIVE,
            ["BC", "BEN", "CC", "ULC"],
            "staff",
            [STAFF_ROLE],
            ["consentContinuationOut", "consentContinuationOut"],
            [None, None],
            [True, False],
            expected_lookup(
                [
                    FilingKey.ADMN_FRZE,
                    FilingKey.AMALGAMATION_REGULAR,
                    FilingKey.AMALGAMATION_VERTICAL,
                    FilingKey.AMALGAMATION_HORIZONTAL,
                    FilingKey.CONTINUATION_OUT,
                    FilingKey.COURT_ORDER,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                    FilingKey.TRANSITION,
                ]
            ),
        ),
        (
            "staff_active_corps_completed_filing_fail",
            LegalEntity.State.ACTIVE,
            ["BC", "BEN", "CC", "ULC"],
            "staff",
            [STAFF_ROLE],
            ["consentContinuationOut", "consentContinuationOut"],
            [None, None],
            [False, False],
            expected_lookup(
                [
                    FilingKey.ADMN_FRZE,
                    FilingKey.AMALGAMATION_REGULAR,
                    FilingKey.AMALGAMATION_VERTICAL,
                    FilingKey.AMALGAMATION_HORIZONTAL,
                    FilingKey.COURT_ORDER,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                    FilingKey.TRANSITION,
                ]
            ),
        ),
        (
            "staff_active_corps_completed_filing_fail",
            LegalEntity.State.ACTIVE,
            ["BC", "BEN", "CC", "ULC"],
            "staff",
            [STAFF_ROLE],
            [None, None],
            [None, None],
            [False, False],
            expected_lookup(
                [
                    FilingKey.ADMN_FRZE,
                    FilingKey.AGM_EXTENSION,
                    FilingKey.AGM_LOCATION_CHANGE,
                    FilingKey.ALTERATION,
                    FilingKey.AMALGAMATION_REGULAR,
                    FilingKey.AMALGAMATION_VERTICAL,
                    FilingKey.AMALGAMATION_HORIZONTAL,
                    FilingKey.AR_CORPS,
                    FilingKey.COA_CORPS,
                    FilingKey.COD_CORPS,
                    FilingKey.CONSENT_CONTINUATION_OUT,
                    FilingKey.CORRCTN,
                    FilingKey.COURT_ORDER,
                    FilingKey.VOL_DISS,
                    FilingKey.ADM_DISS,
                    FilingKey.REGISTRARS_NOTATION,
                    FilingKey.REGISTRARS_ORDER,
                    FilingKey.TRANSITION,
                ]
            ),
        ),
    ],
)
def test_allowed_filings_completed_filing_check(
    monkeypatch,
    app,
    session,
    jwt,
    test_name,
    state,
    legal_types,
    username,
    roles,
    filing_types,
    filing_sub_types,
    is_completed,
    expected,
):
    """Assert that get allowed returns valid filings when completedFilings blocker is defined.

    A filing with completedFilings defined should only return a target filing if the business state filing matches
    one of the state filing types defined in completedFiling.
    """
    token = helper_create_jwt(jwt, roles=roles, username=username)
    headers = {"Authorization": "Bearer " + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers[one]

    with app.test_request_context():
        monkeypatch.setattr("flask.request.headers.get", mock_auth)

        for legal_type in legal_types:
            business = create_business(legal_type, state)
            for idx, filing_type in enumerate(filing_types):
                filing_sub_type = filing_sub_types[idx]
                if filing_type:
                    if is_completed[idx]:
                        create_filing(business, filing_type, filing_sub_type)
                    else:
                        filing_dict = FILING_DATA.get(filing_type, filing_sub_type)
                        create_incomplete_filing(
                            legal_entity=business,
                            filing_name="unknown",
                            filing_status=Filing.Status.DRAFT.value,
                            filing_dict=filing_dict,
                            filing_type=filing_type,
                            filing_sub_type=filing_sub_type,
                        )

            allowed_filing_types = get_allowed_filings(business, state, legal_type, jwt)
            assert allowed_filing_types == expected


@patch("legal_api.models.User.find_by_jwt_token", return_value=User(id=1, login_source="BCSC"))
@patch("legal_api.services.authz.is_self_registered_owner_operator", return_value=True)
def test_are_digital_credentials_allowed_false_when_no_token(monkeypatch, app, session, jwt):
    token_json = {"username": "test"}
    token = helper_create_jwt(jwt, roles=[PUBLIC_USER], username=token_json["username"])
    headers = {"Authorization": "Bearer " + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers[one]

    with app.test_request_context():
        jwt.get_token_auth_header = MagicMock(return_value=token)
        pyjwt.decode = MagicMock(return_value=None)
        monkeypatch.setattr("flask.request.headers.get", mock_auth)

        business = create_business("SP", LegalEntity.State.ACTIVE)
        assert are_digital_credentials_allowed(business, jwt) is False


@patch("legal_api.models.User.find_by_jwt_token", return_value=None)
@patch("legal_api.services.authz.is_self_registered_owner_operator", return_value=True)
def test_are_digital_credentials_allowed_false_when_no_user(monkeypatch, app, session, jwt):
    token_json = {"username": "test"}
    token = helper_create_jwt(jwt, roles=[PUBLIC_USER], username=token_json["username"])
    headers = {"Authorization": "Bearer " + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers[one]

    with app.test_request_context():
        jwt.get_token_auth_header = MagicMock(return_value=token)
        pyjwt.decode = MagicMock(return_value=token_json)
        monkeypatch.setattr("flask.request.headers.get", mock_auth)

        business = create_business("SP", LegalEntity.State.ACTIVE)
        assert are_digital_credentials_allowed(business, jwt) is False


@patch("legal_api.models.User.find_by_jwt_token", return_value=User(id=1, login_source="BCSC"))
@patch("legal_api.services.authz.is_self_registered_owner_operator", return_value=True)
def test_are_digital_credentials_allowed_false_when_user_is_staff(monkeypatch, app, session, jwt):
    token_json = {"username": "test"}
    token = helper_create_jwt(jwt, roles=[STAFF_ROLE], username=token_json["username"])
    headers = {"Authorization": "Bearer " + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers[one]

    with app.test_request_context():
        jwt.get_token_auth_header = MagicMock(return_value=token)
        pyjwt.decode = MagicMock(return_value=token_json)
        monkeypatch.setattr("flask.request.headers.get", mock_auth)

        business = create_business("SP", LegalEntity.State.ACTIVE)
        assert are_digital_credentials_allowed(business, jwt) is False


@patch("legal_api.models.User.find_by_jwt_token", return_value=User(id=1, login_source="NOT_BCSC"))
@patch("legal_api.services.authz.is_self_registered_owner_operator", return_value=True)
def test_are_digital_credentials_allowed_false_when_login_source_not_bcsc(monkeypatch, app, session, jwt):
    token_json = {"username": "test"}
    token = helper_create_jwt(jwt, roles=[PUBLIC_USER], username=token_json["username"])
    headers = {"Authorization": "Bearer " + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers[one]

    with app.test_request_context():
        jwt.get_token_auth_header = MagicMock(return_value=token)
        pyjwt.decode = MagicMock(return_value=token_json)
        monkeypatch.setattr("flask.request.headers.get", mock_auth)

        business = create_business("SP", LegalEntity.State.ACTIVE)
        assert are_digital_credentials_allowed(business, jwt) is False


@patch("legal_api.models.User.find_by_jwt_token", return_value=User(id=1, login_source="BCSC"))
@patch("legal_api.services.authz.is_self_registered_owner_operator", return_value=True)
def test_are_digital_credentials_allowed_false_when_wrong_business_type(monkeypatch, app, session, jwt):
    token_json = {"username": "test"}
    token = helper_create_jwt(jwt, roles=[PUBLIC_USER], username=token_json["username"])
    headers = {"Authorization": "Bearer " + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers[one]

    with app.test_request_context():
        jwt.get_token_auth_header = MagicMock(return_value=token)
        pyjwt.decode = MagicMock(return_value=token_json)
        monkeypatch.setattr("flask.request.headers.get", mock_auth)

        business = create_business("GP", LegalEntity.State.ACTIVE)
        assert are_digital_credentials_allowed(business, jwt) is False


@patch("legal_api.models.User.find_by_jwt_token", return_value=User(id=1, login_source="BCSC"))
@patch("legal_api.services.authz.is_self_registered_owner_operator", return_value=False)
def test_are_digital_credentials_allowed_false_when_not_owner_operator(monkeypatch, app, session, jwt):
    token_json = {"username": "test"}
    token = helper_create_jwt(jwt, roles=[PUBLIC_USER], username=token_json["username"])
    headers = {"Authorization": "Bearer " + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers[one]

    with app.test_request_context():
        jwt.get_token_auth_header = MagicMock(return_value=token)
        pyjwt.decode = MagicMock(return_value=token_json)
        monkeypatch.setattr("flask.request.headers.get", mock_auth)

        business = create_business("SP", LegalEntity.State.ACTIVE)
        assert are_digital_credentials_allowed(business, jwt) is False


@patch("legal_api.models.User.find_by_jwt_token", return_value=User(id=1, login_source="BCSC"))
@patch("legal_api.services.authz.is_self_registered_owner_operator", return_value=True)
def test_are_digital_credentials_allowed_true(monkeypatch, app, session, jwt):
    token_json = {"username": "test"}
    token = helper_create_jwt(jwt, roles=[PUBLIC_USER], username=token_json["username"])
    headers = {"Authorization": "Bearer " + token}

    def mock_auth(one, two):  # pylint: disable=unused-argument; mocks of library methods
        return headers[one]

    with app.test_request_context():
        jwt.get_token_auth_header = MagicMock(return_value=token)
        pyjwt.decode = MagicMock(return_value=token_json)
        monkeypatch.setattr("flask.request.headers.get", mock_auth)

        business = create_business("SP", LegalEntity.State.ACTIVE)
        assert are_digital_credentials_allowed(business, jwt) is True


@patch("legal_api.services.authz.get_registration_filing", return_value=None)
def test_is_self_registered_owner_operator_false_when_no_registration_filing(app, session):
    user = factory_user(username="test", firstname="Test", lastname="User")
    business = create_business("SP", LegalEntity.State.ACTIVE)

    assert is_self_registered_owner_operator(business, user) is False


def test_is_self_registered_owner_operator_false_when_no_proprietors(app, session):
    user = factory_user(username="test", firstname="Test", lastname="User")
    business = create_business("SP", LegalEntity.State.ACTIVE)
    completing_party_role = create_party_role(EntityRole.RoleTypes.completing_party, **create_test_user())
    filing = factory_completed_filing(
        business=business,
        data_dict={"filing": {"header": {"name": "registration"}}},
        filing_date=_datetime.utcnow(),
        filing_type="registration",
    )
    filing.filing_party_roles.append(completing_party_role)
    filing.submitter_id = user.id
    filing.save()

    assert is_self_registered_owner_operator(business, user) is False


@patch(
    "legal_api.models.EntityRole.get_parties_by_role",
    return_value=[EntityRole(role_type=EntityRole.RoleTypes.proprietor)],
)
def test_is_self_registered_owner_operator_false_when_no_proprietor(app, session):
    user = factory_user(username="test", firstname="Test", lastname="User")
    business = create_business("SP", LegalEntity.State.ACTIVE)
    completing_party_role = create_party_role(EntityRole.RoleTypes.completing_party, **create_test_user())
    filing = factory_completed_filing(
        business=business,
        data_dict={"filing": {"header": {"name": "registration"}}},
        filing_date=_datetime.utcnow(),
        filing_type="registration",
    )
    filing.filing_party_roles.append(completing_party_role)
    filing.submitter_id = user.id
    filing.save()

    assert is_self_registered_owner_operator(business, user) is False


@patch("legal_api.models.EntityRole.get_party_roles_by_filing", return_value=None)
def test_is_self_registered_owner_operator_false_when_no_completing_parties(app, session):
    user = factory_user(username="test", firstname="Test", lastname="User")
    business = create_business("SP", LegalEntity.State.ACTIVE)
    proprietor_party_role = create_party_role(EntityRole.RoleTypes.proprietor, **create_test_user())
    proprietor_party_role.legal_entity_id = business.id
    proprietor_party_role.save()

    assert is_self_registered_owner_operator(business, user) is False


@patch(
    "legal_api.models.EntityRole.get_party_roles_by_filing",
    return_value=[EntityRole(role_type=EntityRole.RoleTypes.completing_party)],
)
def test_is_self_registered_owner_operator_false_when_no_completing_party(app, session):
    user = factory_user(username="test", firstname="Test", lastname="User")
    business = create_business("SP", LegalEntity.State.ACTIVE)
    proprietor_party_role = create_party_role(EntityRole.RoleTypes.PROPRIETOR, **create_test_user())
    proprietor_party_role.legal_entity_id = business.id
    proprietor_party_role.save()

    assert is_self_registered_owner_operator(business, user) is False


def test_is_self_registered_owner_operator_false_when_parties_not_matching(app, session):
    user = factory_user(username="test", firstname="Test1", lastname="User1")
    business = create_business("SP", LegalEntity.State.ACTIVE)
    completing_party_role = create_party_role(EntityRole.RoleTypes.completing_party, **create_test_user("1"))
    filing = factory_completed_filing(
        business=business,
        data_dict={"filing": {"header": {"name": "registration"}}},
        filing_date=_datetime.utcnow(),
        filing_type="registration",
    )
    filing.filing_party_roles.append(completing_party_role)
    filing.submitter_id = user.id
    filing.save()

    proprietor_party_role = create_party_role(EntityRole.RoleTypes.proprietor, **create_test_user("2"))
    proprietor_party_role.legal_entity_id = business.id
    proprietor_party_role.save()

    assert is_self_registered_owner_operator(business, user) is False


def test_is_self_registered_owner_operator_false_when_user_not_matching(app, session):
    user = factory_user(username="test", firstname="Test1", lastname="User1")
    business = create_business("SP", LegalEntity.State.ACTIVE)
    completing_party_role = create_party_role(EntityRole.RoleTypes.completing_party, **create_test_user("2"))
    filing = factory_completed_filing(
        business=business,
        data_dict={"filing": {"header": {"name": "registration"}}},
        filing_date=_datetime.utcnow(),
        filing_type="registration",
    )
    filing.filing_party_roles.append(completing_party_role)
    filing.submitter_id = user.id
    filing.save()

    proprietor_party_role = create_party_role(EntityRole.RoleTypes.proprietor, **create_test_user("2"))
    proprietor_party_role.legal_entity_id = business.id
    proprietor_party_role.save()

    assert is_self_registered_owner_operator(business, user) is False


def test_is_self_registered_owner_operator_false_when_proprietor_uses_middle_name_field_and_user_does_not(app, session):
    user = factory_user(username="test", firstname="Test", lastname="User")
    business = create_business("SP", LegalEntity.State.ACTIVE)
    completing_party_role = create_party_role(
        EntityRole.RoleTypes.completing_party, **create_test_user(first_name="TEST", last_name="USER")
    )
    filing = factory_completed_filing(
        business=business,
        data_dict={"filing": {"header": {"name": "registration"}}},
        filing_date=_datetime.utcnow(),
        filing_type="registration",
    )
    filing.filing_party_roles.append(completing_party_role)
    filing.submitter_id = user.id
    filing.save()

    proprietor_party_role = create_party_role(
        EntityRole.RoleTypes.proprietor, **create_test_user(first_name="TEST", middle_initial="TU", last_name="USER")
    )
    proprietor_party_role.legal_entity_id = business.id
    proprietor_party_role.save()

    assert is_self_registered_owner_operator(business, user) is False


def test_is_self_registered_owner_operator_true_when_proprietor_and_user_uses_middle_name_field(app, session):
    user = factory_user(username="test", firstname="Test Tu", lastname="User")
    business = create_business("SP", LegalEntity.State.ACTIVE)
    completing_party_role = create_party_role(
        EntityRole.RoleTypes.completing_party, **create_test_user(first_name="TEST TU", last_name="USER")
    )
    filing = factory_completed_filing(
        business=business,
        data_dict={"filing": {"header": {"name": "registration"}}},
        filing_date=_datetime.utcnow(),
        filing_type="registration",
    )
    filing.filing_party_roles.append(completing_party_role)
    filing.submitter_id = user.id
    filing.save()

    proprietor_party_role = create_party_role(
        EntityRole.RoleTypes.proprietor, **create_test_user(first_name="TEST", middle_initial="TU", last_name="USER")
    )
    proprietor_party_role.legal_entity_id = business.id
    proprietor_party_role.save()

    assert is_self_registered_owner_operator(business, user) is True


def test_is_self_registered_owner_operator_true(app, session):
    user = factory_user(username="test", firstname="Test", lastname="User")
    business = create_business("SP", LegalEntity.State.ACTIVE)
    completing_party_role = create_party_role(
        EntityRole.RoleTypes.completing_party, **create_test_user(first_name="TEST", last_name="USER")
    )
    filing = factory_completed_filing(
        business=business,
        data_dict={"filing": {"header": {"name": "registration"}}},
        filing_date=_datetime.utcnow(),
        filing_type="registration",
    )
    filing.filing_party_roles.append(completing_party_role)
    filing.submitter_id = user.id
    filing.save()

    proprietor_party_role = create_party_role(
        EntityRole.RoleTypes.proprietor, **create_test_user(first_name="TEST", last_name="USER")
    )
    proprietor_party_role.legal_entity_id = business.id
    proprietor_party_role.save()
    proprietor_party_role.party.middle_initial = None
    proprietor_party_role.party.save()
    assert is_self_registered_owner_operator(business, user) is True


def create_business(legal_type, state):
    """Create a business."""
    identifier = (f"BC{random.SystemRandom().getrandbits(0x58)}")[:9]
    legal_entity = factory_legal_entity(
        identifier=identifier, entity_type=legal_type, state=state, founding_date=_datetime.now()
    )
    return legal_entity


def create_incomplete_filing(
    legal_entity,
    filing_name,
    filing_status,
    filing_dict: dict = copy.deepcopy(ANNUAL_REPORT),
    filing_type=None,
    filing_sub_type=None,
    is_future_effective=False,
):
    """Create an incomplete filing of a given status."""
    filing_dict["filing"]["header"]["name"] = filing_name
    if filing_dict:
        filing_dict = copy.deepcopy(filing_dict)
    filing = factory_filing(
        legal_entity=legal_entity,
        data_dict=filing_dict,
        filing_sub_type=filing_sub_type,
        is_future_effective=is_future_effective,
    )
    filing.skip_status_listener = True
    filing._status = filing_status
    filing._filing_type = filing_type
    filing._filing_sub_type = filing_sub_type
    return filing


def create_filing(legal_entity, filing_type, filing_sub_type=None):
    """Create a state filing."""
    filing_key = filing_type
    if filing_sub_type:
        filing_key = f"{filing_type}.{filing_sub_type}"
    filing_dict = copy.deepcopy(FILING_DATA.get(filing_key, None))
    filing_dict["filing"]["header"]["name"] = filing_type
    if filing_sub_type:
        filing_sub_type_key = Filing.FILING_SUB_TYPE_KEYS.get(filing_type, None)
        filing_dict["filing"][filing_type][filing_sub_type_key] = filing_sub_type
    filing = factory_completed_filing(
        legal_entity=legal_entity, data_dict=filing_dict, filing_type=filing_type, filing_sub_type=filing_sub_type
    )
    return filing


def create_party_role(
    role_type=EntityRole.RoleTypes.completing_party, first_name=None, last_name=None, middle_initial=None
):
    completing_party_address = Address(city="Test Mailing City", address_type=Address.DELIVERY)
    officer = {
        "firstName": first_name or "TEST",
        "middleInitial": middle_initial or "TU",
        "lastName": last_name or "USER",
        "partyType": "person",
        "organizationName": "",
    }
    party_role = factory_party_role(completing_party_address, None, officer, _datetime.utcnow(), None, role_type)
    return party_role


def create_test_user(suffix=""):
    return {"first_name": f"TEST{suffix}", "last_name": f"USER{suffix}", "middle_initial": f"TU{suffix}"}


def create_test_user(first_name=None, last_name=None, middle_initial=None):  # noqa: F811
    return {"first_name": first_name, "last_name": last_name, "middle_initial": middle_initial}
