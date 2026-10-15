# Copyright © 2026 Province of British Columbia
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
"""File processing rules and actions for review imported data filings."""
from datetime import UTC, datetime

from business_model.models import Business, Filing, PartyRole

from business_filer.exceptions import QueueException
from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors.filing_components import (
    create_address,
    update_address,
)
from business_filer.filing_processors.filing_components.relationships import (
    _str_to_int,
    update_relationship_addresses,
)


def _update_office(business: Business, office_type: str, office_info: dict) -> None:
    """Update the supplied addresses for an existing office."""
    office = business.offices.filter_by(office_type=office_type).one_or_none()
    if not office:
        raise QueueException(
            f"Could not find {office_type} office for business {business.id}."
        )

    for address_key, address_info in office_info.items():
        if not address_info:
            continue

        address_type = address_key.replace("Address", "")
        address = office.addresses.filter_by(address_type=address_type).one_or_none()
        if address:
            update_address(address, address_info)
        else:
            address = create_address(address_info, address_type)
            office.addresses.append(address)


def _check_active_directors(business: Business, relationships: list[dict]) -> None:
    """Ensure every relationship still references an active director.

    Validation already checks this at submission, but a director may have been
    ceased between submission and processing, so this guards that gap.
    """
    active_director_ids = {
        role.party_id
        for role in PartyRole.get_party_roles(
            business.id,
            datetime.now(UTC).date(),
            PartyRole.RoleTypes.DIRECTOR.value,
        )
    }
    for relationship in relationships:
        identifier = relationship["entity"]["identifier"]
        if _str_to_int(identifier) not in active_director_ids:
            raise QueueException(
                f"Could not find active director with identifier {identifier} "
                f"for business {business.id}."
            )


def process(
    business: Business,
    filing_rec: Filing,
    filing_meta: FilingMeta,
) -> None:
    """Apply supplied office and director address changes."""
    filing_json = filing_rec.filing_json["filing"]["reviewImportedData"]
    offices = filing_json.get("offices", {})
    relationships = filing_json.get("relationships", [])
    changed_sections = []

    if relationships:
        _check_active_directors(business, relationships)

    for office_type, office_info in offices.items():
        _update_office(business, office_type, office_info)
    if offices:
        changed_sections.append("offices")

    if relationships:
        update_relationship_addresses(relationships, business)
        changed_sections.append("directors")

    filing_meta.review_imported_data = {"sectionsChanged": changed_sections}
