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
"""File processing rules and actions for the continuation out filing."""
from contextlib import suppress
from typing import Dict

import dpath
from business_model.models import Business, Filing
from business_filer.common.legislation_datetime import LegislationDatetime

from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors.filing_components import filings


def process(business: Business, continuation_out_filing: Filing, filing: Dict, filing_meta: FilingMeta):
    """Render the continuation out filing into the business model objects."""
    # update continuation out, if any is present
    with suppress(IndexError, KeyError, TypeError):
        court_order_json = dpath.util.get(filing, '/continuationOut/courtOrder')
        filings.update_filing_court_order(continuation_out_filing, court_order_json)

    continuation_out_json = filing['continuationOut']

    legal_name = continuation_out_json.get('legalName')
    continuation_out_date_str = continuation_out_json.get('continuationOutDate')
    continuation_out_date = LegislationDatetime.as_utc_timezone_from_legislation_date_str(continuation_out_date_str)
    foreign_jurisdiction = continuation_out_json.get('foreignJurisdiction')
    foreign_jurisdiction_country = foreign_jurisdiction.get('country').upper()

    business.state = Business.State.HISTORICAL
    business.state_filing_id = continuation_out_filing.id

    business.jurisdiction = foreign_jurisdiction_country
    business.foreign_legal_name = legal_name
    business.continuation_out_date = continuation_out_date

    with suppress(IndexError, KeyError, TypeError):
        foreign_jurisdiction_region = foreign_jurisdiction.get('region')
        foreign_jurisdiction_region = foreign_jurisdiction_region.upper() if foreign_jurisdiction_region else None
        business.foreign_jurisdiction_region = foreign_jurisdiction_region

    filing_meta.continuation_out = {}
    filing_meta.continuation_out = {
        **filing_meta.continuation_out,
        'country': foreign_jurisdiction_country,
        'region': foreign_jurisdiction_region,
        'legalName': legal_name,
        'continuationOutDate': continuation_out_date_str
    }
