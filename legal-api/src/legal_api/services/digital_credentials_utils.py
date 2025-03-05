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
from datetime import datetime
from typing import List, Union

from legal_api.models import Business, Filing, Party, PartyRole, User
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


def _registration_filings(business: Business) -> List[Filing]:
    """Return the registration filings for the business."""
    return Filing.get_filings_by_types(business.id, ['registration'])


def _registration_filing(business: Business) -> Filing:
    """Return the registration filing for the business."""
    if len(filings := _registration_filings(business)) <= 0:
        return None

    return filings[0]


def _incorporation_filings(business: Business) -> List[Filing]:
    """Return the incorporation filings for the business."""
    return Filing.get_filings_by_types(business.id, ['incorporationApplication'])


def _incorporation_filing(business: Business) -> Filing:
    """Return the incorporation filing for the business."""
    if len(filings := _incorporation_filings(business)) <= 0:
        return None

    return filings[0]


def _parties_by_role(business: Business, role: PartyRole.RoleTypes) -> List[PartyRole]:
    """Return the party roles of a role type the business."""
    return PartyRole.get_parties_by_role(business.id, role)


def _completing_parties(registration_filing: Filing) -> List[PartyRole]:
    """Return the completing parties of the registration filing."""
    return PartyRole.get_party_roles_by_filing(
        registration_filing.id,
        datetime.utcnow(),
        PartyRole.RoleTypes.COMPLETING_PARTY.value,
    )


def user_completing_party_role(user: User, business: Business) -> Union[PartyRole, None]:
    """Return the PartyRole if the user is the completing party."""
    if not (filing := _registration_filing(business) or _incorporation_filing(business)):
        logging.debug(
            'No registration or incorporation filing found for the business.')
        return None

    if len(party_roles := _completing_parties(filing)) <= 0:
        logging.debug(
            'No completing parties found for the registration filing.')
        return None

    for party_role in party_roles:
        if (party := party_role.party) is None:
            continue

        cp = FormattedUser(party)
        u = FormattedUser(user)
        if (user.id == filing.submitter_id and
                u.first_name == cp.first_name and u.last_name == cp.last_name):
            return party_role

    logging.debug('No completing party found for the registration filing.')
    return None


def user_party_role(user: User, business: Business, role: PartyRole.RoleTypes) -> Union[PartyRole, None]:
    """Return the PartyRole if the user has a party role in the business."""
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
