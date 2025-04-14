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

from dateutil.parser import parse
from business_model.models import Business, Party


def find_resolution_with_largest_id(resolutions) -> Optional[Dict]:
    """Find the resolution with the largest id from the given list of resolutions."""
    return max(resolutions, key=lambda resolution: resolution.id, default=None)


def update_resolution(business: Business, resolution_correction) -> Optional[Dict]:
    """Update the resolution with the largest id."""
    if not business or not resolution_correction:
        return None

    # Find and update the resolution with the largest id
    largest_resolution = find_resolution_with_largest_id(business.resolutions.all())
    if largest_resolution:
        largest_resolution.resolution = resolution_correction

    return largest_resolution


def update_signatory(business: Business, signatory: Dict) -> Optional[Dict]:
    """Update the signatory with the largest id."""
    if not business or not signatory:
        return None

    largest_resolution = find_resolution_with_largest_id(business.resolutions.all())
    if not largest_resolution:
        return None

    # Update the resolution with the largest id
    party = Party(
        first_name=signatory.get('givenName', '').upper(),
        last_name=signatory.get('familyName', '').upper(),
        middle_initial=(signatory.get('additionalName', '') or '').upper(),
        title='',
        organization_name='',
        email='',
        identifier=''
    )
    largest_resolution.party = party
    return largest_resolution


def update_resolution_date(business: Business, date: str) -> Optional[Dict]:
    """Update the resolution_date with the largest id."""
    if not business or not date:
        return None

    largest_resolution = find_resolution_with_largest_id(business.resolutions.all())
    if not largest_resolution:
        return None

    # Update the resolution with the largest id
    largest_resolution.resolution_date = parse(date).date()
    return largest_resolution


def update_signing_date(business: Business, date: str) -> Optional[Dict]:
    """Update the signing_date with the largest id."""
    if not business or not date:
        return None

    largest_resolution = find_resolution_with_largest_id(business.resolutions.all())
    if not largest_resolution:
        return None

    # Update the resolution with the largest id
    largest_resolution.signing_date = parse(date).date()
    return largest_resolution
