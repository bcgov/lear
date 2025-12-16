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
from typing import Optional

from legal_api.errors import Error
from legal_api.models import Business, PartyRole
from legal_api.services.filings.validations.common_validations import validate_offices_addresses, validate_relationships


def validate(business: Business, filing_json: dict) -> Optional[Error]:
    """Validate the Change of Liquidators filing."""
    filing_type = "changeOfLiquidators"
    filing_sub_type = filing_json["filing"][filing_type]["type"]

    msg = []

    if filing_json["filing"][filing_type].get('relationships'):
        msg.extend(validate_relationships(
            business,
            filing_json,
            filing_type,
            PartyRole.RoleTypes.LIQUIDATOR,
            filing_sub_type in ["appointLiquidator", "intentToLiquidate"],
            filing_sub_type in ["ceaseLiquidator", "changeAddressLiquidator"]
        ))

    if filing_json["filing"][filing_type].get('offices'):
        msg.extend(validate_offices_addresses(filing_json, filing_type))

    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)
    return None
