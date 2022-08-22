# Copyright © 2022 Province of British Columbia
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
"""Manages the share structure for a business."""
from __future__ import annotations

from typing import Dict, List, Optional

from dateutil.parser import parse
from legal_api.models import Business, Resolution, ShareClass, ShareSeries


def update_rules(business: Business, share_structure: Dict) -> Optional[List]:
    """Manage the share structure for a business.

    Assumption: The structure has already been validated, upon submission.

    Other errors are recorded and will be managed out of band.
    """
    if not business or not share_structure:
        # if nothing is passed in, we don't care and it's not an error
        return None

    err = []
    rules_file_key = cooperative_obj.get('rulesFileKey')
    rules_file = MinioService.get_file(rules_file_key)
    rules_file_name = cooperative_obj.get('rulesFileName')
    replace_file_with_certified_copy(rules_file.data, business, rules_file_key, business.founding_date)

    business.association_type = cooperative_obj.get('cooperativeAssociationType')
    document = Document()
    document.type = DocumentType.COOP_RULES.value
    document.file_key = rules_file_key
    document.file_name = rules_file_name
    document.content_type = document.file_name.split('.')[-1]
    document.business_id = business.id
    document.filing_id = filing.id
    business.documents.append(document)

    # create certified copy for memorandum document
    memorandum_file_key = cooperative_obj.get('memorandumFileKey')
    memorandum_file = MinioService.get_file(memorandum_file_key)
    memorandum_file_name = cooperative_obj.get('memorandumFileName')
    replace_file_with_certified_copy(memorandum_file.data, business, memorandum_file_key, business.founding_date)

    document = Document()
    document.type = DocumentType.COOP_MEMORANDUM.value
    document.file_key = memorandum_file_key
    document.file_name = memorandum_file_name
    document.content_type = document.file_name.split('.')[-1]
    document.business_id = business.id
    document.filing_id = filing.id
    business.documents.append(document)

    return err
