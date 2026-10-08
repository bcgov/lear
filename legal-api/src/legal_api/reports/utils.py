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
        return _format_amalg_business_data(identifier, foreign_name, "N/A",
                                           foreign_country_code, foreign_region_code)
    if ting_business:
        return _format_amalg_business_data(identifier, ting_business.legal_name, ting_business._identifier,
                                           "CA", "BC", is_bc_company=True)
    if identifier:
        return _colin_amalg_business_data(identifier)

    raise BusinessException(
        "Error: Tried to process an amalgamating business which is not a foreign business or a ting business",
        HTTPStatus.UNPROCESSABLE_ENTITY)


def _colin_amalg_business_data(identifier: str) -> dict:
    """Return the data of a COLIN business not loaded in LEAR, resolved from COLIN at render time."""
    colin_json, colin_status = ColinService.query_business(identifier)
    colin_business = (colin_json or {}).get("business") if colin_status == HTTPStatus.OK else None
    is_extraprovincial = bool(colin_business and
                              colin_business.get("legalType") == Business.LegalTypes.EXTRA_PRO_A.value)
    if (
        not colin_business or
        not (business_legal_name := colin_business.get("legalName")) or
        not colin_business.get("legalType") or
        (is_extraprovincial and not colin_business.get("jurisdiction"))
    ):
        # Needed COLIN data cannot be resolved, so the amalgamation report should not be generated
        current_app.logger.error("Unable to get COLIN data for amalgamating business %s (status %s)",
                                 identifier, colin_status)
        raise BusinessException(
            f"Unable to get COLIN data for amalgamating business {identifier}",
            HTTPStatus.SERVICE_UNAVAILABLE)

    region_code = colin_business["jurisdiction"] if is_extraprovincial else "BC"
    return _format_amalg_business_data(identifier, business_legal_name, identifier, "CA", region_code,
                                       is_bc_company=not is_extraprovincial,
                                       is_extraprovincial=is_extraprovincial)


def _format_amalg_business_data(  # noqa: PLR0913
        identifier: str | None,
        legal_name: str | None,
        display_identifier: str | None,
        country_code: str | None,
        region_code: str | None,
        is_bc_company: bool = False,
        is_extraprovincial: bool = False) -> dict:
    jurisdiction = get_amalg_formatted_jurisdiction(identifier, country_code, region_code)

    return {
        "legalName": legal_name or "N/A",
        "identifier": display_identifier or "N/A",
        "jurisdiction": jurisdiction or "N/A",
        "isBcCompany": is_bc_company,
        "isExtraprovincial": is_extraprovincial
    }
