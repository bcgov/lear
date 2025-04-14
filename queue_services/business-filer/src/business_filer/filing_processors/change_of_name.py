# Copyright © 2019 Province of British Columbia
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
"""File processing rules and actions for the Change of Name filing."""
from typing import Dict

from flask import current_app
from business_model.models import Business

from business_filer.filing_meta import FilingMeta


def process(business: Business, filing: Dict, filing_meta: FilingMeta):
    """Render the change of name into the business model objects."""
    current_app.logger.debug('processing Change of Name: %s', filing)

    if name_request_json := filing['changeOfName'].get('nameRequest'):
        new_name = name_request_json.get('legalName')
    else:
        new_name = filing['changeOfName'].get('legalName')

    filing_meta.change_of_name = {'fromLegalName': business.legal_name,
                                  'toLegalName': new_name}

    business.legal_name = new_name
