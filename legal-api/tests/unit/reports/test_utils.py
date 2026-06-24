# Copyright (c) 2026, Province of British Columbia

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.

# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.

# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""Test-Suite to ensure that the Report utils are working as expected."""
from http import HTTPStatus
from unittest.mock import MagicMock

import pytest

from legal_api.exceptions import BusinessException
from legal_api.reports.utils import ColinService, get_amalg_formatted_jurisdiction, get_formatted_amalg_business_data


@pytest.mark.parametrize(
    'test_name, identifier, country_code, region_code, expected',
    [
        ('ca-bc-province', 'BC1234567', 'CA', 'BC', 'British Columbia'),
        ('ca-on-province', 'BC1234567', 'CA', 'ON', 'Ontario'),
        ('ca-federal-uppercase', 'BC1234567', 'CA', 'FEDERAL', 'Federal'),
        ('ca-federal-lowercase', 'BC1234567', 'CA', 'federal', 'Federal'),
        ('ca-federal-mixedcase', 'BC1234567', 'CA', 'Federal', 'Federal'),
        # Region code 'FD' is how COLIN stores the Federal jurisdiction (LEAR uses 'FEDERAL').
        # Both must resolve to "Federal" (we are getting the jurisdiction from colin for expros).
        ('ca-fd-uppercase', 'A1234567', 'CA', 'FD', 'Federal'),
        ('ca-fd-lowercase', 'A1234567', 'CA', 'fd', 'Federal'),
        ('ca-fd-mixedcase', 'A1234567', 'CA', 'Fd', 'Federal'),
        ('us-with-region', 'BC1234567', 'US', 'WA', 'United States'),
        ('us-no-region', 'BC1234567', 'US', None, 'United States'),
        ('gb-no-region', 'BC1234567', 'GB', None, 'United Kingdom'),
        ('ca-invalid-region-falls-back-to-country', 'BC1234567', 'CA', 'ZZ', 'Canada'),
    ],
)
def test_get_amalg_formatted_jurisdiction_happy_paths(
        app, test_name, identifier, country_code, region_code, expected):
    """Assert that the correct jurisdiction label is returned for valid country and region inputs."""
    with app.app_context():
        result = get_amalg_formatted_jurisdiction(identifier, country_code, region_code)

    assert result == expected


@pytest.mark.parametrize(
    'test_name, identifier, country_code, region_code',
    [
        ('ca-region-none-triggers-attribute-error', 'BC1234567', 'CA', None),
        ('unknown-country-code', 'BC1234567', 'XX', None),
        ('empty-country-code', 'BC1234567', None, None),
    ],
)
def test_get_amalg_formatted_jurisdiction_error_paths(
        app, test_name, identifier, country_code, region_code):
    """Assert that N/A is returned and no exception is raised when an AttributeError occurs internally."""
    with app.app_context():
        result = get_amalg_formatted_jurisdiction(identifier, country_code, region_code)

    assert result == 'N/A'


# ---------------------------------------------------------------------------
# Tests for get_formatted_amalg_business_data
# ---------------------------------------------------------------------------

def _make_ting_business(identifier='BC1234567', legal_name='Ting Corp Ltd.'):
    """Return a lightweight mock that behaves like a versioned Business object."""
    ting = MagicMock()
    ting._identifier = identifier  # pylint: disable=protected-access
    ting.legal_name = legal_name
    return ting


def _make_colin_response(status_code, jurisdiction=None):
    """Return a mock HTTP response imitating a ColinService.query_business result."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = {'business': {'jurisdiction': jurisdiction}}
    return resp


@pytest.mark.parametrize('test_name, identifier, foreign_name, country_code, region_code, expected_id, expected_name, expected_jurisdiction', [
    ('us-foreign-non-expro', 'UK1234567', 'Foreign Corp USA', 'US', 'WA', 'N/A', 'Foreign Corp USA', 'United States'),
    ('gb-foreign-non-expro', 'GB9999999', 'British Co', 'GB', None, 'N/A', 'British Co', 'United Kingdom'),
    ('ca-on-foreign-non-expro', 'ON1234567', 'Ontario Corp', 'CA', 'ON', 'N/A', 'Ontario Corp', 'Ontario'),
], ids=[
    'foreign non-expro US',
    'foreign non-expro GB',
    'foreign non-expro CA-ON',
])
def test_get_formatted_amalg_business_data_foreign_non_expro(
        app, monkeypatch, test_name, identifier, foreign_name, country_code, region_code,
        expected_id, expected_name, expected_jurisdiction):
    """Assert that a foreign non-expro business returns N/A identifier and correct jurisdiction without calling COLIN."""
    colin_call_count = {'count': 0}

    def mock_colin(id_):
        colin_call_count['count'] += 1
        return _make_colin_response(HTTPStatus.OK)

    monkeypatch.setattr(ColinService, 'query_business', mock_colin)

    with app.app_context():
        result = get_formatted_amalg_business_data(
            identifier=identifier,
            foreign_name=foreign_name,
            foreign_country_code=country_code,
            foreign_region_code=region_code,
        )

    assert result['identifier'] == expected_id
    assert result['legalName'] == expected_name
    assert result['jurisdiction'] == expected_jurisdiction
    # COLIN must NOT be called for identifiers that do not start with 'A'
    assert colin_call_count['count'] == 0


@pytest.mark.parametrize('test_name, colin_jurisdiction, expected_id, expected_jurisdiction', [
    ('expro-on-province', 'ON', 'A1234567', 'Ontario'),
    ('expro-federal', 'FD', 'A1234567', 'Federal'),
    ('expro-no-jurisdiction-in-colin', None, 'A1234567', 'N/A'),
], ids=[
    'expro ON province',
    'expro FD federal',
    'expro no jurisdiction in colin',
])
def test_get_formatted_amalg_business_data_foreign_expro_colin_200(
        app, monkeypatch, test_name, colin_jurisdiction, expected_id, expected_jurisdiction):
    """Assert that a foreign business whose identifier starts with A and COLIN returns 200 is treated as an expro."""
    foreign_identifier = 'A1234567'
    foreign_name = 'Expro Corp'
    colin_call_count = {'count': 0}

    def mock_colin(id_):
        colin_call_count['count'] += 1
        return _make_colin_response(HTTPStatus.OK, jurisdiction=colin_jurisdiction)

    monkeypatch.setattr(ColinService, 'query_business', mock_colin)

    with app.app_context():
        result = get_formatted_amalg_business_data(
            identifier=foreign_identifier,
            foreign_name=foreign_name,
            foreign_country_code='CA',
            foreign_region_code='BC',
        )

    assert result['identifier'] == expected_id
    assert result['legalName'] == foreign_name
    assert result['jurisdiction'] == expected_jurisdiction
    assert colin_call_count['count'] == 1


def test_get_formatted_amalg_business_data_foreign_a_prefix_colin_non_200(app, monkeypatch):
    """Assert that a foreign A-prefix business where COLIN returns non-200 keeps N/A identifier and original jurisdiction."""
    foreign_identifier = 'A1234567'
    foreign_name = 'Would-be Expro Corp'
    colin_call_count = {'count': 0}

    def mock_colin(id_):
        colin_call_count['count'] += 1
        return _make_colin_response(HTTPStatus.NOT_FOUND)

    monkeypatch.setattr(ColinService, 'query_business', mock_colin)

    with app.app_context():
        result = get_formatted_amalg_business_data(
            identifier=foreign_identifier,
            foreign_name=foreign_name,
            foreign_country_code='US',
            foreign_region_code='WA',
        )

    assert result['identifier'] == 'N/A'
    assert result['legalName'] == foreign_name
    assert result['jurisdiction'] == 'United States'
    assert colin_call_count['count'] == 1


def test_get_formatted_amalg_business_data_bc_business_with_ting(app):
    """Assert that a domestic BC business returns the ting_business identifier, legal name, and BC jurisdiction."""
    ting = _make_ting_business(identifier='BC9876543', legal_name='Ting Corp Ltd.')

    with app.app_context():
        result = get_formatted_amalg_business_data(
            identifier=None,
            foreign_name=None,
            foreign_country_code=None,
            foreign_region_code=None,
            ting_business=ting,
        )

    assert result['identifier'] == 'BC9876543'
    assert result['legalName'] == 'Ting Corp Ltd.'
    assert result['jurisdiction'] == 'British Columbia'


def test_get_formatted_amalg_business_data_raises_when_no_foreign_name_and_no_ting(app):
    """Assert that BusinessException with UNPROCESSABLE_ENTITY is raised when neither foreign_name nor ting_business is provided."""
    with app.app_context():
        with pytest.raises(BusinessException) as exc_info:
            get_formatted_amalg_business_data(
                identifier='BC1234567',
                foreign_name=None,
                foreign_country_code=None,
                foreign_region_code=None,
                ting_business=None,
            )

    assert exc_info.value.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_get_formatted_amalg_business_data_foreign_no_identifier_skips_colin(app, monkeypatch):
    """Assert that a foreign business with no identifier does not call COLIN and returns N/A identifier."""
    colin_called = {'called': False}

    def mock_colin(id_):
        colin_called['called'] = True
        return _make_colin_response(HTTPStatus.OK)

    monkeypatch.setattr(ColinService, 'query_business', mock_colin)

    with app.app_context():
        result = get_formatted_amalg_business_data(
            identifier=None,
            foreign_name='No ID Foreign Corp',
            foreign_country_code='US',
            foreign_region_code='WA',
        )

    assert result['identifier'] == 'N/A'
    assert result['legalName'] == 'No ID Foreign Corp'
    assert not colin_called['called']
