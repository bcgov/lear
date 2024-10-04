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
from legal_api.utils.datetime import datetime as dt



def validate(filing: Dict) -> Optional[Error]:
    """Validate the Notice of Withdrawal filing."""
    if not filing:
        return Error(HTTPStatus.BAD_REQUEST, [{'error': babel('A valid filing is required.')}])
    
    msg = []

    withdrawn_filing_id_path: Final = '/filing/noticeOfWithdrawal/filingId'
    withdrawn_filing_id = get_int(filing, withdrawn_filing_id_path)
    if not withdrawn_filing_id:
        msg.append({'error': babel('Filing Id is required.'), 'path': withdrawn_filing_id_path})
        return msg # cannot continue validation without the to be withdrawn filing id
    
    err = validate_withdrawn_filing(withdrawn_filing_id)
    if err:
        msg.extend(err)
    
    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)
    return None
    


def validate_withdrawn_filing(withdrawn_filing_id: int):
    """Validate the to be withdrawn filing id exists, the filing has a FED, the filing status is PAID """
    msg = []
    
    # check whether the filing ID exists
    withdrawn_filing = db.session.query(Filing). \
                        filter(Filing.id == withdrawn_filing_id).one_or_none()
    if not withdrawn_filing:
        msg.append({'error':  babel('The filing to be withdrawn cannot be found.')})
        return msg # cannot continue if the withdrawn filing doesn't exist
    
    # check whether the filing has a Future Effective Date(FED)
    now = dt.utcnow()
    filing_effective_date = dt.fromisoformat(str(withdrawn_filing.effective_date))
    if filing_effective_date < now:
        msg.append({'error': babel(f'Only filings with a future effective date can be withdrawn.')})

    # check the filing status
    filing_status = withdrawn_filing.status
    if filing_status != Filing.Status.PAID.value:
        msg.append({'error': babel(f'Only paid filings with a future effective date can be withdrawn.')})
    
    if msg:
        return msg
    return None
