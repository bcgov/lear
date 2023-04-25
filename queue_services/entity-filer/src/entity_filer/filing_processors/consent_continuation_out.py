# Copyright © 2021 Province of British Columbia
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
"""File processing rules and actions for the court order filing."""
from contextlib import suppress
from datetime import datetime
from typing import Dict

import dpath
from dateutil.relativedelta import relativedelta
from legal_api.models import Business, Filing

from entity_filer.filing_meta import FilingMeta


def process(business: Business, cco_filing: Filing, filing: Dict, filing_meta: FilingMeta):
    """Render the court order filing into the business model objects."""
    # update court order, if any is present
    with suppress(IndexError, KeyError, TypeError):
        court_order_json = dpath.util.get(filing, '/consentContinuationOut/courtOrder')
        cco_filing.court_order_file_number = court_order_json.get('fileNumber')
        cco_filing.court_order_effect_of_order = court_order_json.get('effectOfOrder')
        cco_filing.order_details = filing['consentContinuationOut'].get('details')

    business.cco_expiry_date = datetime.now() + relativedelta(months=6)

    filing_meta.consentContinuationOut = {}

    with suppress(IndexError, KeyError, TypeError):
        filing_meta.consentContinuationOut = {**filing_meta.consentContinuationOut,
                                              **{'expiry': datetime.now() + relativedelta(months=6)}}
