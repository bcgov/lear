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
"""Sample data used across many tests."""

import copy


FILING_HEADER = {
    'filing': {
        'header': {
            'name': 'annualReport',
            'availableOnPaperOnly': False,
            'date': '2019-04-08',
            'certifiedBy': 'full name',
            'email': 'no_one@never.get',
            'filingId': 1
        },
        'business': {
            'cacheId': 1,
            'foundingDate': '2007-04-08',
            'identifier': 'CP1234567',
            'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
            'lastPreBobFilingTimestamp': '2019-04-15T20:05:49.068272+00:00',
            'legalName': 'legal name - CP1234567',
            'legalType': 'CP'
        }
    }
}

BUSINESS = {
    'cacheId': 1,
    'foundingDate': '2007-04-08',
    'identifier': 'CP1234567',
    'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
    'lastPreBobFilingTimestamp': '2019-04-15T20:05:49.068272+00:00',
    'legalName': 'legal name - CP1234567',
    'legalType': 'CP'
}

ANNUAL_REPORT = {
    'filing': {
        'header': {
            'name': 'annualReport',
            'availableOnPaperOnly': False,
            'certifiedBy': 'full name',
            'email': 'no_one@never.get',
            'date': '2019-04-08'
        },
        'business': {
            'cacheId': 1,
            'foundingDate': '2007-04-08',
            'identifier': 'CP1234567',
            'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
            'lastPreBobFilingTimestamp': '2019-01-01T20:05:49.068272+00:00',
            'legalName': 'legal name - CP1234567',
            'legalType': 'CP'
        },
        'annualReport': {
            'annualGeneralMeetingDate': '2018-04-08',
            'annualReportDate': '2018-04-08',
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
                    'cessationDate': None
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
                    'appointmentDate': '2018-01-01'
                }
            ],
            'deliveryAddress': {
                'streetAddress': 'delivery_address - address line one',
                'addressCity': 'delivery_address city',
                'addressCountry': 'delivery_address country',
                'postalCode': 'H0H0H0',
                'addressRegion': 'BC'
            },
            'mailingAddress': {
                'streetAddress': 'mailing_address - address line one',
                'addressCity': 'mailing_address city',
                'addressCountry': 'mailing_address country',
                'postalCode': 'H0H0H0',
                'addressRegion': 'BC'
            }
        }
    }
}

CHANGE_OF_DIRECTORS = {
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

CHANGE_OF_DIRECTORS_MAILING = {
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
            'mailingAddress': {
                'streetAddress': 'mailing_address - address line #2',
                'additionalStreetAddress': 'Kirkintiloch',
                'addressCity': 'Glasgow',
                'addressCountry': 'UK',
                'postalCode': 'H0H 0H0',
                'addressRegion': 'SC'
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
            'mailingAddress': {
                'streetAddress': 'mailing_address - address line #2',
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
    'legalType': 'CP',
    'offices': {
        'registeredOffice': {
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
    }
}

CORP_CHANGE_OF_ADDRESS = {
    'legalType': 'BC',
    'offices': {
        'registeredOffice': {
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
        },
        'recordsOffice': {
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
    }
}

VOLUNTARY_DISSOLUTION = {
    'dissolutionDate': '2018-04-08',
    'hasLiabilities': True
}

SPECIAL_RESOLUTION = {
    'meetingDate': '2018-04-08',
    'resolution': 'Be in resolved that cookies are delicious.\n\nNom nom nom...'
}

CHANGE_OF_NAME = {
    'legalName': 'My New Entity Name'
}

FILING_TEMPLATE = {
    'filing': {
        'header': {
            'name': None,
            'date': '2019-04-08',
            'certifiedBy': 'full name',
            'email': 'no_one@never.get',
            'filingId': 1
        },
        'business': {
            'cacheId': 1,
            'foundingDate': '2007-04-08',
            'identifier': 'CP1234567',
            'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
            'lastPreBobFilingTimestamp': '2019-04-15T20:05:49.068272+00:00',
            'legalName': 'legal name - CP1234567',
            'legalType': 'CP'
        }
    }
}


STUB_FILING = {
}

# build complete list of filings with names, for use in the generic test_valid_filing() test
# - not including AR because it's already a complete filing rather than the others that are snippets without header and
#   business elements; prepended to list afterwards.
FILINGS_WITH_TYPES = [
    ('changeOfDirectors', CHANGE_OF_DIRECTORS),
    ('changeOfAddress', CHANGE_OF_ADDRESS),
    ('voluntaryDissolution', VOLUNTARY_DISSOLUTION),
    ('specialResolution', SPECIAL_RESOLUTION),
    ('changeOfName', CHANGE_OF_NAME),
    ('incorporationApplication', STUB_FILING),
    ('amalgamationApplication', STUB_FILING),
    ('dissolved', STUB_FILING),
    ('amendedAGM', STUB_FILING),
    ('restorationApplication', STUB_FILING),
    ('amendedAnnualReport', STUB_FILING),
    ('amendedChangeOfDirectors', STUB_FILING),
    ('voluntaryLiquidation', STUB_FILING),
    ('appointReceiver', STUB_FILING),
    ('continuedOut', STUB_FILING)
]


def _build_complete_filing(name, snippet):
    """Util function to build complete filing from filing template and snippet."""
    complete_dict = copy.deepcopy(FILING_TEMPLATE)
    complete_dict['filing']['header']['name'] = name
    complete_dict['filing'][name] = snippet
    return complete_dict


ALL_FILINGS = [_build_complete_filing(f[0], f[1]) for f in FILINGS_WITH_TYPES]
ALL_FILINGS.insert(0, ANNUAL_REPORT)
