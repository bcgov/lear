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
"""Validation for the Voluntary Dissolution filing."""
from http import HTTPStatus
from typing import Dict, Optional

from flask_babel import _

from legal_api.errors import Error
from legal_api.models import Business

from ...utils import get_str
# noqa: I003; needed as the linter gets confused from the babel override above.


def validate(business: Business, con: Dict) -> Optional[Error]:
    """Validate the dissolution filing."""
    if not business or not con:
        return Error(HTTPStatus.BAD_REQUEST, [{'error': _('A valid business and filing are required.')}])

    legal_type = get_str(con, '/filing/business/legalType')
    msg = []

    if legal_type == Business.LegalTypes.COOP.value:
        err = validate_dissolution_statement_type(con)
        if err:
            msg.extend(err)

    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)
    return None


def validate_dissolution_statement_type(filing_json) -> Error:
    """Validate dissolution statement type of the filing."""
    msg = []
    dissolution_stmt_type_path = '/filing/dissolution/dissolutionStatementType'
    dissolution_stmt_type = get_str(filing_json, dissolution_stmt_type_path)
    if dissolution_stmt_type:
        if dissolution_stmt_type not in ['197NoAssetsNoLiabilities', '197NoAssetsProvisionsLiabilities']:
            msg.append({'error': _('Invalid Dissolution statement type.'),
                        'path': dissolution_stmt_type_path})
            return msg
    else:
        msg.append({'error': _('Dissolution statement type must be provided.'),
                    'path': dissolution_stmt_type_path})
        return msg

    return None
