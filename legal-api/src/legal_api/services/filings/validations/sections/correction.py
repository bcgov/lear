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

"""Partial data validations for correction filings."""

from business_model.models import Business
from legal_api.services.filings.validations.correction import (
    validate_legal_name_designation_unchanged,
)

from . import register_section_validator


@register_section_validator("correction", "nameRequest")
def validate_correction_name_request(
    business: Business,
    filing_type: str,
    data: dict,
    filing_sub_type: str | None = None,
) -> list[dict]:
    """Validate legal name designation preservation for correction filings."""
    return validate_legal_name_designation_unchanged(
        business=business,
        new_legal_name=data.get("legalName"),
        err_path="/legalName",
    )