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
import copy

from registry_schemas.example_data import INCORPORATION_FILING_TEMPLATE
from sqlalchemy_continuum import versioning_manager

from tests import EPOCH_DATETIME


def create_business(identifier):
    """Return a test business."""
    from legal_api.models import Business
    business = Business()
    business.identifier = identifier
    business.save()
    return business


def create_filing(token=None, json_filing=None, business_id=None, filing_date=EPOCH_DATETIME, bootstrap_id: str = None):
    """Return a test filing."""
    from legal_api.models import Filing
    filing = Filing()
    if token:
        filing.payment_token = str(token)
    filing.filing_date = filing_date

    if json_filing:
        filing.filing_json = json_filing
    if business_id:
        filing.business_id = business_id
    if bootstrap_id:
        filing.temp_reg = bootstrap_id

    filing.save()
    return filing


def email_prepped_filing(session, identifier, payment_id, option):
    """Return a test filing ready for email notification."""
    business = create_business(identifier)
    filing_template = copy.deepcopy(INCORPORATION_FILING_TEMPLATE)
    filing_template['filing']['business'] = {'identifier': business.identifier}
    for party in filing_template['filing']['incorporationApplication']['parties']:
        for role in party['roles']:
            if role['roleType'] == 'Completing Party':
                party['officer']['email'] = 'comp_party@email.com'
    filing_template['filing']['incorporationApplication']['contactPoint']['email'] = 'test@test.com'
    filing = create_filing(token=payment_id, json_filing=filing_template, business_id=business.id)
    filing.payment_completion_date = filing.filing_date
    filing.save()
    if option == 'registered':
        uow = versioning_manager.unit_of_work(session)
        transaction = uow.create_transaction(session)
        filing.transaction_id = transaction.id
        filing.save()
    return filing
