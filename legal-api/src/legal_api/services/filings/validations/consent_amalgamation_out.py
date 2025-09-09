# Copyright © 2025 Province of British Columbia
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
"""Validation for the Consent Amalgamation Out filing."""
from datetime import datetime
from http import HTTPStatus
from typing import Dict, Final, Optional

from flask_babel import _ as babel  # noqa: N813, I004, I001; importing camelcase '_' as a name
# noqa: I004
from legal_api.errors import Error
from legal_api.models import Business, ConsentContinuationOut
from legal_api.services import flags
from legal_api.services.filings.validations.common_validations import (
    validate_certify_name,
    validate_court_order,
    validate_foreign_jurisdiction,
)
from legal_api.services.permissions import ListActionsPermissionsAllowed, PermissionService
# noqa: I003;


def validate(business: Business, filing: Dict) -> Optional[Error]:
    """Validate the Consent Amalgamation Out filing."""
    if not business or not filing:
        return Error(HTTPStatus.BAD_REQUEST, [{'error': babel('A valid business and filing are required.')}])

    if business.state != Business.State.ACTIVE or not business.good_standing:
        return Error(HTTPStatus.BAD_REQUEST, [{
            'error': babel('Business should be Active and in Good Standing to file Consent Amalgamation Out.')
        }])

    enabled_filings = flags.value('supported-consent-amalgamation-out-entities').split()
    if business.legal_type not in enabled_filings:
        return Error(HTTPStatus.FORBIDDEN,
                     [{'error': babel(f'{business.legal_type} does not support consent amalgamation out filing.')}])
    
    authorized_permissions = PermissionService.get_authorized_permissions_for_user()
    if not validate_certify_name(filing):
        allowed_role_comments = ListActionsPermissionsAllowed.EDITABLE_CERTIFY_NAME.value
        if allowed_role_comments not in authorized_permissions:
            return Error(
                HTTPStatus.FORBIDDEN,
                [{ 'message': f'Permission Denied - You do not have permissions to change certified by in this filing.'}]
            )

    msg = []
    filing_type = 'consentAmalgamationOut'

    foreign_jurisdiction = filing['filing'][filing_type]['foreignJurisdiction']
    foreign_jurisdiction_path = f'/filing/{filing_type}/foreignJurisdiction'
    if err := validate_foreign_jurisdiction(foreign_jurisdiction, foreign_jurisdiction_path):
        msg.extend(err)
    else:
        now = datetime.utcnow()
        country_code = foreign_jurisdiction.get('country')
        region = foreign_jurisdiction.get('region')
        ccos = ConsentContinuationOut.get_active_cco(business.id, now, country_code, region,
                                                     consent_type=ConsentContinuationOut.ConsentTypes.amalgamation_out)
        if ccos:
            msg.extend([{'error': "Can't have new consent for same jurisdiction if an unexpired one already exists",
                        'path': foreign_jurisdiction_path}])

    if court_order := filing.get('filing', {}).get(filing_type, {}).get('courtOrder', None):
        court_order_path: Final = f'/filing/{filing_type}/courtOrder'
        err = validate_court_order(court_order_path, court_order)
        if err:
            msg.extend(err)

    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)
    return None
