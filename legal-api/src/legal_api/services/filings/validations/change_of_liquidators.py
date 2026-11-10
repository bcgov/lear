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
"""Validation for the Change of Liquidators filing."""
from http import HTTPStatus

from flask_babel import _

from business_common.utils.legislation_datetime import LegislationDatetime
from business_model.models import Business, PartyRole
from legal_api.errors import Error
from legal_api.services.filings.validations.common_validations import get_date, validate_offices, validate_relationships


def validate(business: Business, filing_json: dict) -> Error | None:
    """Validate the Change of Liquidators filing."""
    filing_type = "changeOfLiquidators"
    filing_data = filing_json["filing"][filing_type]
    filing_sub_type = filing_data.get("type")

    msg = []

    msg.extend(_validate_liquidation_date(business, filing_json, filing_type, filing_sub_type))

    if filing_data.get("relationships"):
        msg.extend(validate_relationships(
            business,
            filing_json,
            filing_type,
            [PartyRole.RoleTypes.LIQUIDATOR],
            filing_sub_type in ["appointLiquidator", "intentToLiquidate"],
            filing_sub_type in ["ceaseLiquidator", "changeAddressLiquidator"]
        ))

    offices = filing_data.get("offices")
    if filing_sub_type == "appointLiquidator" and not business.in_liquidation and not offices:
        msg.append({
            "error": _("Missing required offices ['liquidationRecordsOffice']."),
            "path": f"/filing/{filing_type}/offices"
        })
    elif offices:
        allowed = (
            ["liquidationRecordsOffice"]
            if filing_sub_type in ["intentToLiquidate", "appointLiquidator", "changeAddressLiquidator"]
            else []
        )
        msg.extend(validate_offices(filing_json, filing_type, allowed, allowed, True))

    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)
    return None


def _validate_liquidation_date(
    business: Business,
    filing_json: dict,
    filing_type: str = "changeOfLiquidators",
    filing_sub_type: str | None = None
) -> list:
    """Validate changeOfLiquidatorsDate for standard and correction filings."""
    msg = []
    date_path = f"/filing/{filing_type}/changeOfLiquidatorsDate"
    liquidation_date = get_date(filing_json, date_path)

    # Required for appointLiquidator when the business is not yet in liquidation
    is_correction = filing_type == "correction"
    if (
        filing_sub_type == "appointLiquidator"
        and not business.in_liquidation
        and not is_correction
        and not liquidation_date
    ):
        msg.append({
            "error": _("'changeOfLiquidatorsDate' is required when business is not yet in liquidation."),
            "path": date_path
        })
        return msg

    if liquidation_date:
        today = LegislationDatetime.datenow()
        if liquidation_date > today:
            msg.append({
                "error": _("'changeOfLiquidatorsDate' cannot be in the future."),
                "path": date_path
            })

    return msg