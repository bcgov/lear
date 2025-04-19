# Copyright © 2025 Province of British Columbia
#
# Licensed under the BSD 3 Clause License, (the "License");
# you may not use this file except in compliance with the License.
# The template for the license can be found here
#    https://opensource.org/license/bsd-3-clause/
#
# Redistribution and use in source and binary forms,
# with or without modification, are permitted provided that the
# following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS”
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
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
