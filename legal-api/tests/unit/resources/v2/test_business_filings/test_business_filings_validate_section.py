# Copyright © 2026 Province of British Columbia
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

"""Tests for the validate-section resource endpoint."""

from http import HTTPStatus
from unittest.mock import patch

from legal_api.services.authz import PUBLIC_USER, STAFF_ROLE
from tests.unit.models import factory_business
from tests.unit.services.utils import create_header

ENDPOINT_PATH = "/api/v2/businesses/{identifier}/filings/validate-section"


def test_validate_sections_unauthorized(app, session, client, jwt):
    """Test 403 Forbidden when an unauthorized user attempts to validate."""
    identifier = "BC1234567"
    factory_business(identifier, entity_type="BC")

    with patch("legal_api.services.authorized", return_value=False):
        rv = client.post(
            ENDPOINT_PATH.format(identifier=identifier),
            headers=create_header(jwt, [PUBLIC_USER], identifier),
            json={
                "filingType": "correction",
                "section": "nameRequest",
                "data": {"legalName": "SAMPLE LTD."},
            },
        )

        assert rv.status_code == HTTPStatus.FORBIDDEN
        assert "Not Authorized" in rv.json.get("message", "")


def test_validate_sections_missing_required_params(app, session, client, jwt):
    """Test 400 Bad Request when filingType or section is missing."""
    identifier = "BC1234567"
    factory_business(identifier, entity_type="BC")

    headers = create_header(jwt, [STAFF_ROLE], identifier)

    with patch("legal_api.services.authorized", return_value=True):
        rv = client.post(
            ENDPOINT_PATH.format(identifier=identifier),
            headers=headers,
            json={
                "filingType": "correction",
                "data": {"legalName": "SAMPLE LTD."},
            },
        )
        assert rv.status_code == HTTPStatus.BAD_REQUEST
        assert "required" in rv.json.get("message", "")

        rv = client.post(
            ENDPOINT_PATH.format(identifier=identifier),
            headers=headers,
            json={
                "section": "nameRequest",
                "data": {"legalName": "SAMPLE LTD."},
            },
        )
        assert rv.status_code == HTTPStatus.BAD_REQUEST
        assert "required" in rv.json.get("message", "")


def test_validate_sections_unsupported_section(app, session, client, jwt):
    """Test 400 Bad Request when section or filingType has no validator registered."""
    identifier = "BC1234567"
    factory_business(identifier, entity_type="BC")

    with (patch("legal_api.services.authorized", return_value=True)):
        rv = client.post(
            ENDPOINT_PATH.format(identifier=identifier),
            headers=create_header(jwt, [STAFF_ROLE], identifier),
            json={
                "filingType": "unknownFiling",
                "section": "unknownSection",
                "data": {},
            },
        )

        assert rv.status_code == HTTPStatus.BAD_REQUEST
        assert "not supported" in rv.json.get("message", "")


def test_validate_sections_success_with_errors(app, session, client, jwt):
    """Test 200 OK with isValid=False when section data fails validation."""
    identifier = "BC1234567"
    business = factory_business(identifier, entity_type="BC")
    business.legal_name = "TEST SAMPLE LTD."
    session.add(business)
    session.commit()

    with patch("legal_api.services.authorized", return_value=True):
        rv = client.post(
            ENDPOINT_PATH.format(identifier=identifier),
            headers=create_header(jwt, [STAFF_ROLE], identifier),
            json={
                "filingType": "correction",
                "section": "nameRequest",
                "data": {"legalName": "MISMATCH CORP."},
            },
        )

        assert rv.status_code == HTTPStatus.OK
        assert rv.json["isValid"] is False
        assert len(rv.json["errors"]) > 0
        assert any("LTD." in err["error"] for err in rv.json["errors"])


def test_validate_sections_success_valid(app, session, client, jwt):
    """Test 200 OK with isValid=True when section data passes all checks."""
    identifier = "BC1234567"
    business = factory_business(identifier, entity_type="BC")
    business.legal_name = "TEST SAMPLE LTD."
    session.add(business)
    session.commit()

    with patch("legal_api.services.authorized", return_value=True):
        rv = client.post(
            ENDPOINT_PATH.format(identifier=identifier),
            headers=create_header(jwt, [STAFF_ROLE], identifier),
            json={
                "filingType": "correction",
                "section": "nameRequest",
                "data": {"legalName": "NEW SAMPLE LTD."},
            },
        )

        assert rv.status_code == HTTPStatus.OK
        assert rv.json["isValid"] is True
        assert rv.json["errors"] == []