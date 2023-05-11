# Copyright © 2023 Province of British Columbia
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
"""Validation for the Consent Continuation Out filing."""
from http import HTTPStatus
from typing import Dict, Final, Optional

from flask_babel import _ as babel  # noqa: N813, I004, I001; importing camelcase '_' as a name
# noqa: I004
from legal_api.errors import Error
from legal_api.models import LegalEntity
from legal_api.services.filings.validations.common_validations import validate_court_order
# noqa: I003;


def validate(legal_entity: LegalEntity, filing: Dict) -> Optional[Error]:
    """Validate the Consent Continuation Out filing."""
    if not legal_entity or not filing:
        return Error(HTTPStatus.BAD_REQUEST, [{'error': babel('A valid business and filing are required.')}])

    if legal_entity.state != LegalEntity.State.ACTIVE or not legal_entity.good_standing:
        return Error(HTTPStatus.BAD_REQUEST, [{
            'error': babel('Business should be Active and in Good Standing to file Consent Continuation Out.')
        }])

    msg = []
    filing_type = 'consentContinuationOut'
    if court_order := filing.get('filing', {}).get(filing_type, {}).get('courtOrder', None):
        court_order_path: Final = f'/filing/{filing_type}/courtOrder'
        err = validate_court_order(court_order_path, court_order)
        if err:
            msg.extend(err)

    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)
    return None
