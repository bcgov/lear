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
"""File processing rules and actions for the consent amalgamation out filing."""
from contextlib import suppress
from typing import Dict

import dpath
from business_model.models import Business, ConsentContinuationOut, Filing

from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors.consent_continuation_out import get_expiry_date
from business_filer.filing_processors.filing_components import filings


def process(business: Business, cco_filing: Filing, filing: Dict, filing_meta: FilingMeta):
    """Render the consent amalgamation out filing into the business model objects."""
    # update consent amalgamation out, if any is present
    with suppress(IndexError, KeyError, TypeError):
        consent_amalgamation_out_json = dpath.get(filing, '/consentAmalgamationOut/courtOrder')
        filings.update_filing_court_order(cco_filing, consent_amalgamation_out_json)

    foreign_jurisdiction = filing['consentAmalgamationOut']['foreignJurisdiction']
    consent_amalgamation_out = ConsentContinuationOut()
    consent_amalgamation_out.consent_type = ConsentContinuationOut.ConsentTypes.amalgamation_out
    country = foreign_jurisdiction.get('country').upper()
    consent_amalgamation_out.foreign_jurisdiction = country

    region = foreign_jurisdiction.get('region')
    region = region.upper() if region else None
    consent_amalgamation_out.foreign_jurisdiction_region = region

    expiry_date = get_expiry_date(cco_filing)
    consent_amalgamation_out.expiry_date = expiry_date

    consent_amalgamation_out.filing_id = cco_filing.id
    consent_amalgamation_out.business_id = business.id
    business.consent_continuation_outs.append(consent_amalgamation_out)

    filing_meta.consent_amalgamation_out = {
        'country': country,
        'region': region,
        'expiry': expiry_date.isoformat()
    }
