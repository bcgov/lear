# Copyright © 2026 Province of British Columbia
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
"""Updates client document records with filing/business information once a filing completes,
so the document shows up correctly in the ledger and is searchable in the DRS UI.
"""
import re

from business_model.models import Business, Document, Filing
from flask import current_app

from business_filer.services import Flags, document_service

DRS_FEATURE_FLAG = "enable-new-feature"
DRS_FEATURE_VARIATION = "drs-upload"


def _is_drs_upload_enabled() -> bool:
    """Return True if the drs-upload feature is enabled."""
    try:
        flag_values = Flags.value(DRS_FEATURE_FLAG) or []
        return DRS_FEATURE_VARIATION in flag_values
    except Exception as err:  # pylint: disable=broad-except
        current_app.logger.warning(f"Unable to check {DRS_FEATURE_FLAG} flag: {err}")
        return False


def update_document_records(business: Business, filing: Filing):
    """Update the document record(s) for any client documents uploaded via DRS associated with a filing.

    business: The business record associated with the filing.
    filing: The completed filing record.
    """
    if not _is_drs_upload_enabled():
        return

    documents = _find_documents_for_filing(filing.id)

    if not documents:
        return

    update_info = _build_update_info(business, filing)

    for document in documents:
        if not _is_drs_document(document.file_key):
            # Skip legacy Minio-stored documents.
            continue
        try:
            response = document_service.update_document_record(document.file_key, dict(update_info))
            if response is not None and not response.ok:
                current_app.logger.warning(
                    f"Failed to update document record for document id={document.id}, "
                    f"file_key={document.file_key}, filing={filing.id}: "
                    f"status={response.status_code}, body={document_service.get_content(response)}"
                )
        except Exception as err:  # pylint: disable=broad-except;
            current_app.logger.warning(
                f"Error updating document record for document id={document.id}, "
                f"file_key={document.file_key}, filing={filing.id}: {err}"
            )


def _find_documents_for_filing(filing_id: int) -> list[Document]:
    """Find all documents for a filing."""
    return Document.query.filter_by(filing_id=filing_id).all()


def _build_update_info(business: Business, filing: Filing) -> dict:
    """Build the update payload."""
    update_info = {
        "filingId": filing.id,
        "filingDate": filing.completion_date.isoformat() if filing.completion_date else None,
    }
    if business:
        update_info["businessIdentifier"] = business.identifier
    return {k: v for k, v in update_info.items() if v is not None}


_DRS_KEY_PATTERN = re.compile(r"^[A-Z]+-DS\d+$")


def _is_drs_document(file_key: str) -> bool:
    """Return True if the file_key is a DRS key.

    DRS keys are formatted as "{documentClass}-{documentServiceId}", e.g. "COOP-DS0000101951".
    Legacy Minio keys (UUIDs) do not match this pattern.
    """
    return bool(file_key) and bool(_DRS_KEY_PATTERN.match(file_key))
