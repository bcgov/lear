# Copyright © 2024 Province of British Columbia
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
"""Test Put back off validations."""
import copy

from registry_schemas.example_data import PUT_BACK_OFF, FILING_HEADER

from legal_api.services.filings.validations.put_back_off import validate

from tests.unit.models import factory_business


def test_put_back_off(session):
    """Assert valid put back off."""
    identifier = 'CP1234567'
    business = factory_business(identifier)

    filing_json = copy.deepcopy(FILING_HEADER)
    filing_json['filing']['business']['identifier'] = identifier
    filing_json['filing']['putBackOff'] = copy.deepcopy(PUT_BACK_OFF)

    err = validate(business, filing_json)
    assert err is None
