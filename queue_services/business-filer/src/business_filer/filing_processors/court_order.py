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
"""File processing rules and actions for the court order filing."""
from contextlib import suppress
from datetime import datetime
from typing import Dict

from business_model.models import Business, Document, DocumentType, Filing

from business_filer.filing_meta import FilingMeta


def process(business: Business, court_order_filing: Filing, filing: Dict, filing_meta: FilingMeta):
    """Render the court order filing into the business model objects."""
    court_order_filing.court_order_file_number = filing['courtOrder'].get('fileNumber')
    court_order_filing.court_order_effect_of_order = filing['courtOrder'].get('effectOfOrder')
    court_order_filing.order_details = filing['courtOrder'].get('orderDetails')

    with suppress(IndexError, KeyError, TypeError, ValueError):
        court_order_filing.court_order_date = datetime.fromisoformat(filing['courtOrder'].get('orderDate'))

    if file_key := filing['courtOrder'].get('fileKey'):
        document = Document()
        document.type = DocumentType.COURT_ORDER.value
        document.file_key = file_key
        document.business_id = business.id
        document.filing_id = court_order_filing.id
        business.documents.append(document)
