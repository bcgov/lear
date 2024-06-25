# Copyright © 2024 Province of British Columbia
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
"""The Unit Tests for the Change of Address filing."""
import copy
from datetime import datetime

import pytest
from datedelta import datedelta
from legal_api.models import BatchProcessing
from registry_schemas.example_data import CHANGE_OF_ADDRESS, FILING_TEMPLATE

from entity_filer.filing_meta import FilingMeta
from entity_filer.filing_processors import change_of_address
from tests.unit import create_business, factory_batch, factory_batch_processing


CHANGE_OF_ADDRESS_FILING = copy.deepcopy(FILING_TEMPLATE)
CHANGE_OF_ADDRESS_FILING['filing']['changeOfAddress'] = copy.deepcopy(CHANGE_OF_ADDRESS)
CHANGE_OF_ADDRESS_FILING['filing']['changeOfAddress']['offices']['registeredOffice'] = {
    'deliveryAddress': {
        'streetAddress': 'new delivery_address',
        'addressCity': 'new delivery_address city',
        'addressCountry': 'Canada',
        'postalCode': 'H0H0H0',
        'addressRegion': 'BC',
    },
    'mailingAddress': {
        'streetAddress': 'new mailing_address',
        'addressCity': 'new mailing_address city',
        'addressCountry': 'Canada',
        'postalCode': 'H0H0H0',
        'addressRegion': 'BC',
    }
}


def test_change_of_address_process(app, session):
    """Assert that the address is changed."""
    identifier = 'CP1234567'
    business = create_business(identifier)

    filing_meta = FilingMeta()
    change_of_address.process(business, CHANGE_OF_ADDRESS_FILING['filing'], filing_meta, False)

    delivery_address = business.delivery_address.one_or_none()
    assert delivery_address
    assert delivery_address.street == 'new delivery_address'
    assert delivery_address.city == 'new delivery_address city'


@pytest.mark.parametrize('test_name, status, step, trigger_date, delay', [
    (
        'DELAY_IN_DISSOLUTION_STAGE_1',
        BatchProcessing.BatchProcessingStatus.PROCESSING,
        BatchProcessing.BatchProcessingStep.WARNING_LEVEL_1,
        datetime.utcnow()+datedelta(days=42),
        True
    ),
    (
        'DELAY_IN_DISSOLUTION_STAGE_2',
        BatchProcessing.BatchProcessingStatus.PROCESSING,
        BatchProcessing.BatchProcessingStep.WARNING_LEVEL_2,
        datetime.utcnow()+datedelta(days=42),
        True
    ),
    (
        'NO_DELAY_NOT_IN_DISSOLUTION_1',
        BatchProcessing.BatchProcessingStatus.COMPLETED,
        BatchProcessing.BatchProcessingStep.DISSOLUTION,
        datetime.utcnow()+datedelta(days=42),
        False
    ),
    (
        'NO_DELAY_NOT_IN_DISSOLUTION_2',
        BatchProcessing.BatchProcessingStatus.WITHDRAWN,
        BatchProcessing.BatchProcessingStep.WARNING_LEVEL_1,
        datetime.utcnow()+datedelta(days=42),
        False
    ),
    (
        'NO_DELAY_TRIGGER_DATE_MORE_THAN_60_DAYS_STAGE_1',
        BatchProcessing.BatchProcessingStatus.PROCESSING,
        BatchProcessing.BatchProcessingStep.WARNING_LEVEL_1,
        datetime.utcnow()+datedelta(days=70),
        False
    ),
    (
        'NO_DELAY_TRIGGER_DATE_MORE_THAN_60_DAYS_STAGE_2',
        BatchProcessing.BatchProcessingStatus.PROCESSING,
        BatchProcessing.BatchProcessingStep.WARNING_LEVEL_1,
        datetime.utcnow()+datedelta(days=70),
        False
    )
])
def test_change_of_address_delay_dissolution(app, session, test_name, status, step, trigger_date, delay):
    """Assert that involuntary dissolution is delayed."""
    identifier = 'CP1234567'
    business = create_business(identifier)
    batch = factory_batch()
    batch_processing = factory_batch_processing(batch_id=batch.id,
                             business_id=business.id,
                             identifier=business.identifier,
                             status=status,
                             step=step,
                             trigger_date=trigger_date)

    utc_now = datetime.utcnow()
    dissolution_date = utc_now + datedelta(days=72)
    trigger_date = batch_processing.trigger_date
    delay_dissolution_date = utc_now + datedelta(days=92)
    delay_trigger_date = utc_now + datedelta(days=62)
    
    filing_meta = FilingMeta()
    
    change_of_address.process(business, CHANGE_OF_ADDRESS_FILING['filing'], filing_meta, True)

    if delay:
        assert batch_processing.trigger_date.date() == delay_trigger_date.date()
        assert batch_processing.meta_data.get('changeOfAddressDelay') is True
        assert batch_processing.meta_data.get('targetDissolutionDate') == delay_dissolution_date.date().isoformat()
    else:
        assert batch_processing.trigger_date == trigger_date
        assert batch_processing.meta_data.get('changeOfAddressDelay') is None
        assert batch_processing.meta_data.get('targetDissolutionDate') == dissolution_date.date().isoformat()
