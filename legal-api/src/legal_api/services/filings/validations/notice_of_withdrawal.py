# Copyright © 2024 Province of British Columbia
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
"""Validation for the Notice of Withdrawal filing."""
from http import HTTPStatus
from typing import Dict, Optional, Final

from flask_babel import _ as babel  # noqa: N813, I004, I001; importing camelcase '_' as a name
# noqa: I003
from legal_api.errors import Error
from legal_api.services.utils import get_int

from legal_api.models.db import db # noqa: I001
from legal_api.models import Filing



def validate(filing: Dict) -> Optional[Error]:
    """Validate the Notice of Withdrawal filing."""
    if not filing:
        return Error(HTTPStatus.BAD_REQUEST, [{'error': babel('A valid filing is required.')}])
    
    msg = []

    filing_id_path: Final = '/filing/noticeOfWithdrawal/filingId'
    filing_id = get_int(filing, filing_id_path)

