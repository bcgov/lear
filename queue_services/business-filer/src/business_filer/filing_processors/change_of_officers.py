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
"""File processing rules and actions for the change of directors."""
import copy
from datetime import datetime, timezone

from business_model.models import Business, Filing, PartyRole, Party, Address, db
from business_model.models.types.party_class_type import PartyClassType

from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors.filing_components import update_address, create_address

OFFICER_ROLE_CONVERTER = {
    'ceo': PartyRole.RoleTypes.CEO,
    'cfo': PartyRole.RoleTypes.CFO,
    'president': PartyRole.RoleTypes.PRESIDENT,
    'vice president': PartyRole.RoleTypes.VICE_PRESIDENT,
    'chair': PartyRole.RoleTypes.CHAIR,
    'treasurer': PartyRole.RoleTypes.TREASURER,
    'secretary': PartyRole.RoleTypes.SECRETARY,
    'assistant secretary': PartyRole.RoleTypes.ASSISTANT_SECRETARY,
    'other': PartyRole.RoleTypes.OTHER,
}

def process(business: Business, filing_rec: Filing, filing_meta: FilingMeta):  # noqa: PLR0912
    """Render the change_of_officers onto the business model objects."""
    filing_json = copy.deepcopy(filing_rec.filing_json)

    # get list of submitted officers
    if not (submitted_officers := filing_json["filing"]["changeOfOfficers"].get("relationships")):
        return
    
    # get all active officers to compare when updating parties
    end_date = datetime.now(timezone.utc).date()
    active_roles = PartyRole.get_party_roles_by_class_type(business.id, PartyClassType.OFFICER, end_date)
    existing_officers: dict[int, list[PartyRole]] = {} # { party_id: [PartyRole, PartyRole, ...] }

    # group roles by party id
    for pr in active_roles:
        if pr.party_id not in existing_officers:
            existing_officers[pr.party_id] = []
        existing_officers[pr.party_id].append(pr)

    
    # loop through submitted officers and create or update Party, Address and PartyRole's
    for officer in submitted_officers:
        entity = officer.get('entity', {})
        id_str = entity.get('identifier')
        party_id = None

        # submitted identifier is a string, convert to int to match party id
        if id_str:
            try:
                party_id = int(id_str)
            except (ValueError, TypeError):
                party_id = None

        # update existing party and roles
        if party_id:
            party = Party.find_by_id(party_id)
            # skip party if submitted id can't be found
            if not party:
                continue
            
            # update party fields
            party.first_name = entity.get('givenName', '').strip().upper()
            party.last_name = entity.get('familyName', '').strip().upper()
            party.middle_initial = entity.get('middleInitial', '').strip().upper()
            party.alternate_name = entity.get('alternateName', '').strip().upper()

            # update or create party addresses
            if new_delivery_address := officer.get('deliveryAddress'):
                if party.delivery_address:
                    party.delivery_address = update_address(party.delivery_address, new_delivery_address)
                else:
                    new_address = create_address(new_delivery_address, Address.DELIVERY)
                    party.delivery_address = new_address
                    db.session.add(new_address)

            if new_mailing_address := officer.get('mailingAddress'):
                if party.mailing_address:
                    party.mailing_address = update_address(party.mailing_address, new_mailing_address)
                else:
                    new_address = create_address(new_mailing_address, Address.MAILING)
                    party.mailing_address = new_address
                    db.session.add(new_address)
            
            # update or create roles for party
            current_party_roles = existing_officers.get(party_id, [])
            for role in officer.get('roles', []):
                role_str = role.get('roleType', '').strip().lower()
                role_enum = OFFICER_ROLE_CONVERTER.get(role_str)

                # skip role if not found
                if not role_enum:
                    continue

                has_cessation_date = role.get('cessationDate') is not None
                
                # check if role already exists
                existing_role = next((pr for pr in current_party_roles if pr.role == role_enum.value), None)

                if existing_role:
                    # cease role if submitted with cessation date, else do not update the role
                    if has_cessation_date:
                        existing_role.cessation_date = filing_rec.effective_date        
                else:
                    # create new role for party, ignore new roles submitted with a cessation date
                    if not has_cessation_date:
                        new_party_role = PartyRole(
                            role=role_enum.value,
                            appointment_date=filing_rec.effective_date,
                            party_class_type=PartyClassType.OFFICER,
                            party=party
                        )
                        db.session.add(new_party_role)
        # create new party and roles
        else:
            new_party = Party(
                first_name=entity.get('givenName', '').strip().upper(),
                last_name=entity.get('familyName', '').strip().upper(),
                middle_initial=entity.get('middleInitial', '').strip().upper(),
                alternate_name=entity.get('alternateName', '').strip().upper()
            )
            db.session.add(new_party)

            # create addresses for new party
            if new_delivery_address := officer.get('deliveryAddress'):
                new_address = create_address(new_delivery_address, Address.DELIVERY)
                new_party.delivery_address = new_address
                db.session.add(new_address)
            if new_mailing_address := officer.get('mailingAddress'):
                new_address = create_address(new_mailing_address, Address.MAILING)
                new_party.mailing_address = new_address
                db.session.add(new_address)

            # create roles for new party
            for role in officer.get('roles', []):
                # ignore roles submitted with cessation date
                if not role.get('cessationDate'):
                    role_str = role.get('roleType', '').strip().lower()
                    role_enum = OFFICER_ROLE_CONVERTER.get(role_str)
                    new_party_role = PartyRole(
                        role=role_enum.value,
                        appointment_date=filing_rec.effective_date,
                        party_class_type=PartyClassType.OFFICER,
                        party=new_party
                    )
                    db.session.add(new_party_role)
