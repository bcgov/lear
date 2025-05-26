# Copyright © 2020 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Manages the parties and party roles for a business."""
from __future__ import annotations

from typing import Dict, List, Optional

from legal_api.models import Business, Filing, PartyRole

from entity_filer.filing_processors.filing_components import create_party, create_role


def update_parties(business: Business, parties_structure: Dict, filing: Filing, delete_existing=True) -> Optional[List]:
    """Manage the party and party roles for a business.

    Assumption: The structure has already been validated, upon submission.

    Other errors are recorded and will be managed out of band.
    """
    if not business:
        # if nothing is passed in, we don't care and it's not an error
        return None

    err = []

    if parties_structure:
        if delete_existing:
            try:
                delete_parties(business)
            except:  # noqa:E722 pylint: disable=bare-except; catch all exceptions
                err.append(
                    {'error_code': 'FILER_UNABLE_TO_DELETE_PARTY_ROLES',
                     'error_message': f"Filer: unable to delete party roles for :'{business.identifier}'"}
                )
                return err

        try:
            for party_info in parties_structure:
                party = create_party(business_id=business.id, party_info=party_info, create=False)
                for role_type in party_info.get('roles'):
                    role_str = role_type.get('roleType', '').lower()
                    role = {
                        'roleType': role_str,
                        'appointmentDate': role_type.get('appointmentDate', None),
                        'cessationDate': role_type.get('cessationDate', None)
                    }
                    party_role = create_role(party=party, role_info=role)
                    if party_role.role in [PartyRole.RoleTypes.COMPLETING_PARTY.value,
                                           PartyRole.RoleTypes.INCORPORATOR.value,
                                           PartyRole.RoleTypes.APPLICANT.value]:
                        filing.filing_party_roles.append(party_role)
                    else:
                        business.party_roles.append(party_role)
        except KeyError:
            err.append(
                {'error_code': 'FILER_UNABLE_TO_SAVE_PARTIES',
                 'error_message': f"Filer: unable to save new parties for :'{business.identifier}'"}
            )
    return err


def delete_parties(business: Business):
    """Delete the party_roles for a business."""
    if existing_party_roles := business.party_roles.all():
        for role in existing_party_roles:
            if role.role not in [
                PartyRole.RoleTypes.OFFICER.value,
                PartyRole.RoleTypes.RECEIVER.value,
                PartyRole.RoleTypes.LIQUIDATOR.value,
            ]:
                business.party_roles.remove(role)
