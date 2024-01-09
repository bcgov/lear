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

"""Tests to assure the documents API end-point.

Test-Suite to ensure that the /documents endpoint is working as expected.
"""

from http import HTTPStatus

from legal_api.services.authz import STAFF_ROLE
from tests.unit.services.utils import create_header


def test_documents_signature_get_returns_200(client, jwt, session, minio_server):  # pylint:disable=unused-argument
    """Assert get documents/filename/signatures endpoint returns 200."""
    headers = create_header(jwt, [STAFF_ROLE])
    file_name = "test_file.jpeg"
    rv = client.get(f"/api/v2/documents/{file_name}/signatures", headers=headers, content_type="application/json")

    assert rv.status_code == HTTPStatus.OK
    assert "key" in rv.json and "preSignedUrl" in rv.json
