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
"""Manages the  names of a LegalEntity."""
from contextlib import suppress
from typing import Dict, Optional

from business_model import Filing
from flask_babel import _ as babel  # noqa: N813

from ...utils.datetime import datetime


def update_filing_court_order(filing_submission: Filing, court_order_json: Dict) -> Optional[Dict]:
    """Update the court_order info for a Filing."""
    if not Filing:
        return {"error": babel("Filing required before alternate names can be set.")}

    filing_submission.court_order_file_number = court_order_json.get("fileNumber")
    filing_submission.court_order_effect_of_order = court_order_json.get("effectOfOrder")
    filing_submission.order_details = court_order_json.get("orderDetails")

    with suppress(IndexError, KeyError, TypeError, ValueError):
        filing_submission.court_order_date = datetime.fromisoformat(court_order_json.get("orderDate"))

    return None


def update_filing_json(filing_submission: Filing, resolution) -> Optional[Dict]:
    """Update the filing_json info for a Filing."""
    if resolution:
        if not Filing:
            return {"error": babel("Filing required before resolution can be set.")}

        filing_submission.filing_json["filing"]["correction"]["resolution"] = resolution

    return None
