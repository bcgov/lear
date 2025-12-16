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
"""Validation for the Change of Receivers filing."""
from datetime import datetime, timezone
from http import HTTPStatus
from typing import Optional

from legal_api.errors import Error
from legal_api.models import Business, PartyRole
from legal_api.services.filings.validations.common_validations import validate_parties_addresses, validate_relationships


def validate(business: Business, filing_json: dict) -> Optional[Error]:
    """Validate the Appoint Receiver filing."""
    filing_type = "changeOfReceivers"
    filing_sub_type = filing_json["filing"][filing_type]["type"]

    msg = []
    if filing_sub_type in ["appointReceiver", "changeAddressReceiver", "amendReceiver"]:
        msg.extend(validate_parties_addresses(filing_json, filing_type, "relationships"))
    elif filing_sub_type == "ceaseReceiver":
        msg.extend(validate_ceased_relationships(business, filing_json["filing"][filing_type]["relationships"]))
    msg.extend(validate_relationships(filing_json, filing_type))

    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)
    return None

def validate_ceased_relationships(business: Business, ceased_relationships: list[dict]) -> list:
    """Validate party."""
    msg = []

    # get Receivers for the business
    receivers = PartyRole.get_party_roles(business.id,
                                          datetime.now(tz=timezone.utc).date(),
                                          PartyRole.RoleTypes.RECEIVER.value)
    receiver_party_ids = [str(receiver_party_role.party_id) for receiver_party_role in receivers]

    # Check if party is a valid party of receiver role
    for relationship in ceased_relationships:
        if relationship.get("entity").get("identifier") not in receiver_party_ids:
            msg.append({"error": "Must be a valid Receiver relationship.", "path": "/filing/ceaseReceiver/relationships"})

    return msg