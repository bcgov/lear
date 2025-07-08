# Copyright © 2022 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in business with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Service to manage the business checks."""
from enum import Enum


class WarningType(str, Enum):
    """Render an Enum of the Warning Types."""

    MISSING_REQUIRED_BUSINESS_INFO = 'MISSING_REQUIRED_BUSINESS_INFO'
    FUTURE_EFFECTIVE_AMALGAMATION = 'FUTURE_EFFECTIVE_AMALGAMATION'
    NOT_IN_GOOD_STANDING = 'NOT_IN_GOOD_STANDING'
    INVOLUNTARY_DISSOLUTION = 'INVOLUNTARY_DISSOLUTION'


class BusinessWarningCodes(str, Enum):
    """Render an Enum of the Business Warning Codes."""

    NO_BUSINESS_OFFICE = 'NO_BUSINESS_OFFICE'

    NO_BUSINESS_DELIVERY_ADDRESS = 'NO_BUSINESS_DELIVERY_ADDRESS'
    NO_PROPRIETOR = 'NO_PROPRIETOR'
    NO_PROPRIETOR_PERSON_NAME = 'NO_PROPRIETOR_PERSON_NAME'
    NO_PROPRIETOR_ORG_NAME = 'NO_PROPRIETOR_ORG_NAME'
    NO_PARTNER = 'NO_PARTNER'
    NO_PARTNER_PERSON_NAME = 'NO_PARTNER_PERSON_NAME'
    NO_PARTNER_ORG_NAME = 'NO_PARTNER_ORG_NAME'
    NO_COMPLETING_PARTY = 'NO_COMPLETING_PARTY'
    NO_COMPLETING_PARTY_PERSON_NAME = 'NO_COMPLETING_PARTY_PERSON_NAME'
    NO_COMPLETING_PARTY_ORG_NAME = 'NO_COMPLETING_PARTY_ORG_NAME'

    NO_BUSINESS_OFFICE_MAILING_ADDRESS = 'NO_BUSINESS_OFFICE_MAILING_ADDRESS'
    NO_BUSINESS_OFFICE_MAILING_ADDRESS_STREET = 'NO_BUSINESS_OFFICE_MAILING_ADDRESS_STREET'
    NO_BUSINESS_OFFICE_MAILING_ADDRESS_CITY = 'NO_BUSINESS_OFFICE_MAILING_ADDRESS_CITY'
    NO_BUSINESS_OFFICE_MAILING_ADDRESS_COUNTRY = 'NO_BUSINESS_OFFICE_MAILING_ADDRESS_COUNTRY'
    NO_BUSINESS_OFFICE_MAILING_ADDRESS_POSTAL_CODE = 'NO_BUSINESS_OFFICE_MAILING_ADDRESS_POSTAL_CODE'
    NO_BUSINESS_OFFICE_MAILING_ADDRESS_REGION = 'NO_BUSINESS_OFFICE_MAILING_ADDRESS_REGION'

    NO_BUSINESS_OFFICE_DELIVERY_ADDRESS = 'NO_BUSINESS_OFFICE_DELIVERY_ADDRESS'
    NO_BUSINESS_OFFICE_DELIVERY_ADDRESS_STREET = 'NO_BUSINESS_OFFICE_DELIVERY_ADDRESS_STREET'
    NO_BUSINESS_OFFICE_DELIVERY_ADDRESS_CITY = 'NO_BUSINESS_OFFICE_DELIVERY_ADDRESS_CITY'
    NO_BUSINESS_OFFICE_DELIVERY_ADDRESS_COUNTRY = 'NO_BUSINESS_OFFICE_DELIVERY_ADDRESS_COUNTRY'
    NO_BUSINESS_OFFICE_DELIVERY_ADDRESS_POSTAL_CODE = 'NO_BUSINESS_OFFICE_DELIVERY_ADDRESS_POSTAL_CODE'
    NO_BUSINESS_OFFICE_DELIVERY_ADDRESS_REGION = 'NO_BUSINESS_OFFICE_DELIVERY_ADDRESS_REGION'

    NO_BUSINESS_PARTY_MAILING_ADDRESS = 'NO_BUSINESS_PARTY_MAILING_ADDRESS'
    NO_BUSINESS_PARTY_MAILING_ADDRESS_STREET = 'NO_BUSINESS_PARTY_MAILING_ADDRESS_STREET'
    NO_BUSINESS_PARTY_MAILING_ADDRESS_CITY = 'NO_BUSINESS_PARTY_MAILING_ADDRESS_CITY'
    NO_BUSINESS_PARTY_MAILING_ADDRESS_COUNTRY = 'NO_BUSINESS_PARTY_MAILING_ADDRESS_COUNTRY'
    NO_BUSINESS_PARTY_MAILING_ADDRESS_POSTAL_CODE = 'NO_BUSINESS_PARTY_MAILING_ADDRESS_POSTAL_CODE'
    NO_BUSINESS_PARTY_MAILING_ADDRESS_REGION = 'NO_BUSINESS_PARTY_MAILING_ADDRESS_REGION'

    NO_COMPLETING_PARTY_MAILING_ADDRESS = 'NO_COMPLETING_PARTY_MAILING_ADDRESS'
    NO_COMPLETING_PARTY_MAILING_ADDRESS_STREET = 'NO_COMPLETING_PARTY_MAILING_ADDRESS_STREET'
    NO_COMPLETING_PARTY_MAILING_ADDRESS_CITY = 'NO_COMPLETING_PARTY_MAILING_ADDRESS_CITY'
    NO_COMPLETING_PARTY_MAILING_ADDRESS_COUNTRY = 'NO_COMPLETING_PARTY_MAILING_ADDRESS_COUNTRY'
    NO_COMPLETING_PARTY_MAILING_ADDRESS_POSTAL_CODE = 'NO_COMPLETING_PARTY_MAILING_ADDRESS_POSTAL_CODE'
    NO_COMPLETING_PARTY_MAILING_ADDRESS_REGION = 'NO_COMPLETING_PARTY_MAILING_ADDRESS_REGION'

    NO_START_DATE = 'NO_START_DATE'

    MULTIPLE_ANNUAL_REPORTS_NOT_FILED = 'MULTIPLE_ANNUAL_REPORTS_NOT_FILED'
    TRANSITION_NOT_FILED = 'TRANSITION_NOT_FILED'
    NO_REQUIRED_TRANSITION_APPLICATION_FILED = 'NO_REQUIRED_TRANSITION_APPLICATION_FILED'

    DISSOLUTION_IN_PROGRESS = 'DISSOLUTION_IN_PROGRESS'


class BusinessWarningReferers(str, Enum):
    """Enum for business warning referers."""

    BUSINESS_OFFICE = 'BUSINESS_OFFICE'
    BUSINESS_PARTY = 'BUSINESS_PARTY'
    COMPLETING_PARTY = 'COMPLETING_PARTY'


class BusinessWarnings(str, Enum):
    """Enum for business warnings."""

    NO_ADDRESS = 'NO_ADDRESS'
    NO_ADDRESS_STREET = 'NO_ADDRESS_STREET'
    NO_ADDRESS_CITY = 'NO_ADDRESS_CITY'
    NO_ADDRESS_COUNTRY = 'NO_ADDRESS_COUNTRY'
    NO_ADDRESS_POSTAL_CODE = 'NO_ADDRESS_POSTAL_CODE'
    NO_ADDRESS_REGION = 'NO_ADDRESS_REGION'


WARNING_MESSAGE_BASE = {'warningType': WarningType.MISSING_REQUIRED_BUSINESS_INFO}


REFERER_WARNINGS_MAPPING = {
    BusinessWarningReferers.BUSINESS_OFFICE: {
        'addresses': {
            'mailing': {
                BusinessWarnings.NO_ADDRESS: {
                    **WARNING_MESSAGE_BASE,
                    'code': BusinessWarningCodes.NO_BUSINESS_OFFICE_MAILING_ADDRESS,
                    'message': 'Business office mailing address is required.'
                },
                BusinessWarnings.NO_ADDRESS_STREET: {
                    **WARNING_MESSAGE_BASE,
                    'code': BusinessWarningCodes.NO_BUSINESS_OFFICE_MAILING_ADDRESS_STREET,
                    'message': 'Street is required for business office mailing address.'
                },
                BusinessWarnings.NO_ADDRESS_CITY: {
                    **WARNING_MESSAGE_BASE,
                    'code': BusinessWarningCodes.NO_BUSINESS_OFFICE_MAILING_ADDRESS_CITY,
                    'message': 'City is required for business office mailing address.'
                },
                BusinessWarnings.NO_ADDRESS_COUNTRY: {
                    **WARNING_MESSAGE_BASE,
                    'code': BusinessWarningCodes.NO_BUSINESS_OFFICE_MAILING_ADDRESS_COUNTRY,
                    'message': 'Country is required for business office mailing address.'
                },
                BusinessWarnings.NO_ADDRESS_POSTAL_CODE: {
                    **WARNING_MESSAGE_BASE,
                    'code': BusinessWarningCodes.NO_BUSINESS_OFFICE_MAILING_ADDRESS_POSTAL_CODE,
                    'message': 'Postal code is required for business office mailing address.'
                },
                BusinessWarnings.NO_ADDRESS_REGION: {
                    **WARNING_MESSAGE_BASE,
                    'code': BusinessWarningCodes.NO_BUSINESS_OFFICE_MAILING_ADDRESS_REGION,
                    'message': 'Region is required for business office mailing address.'
                }
            },
            'delivery': {
                BusinessWarnings.NO_ADDRESS: {
                    **WARNING_MESSAGE_BASE,
                    'code': BusinessWarningCodes.NO_BUSINESS_OFFICE_DELIVERY_ADDRESS,
                    'message': 'Business office delivery address is required.'
                },
                BusinessWarnings.NO_ADDRESS_STREET: {
                    **WARNING_MESSAGE_BASE,
                    'code': BusinessWarningCodes.NO_BUSINESS_OFFICE_DELIVERY_ADDRESS_STREET,
                    'message': 'Street is required for business office delivery address.'
                },
                BusinessWarnings.NO_ADDRESS_CITY: {
                    **WARNING_MESSAGE_BASE,
                    'code': BusinessWarningCodes.NO_BUSINESS_OFFICE_DELIVERY_ADDRESS_CITY,
                    'message': 'City is required for business office delivery address.'
                },
                BusinessWarnings.NO_ADDRESS_COUNTRY: {
                    **WARNING_MESSAGE_BASE,
                    'code': BusinessWarningCodes.NO_BUSINESS_OFFICE_DELIVERY_ADDRESS_COUNTRY,
                    'message': 'Country is required for business office delivery address.'
                },
                BusinessWarnings.NO_ADDRESS_POSTAL_CODE: {
                    **WARNING_MESSAGE_BASE,
                    'code': BusinessWarningCodes.NO_BUSINESS_OFFICE_DELIVERY_ADDRESS_POSTAL_CODE,
                    'message': 'Postal code is required for business office delivery address.'
                },
                BusinessWarnings.NO_ADDRESS_REGION: {
                    **WARNING_MESSAGE_BASE,
                    'code': BusinessWarningCodes.NO_BUSINESS_OFFICE_DELIVERY_ADDRESS_REGION,
                    'message': 'Region is required for business office delivery address.'
                }
            }
        }
    },
    BusinessWarningReferers.BUSINESS_PARTY: {
        'addresses': {
            'mailing': {
                BusinessWarnings.NO_ADDRESS: {
                    **WARNING_MESSAGE_BASE,
                    'code': BusinessWarningCodes.NO_BUSINESS_PARTY_MAILING_ADDRESS,
                    'message': 'Business party mailing address is required.'
                },
                BusinessWarnings.NO_ADDRESS_STREET: {
                    **WARNING_MESSAGE_BASE,
                    'code': BusinessWarningCodes.NO_BUSINESS_PARTY_MAILING_ADDRESS_STREET,
                    'message': 'Street is required for business party mailing address.'
                },
                BusinessWarnings.NO_ADDRESS_CITY: {
                    **WARNING_MESSAGE_BASE,
                    'code': BusinessWarningCodes.NO_BUSINESS_PARTY_MAILING_ADDRESS_CITY,
                    'message': 'City is required for business party mailing address.'
                },
                BusinessWarnings.NO_ADDRESS_COUNTRY: {
                    **WARNING_MESSAGE_BASE,
                    'code': BusinessWarningCodes.NO_BUSINESS_PARTY_MAILING_ADDRESS_COUNTRY,
                    'message': 'Country is required for business party mailing address.'
                },
                BusinessWarnings.NO_ADDRESS_POSTAL_CODE: {
                    **WARNING_MESSAGE_BASE,
                    'code': BusinessWarningCodes.NO_BUSINESS_PARTY_MAILING_ADDRESS_POSTAL_CODE,
                    'message': 'Postal code is required for business party mailing address.'
                },
                BusinessWarnings.NO_ADDRESS_REGION: {
                    **WARNING_MESSAGE_BASE,
                    'code': BusinessWarningCodes.NO_BUSINESS_PARTY_MAILING_ADDRESS_REGION,
                    'message': 'Region is required for business party mailing address.'
                }
            }
        }
    },
    BusinessWarningReferers.COMPLETING_PARTY: {
        'addresses': {
            'mailing': {
                BusinessWarnings.NO_ADDRESS: {
                    **WARNING_MESSAGE_BASE,
                    'code': BusinessWarningCodes.NO_COMPLETING_PARTY_MAILING_ADDRESS,
                    'message': 'Completing party mailing address is required.'
                },
                BusinessWarnings.NO_ADDRESS_STREET: {
                    **WARNING_MESSAGE_BASE,
                    'code': BusinessWarningCodes.NO_COMPLETING_PARTY_MAILING_ADDRESS_STREET,
                    'message': 'Street is required for completing party mailing address.'
                },
                BusinessWarnings.NO_ADDRESS_CITY: {
                    **WARNING_MESSAGE_BASE,
                    'code': BusinessWarningCodes.NO_COMPLETING_PARTY_MAILING_ADDRESS_CITY,
                    'message': 'City is required for completing party mailing address.'
                },
                BusinessWarnings.NO_ADDRESS_COUNTRY: {
                    **WARNING_MESSAGE_BASE,
                    'code': BusinessWarningCodes.NO_COMPLETING_PARTY_MAILING_ADDRESS_COUNTRY,
                    'message': 'Country is required for completing party mailing address.'
                },
                BusinessWarnings.NO_ADDRESS_POSTAL_CODE: {
                    **WARNING_MESSAGE_BASE,
                    'code': BusinessWarningCodes.NO_COMPLETING_PARTY_MAILING_ADDRESS_POSTAL_CODE,
                    'message': 'Postal code is required for completing party mailing address.'
                },
                BusinessWarnings.NO_ADDRESS_REGION: {
                    **WARNING_MESSAGE_BASE,
                    'code': BusinessWarningCodes.NO_COMPLETING_PARTY_MAILING_ADDRESS_REGION,
                    'message': 'Region is required for completing party mailing address.'
                }
            }
        }
    }
}


def get_address_business_warning(address_referer: BusinessWarningReferers,
                                 address_type: str,
                                 business_warnings: BusinessWarnings) -> dict:
    """Retrieve business warnings for an address."""
    warning_code = \
        REFERER_WARNINGS_MAPPING[address_referer]['addresses'][address_type][business_warnings]
    return warning_code
