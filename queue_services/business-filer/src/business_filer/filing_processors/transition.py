# Copyright © 2020 Province of British Columbia
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
"""File processing rules and actions for the transition of a business."""
from typing import Dict

from business_filer.exceptions import QueueException
from business_model.models import Business, Filing

from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors.filing_components import aliases, shares
from business_filer.filing_processors.filing_components.offices import update_offices
from business_filer.filing_processors.filing_components.parties import update_parties


def process(business: Business, filing_rec: Filing, filing: Dict, filing_meta: FilingMeta):
    # pylint: disable=too-many-locals; 1 extra
    """Process the incoming transition filing."""
    # Extract the filing information for transition application
    if not (transition_filing := filing.get('transition')):  # pylint: disable=superfluous-parens;
        raise QueueException(f'legal_filing:transition data missing from {filing_rec.id}')
    if not business:
        raise QueueException(f'Business does not exist: legal_filing:transitionApplication {filing_rec.id}')

    # Initial insert of the business record
    business.restriction_ind = transition_filing.get('hasProvisions')

    if offices := transition_filing['offices']:
        update_offices(business, offices)

    if parties := transition_filing.get('parties'):
        update_parties(business, parties, filing_rec)

    if share_structure := transition_filing['shareStructure']:
        shares.update_share_structure(business, share_structure)

    if name_translations := transition_filing.get('nameTranslations'):
        aliases.update_aliases(business, name_translations)

    return filing_rec
