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
"""File processing rules and actions for the change of officers."""
import copy

from business_model.models import Business, Filing, PartyRole
from business_model.models.types.party_class_type import PartyClassType

from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors.filing_components.relationships import (
    cease_relationships,
    create_relationsips,
    update_relationship_addresses,
    update_relationship_entity_info,
)


def process(business: Business, filing_rec: Filing, filing_meta: FilingMeta):
    """Render the change_of_officers onto the business model objects."""
    filing_json = copy.deepcopy(filing_rec.filing_json)
    relationships = filing_json["filing"]["changeOfOfficers"].get("relationships")
    create_relationsips(relationships, business, filing_rec, PartyClassType.OFFICER)
    update_relationship_entity_info(relationships, business)
    update_relationship_addresses(relationships, business)

    valid_officer_roles = [
        PartyRole.RoleTypes.CEO.value,
        PartyRole.RoleTypes.CFO.value,
        PartyRole.RoleTypes.PRESIDENT.value,
        PartyRole.RoleTypes.VICE_PRESIDENT.value,
        PartyRole.RoleTypes.CHAIR.value,
        PartyRole.RoleTypes.TREASURER.value,
        PartyRole.RoleTypes.SECRETARY.value,
        PartyRole.RoleTypes.ASSISTANT_SECRETARY.value,
        PartyRole.RoleTypes.OTHER.value,
    ]
    cease_relationships(relationships, business, valid_officer_roles, filing_meta.application_date)
