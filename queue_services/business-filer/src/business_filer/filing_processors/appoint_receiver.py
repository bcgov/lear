# Copyright © 2025 Province of British Columbia
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
"""File processing rules and actions for the appoint receiver."""
from typing import Dict

from business_model.models import Business, Filing

from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors.filing_components.parties import update_parties


def process(business: Business, filing: Dict, filing_rec: Filing, filing_meta: FilingMeta):
    # pylint: disable=too-many-branches;
    """Render the appoint_receiver onto the business model objects."""
    appoint_receiver_filing = filing.get('appointReceiver')
    if not appoint_receiver_filing.get('parties'):
        return

    if parties := appoint_receiver_filing.get('parties'):
        update_parties(business, parties, filing_rec, False)
