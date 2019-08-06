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
from registry_schemas import validate


AR = {
    'filing': {
        'header': {
            'name': 'annualReport',
            'date': '2019-04-08'
        },
        'business': {
            'cacheId': 1,
            'foundingDate': '2007-04-08',
            'identifier': 'CP1234567',
            'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
            'lastPreBobFilingTimestamp': '2019-01-01T20:05:49.068272+00:00',
            'legalName': 'legal name - CP1234567'
        },
        'annualReport': {
            'annualGeneralMeetingDate': '2019-04-08',
            'certifiedBy': 'full name',
            'email': 'no_one@never.get'
        }
    }
}

CHANGE_OF_DIRECTORS = {
    'certifiedBy': 'Joe Smith',
    'email': 'nobody@nothing.com',
    'directors': [
        {
            'officer': {
                'firstName': 'Peter',
                'lastName': 'Griffin',
                'prevFirstName': 'Peter',
                'prevMiddleInitial': 'G',
                'prevLastName': 'Griffin'
            },
            'deliveryAddress': {
                'streetAddress': 'mailing_address - address line one',
                'addressCity': 'mailing_address city',
                'addressCountry': 'mailing_address country',
                'postalCode': 'H0H0H0',
                'addressRegion': 'BC'
            },
            'appointmentDate': '2018-01-01',
            'cessationDate': '2019-04-03',
            'actions': ['addressChanged', 'nameChanged']
        },
        {
            'officer': {
                'firstName': 'Joe',
                'middleInitial': 'P',
                'lastName': 'Swanson'
            },
            'deliveryAddress': {
                'streetAddress': 'mailing_address - address line #1',
                'additionalStreetAddress': 'Kirkintiloch',
                'addressCity': 'Glasgow',
                'addressCountry': 'UK',
                'postalCode': 'H0H 0H0',
                'addressRegion': 'SC'
            },
            'title': 'Treasurer',
            'cessationDate': None,
            'appointmentDate': '2018-01-01',
            'actions': []
        }
    ]
}

CHANGE_OF_ADDRESS = {
    'certifiedBy': 'Joe Smith',
    'email': 'nobody@nothing.com',
    'deliveryAddress': {
        'streetAddress': 'delivery_address - address line one',
        'addressCity': 'delivery_address city',
        'addressCountry': 'delivery_address country',
        'postalCode': 'H0H0H0',
        'addressRegion': 'BC',
        'actions': []
    },
    'mailingAddress': {
        'streetAddress': 'mailing_address - address line one',
        'addressCity': 'mailing_address city',
        'addressCountry': 'mailing_address country',
        'postalCode': 'H0H0H0',
        'addressRegion': 'BC',
        'actions': ['addressChanged']
    }
}


def test_valid_ar_filing():
    """Assert that the schema is performing as expected."""
    is_valid, errors = validate(AR, 'filing')

    # if errors:
    #     for err in errors:
    #         print(err.message)
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
                'foundingDate': '2007-04-08',
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
                'date': '2019-04-08'
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


def test_valid_cod_filing():
    """Assert that the Change of Directors filing schema is performing as expected."""
    filing = {
        'filing': {
            'header': {
                'name': 'changeOfDirectors',
                'date': '2019-04-08'
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

    assert is_valid


def test_invalid_cod_filing():
    """Assert that the Change of Directors filing schema is catching invalid data."""
    filing = {
        'filing': {
            'header': {
                'name': 'changeOfDirectors',
                'date': '2019-04-08'
            },
            'business': {
                'cacheId': 1,
                'foundingDate': '2007-04-08',
                'identifier': 'CP1234567',
                'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
                'legalName': 'legal name - CP1234567'
            },
            'changeOfDirectors': {
                'certifiedBy': 'Joe Smith',
                'email': 'nobody@nothing.com',
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
                'date': '2019-04-08'
            },
            'business': {
                'cacheId': 1,
                'foundingDate': '2007-04-08',
                'identifier': 'CP1234567',
                'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
                'legalName': 'legal name - CP1234567'
            },
            'annualReport': AR,
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
