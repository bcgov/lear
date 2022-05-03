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
import xml.etree.ElementTree as Et

from legal_api.models import Business, RequestTracker

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


async def test_registration(app, session, mocker):
    """Test inform cra about new SP/GP registration."""
    identifier = 'FM1234567'
    business = create_business(identifier, legal_type='SP', legal_name='test-reg')
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
    party = create_party(person_json)
    create_party_role(business, party, ['proprietor'])
    business.save()
    business_id = business.id
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
                'header': {'filingId': filing.id}
            }
        }
    }, app)

    request_trackers = RequestTracker.find_by(business_id,
                                              RequestTracker.ServiceName.BN_HUB,
                                              RequestTracker.RequestType.INFORM_CRA)
    assert request_trackers
    assert len(request_trackers) == 1
    assert request_trackers[0].is_processed

    request_trackers = RequestTracker.find_by(business_id,
                                              RequestTracker.ServiceName.BN_HUB,
                                              RequestTracker.RequestType.GET_BN)
    assert request_trackers
    assert len(request_trackers) == 1
    assert request_trackers[0].is_processed

    business = Business.find_by_internal_id(business_id)
    assert business.tax_id == business_number
