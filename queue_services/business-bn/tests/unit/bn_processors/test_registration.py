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
import xml.etree.ElementTree as Et

from flask import current_app
import pytest
from simple_cloudevent import SimpleCloudEvent
from business_model.models import RequestTracker, Business

from business_bn.exceptions import BNException, BNRetryExceededException
from business_bn.resources.business_bn import process_event
from tests.unit import create_registration_data

acknowledgement_response = """<?xml version="1.0"?>
    <SBNAcknowledgement>
        <header>
            <transactionID>BNTUQ0E1OC0</transactionID>
        </header>
        <body>A Valid SBNCreateProgramAccountRequest Document Type was received.</body>
    </SBNAcknowledgement>"""


@pytest.mark.parametrize('legal_type', [
    ('SP'),
    ('GP'),
])
def test_registration(app, session, mocker, legal_type):
    """Test inform cra about new SP/GP registration."""
    filing_id, business_id = create_registration_data(
        legal_type,
        # adding special character to verify jinja2 autoescape based on the file type (which is .xml)
        # note: not all characters in this require escape
        legal_name="test-reg-'~ ` ! @ # $ % ^ & * ( ) _ - + = \ | ] } [ { ' :; \" / ? > . < ,"
    )

    def mock_request_bn_hub(input_xml):
        root = Et.fromstring(input_xml)  # if it loads xml from string then its a valid xml
        if root.tag == 'SBNCreateProgramAccountRequest':
            return 200, acknowledgement_response

    mocker.patch('business_bn.bn_processors.registration.request_bn_hub', side_effect=mock_request_bn_hub)

    topics_in_queue = {}

    def mock_publish(topic, message):
        topics_in_queue[topic] = topic

    mocker.patch('business_bn.bn_processors.registration.gcp_queue.publish', side_effect=mock_publish)

    business_number = '993775204'
    business_program_id = 'BC'
    program_account_ref_no = 1
    mocker.patch('business_bn.bn_processors.registration._get_program_account', return_value=(200, {
        'business_no': business_number,
        'business_program_id': business_program_id,
        'cross_reference_program_no': 'FM1234567',
        'program_account_ref_no': program_account_ref_no})
    )

    process_event(
        SimpleCloudEvent(
            type = 'bc.registry.business.registration',
            data = {
                'filing': {
                    'header': {'filingId': filing_id}
                }
            }
        )
    )


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

    assert business.tax_id == f'{business_number}{business_program_id}{str(program_account_ref_no).zfill(4)}'


    assert current_app.config['BUSINESS_EVENTS_TOPIC'] in topics_in_queue
    assert current_app.config['BUSINESS_EMAILER_TOPIC'] in topics_in_queue


@pytest.mark.parametrize('request_type', [
    (RequestTracker.RequestType.INFORM_CRA),
    (RequestTracker.RequestType.GET_BN),
])
def test_retry_registration(app, session, mocker, request_type):
    """Test retry new SP/GP registration."""
    is_inform_cra = request_type == RequestTracker.RequestType.INFORM_CRA
    filing_id, business_id = create_registration_data('SP')

    def side_effect(input_xml):
        root = Et.fromstring(input_xml)
        if root.tag == 'SBNCreateProgramAccountRequest':
            return 200, '' if is_inform_cra else acknowledgement_response

    mocker.patch('business_bn.bn_processors.registration.request_bn_hub', side_effect=side_effect)
    mocker.patch('business_bn.bn_processors.registration._get_program_account', return_value=(500, {
        'message': 'Error when trying to retrieve program account from COLIN'})
    )
    mocker.patch('business_bn.bn_processors.registration.gcp_queue.publish')

    for _ in range(10):
        try:
            process_event(
                SimpleCloudEvent(
                    type = 'bc.registry.business.registration',
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
