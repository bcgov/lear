# Copyright © 2019 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Validation for the Change of Address filing."""

from http import HTTPStatus
from typing import Dict

import pycountry
from flask_babel import _

from legal_api.errors import Error
from legal_api.models import Business
from legal_api.services.filings.validations.common_validations import validate_offices_addresses


def validate(business: Business, coa: Dict) -> Error:
    """Validate the Change of Address filing."""
    if not business or not coa:
        return Error(HTTPStatus.BAD_REQUEST, [{"error": _("A valid business and filing are required.")}])

    filing_type = "changeOfAddress"
    msg = []

    msg.extend(validate_offices_addresses(coa, filing_type))

    addresses = coa["filing"][filing_type]["offices"]

    for item in addresses.keys():
        for k, v in addresses[item].items():
            region = v.get("addressRegion")
            country = v["addressCountry"]

            if region != "BC":
                path = "/filing/changeOfAddress/offices/%s/%s/addressRegion" % (item, k)
                msg.append({"error": _("Address Region must be 'BC'."), "path": path})

            try:
                country = pycountry.countries.search_fuzzy(country)[0].alpha_2
                if country != "CA":
                    raise LookupError
            except LookupError:
                err_path = "/filing/changeOfAddress/offices/%s/%s/addressCountry" % (item, k)
                msg.append({"error": _("Address Country must be 'CA'."), "path": err_path})
    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)

    return None
