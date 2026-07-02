# Copyright (c) 2026, Province of British Columbia

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.

# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.

# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""Common helper functions for reports flows."""
from http import HTTPStatus

import pycountry
from flask import current_app

from business_model.models import Business
from legal_api.exceptions import BusinessException
from legal_api.services.colin import ColinService


def get_amalg_formatted_jurisdiction(identifier: str, country_code: str, region_code: str | None = None):
    """Return the jurisdiction region if its in Canada otherwise return the jurisdiction country."""
    try:
        country = pycountry.countries.get(alpha_2=country_code)
        region = None
        # NOTE: Region code is being saved as 'FEDERAL' in lear and 'FD' in colin
        if country_code == "CA" and region_code.upper() in ["FEDERAL", "FD"]:
            return "Federal"
        elif country_code == "CA" and region_code:
            region = pycountry.subdivisions.get(code=f"{country_code}-{region_code}")

        return region.name if region else country.name

    except (AttributeError, LookupError) as err:
        current_app.logger.warning("Unable to get jurisdiction for amalgmating company: %s, country_code: %s, region_code: %s, err: %s",
                                   identifier,
                                   country_code,
                                   region_code,
                                   err.with_traceback(None))
        return "N/A"


def get_formatted_amalg_business_data(
    identifier: str | None = None,
    foreign_name: str | None = None,
    foreign_country_code: str | None = None,
    foreign_region_code: str | None = None,
    ting_business: Business | None = None
):
    """Return the amalgamation business data for the report output."""
    if foreign_name:
        # Set identifier to 'N/A' for foreign businesses (we are showing the 'Number in BC' in the output)
        display_identifier = "N/A"
        business_legal_name = foreign_name or "N/A"
        country_code = foreign_country_code
        region_code = foreign_region_code
        # FUTURE: rework this once expros are in lear
        # Check if this is an expro
        if (identifier
            and identifier.startswith("A")
            and (colin_resp := ColinService.query_business(identifier))
            and colin_resp.status_code == HTTPStatus.OK
        ):
            # this is an expro so set the identifier (it is the BC expro identifier)
            display_identifier = identifier
            # overwrite the region_code if jurisdiction is available in the response
            region_code = colin_resp.json().get("business", {}).get("jurisdiction")
            
    else:
        if not ting_business:
            raise BusinessException(
                "Error: Tried to process an amalgamating business which is not a foreign business or a ting business",
                HTTPStatus.UNPROCESSABLE_ENTITY)

        display_identifier = ting_business._identifier
        business_legal_name = ting_business.legal_name
        country_code = "CA"
        region_code = "BC"

    jurisdiction = get_amalg_formatted_jurisdiction(identifier, country_code, region_code)
    
    return {
        "legalName": business_legal_name or "N/A",
        "identifier": display_identifier or "N/A",
        "jurisdiction": jurisdiction or "N/A"
    }