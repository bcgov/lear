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

from business_model.models import Amalgamation, AmalgamatingBusiness, Business, Jurisdiction
from business_model.utils.legislation_datetime import LegislationDatetime
from legal_api.services.authz import PUBLIC_USER, STAFF_ROLE
from registry_schemas.example_data import (
    AMALGAMATION_APPLICATION,
    AMALGAMATION_OUT,
    CONTINUATION_IN,
    CONTINUATION_OUT,
    INCORPORATION,
    FILING_HEADER,
)

from tests.unit.models import factory_business, factory_business_mailing_address, factory_completed_filing
from tests.unit.services.utils import create_header


@pytest.mark.parametrize('legal_type, filing_type, dependent_filing_type', [
    ("C", "continuationIn", None),
    ("BC", "amalgamationApplication", None),
    ("BC", "amalgamationOut", None),
    ("BC", "continuationOut", None),
    ("C", "amalgamationOut", "continuationIn"),
    ("C", "continuationOut", "continuationIn"),
    ("BC", "amalgamationOut", "amalgamationApplication"),
    ("BC", "continuationOut", "amalgamationApplication")
])
def test_get_business_extended_without_filing_type(app, session, client, jwt, legal_type, filing_type, dependent_filing_type):
    """Assert that business extended data is returned."""
    identifier = 'BC7654321' if legal_type == 'BC' else 'C7654321'
    business = factory_business(identifier, entity_type=legal_type)
    data = {}
    if "continuationIn" in (dependent_filing_type, filing_type):
        data["continuationIn"] = _create_continuation_in_business(business)
    
    if "amalgamationApplication" in (dependent_filing_type, filing_type):
        data["amalgamation"] = _create_amalgation_business(business, True)
    
    if "continuationOut" == filing_type:
        data["continuationOut"] = _create_out_business(business, "continuationOut")
    elif "amalgamationOut" == filing_type:
        data["amalgamationOut"] = _create_out_business(business, "amalgamationOut")
        

    rv = client.get(f'/api/v2/businesses/{identifier}/extended?forCorrection=true',
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )

    assert rv.status_code == HTTPStatus.OK
    assert rv.json == data


@pytest.mark.parametrize('filing_type', ["amalgamationOut", "continuationOut"])
def test_get_business_extended_out(app, session, client, jwt, filing_type):
    """Assert that business extended data is returned."""
    identifier = 'BC7654321'
    business = factory_business(identifier, entity_type='BC')
    data = _create_out_business(business, filing_type)

    rv = client.get(f'/api/v2/businesses/{identifier}/extended/{filing_type}',
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )

    assert rv.status_code == HTTPStatus.OK
    assert rv.json[filing_type] == data


def test_get_business_extended_in(app, session, client, jwt):
    """Assert that business continuation in data is returned."""
    identifier = 'C7654321'
    filing_type = "continuationIn"
    business = factory_business(identifier, entity_type='C')
    data = _create_continuation_in_business(business)
    rv = client.get(f'/api/v2/businesses/{identifier}/extended/{filing_type}',
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )

    assert rv.status_code == HTTPStatus.OK
    assert rv.json[filing_type] == data


@pytest.mark.parametrize('for_correction', [True, False])
def test_get_business_extended_amalgamation(app, session, client, jwt, for_correction):
    """Assert that business amalgamation data is returned."""
    identifier = 'BC7654321'
    business = factory_business(identifier, entity_type='BC')
    data = _create_amalgation_business(business, for_correction)
    query_string = f'?forCorrection={for_correction}' if for_correction else ''
    rv = client.get(f'/api/v2/businesses/{identifier}/extended/amalgamationApplication{query_string}',
                    headers=create_header(jwt, [STAFF_ROLE], identifier)
                    )

    assert rv.status_code == HTTPStatus.OK
    assert rv.json['amalgamation'] == data


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


def _create_out_business(business, filing_type):
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
    return data


def _create_continuation_in_business(business):
    filing_type = "continuationIn"
    filing_json = copy.deepcopy(FILING_HEADER)
    filing_json['filing'][filing_type] = copy.deepcopy(CONTINUATION_IN)
    filing_json['filing']['header']['name'] = filing_type

    filing = factory_completed_filing(business, filing_json)
    data = {
        'country': 'CA',
        'region': 'AB',
        'legalName': 'HAULER SERVICES',
        'identifier': 'AB1234567',
        'incorporationDate': '2020-01-01',
        'expro': {
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
        expro_identifier=data['expro']['identifier'],
        expro_legal_name=data['expro']['legalName']
    )
    business.jurisdictions.append(jurisdiction)
    business.save()
    return data


def _create_amalgation_business(business, for_correction=False):
    amalgamating_identifier = 'BC1234567'
    amalgamating_business = factory_business(amalgamating_identifier, entity_type='BC')
    factory_business_mailing_address(amalgamating_business)
    filing_type = "amalgamationApplication"
    filing_json = copy.deepcopy(FILING_HEADER)
    filing_json['filing'][filing_type] = copy.deepcopy(AMALGAMATION_APPLICATION)
    filing_json['filing']['header']['name'] = filing_type

    filing = factory_completed_filing(business, filing_json)
    amalgamating_business_json = [
        {
            'role': 'amalgamating',
            'identifier': amalgamating_identifier
        },
        {
            'role': 'amalgamating',
            'foreignJurisdiction': {
                'country': 'CA',
                'region': 'AB',
            },
            'legalName': 'HAULER SERVICES',
            'identifier': 'AB1234567'
        }
    ]
    if for_correction:
        amalgamating_business_json[0]['legalName'] = amalgamating_business.legal_name
        amalgamating_business_json[0]['legalType'] = amalgamating_business.legal_type
        amalgamating_business_json[0]['mailingAddress'] = amalgamating_business.mailing_address.one_or_none().json

    data = {
        'courtApproval': False,
        'amalgamatingBusinesses':amalgamating_business_json
    }
    amalgamation = Amalgamation(
        amalgamation_type=Amalgamation.AmalgamationTypes.regular,
        amalgamation_date=LegislationDatetime.now(),
        court_approval=False,
        filing_id=filing.id,
        business_id=business.id,
    )
    amalgamation.save()

    ting1 = AmalgamatingBusiness(
        role=AmalgamatingBusiness.Role.amalgamating,
        business_id=amalgamating_business.id,
        amalgamation_id=amalgamation.id
    )
    ting1.save()
    amalgamating_business_json[0]['id'] = ting1.id

    ting2 = AmalgamatingBusiness(
        role=AmalgamatingBusiness.Role.amalgamating,
        foreign_jurisdiction=amalgamating_business_json[1]['foreignJurisdiction']['country'],
        foreign_jurisdiction_region=amalgamating_business_json[1]['foreignJurisdiction']['region'],
        foreign_name=amalgamating_business_json[1]['legalName'],
        foreign_identifier=amalgamating_business_json[1]['identifier'],
        amalgamation_id=amalgamation.id
    )
    ting2.save()
    amalgamating_business_json[1]['id'] = ting2.id

    return data
