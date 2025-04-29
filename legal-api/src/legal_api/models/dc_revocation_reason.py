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
"""This module holds revocation reasons for digital credentials."""
from enum import Enum


class DCRevocationReason(Enum):
    """Digital Credential Revocation Reasons."""

    ADMINISTRATIVE_REVOCATION = 'Your credential was revoked.'
    UPDATED_INFORMATION = 'You were offered a new credential with updated information ' \
        'and that revoked all previous copies.'
    VOLUNTARY_DISSOLUTION = 'You chose to dissolve your business. ' \
        'A new credential was offered that reflects the new company status and that revoked all previous copies.'
    ADMINISTRATIVE_DISSOLUTION = 'Your business was dissolved by the Registrar.'
    PUT_BACK_ON = 'Your business was put back on the Registry. '
    SELF_REISSUANCE = 'You chose to issue yourself a new credential and that revoked all previous copies.'
    SELF_REVOCATION = 'You chose to revoke your own credential.'