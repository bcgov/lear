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
from legal_api.services import Flags
from legal_api.services.minio import MinioService
from legal_api.services.document_record import DocumentRecordService
from legal_api.constants import DocumentClasses
from legal_api.services.pdf_service import RegistrarStampData

from entity_filer.utils import replace_file_with_certified_copy

flags = Flags()  # pylint: disable=invalid-name

def update_rules(
    business: Business,
    filing: Filing,
    rules_file_key: String,
    file_name: String = None
) -> Optional[List]:
    """Updtes rules if any.

    Assumption: rules file key and name have already been validated
    """
    if not business or not rules_file_key:
        # if nothing is passed in, we don't care and it's not an error
        return None

    is_correction = filing.filing_type == 'correction'

    if not flags.is_on('enable-document-records'):
        rules_file = DocumentRecordService.download_document(
            DocumentClasses.COOP.value, 
            rules_file_key
        )
    else:
        rules_file = MinioService.get_file(rules_file_key)

    registrar_stamp_data = RegistrarStampData(filing.effective_date, business.identifier, file_name, is_correction)
    replace_file_with_certified_copy(
        rules_file.data,
        rules_file_key,
        registrar_stamp_data,
        rules_file.name
    )

    document = Document()
    document.type = DocumentType.COOP_RULES.value
    document.file_key = rules_file_key
    document.business_id = business.id
    document.filing_id = filing.id
    business.documents.append(document)

    return None


def update_memorandum(
    business: Business,
    filing: Filing,
    memorandum_file_key: String,
    file_name: String = None
) -> Optional[List]:
    """Updtes memorandum if any.

    Assumption: memorandum file key and name have already been validated
    """
    if not business or not memorandum_file_key:
        # if nothing is passed in, we don't care and it's not an error
        return None

    is_correction = filing.filing_type == 'correction'
    # create certified copy for memorandum document
    if flags.is_on('enable-document-records'):
        memorandum_file = DocumentRecordService.download_document(
            DocumentClasses.COOP.value, 
            memorandum_file_key
        )
    else:
        memorandum_file = MinioService.get_file(memorandum_file_key)
    registrar_stamp_data = RegistrarStampData(filing.effective_date, business.identifier, file_name, is_correction)
    replace_file_with_certified_copy(
        memorandum_file.data,
        memorandum_file_key,
        registrar_stamp_data,
        memorandum_file.name
    )
    document = Document()
    document.type = DocumentType.COOP_MEMORANDUM.value
    document.file_key = memorandum_file_key
    document.business_id = business.id
    document.filing_id = filing.id
    business.documents.append(document)

    return None
