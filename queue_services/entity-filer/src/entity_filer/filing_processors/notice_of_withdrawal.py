# Copyright © 2025 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""File processing rules and actions for the Notice of Withdrawal filing."""
import datetime
from typing import Dict

from legal_api.models import Filing

from entity_filer.filing_meta import FilingMeta
from entity_filer.filing_processors.filing_components import filings


def process(
    filing_submission: Filing,
    filing: Dict,
    filing_meta: FilingMeta
):  # pylint: disable=W0613, R0914
    """Render the notice_of_withdrawal onto the model objects."""
    now_filing = filing.get('noticeOfWithdrawal')

    if court_order := now_filing.get('courtOrder'):
        filings.update_filing_court_order(filing_submission, court_order)
    filing_meta.notice_of_withdrawal = {**filing_meta.notice_of_withdrawal,
                                        'withdrawnDate': datetime.datetime.utcnow()}

    withdrawn_filing_id = now_filing.get('filingId')
    withdrawn_filing = Filing.find_by_id(withdrawn_filing_id)

    if not withdrawn_filing or \
        withdrawn_filing.withdrawal_pending or \
            withdrawn_filing.status == Filing.Status.WITHDRAWN.value:
        return

    withdrawn_filing._status = Filing.Status.WITHDRAWN.value  # pylint: disable=protected-access
    withdrawn_filing.withdrawal_pending = False
    withdrawn_filing.save_to_session()
