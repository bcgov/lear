# Copyright © 2019 Province of British Columbia
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
"""Test Suite to ensure legal filing schemas are valid.

This suite should have at least 1 test for every filing type allowed.
"""
import copy
from datetime import datetime

import pytest

from registry_schemas import validate
from registry_schemas.example_data import (
    ALL_FILINGS,
    ANNUAL_REPORT,
    CHANGE_OF_ADDRESS,
    CHANGE_OF_DIRECTORS,
    FILING_HEADER,
    CORP_CHANGE_OF_ADDRESS,
)


@pytest.mark.parametrize('filing_data', ALL_FILINGS)
def test_valid_filing(filing_data):
    """Assert that the schema is performing as expected."""
    is_valid, errors = validate(filing_data, 'filing')

    # print filing name for easier debugging
    print(filing_data['filing']['header']['name'])

    if errors:
        for err in errors:
            print(err.message)
    print(errors)

    assert is_valid


def test_invalid_ar_filing():
    """Assert that the schema is performing as expected."""
    iar = {
        'filing': {
            'header': {
                'name': 'annualReport',
                'date': '2019-04-08'
            },
            'business': {
                'cacheId': 1,
                'foundingDate': '2007-04-08T00:00:00+00:00',
                'identifier': 'CP1234567',
                'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
                'legalName': 'legal name - CP1234567'
            }
        }
    }
    is_valid, errors = validate(iar, 'filing')

    # if errors:
    #     for err in errors:
    #         print(err.message)
    print(errors)

    assert not is_valid


def test_valid_coa_filing():
    """Assert that the Change of Address filing schema is performing as expected."""
    iar = {
        'filing': {
            'header': {
                'name': 'changeOfAddress',
                'date': '2019-04-08',
                'certifiedBy': 'full legal name',
                'email': 'no_one@never.get'
            },
            'business': {
                'cacheId': 1,
                'foundingDate': '2007-04-08',
                'identifier': 'CP1234567',
                'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
                'lastPreBobFilingTimestamp': '',
                'legalName': 'legal name - CP1234567'
            },
            'changeOfAddress': CHANGE_OF_ADDRESS
        }
    }
    is_valid, errors = validate(iar, 'filing')

    if errors:
        for err in errors:
            print(err.message)
    print(errors)

    assert is_valid


def test_valid_coa_filing_bcorp():
    """Assert that the Change of Address filing schema is performing as expected."""
    iar = {
        'filing': {
            'header': {
                'name': 'changeOfAddress',
                'date': '2019-04-08',
                'certifiedBy': 'full legal name',
                'email': 'no_one@never.get'
            },
            'business': {
                'cacheId': 1,
                'foundingDate': '2007-04-08',
                'identifier': 'CP1234567',
                'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
                'lastPreBobFilingTimestamp': '',
                'legalName': 'legal name - CP1234567'
            },
            'changeOfAddress': CORP_CHANGE_OF_ADDRESS
        }
    }
    is_valid, errors = validate(iar, 'filing')

    if errors:
        for err in errors:
            print(err.message)
    print(errors)

    assert is_valid


def test_invalid_coa_filing_bcorp():
    """Assert that the Change of Address filing schema conditionals are performing as expected."""
    coa_arr = CHANGE_OF_ADDRESS
    coa_arr['legalType'] = 'BC'
    iar = {
        'filing': {
            'header': {
                'name': 'changeOfAddress',
                'date': '2019-04-08',
                'certifiedBy': 'full legal name',
                'email': 'no_one@never.get'
            },
            'business': {
                'cacheId': 1,
                'foundingDate': '2007-04-08',
                'identifier': 'CP1234567',
                'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
                'lastPreBobFilingTimestamp': '',
                'legalName': 'legal name - CP1234567'
            },
            'changeOfAddress': coa_arr
        }
    }
    is_valid, errors = validate(iar, 'filing')

    if errors:
        for err in errors:
            print(err.message)
    print(errors)

    assert not is_valid


def test_valid_cod_filing():
    """Assert that the Change of Directors filing schema is performing as expected."""
    filing = {
        'filing': {
            'header': {
                'name': 'changeOfDirectors',
                'date': '2019-04-08',
                'certifiedBy': 'full legal name',
                'email': 'no_one@never.get'
            },
            'business': {
                'cacheId': 1,
                'foundingDate': '2007-04-08',
                'identifier': 'CP1234567',
                'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
                'legalName': 'legal name - CP1234567'
            },
            'changeOfDirectors': CHANGE_OF_DIRECTORS
        }
    }

    is_valid, errors = validate(filing, 'filing')

    if errors:
        for err in errors:
            print(err.message)
    print(errors)

    assert not is_valid


def test_invalid_cod_filing():
    """Assert that the Change of Directors filing schema is catching invalid data."""
    filing = {
        'filing': {
            'header': {
                'name': 'changeOfDirectors',
                'date': '2019-04-08',
                'email': 'no_one@never.get',
            },
            'business': {
                'cacheId': 1,
                'foundingDate': '2007-04-08T00:00:00+00:00',
                'identifier': 'CP1234567',
                'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
                'legalName': 'legal name - CP1234567'
            },
            'changeOfDirectors': {
                'directors': [
                    {
                        'officer': {
                            'firstName': False,  # should be string
                            'lastName': 'Griffin'
                        },
                        'deliveryAddress': {
                            'streetAddress': 'mailing_address - address line one',
                            'addressCity': 'mailing_address city',
                            'addressCountry': 'mailing_address country',
                            'postalCode': 'H0H0H0',
                            'addressRegion': 'BC'
                        },
                        'title': 2  # should be string
                    }
                ]
            }
        }
    }

    is_valid, errors = validate(filing, 'filing')

    if errors:
        for err in errors:
            print(err.message)
    print(errors)

    assert not is_valid


def test_valid_multi_filing():
    """Assert that the filing schema is performing as expected with multiple filings included."""
    filing = {
        'filing': {
            'header': {
                'name': 'annualReport',
                'date': '2019-04-08',
                'certifiedBy': 'full legal name',
                'email': 'no_one@never.get'
            },
            'business': {
                'cacheId': 1,
                'foundingDate': '2007-04-08T00:00:00+00:00',
                'identifier': 'CP1234567',
                'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
                'legalName': 'legal name - CP1234567'
            },
            'annualReport': ANNUAL_REPORT,
            'changeOfDirectors': CHANGE_OF_DIRECTORS,
            'changeOfAddress': CHANGE_OF_ADDRESS
        }
    }

    is_valid, errors = validate(filing, 'filing')

    if errors:
        for err in errors:
            print(err.message)
    print(errors)

    assert is_valid


def test_filing_paper():
    """Assert that a Paper Only filing is valid."""
    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['header']['availableOnPaperOnly'] = True

    # filing['filing']['available'] = 'available on paper only.'
    is_valid, errors = validate(filing, 'filing')

    if errors:
        for err in errors:
            print(err.message)
    print(errors)

    assert is_valid


def test_effective_date():
    """Assert that the effective date is working correctly from a structural POV."""
    filing = copy.deepcopy(FILING_HEADER)
    filing['filing']['changeOfAddress'] = CHANGE_OF_ADDRESS

    filing['filing']['header']['effectiveDate'] = datetime.utcnow().isoformat() + 'Z'

    is_valid, errors = validate(filing, 'filing')

    if errors:
        for err in errors:
            print(err.message)
    print(errors)

    assert is_valid

    filing['filing']['header']['effectiveDate'] = 'this should fail'

    is_valid, errors = validate(filing, 'filing')

    if errors:
        for err in errors:
            print(err.message)
    print(errors)

    assert not is_valid
