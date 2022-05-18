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
"""The Test Suites to ensure that the change of registration is operating correctly."""
import xml.etree.ElementTree as Et

import pytest
from entity_queue_common.service_utils import QueueException
from legal_api.models import RequestTracker

from entity_bn.exceptions import BNException
from entity_bn.worker import process_event
from tests.unit import create_filing, create_registration_data


@pytest.mark.parametrize('legal_type', [
    ('SP'),
    ('GP'),
])
async def test_change_of_registration(app, session, mocker, legal_type):
    """Test inform cra about change of SP/GP registration."""
    filing_id, business_id = create_registration_data(legal_type, tax_id='993775204BC0001')
    json_filing = {
        'filing': {
            'header': {
                'name': 'changeOfRegistration'
            },
            'changeOfRegistration': {
                'offices': {
                    'businessOffice': {
                        'mailingAddress': {},
                        'deliveryAddress': {}
                    }
                }
            }
        }
    }
    filing = create_filing(json_filing=json_filing, business_id=business_id)
    filing._meta_data = {'changeOfRegistration': {'toLegalName': 'new name'}}
    filing.save()
    filing_id = filing.id

    acknowledgement_response = """<?xml version="1.0"?>
        <SBNAcknowledgement>
            <header></header>
            <body>A Valid Document Type was received.</body>
        </SBNAcknowledgement>"""

    def side_effect(input_xml):
        root = Et.fromstring(input_xml)
        if root.tag == 'SBNChangeName':
            return 200, acknowledgement_response
        elif root.tag == 'SBNChangeAddress':
            return 200, acknowledgement_response

    mocker.patch('entity_bn.bn_processors.change_of_registration.request_bn_hub', side_effect=side_effect)
    mocker.patch('entity_bn.bn_processors.change_of_registration.has_previous_address', return_value=True)

    await process_event({
        'type': 'bc.registry.business.changeOfRegistration',
        'data': {
            'filing': {
                'header': {'filingId': filing_id}
            }
        }
    }, app)

    request_trackers = RequestTracker.find_by(business_id,
                                              RequestTracker.ServiceName.BN_HUB,
                                              RequestTracker.RequestType.CHANGE_NAME,
                                              filing_id=filing_id)
    assert request_trackers
    assert len(request_trackers) == 1
    assert request_trackers[0].is_processed
    assert request_trackers[0].retry_number == 0

    request_trackers = RequestTracker.find_by(business_id,
                                              RequestTracker.ServiceName.BN_HUB,
                                              RequestTracker.RequestType.CHANGE_DELIVERY_ADDRESS,
                                              filing_id=filing_id)
    assert request_trackers
    assert len(request_trackers) == 1
    assert request_trackers[0].is_processed
    assert request_trackers[0].retry_number == 0

    request_trackers = RequestTracker.find_by(business_id,
                                              RequestTracker.ServiceName.BN_HUB,
                                              RequestTracker.RequestType.CHANGE_MAILING_ADDRESS,
                                              filing_id=filing_id)
    assert request_trackers
    assert len(request_trackers) == 1
    assert request_trackers[0].is_processed
    assert request_trackers[0].retry_number == 0


@pytest.mark.parametrize('request_type, data', [
    (RequestTracker.RequestType.CHANGE_NAME, {'nameRequest': {'legalName': 'new name'}}),
    (RequestTracker.RequestType.CHANGE_DELIVERY_ADDRESS, {'offices': {'businessOffice': {'mailingAddress': {},
                                                                                         'deliveryAddress': {}}}}),
    (RequestTracker.RequestType.CHANGE_MAILING_ADDRESS, {'offices': {'businessOffice': {'mailingAddress': {},
                                                                                        'deliveryAddress': {}}}}),
])
async def test_retry_registration(app, session, mocker, request_type, data):
    """Test retry change of SP/GP registration."""
    filing_id, business_id = create_registration_data('SP', tax_id='993775204BC0001')
    json_filing = {
        'filing': {
            'header': {
                'name': 'changeOfRegistration'
            },
            'changeOfRegistration': {}
        }
    }
    json_filing['filing']['changeOfRegistration'] = data
    filing = create_filing(json_filing=json_filing, business_id=business_id)
    if request_type == RequestTracker.RequestType.CHANGE_NAME:
        filing._meta_data = {'changeOfRegistration': {'toLegalName': 'new name'}}
    filing.save()
    filing_id = filing.id

    mocker.patch('entity_bn.bn_processors.change_of_registration.request_bn_hub', return_value=(500, ''))

    def side_effect(transaction_id, office_id, address_type):
        if address_type in request_type.name.lower():
            return True
        return False

    mocker.patch('entity_bn.bn_processors.change_of_registration.has_previous_address', side_effect=side_effect)

    for _ in range(10):
        try:
            await process_event({
                'type': 'bc.registry.business.changeOfRegistration',
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

    request_trackers = RequestTracker.find_by(business_id, RequestTracker.ServiceName.BN_HUB,
                                              request_type, filing_id=filing_id)
    assert request_trackers
    assert len(request_trackers) == 1
    assert request_trackers[0].is_processed is False
    assert request_trackers[0].retry_number == 9
