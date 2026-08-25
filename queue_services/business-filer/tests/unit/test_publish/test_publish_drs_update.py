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
"""Unit tests for PublishEvent.publish_drs_update_message."""
import json
from datetime import UTC, datetime
from unittest.mock import Mock, patch

from business_model.models import Business, Document, Filing

from business_filer.services import gcp_queue
from business_filer.services.publish_event import PublishEvent

IDENTIFIER = 'BC1234567'
FILING_ID = 1438352
COMPLETION_DATE = '2026-06-09T23:02:02+00:00'
FILE_KEY_1 = 'COOP-DS0000101951'
FILE_KEY_2 = 'BEN-DS0000101952'

def _make_minimal_filing():
    filing = Filing()
    filing.id = FILING_ID
    filing._filing_type = 'continuationIn'
    filing._completion_date = datetime.fromisoformat(COMPLETION_DATE)
    return filing


def test_publish_drs_update_no_documents(app):
    """Assert nothing is published when the filing has no documents."""
    business = Business(identifier=IDENTIFIER)
    filing = _make_minimal_filing()

    mock_query = Mock()
    mock_query.filter_by.return_value.all.return_value = []

    with patch.object(Document, 'query', mock_query), \
         patch.object(gcp_queue, 'publish') as mock_publish:

        PublishEvent.publish_drs_update_message(app, business, filing)

        mock_publish.assert_not_called()


def test_publish_drs_update_drs_document(app):
    """Assert a drs update message is published for a DRS document."""
    business = Business(identifier=IDENTIFIER)
    filing = _make_minimal_filing()

    document = Document(
        id=10,
        filing_id=filing.id,
        file_key=FILE_KEY_1
    )

    mock_query = Mock()
    mock_query.filter_by.return_value.all.return_value = [document]

    with patch.object(Document, 'query', mock_query), \
         patch.object(gcp_queue, 'publish') as mock_publish:

        PublishEvent.publish_drs_update_message(app, business, filing)

        mock_publish.assert_called_once()
        subject, payload = mock_publish.call_args.args
        assert subject == app.config['DOC_UPDATE_REC_TOPIC']
        payload_data = (json.loads(payload)).get('data')
        assert payload_data == {
            'accountId': 'business-api',
            'fileKey': FILE_KEY_1,
            'businessIdentifier': IDENTIFIER,
            'filingDate': COMPLETION_DATE,
            'filingId': FILING_ID
        }


def test_publish_drs_update_multiple_documents(app):
    """Assert one message is published per DRS document, skipping legacy keys."""
    business = Business(identifier=IDENTIFIER)
    filing = _make_minimal_filing()

    documents = [
        Document(id=10, filing_id=filing.id, file_key=FILE_KEY_1),
        Document(id=11, filing_id=filing.id, file_key='550e8400-e29b-41d4-a716-446655440000'),
        Document(id=12, filing_id=filing.id, file_key=FILE_KEY_2),
    ]

    mock_query = Mock()
    mock_query.filter_by.return_value.all.return_value = documents

    with patch.object(Document, 'query', mock_query), \
         patch.object(gcp_queue, 'publish') as mock_publish:

        PublishEvent.publish_drs_update_message(app, business, filing)

        assert mock_publish.call_count == 2
        file_keys = [
            (json.loads(call.args[1])).get('data', {}).get('fileKey')
            for call in mock_publish.call_args_list
        ]
        assert file_keys == [FILE_KEY_1, FILE_KEY_2]


def test_publish_drs_update_skip_legacy_document(app):
    """Assert legacy Minio documents are ignored."""
    business = Business(identifier=IDENTIFIER)
    filing = _make_minimal_filing()

    document = Document(
        id=10,
        filing_id=filing.id,
        file_key='550e8400-e29b-41d4-a716-446655440000'
    )

    mock_query = Mock()
    mock_query.filter_by.return_value.all.return_value = [document]

    with patch.object(Document, 'query', mock_query), \
         patch.object(gcp_queue, 'publish') as mock_publish:

        PublishEvent.publish_drs_update_message(app, business, filing)

        mock_publish.assert_not_called()


def test_publish_drs_update_omits_empty_values(app):
    """Assert filingDate is omitted when the filing has no completion date."""
    business = Business(identifier=IDENTIFIER)
    filing = _make_minimal_filing()
    filing._completion_date = None

    document = Document(
        id=10,
        filing_id=filing.id,
        file_key=FILE_KEY_1
    )

    mock_query = Mock()
    mock_query.filter_by.return_value.all.return_value = [document]

    with patch.object(Document, 'query', mock_query), \
         patch.object(gcp_queue, 'publish') as mock_publish:

        PublishEvent.publish_drs_update_message(app, business, filing)

        mock_publish.assert_called_once()
        payload_data = (json.loads(mock_publish.call_args.args[1])).get('data')
        assert 'filingDate' not in payload_data
        assert payload_data.get('filingId') == FILING_ID


def test_is_drs_document():
    """Assert DRS document detection."""
    assert PublishEvent._is_drs_document(FILE_KEY_1)
    assert PublishEvent._is_drs_document(FILE_KEY_2)
    assert PublishEvent._is_drs_document('COOP-DS0000123456')
    assert PublishEvent._is_drs_document('BEN-DS123456')

    assert not PublishEvent._is_drs_document('550e8400-e29b-41d4-a716-446655440000')
    assert not PublishEvent._is_drs_document('')
    assert not PublishEvent._is_drs_document(None)
