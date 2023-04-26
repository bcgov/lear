# Copyright © 2023 Province of British Columbia
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
"""File processing rules and actions for the consent continuation out filing."""
from contextlib import suppress
from datetime import timedelta
from typing import Dict

import dpath
from dateutil.relativedelta import relativedelta
from legal_api.models import Business, Filing
from legal_api.utils.datetime import datetime

from entity_filer.filing_meta import FilingMeta
from entity_filer.filing_processors.filing_components import filings


def process(business: Business, cco_filing: Filing, filing: Dict, filing_meta: FilingMeta):
    """Render the consent continuation out filing into the business model objects."""
    # update consent continuation out, if any is present
    with suppress(IndexError, KeyError, TypeError):
        consent_continuation_out_json = dpath.util.get(filing, '/consentContinuationOut/courtOrder')
        filings.update_filing_court_order(cco_filing, consent_continuation_out_json)

    cco_filing.order_details = filing['consentContinuationOut'].get('details')
    business.cco_expiry_date = (datetime.now() + relativedelta(months=6)).isoformat()

    filing_meta.consentContinuationOut = {}
    filing_meta.consentContinuationOut = {**filing_meta.consentContinuationOut,
                                          **{'expiry': datetime.now() + relativedelta(months=6) + timedelta(hours=8)}}
