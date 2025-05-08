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
"""The Test Suites to ensure that the dissolution/putBackOn is operating correctly."""
import xml.etree.ElementTree as Et

import pytest
from simple_cloudevent import SimpleCloudEvent
from business_model.models import RequestTracker

from business_bn.bn_processors import bn_note
from business_bn.exceptions import BNException, BNRetryExceededException
from business_bn.resources.business_bn import process_event
from tests.unit import create_filing, create_registration_data


@pytest.mark.parametrize('legal_type, filing_type', [
    ('SP', 'dissolution'),
    ('GP', 'dissolution'),
    ('SP', 'putBackOn'),
    ('GP', 'putBackOn'),
])
def test_change_of_status(app, session, mocker, legal_type, filing_type):
    """Test inform cra about change of status of SP/GP."""
    filing_id, business_id = create_registration_data(legal_type, tax_id='993775204BC0001')

    json_filing = {
        'filing': {
            'header': {
                'name': filing_type
            }
        }
    }

    if filing_type == 'dissolution':
        json_filing['filing'][filing_type] = {'dissolutionType': None}
    else:
        json_filing['filing'][filing_type] = {}

    filing = create_filing(json_filing=json_filing, business_id=business_id)
    filing._filing_type = filing_type
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

    mocker.patch('business_bn.bn_processors.dissolution_or_put_back_on.request_bn_hub', side_effect=side_effect)

    process_event(
        SimpleCloudEvent(
            type = f'bc.registry.business.{filing_type}',
            data = {
                'filing': {
                    'header': {'filingId': filing_id}
                }
            }
        )
    )

    request_trackers = RequestTracker.find_by(business_id,
                                              RequestTracker.ServiceName.BN_HUB,
                                              RequestTracker.RequestType.CHANGE_STATUS,
                                              filing_id=filing_id)

    assert request_trackers
    assert len(request_trackers) == 1
    assert request_trackers[0].is_processed
    assert request_trackers[0].retry_number == 0


@pytest.mark.parametrize('legal_type, filing_type, tax_id', [
    ('SP', 'dissolution', None),
    ('SP', 'dissolution', ''),
    ('SP', 'dissolution', '993775204'),
    ('GP', 'dissolution', None),
    ('GP', 'dissolution', ''),
    ('GP', 'dissolution', '993775204'),
    ('SP', 'putBackOn', None),
    ('SP', 'putBackOn', ''),
    ('SP', 'putBackOn', '993775204'),
    ('GP', 'putBackOn', None),
    ('GP', 'putBackOn', ''),
    ('GP', 'putBackOn', '993775204'),
])
def test_bn15_not_available_change_of_status(app, session, mocker, legal_type, filing_type, tax_id):
    """Skip cra call when BN15 is not available while doing a change of status SP/GP."""
    filing_id, business_id = create_registration_data(legal_type, tax_id=tax_id)

    json_filing = {
        'filing': {
            'header': {
                'name': filing_type
            }
        }
    }

    if filing_type == 'dissolution':
        json_filing['filing'][filing_type] = {'dissolutionType': None}
    else:
        json_filing['filing'][filing_type] = {}

    filing = create_filing(json_filing=json_filing, business_id=business_id)
    filing._filing_type = filing_type
    filing.save()
    filing_id = filing.id

    process_event(
        SimpleCloudEvent(
            type = f'bc.registry.business.{filing_type}',
            data = {
                'filing': {
                    'header': {'filingId': filing_id}
                }
            }
        )
    )

    request_trackers = RequestTracker.find_by(business_id,
                                              RequestTracker.ServiceName.BN_HUB,
                                              RequestTracker.RequestType.CHANGE_STATUS,
                                              filing_id=filing_id)
    assert request_trackers
    assert len(request_trackers) == 1
    assert not request_trackers[0].is_processed
    assert request_trackers[0].response_object == bn_note
    assert request_trackers[0].retry_number == 0


def test_retry_change_of_status(app, session, mocker):
    """Test retry change of status of SP/GP."""
    filing_id, business_id = create_registration_data('SP', tax_id='993775204BC0001')
    json_filing = {
        'filing': {
            'header': {
                'name': 'dissolution'
            },
            'dissolution': {
                'dissolutionType': 'voluntary'
            }
        }
    }
    filing = create_filing(json_filing=json_filing, business_id=business_id)
    filing._filing_type = 'dissolution'
    filing.save()
    filing_id = filing.id

    mocker.patch('business_bn.bn_processors.dissolution_or_put_back_on.request_bn_hub', return_value=(500, ''))

    for _ in range(10):
        try:
            process_event(
                SimpleCloudEvent(
                    type = 'bc.registry.business.dissolution',
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
                                              RequestTracker.RequestType.CHANGE_STATUS,
                                              filing_id=filing_id)
    assert request_trackers
    assert len(request_trackers) == 1
    assert request_trackers[0].is_processed is False
    assert request_trackers[0].retry_number == 9
