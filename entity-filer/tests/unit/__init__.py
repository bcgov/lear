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
            'name': 'annual_report',
            'date': '2001-08-05'
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
    from legal_api.models import Business
    business = Business()
    business.identifier = identifier
    business.save()
    return business
