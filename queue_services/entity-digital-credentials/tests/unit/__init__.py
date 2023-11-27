# Copyright © 2023 Province of British Columbia
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

from legal_api.models import Business, Filing
from sqlalchemy_continuum import versioning_manager


def create_business(identifier):
    """Return a test business."""
    business = Business()
    business.identifier = identifier
    business.legal_type = Business.LegalTypes.SOLE_PROP
    business.legal_name = 'test_business'
    business.save()
    return business


def create_filing(session,  business_id=None,
                  filing_json=None, filing_type=None,
                  filing_status=Filing.Status.COMPLETED.value):
    """Return a test filing."""
    filing = Filing()
    filing._filing_type = filing_type
    filing._filing_sub_type = 'test'
    filing._status = filing_status

    if filing_status == Filing.Status.COMPLETED.value:
        uow = versioning_manager.unit_of_work(session)
        transaction = uow.create_transaction(session)
        filing.transaction_id = transaction.id
    if filing_json:
        filing.filing_json = filing_json
    if business_id:
        filing.business_id = business_id

    filing.save()
    return filing
