# Copyright © 2021 Province of British Columbia
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
"""Validation for the Alteration filing."""
from http import HTTPStatus
from typing import Dict

from flask_babel import _

from legal_api.errors import Error
from legal_api.models import Business

from ... import namex
from ...utils import get_str


def validate(business: Business, filing: Dict) -> Error:
    """Validate the Alteration filing."""
    if not business or not filing:
        return Error(HTTPStatus.BAD_REQUEST, [{'error': _('A valid business and filing are required.')}])
    msg = []

    nr_path = '/filing/alteration/nameRequest/nrNumber'
    nr_number = get_str(filing, nr_path)

    current_legal_type_path = '/filing/business/legalType'
    current_legal_type = get_str(filing, current_legal_type_path)

    if nr_number:
        # ensure legalTypes are valid
        new_legal_type = get_str(filing, '/filing/alteration/nameRequest/legalType')
        if current_legal_type not in ('ULC', 'BC') or new_legal_type != 'BEN':
            msg.append({'error': _('Alteration not valid for selected LegatTypes.'), 'path': nr_path})

        # ensure NR is approved or conditionally approved
        nr_response = namex.query_nr_number(nr_number)
        validation_result = namex.validate_nr(nr_response)
        if not validation_result['is_approved']:
            msg.append({'error': _('Alteration of Name Request is not approved.'), 'path': nr_path})

        # ensure NR request has the same legal name
        path = '/filing/alteration/nameRequest/legalName'
        legal_name = get_str(filing, path)
        nr_name = namex.get_approved_name(nr_response)
        if nr_name != legal_name:
            msg.append({'error': _('Alteration of Name Request has a different legal name.'), 'path': path})
    else:
        # ensure legalTypes are valid
        new_legal_type = get_str(filing, '/filing/alteration/business/legalType')
        if current_legal_type not in ('ULC', 'BC') or new_legal_type != 'BEN':
            msg.append({'error': _('Alteration not valid for selected LegatTypes.'), 'path': nr_path})

        legal_name_path = '/filing/business/legalName'
        legal_name = get_str(filing, legal_name_path)
        if not legal_name:
            msg.append({'error': _('Alteration from Named to Numbered Company can only be done for a Named Company.'),
                        'path': legal_name_path})

    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)

    return None
