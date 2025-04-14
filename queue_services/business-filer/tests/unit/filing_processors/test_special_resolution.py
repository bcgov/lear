# Copyright © 2021 Province of British Columbia
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
