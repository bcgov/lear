# Copyright © 2019 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Validation for the Correction filing."""
from http import HTTPStatus
from typing import Dict

from flask_babel import _

from legal_api.errors import Error
from legal_api.models import Business, Filing
from legal_api.services.filings.validations.registration import (
    validate_naics,
    validate_name_request,
    validate_offices,
    validate_party,
)

from .common_validations import has_at_least_one_share_class


def validate(business: Business, filing: Dict) -> Error:
    """Validate the Correction filing."""
    if not business or not filing:
        return Error(HTTPStatus.BAD_REQUEST, [{'error': _('A valid business and filing are required.')}])
    msg = []

    # confirm corrected filing ID is a valid complete filing
    corrected_filing = Filing.find_by_id(filing['filing']['correction']['correctedFilingId'])
    if not corrected_filing or corrected_filing.status != Filing.Status.COMPLETED.value:
        path = '/filing/correction/correctedFilingId'
        msg.append({'error': _('Corrected filing is not a valid filing.'), 'path': path})

    # confirm that this business owns the corrected filing
    elif not business.id == corrected_filing.business_id:
        path = '/filing/correction/correctedFilingId'
        msg.append({'error': _('Corrected filing is not a valid filing for this business.'), 'path': path})

    if err := has_at_least_one_share_class(filing, 'incorporationApplication'):
        msg.append({'error': _(err), 'path': '/filing/incorporationApplication/shareStructure'})

    # validations for firms
    legal_type = filing.get('filing', {}).get('business', {}).get('legalType')
    if legal_type and legal_type in [Business.LegalTypes.SOLE_PROP.value, Business.LegalTypes.PARTNERSHIP.value]:
        _validate_firms_correction(filing, legal_type, msg)

    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)

    return None


def _validate_firms_correction(filing, legal_type, msg):
    filing_type = 'correction'
    if filing.get('filing', {}).get('correction', {}).get('nameRequest', None):
        msg.extend(validate_name_request(filing, filing_type))
    if filing.get('filing', {}).get('correction', {}).get('parties', None):
        msg.extend(validate_party(filing, legal_type, filing_type))
    if filing.get('filing', {}).get('correction', {}).get('offices', None):
        msg.extend(validate_offices(filing, filing_type))
    msg.extend(validate_naics(filing, filing_type))
