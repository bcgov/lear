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
"""Digital Business Card (DBC) shared package.

Centralizes the Traction REST client, access-rules engine, credential helpers,
and credential-lifecycle DB wrappers used by both legal-api and the
business-digital-credentials queue service.
"""

# Import the service class and create the module-level singleton FIRST.
# Modules imported below (e.g. ``digital_credentials_lifecycle``) reference this
# attribute at top-level, so it must exist before they are imported.
from .digital_credentials import DigitalCredentialsService

digital_credentials = DigitalCredentialsService()

from .digital_credentials_auth import (
    are_digital_credentials_allowed,
    get_digital_credentials_preconditions,
)
from .digital_credentials_helpers import (
    extract_invitation_message_id,
    get_digital_credential_data,
    get_or_create_business_user,
    get_roles,
)
from .digital_credentials_lifecycle import (
    get_all_digital_credentials_for_business,
    issue_digital_credential,
    replace_digital_credential,
    revoke_digital_credential,
)
from .digital_credentials_rules import DigitalCredentialsRulesService
