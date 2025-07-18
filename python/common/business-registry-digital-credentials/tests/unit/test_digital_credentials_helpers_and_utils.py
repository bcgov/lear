# Copyright © 2025 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tests for digital credentials helpers and utility functions.

Test suite to ensure that helpers and utility functions for digital credentials are working as expected
"""

import pytest
from business_model.models import Party, User
from business_registry_digital_credentials.digital_credentials_utils import (
    FormattedUser,
    determine_allowed_business_types,
)


@pytest.mark.parametrize(
    "test_user, expected",
    [
        (Party(**{"first_name": "First", "last_name": "Last"}), {"first_name": "first", "last_name": "last"}),
        (
            Party(**{"first_name": "First", "middle_initial": "M", "last_name": "Last"}),
            {"first_name": "first m", "last_name": "last"},
        ),
        (User(**{"firstname": "First", "lastname": "Last"}), {"first_name": "first", "last_name": "last"}),
        (
            User(**{"firstname": "First", "middlename": "M", "lastname": "Last"}),
            {"first_name": "first m", "last_name": "last"},
        ),
        (User(), {"first_name": "", "last_name": ""}),
        (Party(), {"first_name": "", "last_name": ""}),
    ],
)
def test_formatted_user(test_user, expected):
    """Assert that the user is formatted correctly."""

    assert FormattedUser(test_user).__dict__ == expected


@pytest.mark.parametrize(
    "flag_value, valid_registration_types, valid_incorporation_types, expected",
    [
        ({"types": ["SP", "BEN", "GP"]}, ["SP", "GP"], ["BEN"], ["SP", "BEN", "GP"]),
        ({"types": ["SP", "BEN", "GP", "CBEN"]}, ["SP", "GP"], ["BEN"], ["SP", "BEN", "GP"]),
        ({"types": ["SP"]}, ["SP", "GP"], ["BEN"], ["SP", "BEN", "GP"]),
        ({"types": []}, ["SP", "GP"], ["BEN"], ["SP", "BEN", "GP"]),
        ({"types": ["SP", "GP"]}, [], ["BEN"], ["SP", "BEN", "GP"]),
        ({"types": ["SP", "BEN"]}, ["SP", "GP"], [], ["SP", "BEN", "GP"]),
    ],
)
def test_determine_allowed_business_types(
    app, flag_value, valid_registration_types, valid_incorporation_types, expected
):
    """Test filtering of allowed business types based on flag values."""

    # The app fixture provides Flask context, so current_app.logger works
    result = determine_allowed_business_types(valid_registration_types, valid_incorporation_types)
    assert sorted(result) == sorted(expected)


@pytest.mark.parametrize(
    "flag_value, valid_registration_types, valid_incorporation_types, expected",
    [
        (["SP", "BEN", "GP"], ["SP", "GP"], ["BEN"], ["SP", "BEN", "GP"]),
        ({}, ["SP"], ["BEN"], ["SP", "BEN", "GP"]),
        ({"types": "SP"}, ["SP"], ["BEN"], ["SP", "BEN", "GP"]),
        ({"types": 123}, ["SP"], ["BEN"], ["SP", "BEN", "GP"]),
        ({"type": ["SP", "BEN", "GP"]}, ["SP"], ["BEN"], ["SP", "BEN", "GP"]),
        ("not-a-object", ["SP"], ["BEN"], ["SP", "BEN", "GP"]),
        (123, ["SP"], ["BEN"], ["SP", "BEN", "GP"]),
    ],
)
def test_determine_allowed_business_types_invalid_flags(
    app, flag_value, valid_registration_types, valid_incorporation_types, expected
):
    """Test filtering of allowed business types based on flag values."""

    # The app fixture provides Flask context, so current_app.logger works
    result = determine_allowed_business_types(valid_registration_types, valid_incorporation_types)
    assert sorted(result) == sorted(expected)


def test_determine_allowed_business_types_missing_flag(app):
    """Test filtering of allowed business types based on flag value not set."""

    # The app fixture provides Flask context, so current_app.logger works
    result = determine_allowed_business_types(["SP", "GP"], ["BEN"])
    assert result == ["SP", "BEN", "GP"]
