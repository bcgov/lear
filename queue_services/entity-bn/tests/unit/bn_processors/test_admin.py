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
"""The Test Suites to ensure that the admin is operating correctly."""
import uuid
import xml.etree.ElementTree as Et

import pytest
from legal_api.models import Business, RequestTracker

from entity_bn.worker import process_event
from tests.unit import create_registration_data


acknowledgement_response = """<?xml version="1.0"?>
    <SBNAcknowledgement>
        <header>
            <transactionID>BNTUQ0E1OC0</transactionID>
        </header>
        <body>A Valid Document Type was received.</body>
    </SBNAcknowledgement>"""


@pytest.mark.parametrize('request_type', [
    ('BN15'),
    ('RESUBMIT_INFORM_CRA'),
])
async def test_admin_bn15(app, session, mocker, request_type):
    """Test inform cra about new SP/GP registration."""
    message_id = str(uuid.uuid4())
    filing_id, business_id = create_registration_data('SP')
    if request_type == 'RESUBMIT_INFORM_CRA':
        request_tracker = RequestTracker(
            request_type=RequestTracker.RequestType.INFORM_CRA,
            retry_number=-1,
            service_name=RequestTracker.ServiceName.BN_HUB,
            business_id=business_id,
            is_admin=True,
            message_id=message_id,
            request_object='<SBNCreateProgramAccountRequest></SBNCreateProgramAccountRequest>'
        )
        request_tracker.save()

    def side_effect(input_xml):
        root = Et.fromstring(input_xml)
        if root.tag == 'SBNCreateProgramAccountRequest':
            return 200, acknowledgement_response

    mocker.patch('entity_bn.bn_processors.registration.request_bn_hub', side_effect=side_effect)
    mocker.patch('entity_bn.bn_processors.registration.publish_event')

    business_number = '993775204' if request_type == 'BN15' else None
    business_program_id = 'BC'
    program_account_ref_no = 1
    mocker.patch('entity_bn.bn_processors.registration._get_program_account', return_value=(200, {
        'business_no': business_number,
        'business_program_id': business_program_id,
        'cross_reference_program_no': 'FM1234567',
        'program_account_ref_no': program_account_ref_no})
    )

    business = Business.find_by_internal_id(business_id)
    await process_event({
        'id': message_id,
        'type': 'bc.registry.admin.bn',
        'data': {
            'header': {
                'request': request_type,
                'businessNumber': business_number
            },
            'business': {'identifier': business.identifier}
        }
    }, app)

    request_trackers = RequestTracker.find_by(business_id,
                                              RequestTracker.ServiceName.BN_HUB,
                                              RequestTracker.RequestType.INFORM_CRA,
                                              message_id=message_id)
    assert request_trackers
    assert len(request_trackers) == 1
    assert request_trackers[0].is_processed
    assert request_trackers[0].retry_number == 0
    assert request_trackers[0].is_admin

    request_trackers = RequestTracker.find_by(business_id,
                                              RequestTracker.ServiceName.BN_HUB,
                                              RequestTracker.RequestType.GET_BN,
                                              message_id=message_id)
    assert request_trackers
    assert len(request_trackers) == 1
    assert request_trackers[0].is_processed
    assert request_trackers[0].retry_number == 0
    assert request_trackers[0].is_admin

    business = Business.find_by_internal_id(business_id)
    assert business.tax_id == f'{business_number}{business_program_id}{str(program_account_ref_no).zfill(4)}'


@pytest.mark.parametrize('request_type, request_xml', [
    (RequestTracker.RequestType.CHANGE_DELIVERY_ADDRESS, '<SBNChangeAddress></SBNChangeAddress>'),
    (RequestTracker.RequestType.CHANGE_MAILING_ADDRESS, '<SBNChangeAddress></SBNChangeAddress>'),
    (RequestTracker.RequestType.CHANGE_NAME, '<SBNChangeName></SBNChangeName>'),
    (RequestTracker.RequestType.CHANGE_PARTY, '<SBNChangeName></SBNChangeName>'),
    (RequestTracker.RequestType.CHANGE_STATUS, '<SBNChangeStatus></SBNChangeStatus>'),
])
async def test_admin_resubmit(app, session, mocker, request_type, request_xml):
    """Test resubmit CRA request."""
    message_id = str(uuid.uuid4())
    filing_id, business_id = create_registration_data('SP', tax_id='993775204BC0001')
    request_tracker = RequestTracker(
        request_type=request_type,
        retry_number=-1,
        service_name=RequestTracker.ServiceName.BN_HUB,
        business_id=business_id,
        is_admin=True,
        message_id=message_id,
        request_object=request_xml
    )
    request_tracker.save()

    def side_effect(input_xml):
        return 200, acknowledgement_response

    mocker.patch('entity_bn.bn_processors.admin.request_bn_hub', side_effect=side_effect)

    business = Business.find_by_internal_id(business_id)
    await process_event({
        'id': message_id,
        'type': 'bc.registry.admin.bn',
        'data': {
            'header': {
                'request': f'RESUBMIT_{request_type.name}',
                'businessNumber': None
            },
            'business': {'identifier': business.identifier}
        }
    }, app)

    request_trackers = RequestTracker.find_by(business_id,
                                              RequestTracker.ServiceName.BN_HUB,
                                              request_type,
                                              message_id=message_id)
    assert request_trackers
    assert len(request_trackers) == 1
    assert request_trackers[0].is_processed
    assert request_trackers[0].retry_number == 0
    assert request_trackers[0].is_admin
    assert request_trackers[0].request_object == request_xml
