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
"""The Unit Tests for the Special Resolution filing."""
import copy
import pytest

from registry_schemas.example_data import SPECIAL_RESOLUTION as special_resolution_json, FILING_HEADER

from business_filer.filing_processors import special_resolution
from tests.unit import create_business, create_filing
from business_model.models import  Resolution


@pytest.mark.parametrize('legal_type,identifier,special_resolution_type', [
    ('CP', 'CP1234567', 'specialResolution'),
])
def test_special_resolution(app, session, legal_type, identifier, special_resolution_type):
    """Assert that the resolution is processed."""
    # setup
    filing_json = copy.deepcopy(FILING_HEADER)
    filing_json['filing']['header']['name'] = special_resolution_type

    filing_json['filing']['business']['identifier'] = identifier
    filing_json['filing']['business']['legalType'] = legal_type

    filing_json['filing']['specialResolution'] = special_resolution_json

    business = create_business(identifier, legal_type=legal_type)

    filing = create_filing('123', filing_json)

    # test
    special_resolution.process(business, filing_json['filing'], filing)

    business.save()

    # validate
    assert len(business.resolutions.all()) == 1
    resolution = business.resolutions.all()[0]
    assert resolution.id
    assert resolution.resolution_sub_type == special_resolution_type
