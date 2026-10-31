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

"""Test for Partial data validations for correction filings."""

from unittest.mock import MagicMock
from business_model.models import Business
from legal_api.services.filings.validations.sections.correction import (
    validate_correction_name_request
)

def test_validate_correction_name_request(session):
    """Test that the section adapter extracts legalName and formats errors."""
    business = MagicMock(spec=Business)
    business.identifier = "BC1234567"
    business.legal_type = getattr(Business.LegalTypes, "COMP", "BC")
    business.legal_name = "OLD NAME LTD."

    res_empty = validate_correction_name_request(business, "correction", {})
    assert isinstance(res_empty, list)

    res_mismatch = validate_correction_name_request(
        business, "correction", {"legalName": "NEW NAME INC."}
    )
    assert isinstance(res_mismatch, list)
    assert len(res_mismatch) > 0
    assert any("LTD." in err.get("error", "") for err in res_mismatch)

    res_valid = validate_correction_name_request(
        business, "correction", {"legalName": "NEW NAME LTD."}
    )
    assert res_valid == []
