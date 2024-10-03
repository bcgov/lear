# Copyright © 2024 Province of British Columbia
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
"""Test suite to ensure the Notice of Withdrawal filing is validated correctly."""
import copy
from datetime import date
from http import HTTPStatus

import pytest

from legal_api.models import Filing
from legal_api.services.filings import validate
from legal_api.services.filings.validations.notice_of_withdrawal import validate_withdrawn_filing


# setup
