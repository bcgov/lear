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

"""This provides the service for determining access rules to digital credentials."""

import logging
import os
from enum import Enum
from typing import List

from legal_api.models import Business, PartyRole, User
from legal_api.services.digital_credentials_utils import (
    business_party_role_mapping,
    user_completing_party_role,
    user_party_role,
)
from legal_api.utils.logging import setup_logging


setup_logging(os.path.join(os.path.abspath(os.path.dirname(
    __file__)), 'logging.conf'))  # important to do this first


class DigitalCredentialsRulesService:
    """Digital Credentials Rules service."""

    def are_digital_credentials_allowed(self, user: User, business: Business) -> bool:
        """Return True if the user is allowed to access digital credentials."""
        return self._has_general_access(user) and self._has_specific_access(user, business)

    def _has_general_access(self, user: User) -> bool:
        """Return Ture if general access rules are met."""
        if not user:
            logging.debug('No user is provided.')
            return False

        is_login_source_bcsc = user.login_source == 'BCSC'
        if not is_login_source_bcsc:
            logging.debug('User is not logged in with BCSC.')
            return False

        return True

    def _has_specific_access(self, user: User, business: Business) -> bool:
        """Return True if business rules are met."""
        if not business:
            logging.debug('No buisiness is provided.')
            return False

        if business.legal_type in [Business.LegalTypes.SOLE_PROP.value,
                                   Business.LegalTypes.PARTNERSHIP.value,
                                   Business.LegalTypes.BCOMP.value]:
            return True

        logging.debug('No specific access rules are met.')
        return False

    def is_completing_party_and_has_party_role(self, user, business, role: PartyRole.RoleTypes) -> bool:
        """Return True if the user is the completing party and has a valid party role business."""
        return (self.is_completing_party(user, business)
                and self.has_party_role(user, business, role))

    def is_completing_party(self, user: User, business: Business) -> bool:
        """Return True if the user is the completing party."""
        return user_completing_party_role(user, business) is not None

    def has_party_role(self, user: User, business: Business, role: PartyRole.RoleTypes) -> bool:
        """Return True if the user has a party role in the business."""
        return user_party_role(user, business, role) is not None

    def get_preconditions(self, user: User, business: Business) -> List[str]:
        """Return the preconditions for digital credentials."""

        class PreconditionsEnum(Enum):
            """Digital Credentials Preconditions Enum."""

            BUSINESS_ROLE = 'attest_party_role'
            COMPLETOR_ROLE = 'attest_completor_role'

        role = None
        if business.legal_type in business_party_role_mapping:
            role = business_party_role_mapping[business.legal_type]
        preconditions = []
        if (self.has_party_role(user, business, role)
                and not self.is_completing_party(user, business)):
            preconditions.append(PreconditionsEnum.BUSINESS_ROLE.value)

        if (business.legal_type == Business.LegalTypes.BCOMP
            and self.is_completing_party(user, business)
                and not self.has_party_role(user, business, role)):
            preconditions.append(PreconditionsEnum.COMPLETOR_ROLE.value)

        return preconditions
