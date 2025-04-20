# Copyright © 2025 Province of British Columbia
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
"""The Unit Tests for the Consent Amalgamation Out filing."""
import copy
import random
from datetime import datetime

import pytest
from business_model.models import ConsentContinuationOut, Filing
from business_filer.common.legislation_datetime import LegislationDatetime
from registry_schemas.example_data import CONSENT_AMALGAMATION_OUT, FILING_TEMPLATE

from business_filer.common.filing_message import FilingMessage
from business_filer.services.filer import process_filing
from tests.unit import create_business, create_filing


@pytest.mark.parametrize(
    'test_name, effective_date, expiry_date',
    [
        ('STD_TO_DST', '2023-05-31T17:00:00-07:00', '2023-12-01T23:59:00-08:00'),
        ('DST_TO_STD', '2023-01-31T17:00:00-08:00', '2023-07-31T23:59:00-07:00'),
        ('STD_TO_STD', '2023-03-12T17:00:00-07:00', '2023-09-12T23:59:00-07:00'),
        # DST_TO_DST is not possible. Example: 2023-11-06 (starting day of DST) + 6 months = 2024-05-06 (in STD)
    ]
)
def tests_filer_consent_amalgamation_out(app, session, mocker, test_name, effective_date, expiry_date):
    """Assert that the consent amalgamation out object is correctly populated to model objects."""
    effective_date = LegislationDatetime.as_legislation_timezone(datetime.fromisoformat(effective_date))
    expiry_date = LegislationDatetime.as_legislation_timezone(datetime.fromisoformat(expiry_date))

    identifier = 'BC1234567'
    business = create_business(identifier, legal_type='BC')
    business.save()
    business_id = business.id

    filing_json = copy.deepcopy(FILING_TEMPLATE)
    filing_json['filing']['business']['identifier'] = identifier
    filing_json['filing']['header']['name'] = 'consentAmalgamationOut'
    filing_json['filing']['consentAmalgamationOut'] = CONSENT_AMALGAMATION_OUT

    payment_id = str(random.SystemRandom().getrandbits(0x58))
    cco_filing = create_filing(payment_id, filing_json, business_id=business_id)

    cco_filing.effective_date = LegislationDatetime.as_utc_timezone(effective_date)
    cco_filing.save()
    filing_msg = FilingMessage(filing_identifier=cco_filing.id)

    # mock out the email sender and event publishing
    mocker.patch('business_filer.services.filer.publish_email_message', return_value=None)
    mocker.patch('business_filer.services.filer.publish_event', return_value=None)
    mocker.patch('business_filer.filing_processors.filing_components.name_request.consume_nr', return_value=None)
    mocker.patch('business_filer.filing_processors.filing_components.business_profile.update_business_profile',
                 return_value=None)
    mocker.patch('business_filer.services.AccountService.update_entity', return_value=None)

    # Test
    process_filing(filing_msg)

    # Check outcome
    final_filing = Filing.find_by_id(cco_filing.id)

    assert filing_json['filing']['consentAmalgamationOut']['courtOrder']['fileNumber'] == \
        final_filing.court_order_file_number
    assert filing_json['filing']['consentAmalgamationOut']['courtOrder']['effectOfOrder'] == \
        final_filing.court_order_effect_of_order

    expiry_date_utc = LegislationDatetime.as_utc_timezone(expiry_date)

    cco = ConsentContinuationOut.get_active_cco(business_id, expiry_date_utc, consent_type=ConsentContinuationOut.ConsentTypes.amalgamation_out)
    assert cco
    assert cco[0].consent_type == ConsentContinuationOut.ConsentTypes.amalgamation_out
    assert cco[0].foreign_jurisdiction == \
        filing_json['filing']['consentAmalgamationOut']['foreignJurisdiction']['country']
    assert cco[0].foreign_jurisdiction_region == \
        filing_json['filing']['consentAmalgamationOut']['foreignJurisdiction']['region']
    assert cco[0].expiry_date == expiry_date_utc

    assert final_filing.meta_data['consentAmalgamationOut']['country'] == \
        filing_json['filing']['consentAmalgamationOut']['foreignJurisdiction']['country']
    assert final_filing.meta_data['consentAmalgamationOut']['region'] == \
        filing_json['filing']['consentAmalgamationOut']['foreignJurisdiction']['region']
    assert final_filing.meta_data['consentAmalgamationOut']['expiry'] == expiry_date_utc.isoformat()
