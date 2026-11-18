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
from flask import current_app

from business_filer.exceptions import QueueException
from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors.filing_components.offices import (
    update_or_create_offices,
)
from business_filer.filing_processors.filing_components.relationships import (
    _str_to_int,
    update_relationship_addresses,
)

REGISTRARS_NOTATION_TEXT = (
    "Information was provided by the company through the Migration Validation Process. "
    "The company attested that the information reflects the information that existed "
    "immediately prior to migration from the legacy registry system."
)


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


def _create_registrars_notation(business: Business, filing_rec: Filing) -> Filing:
    """Create the completed Registrar's Notation ledger entry that accompanies every review imported data filing.

    The notation is system generated, so it has no submitter and is shown as filed by Registry Staff.
    It is added to the session only; the filer commits it together with the review imported data filing.
    """
    now = datetime.now(UTC)
    notation = Filing()
    notation.filing_json = {
        "filing": {
            "header": {
                "name": "registrarsNotation",
                "date": now.date().isoformat(),
                "certifiedBy": "system",
            },
            "business": {
                "identifier": business.identifier,
                "legalType": business.legal_type,
            },
            "registrarsNotation": {
                "orderDetails": REGISTRARS_NOTATION_TEXT,
            },
        }
    }
    notation.business_id = business.id
    notation.submitter_roles = "system"
    notation.source = Filing.Source.LEAR.value
    notation.filing_date = now
    notation.effective_date = now
    notation.details = REGISTRARS_NOTATION_TEXT
    notation._meta_data = {  # pylint: disable=protected-access
        "applicationDate": now.isoformat(),
        "legalFilings": ["registrarsNotation"],
    }
    notation.set_processed()
    notation.save_to_session()
    current_app.logger.debug(
        "Created registrars notation for reviewImportedData filing %s on business %s",
        filing_rec.id,
        business.identifier,
    )
    return notation


def process(
    business: Business,
    filing_rec: Filing,
    filing_meta: FilingMeta,
) -> Filing:
    """Apply supplied office and director address changes and return the generated Registrar's Notation."""
    filing_json = filing_rec.filing_json["filing"]["reviewImportedData"]
    offices = filing_json.get("offices", {})
    relationships = filing_json.get("relationships", [])
    changed_sections = []

    if relationships:
        _check_active_directors(business, relationships)

    if offices:
        update_or_create_offices(business, offices)
        changed_sections.append("offices")

    if relationships:
        update_relationship_addresses(relationships, business)
        changed_sections.append("directors")

    filing_meta.review_imported_data = {"sectionsChanged": changed_sections}

    return _create_registrars_notation(business, filing_rec)
