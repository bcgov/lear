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

"""Tests to assure the business extended end-point.

Test-Suite to ensure that the /businesses../extended endpoint is working as expected.
"""
import copy
from http import HTTPStatus
import pytest

from business_model.models import Business, Jurisdiction
from business_model.utils.legislation_datetime import LegislationDatetime
from legal_api.services.authz import PUBLIC_USER, STAFF_ROLE
from registry_schemas.example_data import (
    AMALGAMATION_OUT,
    CONTINUATION_IN_FILING_TEMPLATE,
    CONTINUATION_OUT,
    FILING_HEADER,
)

from tests.unit.models import factory_business, factory_completed_filing
from tests.unit.services.utils import create_header


@pytest.mark.parametrize('filing_type', ["amalgamationOut", "continuationOut"])
def test_get_business_extended_out(app, session, client, jwt, filing_type):
    """Assert that business extended data is returned."""
    identifier = 'BC7654321'
    business = factory_business(identifier, entity_type='BC')
    continuation_out_filing = copy.deepcopy(FILING_HEADER)
    continuation_out_filing['filing'][filing_type] = copy.deepcopy(CONTINUATION_OUT if filing_type == 'continuationOut' else AMALGAMATION_OUT)
    continuation_out_filing['filing']['header']['name'] = filing_type

    filing = factory_completed_filing(business, continuation_out_filing)
    data = {
        'date': '2023-06-19',
        'country': 'CA',
        'region': 'AB',
        'legalName': 'HAULER SERVICES',
    }
    business.state = Business.State.HISTORICAL
    business.state_filing_id = filing.id
    business.jurisdiction = data["country"]
    business.foreign_jurisdiction_region = data["region"]
    business.foreign_legal_name = data["legalName"]
    if filing_type == 'continuationOut':
        business.continuation_out_date = LegislationDatetime.as_utc_timezone_from_legislation_date_str(data["date"])
    elif filing_type == 'amalgamationOut':
        business.amalgamation_out_date = LegislationDatetime.as_utc_timezone_from_legislation_date_str(data["date"])
    business.save()

    rv = client.get(f'/api/v2/businesses/{identifier}/extended/{filing_type}',
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )

    assert rv.status_code == HTTPStatus.OK
    assert filing_type in rv.json
    assert rv.json[filing_type] == data


def test_get_business_extended_in(app, session, client, jwt):
    """Assert that business continuation in data is returned."""
    identifier = 'C7654321'
    business = factory_business(identifier, entity_type='C')
    filing_type = "continuationIn"
    filing = factory_completed_filing(business, CONTINUATION_IN_FILING_TEMPLATE)
    data = {
        'country': 'CA',
        'region': 'AB',
        'legalName': 'HAULER SERVICES',
        'identifier': 'AB1234567',
        'incorporationDate': '2020-01-01',
        'xpro': {
            'identifier': 'A0077779',
            'legalName': 'Test Company Inc.'
        }
    }
    jurisdiction = Jurisdiction(
        filing_id = filing.id,
        country=data['country'],
        region=data['region'],
        identifier=data['identifier'],
        legal_name=data['legalName'],
        incorporation_date=LegislationDatetime.as_utc_timezone_from_legislation_date_str(data['incorporationDate']),
        expro_identifier=data['xpro']['identifier'],
        expro_legal_name=data['xpro']['legalName']
    )
    business.jurisdictions.append(jurisdiction)
    business.save()

    rv = client.get(f'/api/v2/businesses/{identifier}/extended/{filing_type}',
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )

    assert rv.status_code == HTTPStatus.OK
    assert filing_type in rv.json
    assert rv.json[filing_type] == data


def test_get_business_extended_bad_request(app, session, client, jwt):
    """Assert that 400 is returned if filing type does not support."""
    identifier = 'BC7654321'
    filing_type = 'incorporationApplication'
    business = factory_business(identifier)

    rv = client.get(f'/api/v2/businesses/{identifier}/extended/{filing_type}',
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )

    assert rv.status_code == HTTPStatus.BAD_REQUEST
    assert rv.json == {'message': f'{filing_type} not supported'}


@pytest.mark.parametrize('filing_type', ["continuationIn", "amalgamationOut", "continuationOut"])
def test_get_business_extended_not_found(app, session, client, jwt, filing_type):
    """Assert that 404 is returned if business is not found."""
    identifier = 'BC7654321'
    business = factory_business(identifier)

    rv = client.get(f'/api/v2/businesses/{identifier}/extended/{filing_type}',
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )

    assert rv.status_code == HTTPStatus.NOT_FOUND
    assert rv.json == {'message': f"Could not find {filing_type} data for {identifier}"}
