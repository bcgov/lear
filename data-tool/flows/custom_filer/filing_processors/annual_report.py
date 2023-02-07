# Copyright © 2019 Province of British Columbia
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
"""File processing rules and actions for the annual report."""
import copy

import datetime
from typing import Dict

from legal_api.models import Business, Filing

from ..filing_meta import FilingMeta


def process(business: Business,
            filing: Dict,
            filing_rec: Filing,
            filing_meta: FilingMeta):
    """Render the annual_report onto the business model objects."""
    # Note: Removed agm logic as not needed for corps data loading
    legal_filing_name = 'annualReport'
    ar_date = filing[legal_filing_name].get('annualReportDate')

    if ar_date:
        ar_date = datetime.date.fromisoformat(ar_date)
    else:
        # should never get here (schema validation should prevent this from making it to the filer)
        print(f'No annualReportDate given for in annual report. Filing id: {filing.id}')

    business.last_ar_date = ar_date
    business.last_ar_year = business.last_ar_year + 1 if business.last_ar_year else business.founding_date.year + 1

    ar_json = copy.deepcopy(filing_rec.filing_json)
    ar_json['filing']['header']['ARFilingYear'] = business.last_ar_year
    filing_rec._filing_json = ar_json

    # save the annual report date to the filing meta info
    filing_meta.application_date = ar_date
    filing_meta.annual_report = {'annualReportDate': ar_date.isoformat(),
                                 'annualGeneralMeetingDate': None,
                                 'annualReportFilingYear': business.last_ar_year}
