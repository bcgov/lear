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
from typing import Final, Optional

from flask_babel import _ as babel  # noqa: N813, I004, I001, I003;

from legal_api.errors import Error
from legal_api.models import Filing
from legal_api.models.db import db
from legal_api.services.utils import get_bool, get_int
from legal_api.utils.datetime import datetime as dt


def validate(filing: dict) -> Optional[Error]:
    """Validate the Notice of Withdrawal filing."""
    if not filing:
        return Error(HTTPStatus.BAD_REQUEST, [{"error": babel("A valid filing is required.")}])

    msg = []

    base_path: Final = "/filing/noticeOfWithdrawal"

    withdrawn_filing_id_path: Final = f"{base_path}/filingId"
    withdrawn_filing_id = get_int(filing, withdrawn_filing_id_path)

    has_taken_effect = get_bool(filing, f"{base_path}/hasTakenEffect")
    part_of_poa = get_bool(filing, f"{base_path}/partOfPoa")

    if not withdrawn_filing_id:
        msg.append({"error": babel("Filing Id is required."), "path": withdrawn_filing_id_path})
        return msg  # cannot continue validation without the to be withdrawn filing id

    if has_taken_effect and part_of_poa:
        msg.append({"error": babel("Cannot file a Notice of Withdrawal as the filing has a POA in effect.")})
        return Error(HTTPStatus.BAD_REQUEST, msg)  # cannot continue validation if the filing has a POA in effect

    is_not_found, err_msg = validate_withdrawn_filing(withdrawn_filing_id)
    if is_not_found:
        return Error(HTTPStatus.NOT_FOUND, err_msg)
    if err_msg and not is_not_found:
        msg.extend(err_msg)

    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)
    return None


def validate_withdrawn_filing(withdrawn_filing_id: int):
    """Validate the to be withdrawn filing id exists, the filing has a FED, the filing status is PAID."""
    msg = []
    is_not_found = False
    # check whether the filing ID exists
    withdrawn_filing = db.session.query(Filing). \
        filter(Filing.id == withdrawn_filing_id).one_or_none()
    if not withdrawn_filing:
        msg.append({"error": babel("The filing to be withdrawn cannot be found.")})
        is_not_found = True
        return is_not_found, msg  # cannot continue if the withdrawn filing doesn't exist

    # check whether the filing has a Future Effective Date(FED)
    now = dt.utcnow()
    filing_effective_date = dt.fromisoformat(str(withdrawn_filing.effective_date))
    if filing_effective_date < now:
        msg.append({"error": babel("Only filings with a future effective date can be withdrawn.")})

    # check the filing status
    filing_status = withdrawn_filing.status
    if filing_status != Filing.Status.PAID.value:
        msg.append({"error": babel("Only paid filings with a future effective date can be withdrawn.")})

    if msg:
        return is_not_found, msg
    return None, None
