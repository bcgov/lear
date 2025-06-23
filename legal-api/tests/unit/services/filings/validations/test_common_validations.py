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
"""Test Suite for common validations sharing through the different filings."""
import copy

import pytest
from registry_schemas.example_data import (
    AMALGAMATION_APPLICATION,
    APPOINT_RECEIVER,
    CHANGE_OF_ADDRESS,
    CHANGE_OF_DIRECTORS,
    CHANGE_OF_OFFICERS,
    CHANGE_OF_REGISTRATION,
    CONTINUATION_IN,
    CORRECTION_INCORPORATION,
    DISSOLUTION,
    FILING_HEADER,
    FIRMS_CONVERSION,
    INCORPORATION,
    INTENT_TO_LIQUIDATE,
    REGISTRATION,
    RESTORATION,
)

from legal_api.services.filings.validations.common_validations import (
    validate_offices_addresses,
    validate_parties_addresses,
)


CORRECTION = copy.deepcopy(CORRECTION_INCORPORATION['filing']['correction'])


INVALID_ADDRESS_NO_POSTAL_CODE = {
    'streetAddress': 'address line one',
    'addressCity': 'address city',
    'addressCountry': 'CA',
    'postalCode': None,
    'addressRegion': 'BC'
}

VALID_ADDRESS_NO_POSTAL_CODE = {
    'streetAddress': 'address line one',
    'addressCity': 'address city',
    'addressCountry': 'HK',
    'postalCode': None,
    'addressRegion': ''
}


@pytest.mark.parametrize('filing_type, filing_data, office_type', [
    ('amaglamationApplication', AMALGAMATION_APPLICATION, 'registeredOffice'),
    ('changeOfAddress', CHANGE_OF_ADDRESS, 'registeredOffice'),
    ('changeOfRegistration', CHANGE_OF_REGISTRATION, 'businessOffice'),
    ('continuationIn', CONTINUATION_IN, 'registeredOffice'),
    ('conversion', FIRMS_CONVERSION, 'businessOffice'),
    ('correction', CORRECTION, 'registeredOffice'),
    ('incorporationApplication', INCORPORATION, 'registeredOffice'),
    ('registration', REGISTRATION, 'businessOffice'),
    ('restoration', RESTORATION, 'registeredOffice'),
    ('intentToLiquidate', INTENT_TO_LIQUIDATE, 'liquidationOffice')
])
def test_validate_offices_addresses_postal_code(session, filing_type, filing_data, office_type):
    """Test postal code of office address can be validated."""
    filing = copy.deepcopy(FILING_HEADER)
    filing['filing'][filing_type] = copy.deepcopy(filing_data)

    err1 = validate_offices_addresses(filing, filing_type)
    assert err1 == []

    filing['filing'][filing_type]['offices'][office_type]['deliveryAddress'] = INVALID_ADDRESS_NO_POSTAL_CODE
    err2 = validate_offices_addresses(filing, filing_type)
    assert err2
    assert err2[0]['error'] == 'Postal code is required.'

    filing['filing'][filing_type]['offices'][office_type]['deliveryAddress'] = VALID_ADDRESS_NO_POSTAL_CODE
    err3 = validate_offices_addresses(filing, filing_type)
    assert err3 == []
    

@pytest.mark.parametrize('filing_type, filing_data, party_key', [
    ('amaglamationApplication', AMALGAMATION_APPLICATION, 'parties'),
    ('appointReceiver', APPOINT_RECEIVER, 'parties'),
    ('changeOfDirectors', CHANGE_OF_DIRECTORS, 'directors'),
    ('changeOfOfficers', CHANGE_OF_OFFICERS, 'relationships'),
    ('changeOfRegistration', CHANGE_OF_REGISTRATION, 'parties'),
    ('continuationIn', CONTINUATION_IN, 'parties'),
    ('conversion', FIRMS_CONVERSION, 'parties'),
    ('correction', CORRECTION, 'parties'),
    ('dissolution', DISSOLUTION, 'parties'),
    ('incorporationApplication', INCORPORATION, 'parties'),
    ('registration', REGISTRATION, 'parties'),
    ('restoration', RESTORATION, 'parties'),
    ('intentToLiquidate', INTENT_TO_LIQUIDATE, 'parties')
])
def test_validate_parties_addresses_postal_code(session, filing_type, filing_data, party_key):
    """Test postal code of party address can be validated."""
    filing = copy.deepcopy(FILING_HEADER)
    filing['filing'][filing_type] = copy.deepcopy(filing_data)

    err1 = validate_parties_addresses(filing, filing_type, party_key)
    assert err1 == []

    filing['filing'][filing_type][party_key][0]['deliveryAddress'] = INVALID_ADDRESS_NO_POSTAL_CODE
    err2 = validate_parties_addresses(filing, filing_type, party_key)
    assert err2
    assert err2[0]['error'] == 'Postal code is required.'

    filing['filing'][filing_type][party_key][0]['deliveryAddress'] = VALID_ADDRESS_NO_POSTAL_CODE
    err3 = validate_parties_addresses(filing, filing_type, party_key)
    assert err3 == []
