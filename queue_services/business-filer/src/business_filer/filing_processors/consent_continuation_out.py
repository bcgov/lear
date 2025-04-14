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

import datedelta
import dpath
from business_model.models import Business, ConsentContinuationOut, Filing
from business_filer.common.legislation_datetime import LegislationDatetime

from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors.filing_components import filings


def process(business: Business, cco_filing: Filing, filing: Dict, filing_meta: FilingMeta):
    """Render the consent continuation out filing into the business model objects."""
    # update consent continuation out, if any is present
    with suppress(IndexError, KeyError, TypeError):
        consent_continuation_out_json = dpath.util.get(filing, '/consentContinuationOut/courtOrder')
        filings.update_filing_court_order(cco_filing, consent_continuation_out_json)

    foreign_jurisdiction = filing['consentContinuationOut']['foreignJurisdiction']
    consent_continuation_out = ConsentContinuationOut()
    consent_continuation_out.consent_type = ConsentContinuationOut.ConsentTypes.continuation_out
    country = foreign_jurisdiction.get('country').upper()
    consent_continuation_out.foreign_jurisdiction = country

    region = foreign_jurisdiction.get('region')
    region = region.upper() if region else None
    consent_continuation_out.foreign_jurisdiction_region = region

    expiry_date = get_expiry_date(cco_filing)
    consent_continuation_out.expiry_date = expiry_date

    consent_continuation_out.filing_id = cco_filing.id
    consent_continuation_out.business_id = business.id
    business.consent_continuation_outs.append(consent_continuation_out)

    filing_meta.consent_continuation_out = {
        'country': country,
        'region': region,
        'expiry': expiry_date.isoformat()
    }


def get_expiry_date(filing: Filing):
    """Get expiry after 6 months from consent continuation out."""
    effective_date = LegislationDatetime.as_legislation_timezone(filing.effective_date)
    _date = effective_date.replace(hour=23, minute=59, second=0, microsecond=0)
    _date += datedelta.datedelta(months=6)

    # Setting legislation timezone again after adding 6 months to recalculate the UTC offset and DST info
    _date = LegislationDatetime.as_legislation_timezone(_date)

    # Adjust day light savings. Handle DST +-1 hour changes
    dst_offset_diff = effective_date.dst() - _date.dst()
    _date += dst_offset_diff

    return LegislationDatetime.as_utc_timezone(_date)
