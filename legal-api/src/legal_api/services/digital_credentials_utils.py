# Copyright © 2025 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""This provides utility functions for specific actions related to digital credentials."""

import logging
import os
from typing import List, Union

from legal_api.models import Business, Party, PartyRole, User
from legal_api.utils.logging import setup_logging


setup_logging(os.path.join(os.path.abspath(os.path.dirname(
    __file__)), 'logging.conf'))  # important to do this first


business_party_role_mapping = {
    Business.LegalTypes.SOLE_PROP.value: PartyRole.RoleTypes.PROPRIETOR.value,
    Business.LegalTypes.PARTNERSHIP.value: PartyRole.RoleTypes.PARTNER.value,
    Business.LegalTypes.BCOMP.value: PartyRole.RoleTypes.DIRECTOR.value
}


class FormattedUser:
    """Formatted user class."""

    first_name: str
    last_name: str

    def __init__(self, user: Union[User, Party]):
        """Initialize the formatted user."""
        first_name, last_name = self._formatted_user(user)
        self.first_name = first_name
        self.last_name = last_name

    def _formatted_user(self, user: Union[User, Party]) -> dict:
        """Return the formatted name of the user."""
        first_name = (getattr(user, 'firstname', '') or getattr(
            user, 'first_name', '') or '').lower()
        last_name = (getattr(user, 'lastname', '') or getattr(
            user, 'last_name', '') or '').lower()
        middle_name = (getattr(user, 'middlename', '') or getattr(
            user, 'middle_initial', '') or '').lower()

        if middle_name:
            first_name = f'{first_name} {middle_name}'

        return first_name, last_name


def _parties_by_role(business: Business, role: PartyRole.RoleTypes) -> List[PartyRole]:
    """DEPRECATED: Return the party roles of a role type the business."""
    return PartyRole.get_parties_by_role(business.id, role)


def user_party_role(user: User, business: Business, role: PartyRole.RoleTypes) -> Union[PartyRole, None]:
    """DEPRECATED: Return the PartyRole if the user has a party role in the business."""
    if len(parties := _parties_by_role(business, role)) <= 0:
        logging.debug('No parties found for the business with role: %s.', role)
        return None

    for party_role in parties:
        if not (party := party_role.party):
            continue

        u = FormattedUser(user)
        p = FormattedUser(party)

        if u.first_name == p.first_name and u.last_name == p.last_name:
            return party_role

    logging.debug('No party found for the business with role: %s.', role)
    return None
