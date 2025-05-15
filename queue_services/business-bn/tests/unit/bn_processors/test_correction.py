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
"""The Test Suites to ensure that the correction of registration or change of registration is operating correctly."""
import xml.etree.ElementTree as Et

import pytest
from simple_cloudevent import SimpleCloudEvent
from business_model.models import RequestTracker

from business_bn.bn_processors import bn_note
from business_bn.exceptions import BNException, BNRetryExceededException
from business_bn.resources.business_bn import process_event
from tests.unit import create_filing, create_registration_data


@pytest.mark.parametrize('legal_type', [
    ('SP'),
    ('GP'),
])
def test_correction(app, session, mocker, legal_type):
    """Test inform cra about correction of SP/GP."""
    filing_id, business_id = create_registration_data(legal_type, tax_id='993775204BC0001')
    json_filing = {
        'filing': {
            'header': {
                'name': 'correction'
            },
            'correction': {
                'offices': {
                    'businessOffice': {
                        'mailingAddress': {},
                        'deliveryAddress': {}
                    }
                },
                'parties': [{}]
            }
        }
    }
    filing = create_filing(json_filing=json_filing, business_id=business_id)
    filing._meta_data = {'correction': {'toLegalName': 'new name'}}
    filing.save()
    filing_id = filing.id

    acknowledgement_response = """<?xml version="1.0"?>
        <SBNAcknowledgement>
            <header></header>
            <body>A Valid Document Type was received.</body>
        </SBNAcknowledgement>"""

    def side_effect(input_xml):
        root = Et.fromstring(input_xml)
        if root.tag in ['SBNChangeName', 'SBNChangeAddress']:
            return 200, acknowledgement_response

    mocker.patch('business_bn.bn_processors.change_of_registration.request_bn_hub', side_effect=side_effect)
    mocker.patch('business_bn.bn_processors.correction.has_previous_address', return_value=True)
    mocker.patch('business_bn.bn_processors.correction.has_party_name_changed', return_value=True)

    process_event(
        SimpleCloudEvent(
            type = 'bc.registry.business.correction',
            data = {
                'filing': {
                    'header': {'filingId': filing_id}
                }
            }
        )
    )

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
                                              RequestTracker.RequestType.CHANGE_PARTY,
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


@pytest.mark.parametrize('legal_type, tax_id', [
    ('SP', None),
    ('SP', ''),
    ('SP', '993775204'),
    ('GP', None),
    ('GP', ''),
    ('GP', '993775204'),
])
def test_bn15_not_available_correction(app, session, mocker, legal_type, tax_id):
    """Skip cra call when BN15 is not available while doing a correction of SP/GP."""
    filing_id, business_id = create_registration_data(legal_type, tax_id=tax_id)
    json_filing = {
        'filing': {
            'header': {
                'name': 'correction'
            },
            'correction': {
                'offices': {
                    'businessOffice': {
                        'mailingAddress': {},
                        'deliveryAddress': {}
                    }
                },
                'parties': [{}]
            }
        }
    }
    filing = create_filing(json_filing=json_filing, business_id=business_id)
    filing._meta_data = {'correction': {'toLegalName': 'new name'}}
    filing.save()
    filing_id = filing.id

    mocker.patch('business_bn.bn_processors.correction.has_previous_address', return_value=True)
    mocker.patch('business_bn.bn_processors.correction.has_party_name_changed', return_value=True)

    process_event(
        SimpleCloudEvent(
            type = 'bc.registry.business.correction',
            data = {
                'filing': {
                    'header': {'filingId': filing_id}
                }
            }
        )
    )

    request_trackers = RequestTracker.find_by(business_id,
                                              RequestTracker.ServiceName.BN_HUB,
                                              RequestTracker.RequestType.CHANGE_NAME,
                                              filing_id=filing_id)
    assert request_trackers
    assert len(request_trackers) == 1
    assert not request_trackers[0].is_processed
    assert request_trackers[0].response_object == bn_note
    assert request_trackers[0].retry_number == 0

    request_trackers = RequestTracker.find_by(business_id,
                                              RequestTracker.ServiceName.BN_HUB,
                                              RequestTracker.RequestType.CHANGE_PARTY,
                                              filing_id=filing_id)
    assert request_trackers
    assert len(request_trackers) == 1
    assert not request_trackers[0].is_processed
    assert request_trackers[0].response_object == bn_note
    assert request_trackers[0].retry_number == 0

    request_trackers = RequestTracker.find_by(business_id,
                                              RequestTracker.ServiceName.BN_HUB,
                                              RequestTracker.RequestType.CHANGE_DELIVERY_ADDRESS,
                                              filing_id=filing_id)
    assert request_trackers
    assert len(request_trackers) == 1
    assert not request_trackers[0].is_processed
    assert request_trackers[0].response_object == bn_note
    assert request_trackers[0].retry_number == 0

    request_trackers = RequestTracker.find_by(business_id,
                                              RequestTracker.ServiceName.BN_HUB,
                                              RequestTracker.RequestType.CHANGE_MAILING_ADDRESS,
                                              filing_id=filing_id)
    assert request_trackers
    assert len(request_trackers) == 1
    assert not request_trackers[0].is_processed
    assert request_trackers[0].response_object == bn_note
    assert request_trackers[0].retry_number == 0


@pytest.mark.parametrize('request_type, data', [
    (RequestTracker.RequestType.CHANGE_NAME, {'nameRequest': {'legalName': 'new name'}}),
    (RequestTracker.RequestType.CHANGE_PARTY, {'parties': [{}]}),
    (RequestTracker.RequestType.CHANGE_DELIVERY_ADDRESS, {'offices': {'businessOffice': {'mailingAddress': {},
                                                                                         'deliveryAddress': {}}}}),
    (RequestTracker.RequestType.CHANGE_MAILING_ADDRESS, {'offices': {'businessOffice': {'mailingAddress': {},
                                                                                        'deliveryAddress': {}}}}),
])
def test_retry_correction(app, session, mocker, request_type, data):
    """Test retry correction of SP/GP."""
    filing_id, business_id = create_registration_data('SP', tax_id='993775204BC0001')
    json_filing = {
        'filing': {
            'header': {
                'name': 'correction'
            },
            'correction': {}
        }
    }
    json_filing['filing']['correction'] = data
    filing = create_filing(json_filing=json_filing, business_id=business_id)
    if request_type == RequestTracker.RequestType.CHANGE_NAME:
        filing._meta_data = {'correction': {'toLegalName': 'new name'}}
    filing.save()
    filing_id = filing.id

    mocker.patch('business_bn.bn_processors.change_of_registration.request_bn_hub', return_value=(500, ''))

    def side_effect(transaction_id, office_id, address_type):
        if address_type in request_type.name.lower():
            return True
        return False

    mocker.patch('business_bn.bn_processors.correction.has_previous_address', side_effect=side_effect)
    mocker.patch('business_bn.bn_processors.correction.has_party_name_changed', return_value=True)

    for _ in range(10):
        try:
            process_event(
                SimpleCloudEvent(
                    type = 'bc.registry.business.correction',
                    data = {
                        'filing': {
                            'header': {'filingId': filing_id}
                        }
                    }
                )
            )

        except BNException:
            continue
        except BNRetryExceededException:
            break

    request_trackers = RequestTracker.find_by(business_id, RequestTracker.ServiceName.BN_HUB,
                                              request_type, filing_id=filing_id)
    assert request_trackers
    assert len(request_trackers) == 1
    assert request_trackers[0].is_processed is False
    assert request_trackers[0].retry_number == 9
