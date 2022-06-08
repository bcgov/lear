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
"""The Test Suites to ensure that the dissolution is operating correctly."""
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
async def test_dissolution(app, session, mocker, legal_type):
    """Test inform cra about dissolution of SP/GP."""
    filing_id, business_id = create_registration_data(legal_type, tax_id='993775204BC0001')
    json_filing = {
        'filing': {
            'header': {
                'name': 'dissolution'
            },
            'dissolution': {
            }
        }
    }
    filing = create_filing(json_filing=json_filing, business_id=business_id)
    filing._filing_type = 'dissolution'
    filing.save()
    filing_id = filing.id

    acknowledgement_response = """<?xml version="1.0"?>
        <SBNAcknowledgement>
            <header></header>
            <body>A Valid Document Type was received.</body>
        </SBNAcknowledgement>"""

    def side_effect(input_xml):
        root = Et.fromstring(input_xml)
        if root.tag == 'SBNChangeStatus':
            return 200, acknowledgement_response

    mocker.patch('entity_bn.bn_processors.dissolution.request_bn_hub', side_effect=side_effect)

    await process_event({
        'type': 'bc.registry.business.dissolution',
        'data': {
            'filing': {
                'header': {'filingId': filing_id}
            }
        }
    }, app)

    request_trackers = RequestTracker.find_by(business_id,
                                              RequestTracker.ServiceName.BN_HUB,
                                              RequestTracker.RequestType.CHANGE_STATUS,
                                              filing_id=filing_id)
    assert request_trackers
    assert len(request_trackers) == 1
    assert request_trackers[0].is_processed
    assert request_trackers[0].retry_number == 0


async def test_retry_dissolution(app, session, mocker):
    """Test retry change of SP/GP dissolution."""
    filing_id, business_id = create_registration_data('SP', tax_id='993775204BC0001')
    json_filing = {
        'filing': {
            'header': {
                'name': 'dissolution'
            },
            'dissolution': {}
        }
    }
    filing = create_filing(json_filing=json_filing, business_id=business_id)
    filing._filing_type = 'dissolution'
    filing.save()
    filing_id = filing.id

    mocker.patch('entity_bn.bn_processors.dissolution.request_bn_hub', return_value=(500, ''))

    for _ in range(10):
        try:
            await process_event({
                'type': 'bc.registry.business.dissolution',
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
                                              RequestTracker.RequestType.CHANGE_STATUS,
                                              filing_id=filing_id)
    assert request_trackers
    assert len(request_trackers) == 1
    assert request_trackers[0].is_processed is False
    assert request_trackers[0].retry_number == 9
