# Copyright © 2025 Province of British Columbia
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
"""
Processing auth affiliation actions.

Used in the event that a user is unaffiliated from a business where they have a DBC:

- Business Unaffiliated
- Team Member Removed

Note: The credential is not replaced, it is simply revoked.
"""
from flask import current_app

from business_model.models import DCRevocationReason


def process(idp_userid: str, login_source: str, unaffiliated_identifiers: list) -> None:
    """Process auth actions."""
    
    current_app.logger.debug(
        f"Process auth unaffiliation for user: {login_source} {idp_userid} from identifiers: {unaffiliated_identifiers}"
    )
    current_app.logger.warning(f"Auth unaffiliation processing not implemented yet. {DCRevocationReason.AUTH_UNAFFILIATED}")
