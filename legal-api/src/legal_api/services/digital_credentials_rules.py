# Copyright © 2024 Province of British Columbia
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

"""This provides the service for determining access rules to digital credentials."""

import logging
import os
from datetime import datetime
from typing import List, Union

from legal_api.models import Filing, PartyRole
from legal_api.models.business import Business
from legal_api.models.party import Party
from legal_api.models.user import User
from legal_api.utils.logging import setup_logging


setup_logging(os.path.join(os.path.abspath(os.path.dirname(
    __file__)), 'logging.conf'))  # important to do this first


class DigitalCredentialsRulesService:
    """Digital Credentials Rules service."""

    def registration_filings(self, business: Business) -> List[Filing]:
        """Return the registration filings for the business."""
        return Filing.get_filings_by_types(business.id, ['registration'])

    def registration_filing(self, business: Business) -> Filing:
        """Return the registration filing for the business."""
        if len(registration_filings := self.registration_filings(business)) <= 0:
            return None

        return registration_filings[0]

    def proprietors(self, business: Business) -> List[PartyRole]:
        """Return the proprietors of the business."""
        return PartyRole.get_parties_by_role(
            business.id, PartyRole.RoleTypes.PROPRIETOR.value
        )

    def completing_parties(self, registration_filing: Filing) -> List[PartyRole]:
        """Return the completing parties of the registration filing."""
        return PartyRole.get_party_roles_by_filing(
            registration_filing.id,
            datetime.utcnow(),
            PartyRole.RoleTypes.COMPLETING_PARTY.value,
        )

    def formatted_user(self, user: Union[User, Party]) -> dict:
        """Return the formatted name of the user."""
        first_name = (getattr(user, 'firstname', '') or getattr(
            user, 'first_name', '') or '').lower()
        last_name = (getattr(user, 'lastname', '') or getattr(
            user, 'last_name', '') or '').lower()
        middle_name = (getattr(user, 'middlename', '') or getattr(
            user, 'middle_initial', '') or '').lower()

        if middle_name:
            first_name = f'{first_name} {middle_name}'

        return {
            'first_name': first_name,
            'last_name': last_name,
        }

    def are_digital_credentials_allowed(self, user: User, business: Business) -> bool:
        return self.has_general_access(user) and self.has_specific_access(user, business)

    def has_general_access(self, user: User) -> bool:
        """Return Ture if general access rules are met."""
        if not user:
            logging.debug('No user is provided.')
            return False

        is_login_source_bcsc = user.login_source == 'BCSC'
        if not is_login_source_bcsc:
            logging.debug('User is not logged in with BCSC.')
            return False

        return True

    def has_specific_access(self, user: User, business: Business) -> bool:
        """Return True if business rules are met."""
        if not business:
            logging.debug('No buisiness is provided.')
            return False

        if business.legal_type == Business.LegalTypes.SOLE_PROP.value:
            return self.is_self_registered_owner_operator(user, business)

        return False

    def is_self_registered_owner_operator(self, user, business) -> bool:
        """Return True if the user is the self-registered owner operator of the business."""
        if not (registration_filing := self.registration_filing(business)):
            logging.debug('No registration filing found for the business.')
            return False

        if len(proprietors := self.proprietors(business)) <= 0:
            logging.debug('No proprietors found for the business.')
            return False

        if len(completing_parties := self.completing_parties(registration_filing)) <= 0:
            logging.debug(
                'No completing parties found for the registration filing.')
            return False

        if not (proprietor := proprietors[0].party):
            logging.debug('No proprietor found for the business.')
            return False

        if not (completing_party := completing_parties[0].party):
            logging.debug(
                'No completing party found for the registration filing.')
            return False

        cp_first_name, cp_last_name = self.formatted_user(
            completing_party).values()
        p_first_name, p_last_name = self.formatted_user(proprietor).values()
        u_first_name, u_last_name = self.formatted_user(user).values()

        return (
            registration_filing.submitter_id == user.id
            and cp_first_name == p_first_name
            and cp_last_name == p_last_name
            and p_first_name == u_first_name
            and p_last_name == u_last_name
        )
