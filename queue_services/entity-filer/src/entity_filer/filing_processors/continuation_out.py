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
from typing import Dict

import dpath
from legal_api.models import Business, Filing

from entity_filer.filing_meta import FilingMeta
from entity_filer.filing_processors.filing_components import filings


def process(business: Business, continuation_out_filing: Filing, filing: Dict, filing_meta: FilingMeta):
    """Render the continuation out filing into the business model objects."""
    # update continuation out, if any is present
    with suppress(IndexError, KeyError, TypeError):
        court_order_json = dpath.util.get(filing, '/continuationOut/courtOrder')
        filings.update_filing_court_order(continuation_out_filing, court_order_json)

    continuation_out_json = filing['continuationOut']

    details = continuation_out_json.get('details')
    legal_name = continuation_out_json.get('legalName')
    continuation_out_date = continuation_out_json.get('continuationOutDate')
    foreign_jurisdiction = continuation_out_json.get('foreignJurisdiction')
    foreign_jurisdiction_country = foreign_jurisdiction.get('country')

    continuation_out_filing.order_details = details

    # if business.dissolution_date > datetime.now():
    business.state = Business.State.HISTORICAL
    business.state_filing_id = continuation_out_filing.id

    business.jurisdiction = foreign_jurisdiction_country
    business.foreign_legal_name = legal_name
    business.continuation_out_date = continuation_out_date

    with suppress(IndexError, KeyError, TypeError):
        foreign_jurisdiction_region = foreign_jurisdiction.get('region')
        business.foreign_jurisdiction_region = foreign_jurisdiction_region

    filing_meta.continuation_out = {}
    filing_meta.continuation_out = {**filing_meta.continuation_out,
                                    **{'foreignJurisdictionCountry': foreign_jurisdiction_country},
                                    **{'foreignJurisdictionRegion': foreign_jurisdiction_region},
                                    **{'foreignLegalName': legal_name}}
