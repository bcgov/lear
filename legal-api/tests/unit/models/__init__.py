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

"""The Test-Suite used to ensure that the Model objects are working correctly."""
from datetime import datetime

from sqlalchemy_continuum import versioning_manager

from legal_api.models import Address, Business, Director, Filing, db
from tests import EPOCH_DATETIME, FROZEN_DATETIME


AR_FILING = {
    'filing': {
        'header': {
            'name': 'annualReport',
            'date': '2019-08-13'
        },
        'business': {
            'cacheId': 1,
            'foundingDate': '2007-04-08',
            'identifier': 'CP1234567',
            'legalName': 'legal name - CP1234567'
        },
        'annualReport': {
            'annualGeneralMeetingDate': '2019-04-08',
            'certifiedBy': 'full name',
            'email': 'no_one@never.get'
        }
    }
}


def factory_business(identifier):
    """Create a business entity."""
    business = Business(legal_name=f'legal_name-{identifier}',
                        founding_date=EPOCH_DATETIME,
                        last_ledger_timestamp=EPOCH_DATETIME,
                        dissolution_date=EPOCH_DATETIME,
                        identifier=identifier,
                        tax_id='BN123456789',
                        fiscal_year_end_date=FROZEN_DATETIME)

    business.save()
    return business


def factory_business_mailing_address(business):
    """Create a business entity."""
    address = Address(
        city='Test City',
        street=f'{business.identifier}-Test Street',
        postal_code='T3S3T3',
        country='TA',
        region='BC',
        address_type=Address.MAILING
    )
    business.mailing_address.append(address)
    business.save()
    return business


def factory_filing(business, data_dict):
    """Create a filing."""
    filing = Filing()
    filing.business_id = business.id
    filing.filing_date = FROZEN_DATETIME
    filing.filing_json = data_dict
    filing.save()
    return filing


def factory_completed_filing(business, data_dict):
    """Create a completed filing."""
    filing = Filing()
    filing.business_id = business.id
    filing.filing_date = FROZEN_DATETIME
    filing.filing_json = data_dict
    filing.save()

    uow = versioning_manager.unit_of_work(db.session)
    transaction = uow.create_transaction(db.session)
    filing.transaction_id = transaction.id
    filing.payment_token = 1
    filing.payment_completion_date = datetime.now()
    return filing


def factory_pending_filing(business, data_dict):
    """Create a pending filing."""
    filing = Filing()
    filing.business_id = business.id
    filing.filing_date = FROZEN_DATETIME
    filing.filing_json = data_dict
    filing.payment_token = 2
    filing.save()
    return filing


def factory_error_filing(business, data_dict):
    """Create an error filing."""
    filing = Filing()
    filing.business_id = business.id
    filing.filing_date = FROZEN_DATETIME
    filing.filing_json = data_dict
    filing.save()
    filing.payment_token = 5
    filing.payment_completion_date = datetime.now()
    return filing
