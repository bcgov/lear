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
"""Centralized setup of logging for the service."""
from datetime import datetime


class MockResponse:
    """Mock http response."""

    def __init__(self, json_data):
        """Initialize mock http response."""
        self.json_data = json_data

    def json(self):
        """Return mock json data."""
        return self.json_data


def has_expected_date_str_format(date_str: str, format: str) -> bool:
    "Determine if date string confirms to expected format"
    try:
        datetime.strptime(date_str, format)
    except ValueError:
        return False
    return True


ANNUAL_REPORT_SAMPLE = {
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
            'foundingDate': '2007-04-08T00:00:00+00:00',
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
                        'addressCountry': 'Canada',
                        'postalCode': 'H0H0H0',
                        'addressRegion': 'BC'
                    },
                    'mailingAddress': {
                        'streetAddress': 'mailing_address - address line one',
                        'addressCity': 'mailing_address city',
                        'addressCountry': 'Canada',
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
                    'mailingAddress': {
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
            'offices': {
                'registeredOffice': {
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
                        'addressCountry': 'Canada',
                        'postalCode': 'H0H0H0',
                        'addressRegion': 'BC'
                    }
                },
                'recordsOffice': {
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
                        'addressCountry': 'Canada',
                        'postalCode': 'H0H0H0',
                        'addressRegion': 'BC'
                    }
                }
            }
        }
    }
}

CHANGE_OF_DIRECTORS_SAMPLE = {
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
                'addressCountry': 'Canada',
                'postalCode': 'H0H0H0',
                'addressRegion': 'BC'
            },
            'mailingAddress': {
                'streetAddress': 'mailing_address - address line one',
                'addressCity': 'mailing_address city',
                'addressCountry': 'Canada',
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
            'mailingAddress': {
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
