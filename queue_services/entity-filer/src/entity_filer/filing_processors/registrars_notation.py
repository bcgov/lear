# Copyright © 2021 Province of British Columbia
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
"""File processing rules and actions for the registrars notation filing."""
from contextlib import suppress
from datetime import datetime
from typing import Dict

from legal_api.models import Comment, Filing


def process(registrars_notation_filing: Filing, filing: Dict):
    """Render the registrars notation filing into the business model objects."""
    registrars_notation_filing.court_order_file_number = filing['registrarsNotation'].get('fileNumber')
    registrars_notation_filing.court_order_effect_of_order = filing['registrarsNotation'].get('effectOfOrder')

    with suppress(IndexError, KeyError, TypeError, ValueError):
        registrars_notation_filing.court_order_date = datetime.fromisoformat(
            filing['registrarsNotation'].get('orderDate'))

    # add comment to the registrars notation filing
    registrars_notation_filing.comments.append(
        Comment(
            comment=filing['registrarsNotation']['orderDetails'],
            staff_id=registrars_notation_filing.submitter_id
        )
    )
