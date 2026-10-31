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

"""
    Filing section validation registry.
    Helper to expose complex validations to the UI.
    Enables UI to send lightweight validation checks without having to construct the whole filing payload.
"""

from typing import Callable, Optional
from business_model.models import Business

SectionValidatorFn = Callable[
    [Business, str, dict, Optional[str]],
    list[dict]
]

SECTION_VALIDATORS: dict[tuple[str, Optional[str], str], SectionValidatorFn] = {}


def register_section_validator(
    filing_type: str,
    section: str,
    filing_sub_type: Optional[str] = None,
):
    """Decorator to register a validator function for a filing type and section."""
    def decorator(fn: SectionValidatorFn) -> SectionValidatorFn:
        key = (filing_type, filing_sub_type, section)
        if key in SECTION_VALIDATORS:
            raise KeyError(f"Validator already registered for {key}")
        SECTION_VALIDATORS[key] = fn
        return fn
    return decorator


def validate_section(
    business: Business,
    filing_type: str,
    section: str,
    data: dict,
    filing_sub_type: Optional[str] = None,
) -> tuple[Optional[list[dict]], bool]:
    """Validate data to the appropriate section validator.

    Returns:
        (errors, is_supported): errors list and boolean indicating if a validator was found.
    """
    validator_fn = None
    if filing_sub_type:
        validator_fn = SECTION_VALIDATORS.get((filing_type, filing_sub_type, section))

    if not validator_fn:
        validator_fn = SECTION_VALIDATORS.get((filing_type, None, section))

    if not validator_fn:
        return None, False

    return validator_fn(business, filing_type, data, filing_sub_type), True


from . import correction  # noqa: F401, E402
