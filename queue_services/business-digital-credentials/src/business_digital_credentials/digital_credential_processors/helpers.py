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
"""Event-payload helpers specific to the digital-credentials queue service.

Credential-lifecycle helpers (issue / revoke / replace / get-all) have moved
to ``business_registry_digital_credentials`` so legal-api can share them. The
helpers that remain here parse Cloud-Event payload dicts, which only the queue
service deals with.
"""

from business_model.models import DCBusinessUser


def _does_officer_match_user(officer: dict, user: DCBusinessUser) -> bool:
    """Check if officer name matches user name (case insensitive)."""
    return (
        officer.get("firstName", "").lower() == user.firstname.lower()
        and officer.get("lastName", "").lower() == user.lastname.lower()
    )


def is_user_in_officers(
    user: DCBusinessUser,
    filing_data: dict,
    role_name: str,
) -> bool:
    """Check if the user associated with the business user is in the filing parties as a specific role."""
    for party in filing_data.get("parties", []):
        officer = party.get("officer", {})
        roles = party.get("roles", [])
        has_partner_role = any(role.get("roleType").lower() == role_name.lower() for role in roles)
        if _does_officer_match_user(officer, user) and has_partner_role:
            return True
    return False


def does_officer_have_action(
    user: DCBusinessUser,
    filing_data: dict,
    officer_type: str,
    action_type: str,
) -> bool:
    """Check if a type of officer has a specific action on them.

    e.g., Check if a director has a 'ceased' action.
    """
    for officer_record in filing_data.get(officer_type, []):
        officer = officer_record.get("officer", {})
        if _does_officer_match_user(officer, user):
            actions = [a.lower() for a in officer_record.get("actions", [])]
            if action_type.lower() in actions:
                return True
            break
    return False
