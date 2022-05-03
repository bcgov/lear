# Copyright © 2022 Province of British Columbia
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
"""The Test Suites to ensure that the registration is operating correctly."""
import copy
import pytest
import xml.etree.ElementTree as Et

from entity_queue_common.service_utils import QueueException
from legal_api.models import Business, RequestTracker
from entity_bn.exceptions import BNException

from entity_bn.worker import process_event
from tests import MockResponse
from tests.unit import create_business, create_filing, create_party, create_party_role


person_json = {
    'officer': {
        'id': 2,
        'firstName': 'Peter',
        'lastName': 'Griffin',
        'middleName': '',
        'partyType': 'person'
    },
    'mailingAddress': {
        'streetAddress': 'mailing_address - address line one',
        'streetAddressAdditional': '',
        'addressCity': 'mailing_address city',
        'addressCountry': 'CA',
        'postalCode': 'H0H0H0',
        'addressRegion': 'BC'
    }
}

org_json = copy.deepcopy(person_json)
org_json['officer'] = {
    'id': 2,
    'organizationName': 'Xyz Inc.',
    'identifier': 'BC1234567',
    'taxId': '123456789',
    'email': 'peter@email.com',
    'partyType': 'organization'
}


def create_data(legal_type, identifier='FM1234567'):
    """Test data for registration."""
    business = create_business(identifier, legal_type=legal_type, legal_name='test-reg-' + legal_type)
    json_filing = {
        'filing': {
            'header': {
                'name': 'registration'
            },
            'registration': {

            }
        }
    }
    filing = create_filing(json_filing=json_filing, business_id=business.id)
    party = create_party(person_json if legal_type == 'SP' else org_json)
    role = 'proprietor' if legal_type == 'SP' else 'partner'
    create_party_role(business, party, [role])
    business.save()
    return filing.id, business.id


@pytest.mark.parametrize('legal_type', [
    ('SP'),
    ('GP'),
])
async def test_registration(app, session, mocker, legal_type):
    """Test inform cra about new SP/GP registration."""
    filing_id, business_id = create_data(legal_type)
    business_number = '993775204'
    acknowledgement_response = """<?xml version="1.0"?>
        <SBNAcknowledgement>
            <header></header>
            <body>A Valid SBNCreateProgramAccountRequest Document Type was received.</body>
        </SBNAcknowledgement>"""
    search_response = f"""<?xml version="1.0"?>
        <SBNClientBasicInformationSearchResponse>
            <body>
                <clientBasicInformationSearchResult>
                    <businessRegistrationNumber>{business_number}</businessRegistrationNumber>
                </clientBasicInformationSearchResult>
            </body>
        </SBNClientBasicInformationSearchResponse>"""

    def side_effect(input_xml):
        root = Et.fromstring(input_xml)
        if root.tag == 'SBNCreateProgramAccountRequest':
            return MockResponse(200, text=acknowledgement_response)
        elif root.tag == 'SBNClientBasicInformationSearchRequest':
            return MockResponse(200, text=search_response)

    mocker.patch('entity_bn.bn_processors.registration._request_bn', side_effect=side_effect)

    await process_event({
        'type': 'bc.registry.business.registration',
        'data': {
            'filing': {
                'header': {'filingId': filing_id}
            }
        }
    }, app)

    request_trackers = RequestTracker.find_by(business_id,
                                              RequestTracker.ServiceName.BN_HUB,
                                              RequestTracker.RequestType.INFORM_CRA)
    assert request_trackers
    assert len(request_trackers) == 1
    assert request_trackers[0].is_processed
    assert request_trackers[0].retry_number == 0

    request_trackers = RequestTracker.find_by(business_id,
                                              RequestTracker.ServiceName.BN_HUB,
                                              RequestTracker.RequestType.GET_BN)
    assert request_trackers
    assert len(request_trackers) == 1
    assert request_trackers[0].is_processed
    assert request_trackers[0].retry_number == 0

    business = Business.find_by_internal_id(business_id)
    assert business.tax_id == business_number


@pytest.mark.parametrize('request_type', [
    (RequestTracker.RequestType.INFORM_CRA),
    (RequestTracker.RequestType.GET_BN),
])
async def test_retry_registration(app, session, mocker, request_type):
    """Test retry new SP/GP registration."""
    is_inform_cra = request_type == RequestTracker.RequestType.INFORM_CRA
    filing_id, business_id = create_data('SP')
    acknowledgement_response = """<?xml version="1.0"?>
        <SBNAcknowledgement>
            <header></header>
            <body>A Valid SBNCreateProgramAccountRequest Document Type was received.</body>
        </SBNAcknowledgement>"""

    def side_effect(input_xml):
        root = Et.fromstring(input_xml)
        if root.tag == 'SBNCreateProgramAccountRequest':
            return MockResponse(
                200,
                text='' if is_inform_cra else acknowledgement_response
            )
        elif root.tag == 'SBNClientBasicInformationSearchRequest':
            return MockResponse(200, text='')

    mocker.patch('entity_bn.bn_processors.registration._request_bn', side_effect=side_effect)

    for _ in range(10):
        try:
            await process_event({
                'type': 'bc.registry.business.registration',
                'data': {
                    'filing': {
                        'header': {'filingId': filing_id}
                    }
                }
            }, app)

        except BNException:
            continue
        except QueueException:
            break

    request_trackers = RequestTracker.find_by(business_id,
                                              RequestTracker.ServiceName.BN_HUB,
                                              RequestTracker.RequestType.INFORM_CRA)
    assert request_trackers
    assert len(request_trackers) == 1
    assert request_trackers[0].is_processed is (False if is_inform_cra else True)
    assert request_trackers[0].retry_number == (9 if is_inform_cra else 0)

    request_trackers = RequestTracker.find_by(business_id,
                                              RequestTracker.ServiceName.BN_HUB,
                                              RequestTracker.RequestType.GET_BN)

    if is_inform_cra:
        assert not request_trackers
    else:
        assert len(request_trackers) == 1
        assert request_trackers[0].is_processed is False
        assert request_trackers[0].retry_number == 9
