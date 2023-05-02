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
"""Manages the rules and memorandum for a business."""
from __future__ import annotations

from tokenize import String
from typing import List, Optional

from legal_api.models import Business, Document, Filing
from legal_api.models.document import DocumentType
from legal_api.services.minio import MinioService

from entity_filer.utils import replace_file_with_certified_copy


def update_rules(
    business: Business,
    filing: Filing,
    file_key: String,
    file_name: String
) -> Optional[List]:
    """Updates rules if any.

    Assumption: rules file key and name have already been validated
    """
    if not business or not file_key:
        # if nothing is passed in, we don't care and it's not an error
        return None

    rules_file = MinioService.get_file(file_key)
    replace_file_with_certified_copy(rules_file.data, business, file_key, business.founding_date)

    document = Document()
    document.type = DocumentType.COOP_RULES.value
    document.file_key = file_key
    document.file_name = file_name
    document.business_id = business.id
    document.filing_id = filing.id
    business.documents.append(document)

    return None


def update_memorandum(
    business: Business,
    filing: Filing,
    file_key: String,
    file_name: String
) -> Optional[List]:
    """Updates memorandum if any.

    Assumption: memorandum file key and name have already been validated
    """
    if not business or not file_key:
        # if nothing is passed in, we don't care and it's not an error
        return None

    # create certified copy for memorandum document
    memorandum_file = MinioService.get_file(file_key)
    replace_file_with_certified_copy(memorandum_file.data, business, file_key, business.founding_date)

    document = Document()
    document.type = DocumentType.COOP_MEMORANDUM.value
    document.file_key = file_key
    document.file_name = file_name
    document.business_id = business.id
    document.filing_id = filing.id
    business.documents.append(document)

    return None
