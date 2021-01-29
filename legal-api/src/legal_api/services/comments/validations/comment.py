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
"""Validation for the Special Resolution filing."""
from http import HTTPStatus
from typing import Dict

from flask_babel import _

from legal_api.errors import Error

from ...utils import get_str


def validate(comment: Dict, is_filing: bool) -> Error:
    """Validate a standalone comment."""
    if not comment:
        return Error(HTTPStatus.BAD_REQUEST, [{'error': _('A valid comment is required.')}])
    msg = []

    comment_text_path = '/comment/comment'
    comment_text = get_str(comment, comment_text_path)
    if not comment_text:
        msg.append({'error': _('Comment text must be provided.'),
                    'path': comment_text_path})

    if is_filing:
        filing_id_path = '/comment/filingId'
        filing_id = get_str(comment, filing_id_path)
        if not filing_id:
            msg.append({'error': _('Filing ID must be provided.'),
                        'path': filing_id_path})

    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)
    return None
