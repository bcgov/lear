# Copyright © 2022 Province of British Columbia
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
"""Service to manage the compliance checks."""
from enum import Enum


class ComplianceWarningCodes(str, Enum):
    """Render an Enum of the Compliance Warning Codes."""

    NO_BUSINESS_OFFICE = 'NO_BUSINESS_OFFICE'

    NO_BUSINESS_DELIVERY_ADDRESS = 'NO_BUSINESS_DELIVERY_ADDRESS'
    NO_PROPRIETOR = 'NO_PROPRIETOR'
    NO_PROPRIETOR_PERSON_NAME = 'NO_PROPRIETOR_PERSON_NAME'
    NO_PROPRIETOR_ORG_NAME = 'NO_PROPRIETOR_ORG_NAME'
    NO_PROPRIETOR_ORG_IDENTIFIER = 'NO_PROPRIETOR_ORG_IDENTIFIER'
    NO_PARTNER = 'NO_PARTNER'
    NO_PARTNER_PERSON_NAME = 'NO_PARTNER_PERSON_NAME'
    NO_PARTNER_ORG_NAME = 'NO_PARTNER_ORG_NAME'
    NO_PARTNER_ORG_IDENTIFIER = 'NO_PARTNER_ORG_IDENTIFIER'
    NO_COMPLETING_PARTY = 'NO_COMPLETING_PARTY'
    NO_COMPLETING_PARTY_PERSON_NAME = 'NO_COMPLETING_PARTY_PERSON_NAME'
    NO_COMPLETING_PARTY_ORG_NAME = 'NO_COMPLETING_PARTY_ORG_NAME'
    NO_COMPLETING_PARTY_ORG_IDENTIFIER = 'NO_COMPLETING_PARTY_ORG_IDENTIFIER'

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


class ComplianceWarningReferers(str, Enum):
    """Enum for for compliance warning referers."""

    BUSINESS_OFFICE = 'BUSINESS_OFFICE'
    BUSINESS_PARTY = 'BUSINESS_PARTY'
    COMPLETING_PARTY = 'COMPLETING_PARTY'


class ComplianceWarnings(str, Enum):
    """Enum for for compliance warnings."""

    NO_ADDRESS = 'NO_ADDRESS'
    NO_ADDRESS_STREET = 'NO_ADDRESS_STREET'
    NO_ADDRESS_CITY = 'NO_ADDRESS_CITY'
    NO_ADDRESS_COUNTRY = 'NO_ADDRESS_COUNTRY'
    NO_ADDRESS_POSTAL_CODE = 'NO_ADDRESS_POSTAL_CODE'
    NO_ADDRESS_REGION = 'NO_ADDRESS_REGION'


REFERER_WARNINGS_MAPPING = {
    ComplianceWarningReferers.BUSINESS_OFFICE: {
        'addresses': {
            'mailing': {
                ComplianceWarnings.NO_ADDRESS: {
                    'code': ComplianceWarningCodes.NO_BUSINESS_OFFICE_MAILING_ADDRESS,
                    'message': 'Business office mailing address is required.'
                },
                ComplianceWarnings.NO_ADDRESS_STREET: {
                    'code': ComplianceWarningCodes.NO_BUSINESS_OFFICE_MAILING_ADDRESS_STREET,
                    'message': 'Street is required for business office mailing address.'
                },
                ComplianceWarnings.NO_ADDRESS_CITY: {
                    'code': ComplianceWarningCodes.NO_BUSINESS_OFFICE_MAILING_ADDRESS_CITY,
                    'message': 'City is required for business office mailing address.'
                },
                ComplianceWarnings.NO_ADDRESS_COUNTRY: {
                    'code': ComplianceWarningCodes.NO_BUSINESS_OFFICE_MAILING_ADDRESS_COUNTRY,
                    'message': 'Country is required for business office mailing address.'
                },
                ComplianceWarnings.NO_ADDRESS_POSTAL_CODE: {
                    'code': ComplianceWarningCodes.NO_BUSINESS_OFFICE_MAILING_ADDRESS_POSTAL_CODE,
                    'message': 'Postal code is required for business office mailing address.'
                },
                ComplianceWarnings.NO_ADDRESS_REGION: {
                    'code': ComplianceWarningCodes.NO_BUSINESS_OFFICE_MAILING_ADDRESS_REGION,
                    'message': 'Region is required for business office mailing address.'
                }
            },
            'delivery': {
                ComplianceWarnings.NO_ADDRESS: {
                    'code': ComplianceWarningCodes.NO_BUSINESS_OFFICE_DELIVERY_ADDRESS,
                    'message': 'Business office delivery address is required.'
                },
                ComplianceWarnings.NO_ADDRESS_STREET: {
                    'code': ComplianceWarningCodes.NO_BUSINESS_OFFICE_DELIVERY_ADDRESS_STREET,
                    'message': 'Street is required for business office delivery address.'
                },
                ComplianceWarnings.NO_ADDRESS_CITY: {
                    'code': ComplianceWarningCodes.NO_BUSINESS_OFFICE_DELIVERY_ADDRESS_CITY,
                    'message': 'City is required for business office delivery address.'
                },
                ComplianceWarnings.NO_ADDRESS_COUNTRY: {
                    'code': ComplianceWarningCodes.NO_BUSINESS_OFFICE_DELIVERY_ADDRESS_COUNTRY,
                    'message': 'Country is required for business office delivery address.'
                },
                ComplianceWarnings.NO_ADDRESS_POSTAL_CODE: {
                    'code': ComplianceWarningCodes.NO_BUSINESS_OFFICE_DELIVERY_ADDRESS_POSTAL_CODE,
                    'message': 'Postal code is required for business office delivery address.'
                },
                ComplianceWarnings.NO_ADDRESS_REGION: {
                    'code': ComplianceWarningCodes.NO_BUSINESS_OFFICE_DELIVERY_ADDRESS_REGION,
                    'message': 'Region is required for business office delivery address.'
                }
            }
        }
    },
    ComplianceWarningReferers.BUSINESS_PARTY: {
        'addresses': {
            'mailing': {
                ComplianceWarnings.NO_ADDRESS: {
                    'code': ComplianceWarningCodes.NO_BUSINESS_PARTY_MAILING_ADDRESS,
                    'message': 'Business party mailing address is required.'
                },
                ComplianceWarnings.NO_ADDRESS_STREET: {
                    'code': ComplianceWarningCodes.NO_BUSINESS_PARTY_MAILING_ADDRESS_STREET,
                    'message': 'Street is required for business party mailing address.'
                },
                ComplianceWarnings.NO_ADDRESS_CITY: {
                    'code': ComplianceWarningCodes.NO_BUSINESS_PARTY_MAILING_ADDRESS_CITY,
                    'message': 'City is required for business party mailing address.'
                },
                ComplianceWarnings.NO_ADDRESS_COUNTRY: {
                    'code': ComplianceWarningCodes.NO_BUSINESS_PARTY_MAILING_ADDRESS_COUNTRY,
                    'message': 'Country is required for business party mailing address.'
                },
                ComplianceWarnings.NO_ADDRESS_POSTAL_CODE: {
                    'code': ComplianceWarningCodes.NO_BUSINESS_PARTY_MAILING_ADDRESS_POSTAL_CODE,
                    'message': 'Postal code is required for business party mailing address.'
                },
                ComplianceWarnings.NO_ADDRESS_REGION: {
                    'code': ComplianceWarningCodes.NO_BUSINESS_PARTY_MAILING_ADDRESS_REGION,
                    'message': 'Region is required for business party mailing address.'
                }
            }
        }
    },
    ComplianceWarningReferers.COMPLETING_PARTY: {
        'addresses': {
            'mailing': {
                ComplianceWarnings.NO_ADDRESS: {
                    'code': ComplianceWarningCodes.NO_COMPLETING_PARTY_MAILING_ADDRESS,
                    'message': 'Completing party mailing address is required.'
                },
                ComplianceWarnings.NO_ADDRESS_STREET: {
                    'code': ComplianceWarningCodes.NO_COMPLETING_PARTY_MAILING_ADDRESS_STREET,
                    'message': 'Street is required for completing party mailing address.'
                },
                ComplianceWarnings.NO_ADDRESS_CITY: {
                    'code': ComplianceWarningCodes.NO_COMPLETING_PARTY_MAILING_ADDRESS_CITY,
                    'message': 'City is required for completing party mailing address.'
                },
                ComplianceWarnings.NO_ADDRESS_COUNTRY: {
                    'code': ComplianceWarningCodes.NO_COMPLETING_PARTY_MAILING_ADDRESS_COUNTRY,
                    'message': 'Country is required for completing party mailing address.'
                },
                ComplianceWarnings.NO_ADDRESS_POSTAL_CODE: {
                    'code': ComplianceWarningCodes.NO_COMPLETING_PARTY_MAILING_ADDRESS_POSTAL_CODE,
                    'message': 'Postal code is required for completing party mailing address.'
                },
                ComplianceWarnings.NO_ADDRESS_REGION: {
                    'code': ComplianceWarningCodes.NO_COMPLETING_PARTY_MAILING_ADDRESS_REGION,
                    'message': 'Region is required for completing party mailing address.'
                }
            }
        }
    }
}


def get_address_compliance_warning(address_referer: ComplianceWarningReferers,
                                   address_type: str,
                                   compliance_warnings: ComplianceWarnings) -> dict:
    """Retrieve compliance warnings for an address."""
    warning_code = \
        REFERER_WARNINGS_MAPPING[address_referer]['addresses'][address_type][compliance_warnings]
    return warning_code
