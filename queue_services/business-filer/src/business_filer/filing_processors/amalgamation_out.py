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
"""File processing rules and actions for the amalgamation out filing."""
from contextlib import suppress

import dpath
from business_model.models import Business, Comment, Filing
from business_model.utils.legislation_datetime import LegislationDatetime

from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors.filing_components import filings


def process(business: Business, amalgamation_out_filing: Filing, filing: dict, filing_meta: FilingMeta):
    """Render the amalgamation out filing into the business model objects."""
    # update amalgamation out, if any is present
    with suppress(IndexError, KeyError, TypeError):
        court_order_json = dpath.get(filing, "/amalgamationOut/courtOrder")
        filings.update_filing_court_order(amalgamation_out_filing, court_order_json)

    amalgamation_out_json = filing["amalgamationOut"]

    legal_name = amalgamation_out_json.get("legalName")
    details = amalgamation_out_json.get("details")
    amalgamation_out_date_str = amalgamation_out_json.get("amalgamationOutDate")
    amalgamation_out_date = LegislationDatetime.as_utc_timezone_from_legislation_date_str(amalgamation_out_date_str)
    foreign_jurisdiction = amalgamation_out_json.get("foreignJurisdiction")
    foreign_jurisdiction_country = foreign_jurisdiction.get("country").upper()

    business.state = Business.State.HISTORICAL
    business.state_filing_id = amalgamation_out_filing.id

    business.jurisdiction = foreign_jurisdiction_country
    business.foreign_legal_name = legal_name
    business.amalgamation_out_date = amalgamation_out_date

    with suppress(IndexError, KeyError, TypeError):
        foreign_jurisdiction_region = foreign_jurisdiction.get("region")
        foreign_jurisdiction_region = foreign_jurisdiction_region.upper() if foreign_jurisdiction_region else None
        business.foreign_jurisdiction_region = foreign_jurisdiction_region

    filing_meta.amalgamation_out = {}
    filing_meta.amalgamation_out = {
        **filing_meta.amalgamation_out,
        "country": foreign_jurisdiction_country,
        "region": foreign_jurisdiction_region,
        "legalName": legal_name,
        "amalgamationOutDate": amalgamation_out_date_str
    }

    # add comment to the filing
    amalgamation_out_filing.comments.append(
        Comment(
            comment=details,
            staff_id=amalgamation_out_filing.submitter_id
        )
    )
