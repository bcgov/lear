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


def float_to_str(f, precision=17):
    """Convert the given float to a string without resorting to scientific notation."""
    ctx = decimal.Context()  # create a new context for this task
    ctx.prec = precision

    value = ctx.create_decimal(repr(f))
    return format(value, "f")
