# Copyright © 2026 Province of British Columbia
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
"""Unit tests for document_records filing component processor."""

from unittest.mock import Mock, patch

from business_model.models import Business, Document, Filing

from business_filer.filing_processors.filing_components import document_records


@patch("business_filer.filing_processors.filing_components.document_records.Flags")
def test_skip_when_feature_flag_disabled(mock_flags):
    """Assert nothing happens when the feature flag is disabled."""
    mock_flags.value.return_value = []

    business = Business(identifier="BC1234567")
    filing = Filing(id=1)

    with patch.object(Document, "query") as mock_query, \
         patch.object(document_records.document_service, "update_document_record") as mock_update:

        document_records.update_document_records(business, filing)

        mock_query.filter_by.assert_not_called()
        mock_update.assert_not_called()


@patch("business_filer.filing_processors.filing_components.document_records.Flags")
def test_skip_when_no_documents(mock_flags):
    """Assert nothing happens when no documents exist."""
    mock_flags.value.return_value = ["drs-upload"]

    business = Business(identifier="BC1234567")
    filing = Filing(id=1)

    mock_query = Mock()
    mock_query.filter_by.return_value.all.return_value = []

    with patch.object(Document, "query", mock_query), \
         patch.object(document_records.document_service, "update_document_record") as mock_update:

        document_records.update_document_records(business, filing)

        mock_update.assert_not_called()


@patch("business_filer.filing_processors.filing_components.document_records.Flags")
def test_updates_drs_document(mock_flags):
    """Assert DRS documents are updated."""
    mock_flags.value.return_value = ["drs-upload"]

    business = Business(identifier="BC1234567")

    filing = Filing(id=1)
    filing._completion_date = None

    document = Document(
        id=10,
        filing_id=1,
        file_key="COOP-DS0000001234"
    )

    mock_query = Mock()
    mock_query.filter_by.return_value.all.return_value = [document]

    response = Mock()
    response.ok = True

    with patch.object(Document, "query", mock_query), \
         patch.object(document_records.document_service,
                      "update_document_record",
                      return_value=response) as mock_update:

        document_records.update_document_records(business, filing)

        mock_update.assert_called_once()

        args = mock_update.call_args[0]

        assert args[0] == "COOP-DS0000001234"
        assert args[1]["filingId"] == 1
        assert args[1]["businessIdentifier"] == "BC1234567"


@patch("business_filer.filing_processors.filing_components.document_records.Flags")
def test_skip_legacy_document(mock_flags):
    """Assert legacy Minio documents are ignored."""
    mock_flags.value.return_value = ["drs-upload"]

    business = Business(identifier="BC1234567")
    filing = Filing(id=1)

    document = Document(
        id=10,
        filing_id=1,
        file_key="550e8400-e29b-41d4-a716-446655440000"
    )

    mock_query = Mock()
    mock_query.filter_by.return_value.all.return_value = [document]

    with patch.object(Document, "query", mock_query), \
         patch.object(document_records.document_service,
                      "update_document_record") as mock_update:

        document_records.update_document_records(business, filing)

        mock_update.assert_not_called()


def test_is_drs_document():
    """Assert DRS document detection."""
    assert document_records._is_drs_document("COOP-DS0000123456")
    assert document_records._is_drs_document("BEN-DS123456")

    assert not document_records._is_drs_document(
        "550e8400-e29b-41d4-a716-446655440000"
    )
    assert not document_records._is_drs_document("")
    assert not document_records._is_drs_document(None)
