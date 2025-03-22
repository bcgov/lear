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
from datetime import datetime, timezone
from enum import Enum
from typing import List

from legal_api.models import Business, Filing, Party, PartyRole, User
from legal_api.services.digital_credentials_utils import FormattedUser
from legal_api.utils.logging import setup_logging


setup_logging(os.path.join(os.path.abspath(os.path.dirname(
    __file__)), 'logging.conf'))  # important to do this first


class DigitalCredentialsRulesService:
    """Digital Credentials Rules service."""

    class FilingTypes(Enum):
        """Filing Types Enum."""

        REGISTRATION = 'registration'
        INCORPORATION_APPLICATION = 'incorporationApplication'

    valid_filing_types = [
        FilingTypes.REGISTRATION.value,
        FilingTypes.INCORPORATION_APPLICATION.value,
    ]

    valid_registration_types = [
        Business.LegalTypes.SOLE_PROP.value,
        Business.LegalTypes.PARTNERSHIP.value,
    ]

    valid_incorporation_types = [
        Business.LegalTypes.BCOMP.value,
    ]

    valid_business_types = valid_registration_types + valid_incorporation_types

    def are_digital_credentials_allowed(self, user: User, business: Business) -> bool:
        """Return True if the user is allowed to access digital credentials."""
        return self._has_general_access(user) and self._has_specific_access(user, business)

    def get_preconditions(self, user: User, business: Business) -> List[str]:
        """Return the preconditions for digital credentials."""
        preconditions = []
        if not self.user_is_completing_party(user, business):
            if self.user_has_business_party_role(user, business):
                preconditions += self.user_business_party_roles(user, business)
            if self.user_has_filing_party_role(user, business):
                preconditions += self.user_filing_party_roles(user, business)
        return list(map(lambda party_role: 'attest_' + party_role.role, preconditions))

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

        if business.legal_type in self.valid_business_types:
            return (self.user_has_filing_party_role(user, business)
                    or self.user_has_business_party_role(user, business))

        logging.debug('No specific access rules are met.')
        return False

    def user_is_completing_party(self, user: User, business: Business) -> bool:
        """Return True if the user is the completing party."""
        if len(filings := self.valid_filings(business)) <= 0:
            logging.debug(
                'No registration or incorporation filing found for the business.')
            return False

        filing = filings.pop(0)
        return self.user_submitted_filing(user, filing) and self.user_matches_completing_party(user, filing)

    def user_has_filing_party_role(self, user: User, business: Business) -> bool:
        """
        Return True if the user has a filing party role in the business. Excludes the completing party role.

        For example: if a user is an incorporator.
        """
        return len(self.user_filing_party_roles(user, business)) > 0

    def user_has_business_party_role(self, user: User, business: Business) -> bool:
        """
        Return True if the user has a business party role in the business.

        For example: if a user is a director.
        """
        return len(self.user_business_party_roles(user, business)) > 0

    def user_filing_party_roles(self, user: User, business: Business) -> List[PartyRole]:
        """Return the filing roles of the user for the business, if any."""
        if len(filings := self.valid_filings(business)) <= 0:
            logging.debug(
                'No registration or incorporation filing found for the business.')
            return []

        if business.legal_type in self.valid_registration_types:
            return []

        filing = filings.pop(0)
        roles = filing.filing_party_roles.filter(
            PartyRole.role != PartyRole.RoleTypes.COMPLETING_PARTY.value).all()
        return list(filter(lambda role: self.user_matches_party(user, role.party), roles))

    def user_business_party_roles(self, user: User, business: Business) -> List[PartyRole]:
        """Return the party roles of the user for the business, if any."""
        roles = business.party_roles.all()
        return list(filter(lambda role: self.user_matches_party(user, role.party), roles))

    def user_submitted_filing(self, user: User, filing: Filing) -> bool:
        """Return True if the user submitted the filing."""
        did_user_submit_filing = user.id == filing.submitter_id
        if not did_user_submit_filing:
            logging.debug('User is not the filing submitter.')
        return did_user_submit_filing

    def user_matches_completing_party(self, user: User, filing: Filing) -> bool:
        """Return the True if the user matches a completing party."""
        if len(roles := self.completing_party_roles(filing)) <= 0:
            logging.debug(
                'No completing parties found for the registration or incorporation filing.')
            return False

        is_user_completing_party = len(
            list(filter(lambda role: self.user_matches_party(user, role.party), roles))) > 0
        if not is_user_completing_party:
            logging.debug('User is not the completing party.')
        return is_user_completing_party

    def user_matches_party(self, user: User, party: Party) -> bool:
        """Return True if the user matches the party."""
        u = FormattedUser(user)
        p = FormattedUser(party)
        return u.first_name == p.first_name and u.last_name == p.last_name

    def valid_filings(self, business: Business) -> List[Filing]:
        """Return the registration or incorporation filings for the business."""
        return Filing.get_filings_by_types(business.id, self.valid_filing_types)

    def completing_party_roles(self, filing: Filing) -> List[PartyRole]:
        """Return the completing parties of a filing."""
        return PartyRole.get_party_roles_by_filing(
            filing.id,
            datetime.now(timezone.utc),
            PartyRole.RoleTypes.COMPLETING_PARTY.value,
        )

    def filing_party_roles(self, filing: Filing) -> List[PartyRole]:
        """Return the party roles of a filing."""
        return PartyRole.get_party_roles_by_filing(
            filing.id,
            datetime.now(timezone.utc),
        )
