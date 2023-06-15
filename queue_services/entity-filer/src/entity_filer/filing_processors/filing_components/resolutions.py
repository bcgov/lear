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
"""Manages the resolutions of a Business."""
from typing import Dict, Optional

from flask_babel import _ as babel  # noqa: N813
from legal_api.models import Business, Party


def find_resolution_with_largest_id(resolutions) -> Optional[Dict]:
    """Find the resolution with the largest id from the given list of resolutions."""
    return max(resolutions, key=lambda resolution: resolution.id, default=None)


def update_resolution(business: Business, resolution_correction) -> Dict:
    """Update the resolution with the largest id."""
    if not business:
        return None

    if not resolution_correction:
        return {'error': babel('Resolution correction text is required.')}

    largest_resolution = find_resolution_with_largest_id(business.resolutions.all())

    # Update the resolution with the largest id
    if largest_resolution:
        largest_resolution.resolution = resolution_correction
        return largest_resolution
    return None


def update_signatory(business: Business, signatory: Dict) -> Dict:
    """Update the signatory with the largest id."""
    if not signatory:
        return None

    if not business:
        return {'error': babel('A business is required to update signatory.')}

    largest_resolution = find_resolution_with_largest_id(business.resolutions.all())

    # Update the resolution with the largest id
    if largest_resolution:
        party = Party(
            first_name=signatory.get('givenName', '').upper(),
            last_name=signatory.get('familyName', '').upper(),
            middle_initial=(signatory.get('additionalName', '') or '').upper()
        )
        largest_resolution.party = party
        return largest_resolution
