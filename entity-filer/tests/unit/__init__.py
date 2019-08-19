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
"""The Unit Tests and the helper routines."""

from tests import EPOCH_DATETIME


AR_FILING = {
    'filing': {
        'header': {
            'name': 'annualReport',
            'date': '2001-08-05'
        },
        'business': {
            'cacheId': 1,
            'foundingDate': '2007-04-08',
            'identifier': 'CP1234567',
            'last_agm_date': '2017-04-08',
            'legalName': 'legal name - CP1234567'
        },
        'annualReport': {
            'annualGeneralMeetingDate': '2018-04-08',
            'certifiedBy': 'full name',
            'email': 'no_one@never.get'
        }
    }
}

COA_FILING = {
    'filing': {
        'header': {
            'name': 'changeOfAddress',
            'date': '2019-07-30'
        },
        'business': {
            'cacheId': 1,
            'foundingDate': '2007-04-08',
            'identifier': 'CP1234567',
            'last_agm_date': '2018-04-08',
            'legalName': 'legal name - CP1234567'
        },
        'changeOfAddress': {
            'deliveryAddress': {
                'streetAddress': 'test lane',
                'streetAddressAdditional': 'test line 1',
                'addressCity': 'testcity',
                'addressCountry': 'Canada',
                'addressRegion': 'BC',
                'postalCode': 'T3S T3R',
                'deliveryInstructions': 'Test address delivery',
                'actions': ['addressChanged']
            },
            'mailingAddress': {
                'streetAddress': 'test lane',
                'streetAddressAdditional': 'test line 1',
                'addressCity': 'testcity',
                'addressCountry': 'Canada',
                'addressRegion': 'BC',
                'postalCode': 'T3S T3R',
                'deliveryInstructions': 'Test address mailing',
                'actions': ['addressChanged']
            },
            'certifiedBy': 'full name',
            'email': 'no_one@never.get'
        }
    }
}

COD_FILING = {
    'filing': {
        'header': {
            'name': 'changeOfDirectors',
            'date': '2019-07-29'
        },
        'business': {
            'cacheId': 1,
            'foundingDate': '2007-04-08',
            'identifier': 'CP1234567',
            'last_agm_date': '2018-04-08',
            'legalName': 'legal name - CP1234567'
        },
        'changeOfDirectors': {
            'directors': [
                {
                    'title': '',
                    'appointmentDate': '2017-01-01',
                    'cessationDate': None,
                    'officer': {
                        'firstName': 'director1',
                        'lastName': 'test1',
                        'middleInitial': 'd',
                    },
                    'deliveryAddress': {
                        'streetAddress': 'test lane',
                        'streetAddressAdditional': 'test line 1',
                        'addressCity': 'testcity',
                        'addressCountry': 'Canada',
                        'addressRegion': 'BC',
                        'postalCode': 'T3S T3R',
                        'deliveryInstructions': 'director1'
                    },
                    'actions': []
                },
                {
                    'title': 'title',
                    'appointmentDate': '2018-01-01',
                    'cessationDate': None,
                    'officer': {
                        'firstName': 'director2',
                        'lastName': 'test2',
                        'middleInitial': 'd',
                        'prevFirstName': 'shouldchange',
                        'prevMiddleInitial': '',
                        'prevLastName': 'shouldchange',
                    },
                    'deliveryAddress': {
                        'streetAddress': 'test lane',
                        'streetAddressAdditional': 'test line 1',
                        'addressCity': 'testcity',
                        'addressCountry': 'Canada',
                        'addressRegion': 'BC',
                        'postalCode': 'T3S T3R',
                        'deliveryInstructions': 'director2'
                    },
                    'actions': ['nameChanged']
                },
                {
                    'title': 'title',
                    'appointmentDate': '2019-01-01',
                    'cessationDate': '2019-08-01',
                    'officer': {
                        'firstName': 'director3',
                        'lastName': 'test3',
                        'middleInitial': 'd',
                    },
                    'deliveryAddress': {
                        'streetAddress': 'test lane',
                        'streetAddressAdditional': 'test line 1',
                        'addressCity': 'testcity',
                        'addressCountry': 'Canada',
                        'addressRegion': 'BC',
                        'postalCode': 'T3S T3R',
                        'deliveryInstructions': 'director3'
                    },
                    'actions': ['ceased']
                },
                {
                    'title': 'title',
                    'appointmentDate': '2019-01-01',
                    'cessationDate': None,
                    'officer': {
                        'firstName': 'director4',
                        'lastName': 'test4',
                        'middleInitial': 'd',
                    },
                    'deliveryAddress': {
                        'streetAddress': 'test lane',
                        'streetAddressAdditional': 'test line 1',
                        'addressCity': 'testcity',
                        'addressCountry': 'Canada',
                        'addressRegion': 'BC',
                        'postalCode': 'T3S T3R',
                        'deliveryInstructions': 'director4'
                    },
                    'actions': ['addressChanged']
                },
                {
                    'title': 'title',
                    'appointmentDate': '2019-01-01',
                    'cessationDate': None,
                    'officer': {
                        'firstName': 'director5',
                        'lastName': 'test5',
                        'middleInitial': 'd',
                    },
                    'deliveryAddress': {
                        'streetAddress': 'test lane',
                        'streetAddressAdditional': 'test line 1',
                        'addressCity': 'testcity',
                        'addressCountry': 'Canada',
                        'addressRegion': 'BC',
                        'postalCode': 'T3S T3R',
                        'deliveryInstructions': 'director5'
                    },
                    'actions': ['appointed']
                }
            ],
            'certifiedBy': 'full name',
            'email': 'no_one@never.get'
        }
    }
}

COMBINED_FILING = {
    'filing': {
        'header': {
            'name': 'annualReport',
            'date': '2019-07-28'
        },
        'business': {
            'cacheId': 1,
            'foundingDate': '2007-04-08',
            'identifier': 'CP1234567',
            'last_agm_date': '2018-04-08',
            'legalName': 'legal name - CP1234567'
        },
        'annualReport': {
            'annualGeneralMeetingDate': '2019-04-08',
            'certifiedBy': 'full name',
            'email': 'no_one@never.get'
        },
        'changeOfAddress': COA_FILING['filing']['changeOfAddress'],
        'changeOfDirectors': COD_FILING['filing']['changeOfDirectors']
    }
}


def create_filing(token, json_filing=None, business_id=None):
    """Return a test filing."""
    from legal_api.models import Filing
    filing = Filing()
    filing.payment_token = str(token)
    filing.filing_date = EPOCH_DATETIME

    if json_filing:
        filing.filing_json = json_filing
    if business_id:
        filing.business_id = business_id

    filing.save()
    return filing


def create_business(identifier):
    """Return a test business."""
    from legal_api.models import Address, Business
    business = Business()
    business.identifier = identifier
    business = create_business_address(business, Address.DELIVERY)
    business = create_business_address(business, Address.MAILING)
    business.save()
    return business


def create_business_address(business, type):
    """Create an address."""
    from legal_api.models import Address
    address = Address(
        city='Test City',
        street=f'{business.identifier}-Test Street',
        postal_code='T3S3T3',
        country='TA',
        region='BC',
    )
    if type == 'mailing':
        address.address_type = Address.MAILING
        business.mailing_address.append(address)
    else:
        address.address_type = Address.DELIVERY
        business.delivery_address.append(address)
    business.save()
    return business


def create_director(director):
    """Create a director."""
    from legal_api.models import Address, Director
    new_address = Address(
        street=director['deliveryAddress']['streetAddress'],
        city=director['deliveryAddress']['addressCity'],
        country='CA',
        postal_code=director['deliveryAddress']['postalCode'],
        region=director['deliveryAddress']['addressRegion'],
        delivery_instructions=director['deliveryAddress'].get('deliveryInstructions', '').upper()
    )
    new_address.save()
    new_director = Director(
        first_name=director['officer'].get('firstName', '').upper(),
        last_name=director['officer'].get('lastName', '').upper(),
        middle_initial=director['officer'].get('middleInitial', '').upper(),
        appointment_date=director['appointmentDate'],
        cessation_date=None,
        delivery_address=new_address
    )
    new_director.save()
    return new_director
