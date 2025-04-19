# Copyright © 2025 Province of British Columbia
#
# Licensed under the BSD 3 Clause License, (the "License");
# you may not use this file except in compliance with the License.
# The template for the license can be found here
#    https://opensource.org/license/bsd-3-clause/
#
# Redistribution and use in source and binary forms,
# with or without modification, are permitted provided that the
# following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS”
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
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
