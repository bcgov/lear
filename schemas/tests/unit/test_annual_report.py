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
"""Test Suite to ensure annual report schemas are valid."""
from registry_schemas import validate
from registry_schemas.example_data import ANNUAL_REPORT


def test_annual_report_schema():
    """Assert that the JSONSchema validator is working."""
    ar_json = {'annualReport': ANNUAL_REPORT['filing']['annualReport']}

    is_valid, errors = validate(ar_json, 'annual_report')

    if errors:
        for err in errors:
            print(err.message)
    print(errors)

    assert is_valid


def test_validate_no_office():
    """Assert that an offices node is present in the Annual Report."""
    ar_json = {'annualReport': ANNUAL_REPORT['filing']['annualReport']}
    mailing_address = ar_json['annualReport']['offices']['registeredOffice']['mailingAddress']
    delivery_address = ar_json['annualReport']['offices']['registeredOffice']['deliveryAddress']
    del ar_json['annualReport']['offices']
    ar_json['annualReport']['mailingAddress'] = mailing_address
    ar_json['annualReport']['deliveryAddress'] = delivery_address

    is_valid, errors = validate(ar_json, 'annual_report')

    if errors:
        for err in errors:
            print(err.message)
    print(errors)

    assert not is_valid
