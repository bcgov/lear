# Copyright © 2023 Province of British Columbia
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
"""Custom formatting."""
import decimal
import re


def float_to_str(f, precision=17):
    """Convert the given float to a string without resorting to scientific notation."""
    ctx = decimal.Context()  # create a new context for this task
    ctx.prec = precision

    value = ctx.create_decimal(repr(f))
    return format(value, 'f')


def normalize_phone(phone: str) -> str:
    """
    Normalize a phone number by stripping all non-digit characters.

    This function takes a phone number string in various formats
    (e.g., "555-555-5555", "555 555 5555", "(555) 555-5555", "+1 (555) 555-5555") and returns
    a normalized string containing only digits.

    Args:
        phone_number (str): The phone number string to normalize.

    Returns:
        str: The normalized phone number containing only digits.
             Example: "5555555555".
    """
    # keep only digits
    digits = re.sub(r"\D", "", phone)

    # handle North America: allow 10 digits, or 11 with leading "1"
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits
