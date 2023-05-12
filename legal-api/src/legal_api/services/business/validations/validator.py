# Copyright © 2022 Province of British Columbia
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
"""Perform various validations."""
from http import HTTPStatus

from flask_babel import _ as babel  # noqa: N813, I004, I001, I003

from legal_api.errors import Error
from legal_api.models import LegalEntity


document_rule_set = {
    'cstat': {
        'legal_types': ['CP', 'BC', 'BEN'],
        'status': LegalEntity.State.ACTIVE
    },
    'cogs': {
        'legal_types': ['CP', 'BC', 'BEN'],
        'goodStanding': True
    },
    'lseal': {
        # NB: will be available for all business types once the outputs have been updated for them
        'legal_types': ['CP', 'BEN', 'SP', 'GP']
    }
}


def validate_document_request(document_type, legal_entity: LegalEntity):
    """Validate the business document request."""
    errors = []
    # basic checks
    if document_rules := document_rule_set.get(document_type, None):
        allowed_legal_types = document_rules.get('legal_types', None)
        if allowed_legal_types and legal_entity.entity_type not in allowed_legal_types:
            errors.append({'error': babel('Specified document type is not valid for the entity.')})
        status = document_rules.get('status', None)
        if status and legal_entity.state != status:
            errors.append({'error': babel('Specified document type is not valid for the current entity status.')})
        good_standing = document_rules.get('goodStanding', None)
        if good_standing and not legal_entity.good_standing:
            errors.append({'error': babel('Specified document type is not valid for the current entity status.')})
    if errors:
        return Error(HTTPStatus.BAD_REQUEST, errors)
    return None
