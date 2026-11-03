# Copyright © 2026 Province of British Columbia
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

"""Tests for the filing section validation registry and dispatcher."""

from unittest.mock import MagicMock
from business_model.models import Business

from legal_api.services.filings.validations.sections import (
    SECTION_VALIDATORS,
    register_section_validator,
    validate_section,
)


def test_validate_section_successful_resolution():
    """Verify that a registered (filing_type, None, section) successfully resolves and executes."""
    mock_business = MagicMock(spec=Business)
    sample_data = {"legalName": "TEST NAME INC."}
    expected_errors = [{"error": "Sample validation error", "path": "/legalName"}]

    @register_section_validator("testFiling", "testSection")
    def mock_validator(business, filing_type, data, filing_sub_type=None):
        assert business == mock_business
        assert filing_type == "testFiling"
        assert data == sample_data
        assert filing_sub_type is None
        return expected_errors

    try:
        errors, is_supported = validate_section(
            business=mock_business,
            filing_type="testFiling",
            section="testSection",
            data=sample_data,
        )

        assert is_supported is True
        assert errors == expected_errors
    finally:
        SECTION_VALIDATORS.pop(("testFiling", None, "testSection"), None)


def test_validate_section_subtype_fallback():
    """Verify fallback to generic validator when a specific subtype is requested but not registered."""
    mock_business = MagicMock(spec=Business)
    sample_data = {"key": "value"}
    fallback_errors = []

    @register_section_validator("testFiling", "testSection")
    def fallback_validator(business, filing_type, data, filing_sub_type=None):
        assert filing_sub_type == "unregisteredSubtype"
        return fallback_errors

    try:
        errors, is_supported = validate_section(
            business=mock_business,
            filing_type="testFiling",
            section="testSection",
            data=sample_data,
            filing_sub_type="unregisteredSubtype",
        )

        assert is_supported is True
        assert errors == fallback_errors
    finally:
        SECTION_VALIDATORS.pop(("testFiling", None, "testSection"), None)


def test_validate_section_unsupported():
    """Verify that calling an unregistered filing_type or section returns (None, False)."""
    mock_business = MagicMock(spec=Business)

    errors, is_supported = validate_section(
        business=mock_business,
        filing_type="unknownFilingType",
        section="invalidSection",
        data={},
    )

    assert is_supported is False
    assert errors is None
