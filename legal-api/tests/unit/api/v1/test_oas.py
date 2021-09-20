# Copyright © 2019 Province of British Columbia
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

"""Tests to assure the oas end-point.

Test-Suite to ensure that the oas endpoint is working as expected.
"""
from http import HTTPStatus


def test_oas_root_redirect(client):
    """Assert that / permanently redirects to /api/v1."""
    rv = client.get('/')

    assert rv.status_code == HTTPStatus.MOVED_PERMANENTLY
    assert rv.location == 'http://localhost/api/v1'


def test_oas_docs(client):
    """Assert that the swagger docs are loaded at the redirect point."""
    rv = client.get('/api/v1/')

    assert rv.status_code == HTTPStatus.OK
    assert rv.data.startswith(b'<!DOCTYPE html>\n<html>\n<head>\n    <title>BCROS Business API</title>')
