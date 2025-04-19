# Copyright © 2025 Province of British Columbia
#
# Licensed under the BSD 3 Clause License, (the "License");
# you may not use this file except in compliance with the License.
# The template for the license can be found here
#    https://opensource.org/license/bsd-3-clause/
#
# Redistribution and use in source and binary forms,
# with or without modification, are permitted provided that the
# following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS”
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
"""Manages the rules and memorandum for a business."""
from __future__ import annotations

from tokenize import String
from typing import List, Optional

from business_model.models import Business, Document, Filing
from business_model.models.document import DocumentType
# from legal_api.services.minio import MinioService
# from legal_api.services.pdf_service import RegistrarStampData

# from business_filer.utils import replace_file_with_certified_copy


def update_rules(
    business: Business,
    filing: Filing,
    rules_file_key: String,
    file_name: String = None
) -> Optional[List]:
    """Updtes rules if any.

    Assumption: rules file key and name have already been validated
    """
    # TODO: Fix this
    return None
    if not business or not rules_file_key:
        # if nothing is passed in, we don't care and it's not an error
        return None

    is_correction = filing.filing_type == 'correction'
    # rules_file = MinioService.get_file(rules_file_key)
    # registrar_stamp_data = RegistrarStampData(filing.effective_date, business.identifier, file_name, is_correction)
    # replace_file_with_certified_copy(rules_file.data, rules_file_key, registrar_stamp_data)

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
    # TODO: Fix this
    return None
    if not business or not memorandum_file_key:
        # if nothing is passed in, we don't care and it's not an error
        return None

    is_correction = filing.filing_type == 'correction'
    # create certified copy for memorandum document
    # memorandum_file = MinioService.get_file(memorandum_file_key)
    # registrar_stamp_data = RegistrarStampData(filing.effective_date, business.identifier, file_name, is_correction)
    # replace_file_with_certified_copy(memorandum_file.data, memorandum_file_key, registrar_stamp_data)

    document = Document()
    document.type = DocumentType.COOP_MEMORANDUM.value
    document.file_key = memorandum_file_key
    document.business_id = business.id
    document.filing_id = filing.id
    business.documents.append(document)

    return None
