# Copyright © 2019 Province of British Columbia
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
"""Test Correction SPECIAL_RESOLUTION validations."""

import copy

from registry_schemas.example_data import CORRECTION_CP_SPECIAL_RESOLUTION, CP_SPECIAL_RESOLUTION_TEMPLATE

from legal_api.services.filings import validate
from tests.unit.models import factory_business, factory_completed_filing

CP_SPECIAL_RESOLUTION_APPLICATION = copy.deepcopy(CP_SPECIAL_RESOLUTION_TEMPLATE)
CORRECTION = copy.deepcopy(CORRECTION_CP_SPECIAL_RESOLUTION)


def test_valid_special_resolution_correction(session):
    """Test that a valid SPECIAL_RESOLUTION correction passes validation."""
    # setup
    identifier = 'CP1234567'
    business = factory_business(identifier)

    corrected_filing = factory_completed_filing(business, CP_SPECIAL_RESOLUTION_APPLICATION)

    f = copy.deepcopy(CORRECTION)
    f['filing']['header']['identifier'] = identifier
    f['filing']['correction']['correctedFilingId'] = corrected_filing.id

    err = validate(business, f)

    if err:
        print(err.msg)

    # check that validation passed
    assert None is err
