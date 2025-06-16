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
"""File processing rules and actions for the Intent to Liquidate filing."""
from contextlib import suppress

import dpath
from business_filer.exceptions import QueueException
from flask import current_app
from business_model.models import Business, Comment, Filing

from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors.filing_components import filings


def process(business: Business,
            filing: dict,
            filing_rec: Filing,
            filing_meta: FilingMeta):
    """Render the intent to liquidate filing unto the model objects."""
    if not (intent_to_liquidate := filing.get("intentToLiquidate")):
        current_app.logger.error("Could not find intentToLiquidate in: %s", filing)
        raise QueueException(f"legal_filing:intentToLiquidate missing from {filing}")

    current_app.logger.debug("processing intentToLiquidate: %s", filing)

    liquidation_date = intent_to_liquidate.get("dateOfCommencementOfLiquidation")

    filing_meta.intent_to_liquidate = {}
    filing_meta.intent_to_liquidate = {
        **filing_meta.intent_to_liquidate,
        "dateOfCommencementOfLiquidation": liquidation_date
    }

    # Add comment about liquidation date
    filing_rec.comments.append(
            Comment(
                comment=f"Liquidation is scheduled to commence on {liquidation_date}.",
                staff_id=filing_rec.submitter_id
            )
        )

    # Update business in_liquidation flag
    business.in_liquidation = True

    # update court order, if any is present
    with suppress(IndexError, KeyError, TypeError):
        court_order_json = dpath.util.get(filing, "/intentToLiquidate/courtOrder")
        filings.update_filing_court_order(filing_rec, court_order_json)
