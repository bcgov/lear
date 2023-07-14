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

"""Tests to assure the Document Model.

Test-Suite to ensure that the Document Model is working as expected.
"""
from business_model.models.document import Document, DocumentType


def test_document_save_and_find(session):
    """Assert that the document was saved and find by id."""
    document = Document()
    document.type = DocumentType.COOP_RULES.value
    document.file_key = 'cooperative/a5c51016-4de7-407b-ab73-bb131f852053.pdf'
    document.save()
    assert document.id

    assert Document.find_by_id(document.id)
