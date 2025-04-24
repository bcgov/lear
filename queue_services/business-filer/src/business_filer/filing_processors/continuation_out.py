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
"""File processing rules and actions for the continuation out filing."""
from contextlib import suppress

import dpath
from business_model.models import Business, Filing

from business_filer.common.legislation_datetime import LegislationDatetime
from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors.filing_components import filings


def process(business: Business, continuation_out_filing: Filing, filing: dict, filing_meta: FilingMeta):
    """Render the continuation out filing into the business model objects."""
    # update continuation out, if any is present
    with suppress(IndexError, KeyError, TypeError):
        court_order_json = dpath.get(filing, "/continuationOut/courtOrder")
        filings.update_filing_court_order(continuation_out_filing, court_order_json)

    continuation_out_json = filing["continuationOut"]

    legal_name = continuation_out_json.get("legalName")
    continuation_out_date_str = continuation_out_json.get("continuationOutDate")
    continuation_out_date = LegislationDatetime.as_utc_timezone_from_legislation_date_str(continuation_out_date_str)
    foreign_jurisdiction = continuation_out_json.get("foreignJurisdiction")
    foreign_jurisdiction_country = foreign_jurisdiction.get("country").upper()

    business.state = Business.State.HISTORICAL
    business.state_filing_id = continuation_out_filing.id

    business.jurisdiction = foreign_jurisdiction_country
    business.foreign_legal_name = legal_name
    business.continuation_out_date = continuation_out_date

    with suppress(IndexError, KeyError, TypeError):
        foreign_jurisdiction_region = foreign_jurisdiction.get("region")
        foreign_jurisdiction_region = foreign_jurisdiction_region.upper() if foreign_jurisdiction_region else None
        business.foreign_jurisdiction_region = foreign_jurisdiction_region

    filing_meta.continuation_out = {}
    filing_meta.continuation_out = {
        **filing_meta.continuation_out,
        "country": foreign_jurisdiction_country,
        "region": foreign_jurisdiction_region,
        "legalName": legal_name,
        "continuationOutDate": continuation_out_date_str
    }
