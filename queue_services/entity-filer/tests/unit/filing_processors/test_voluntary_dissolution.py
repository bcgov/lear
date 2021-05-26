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
"""The Unit Tests for the Voluntary Dissolution filing."""
import copy
from datetime import datetime

from entity_filer.filing_processors import voluntary_dissolution
from tests.unit import create_business

FILING_JSON = {
    'filing': {
        'header': {
            'name': 'voluntaryDissolution',
            'availableOnPaperOnly': True,
            'date': '2021-05-06',
            'certifiedBy': 'certifier',
            'bcolAccountNumber': '123',                 # optional - depends on payment
            'datNumber': 'C1011557',                    # optional - depends on payment
            # 'routingSlipNumber': '<string>',          # optional - depends on payment
            'folioNumber': '2684-001',
            'waiveFees': False,
            'priority': False
        },
        'business': {
            'foundingDate': '',
            'identifier': '',
            'legalName': '',
            'legalType': ''
        },
        'voluntaryDissolution': {
            'dissolutionDate': None, 
            'hasLiabilities': False,
            'parties': [
                       {
                            'officer': {
                                'firstName': 'OfficerFirst',
                                'lastName': 'OfficerLast',
                                'middleName': '',
                                'orgName': '',
                                'partyType': 'person'
                            },
                            'mailingAddress': {
                                'streetAddress': '12345 - 10th Street',
                                'streetAddressAdditional': '',
                                'addressCity': 'Victoria',
                                'addressCountry': 'CA',
                                'postalCode': 'H0H0H0',
                                'addressRegion': 'BC'
                            },
                            'deliveryAddress': {
                                'streetAddress': '12345 - 10th Street',
                                'streetAddressAdditional': '',
                                'addressCity': 'Victoria',
                                'addressCountry': 'CA',
                                'postalCode': 'H0H0H0',
                                'addressRegion': 'BC'
                            },
                            'roles': [
                                {
                                    'roleType': 'Custodian',
                                    'appointmentDate': '2021-05-06'

                                }
                            ]
                        },
                        {
                            'officer': {
                                'firstName': '',
                                'lastName': '',
                                'middleName': '',
                                'orgName': 'LAWYER GUY & ASSOCIATES',
                                'partyType': 'org'
                            },
                           'mailingAddress': {
                                'streetAddress': '1243 Legal Street',
                                'streetAddressAdditional': '',
                                'addressCity': 'Victoria',
                                'addressCountry': 'CA',
                                'postalCode': 'H0H0H0',
                                'addressRegion': 'BC'
                            },
                            'roles': [
                                {
                                    'roleType': 'Completing Party',
                                    'appointmentDate': '2021-05-06'
                                }
                            ]
                        }
                        ]
        }
    }
}


def test_voluntary_dissolution(app, session):
    """Assert that the voluntary dissolution date is set."""
    # setup
    filing_json = copy.deepcopy(FILING_JSON)
    dissolution_date = '2021-05-06T07:01:01.000000+00:00' # this  will be 1 min after midnight
    # dissolution_date = '2019-04-15T20:05:49.068272+00:00' # this  will be 1 min after midnight
    # '2019-04-15T20:05:49.068272+00:00'
    has_liabilities = False
    identifier = 'BC1234567'
    legal_type = 'BEN'
    filing_json['filing']['business']['identifier'] = identifier
    filing_json['filing']['business']['legalType'] = legal_type
    filing_json['filing']['voluntaryDissolution']['dissolutionDate'] = dissolution_date
    filing_json['filing']['voluntaryDissolution']['hasLiabilities'] = has_liabilities

    business = create_business(identifier, legal_type=legal_type)
    business.dissolution_date = None

    # test
    voluntary_dissolution.process(business, filing_json['filing'])

    # validate
    assert business.dissolution_date == datetime.fromisoformat(dissolution_date)
