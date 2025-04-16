# Copyright © 2024 Province of British Columbia
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
"""Common setup and fixtures for the pytest suite used by this service."""

import pytest

from expired_limited_restoration import create_app


@pytest.fixture(scope="session")
def app():
    """Return a session-wide application configured in TEST mode."""
    _app = create_app("testing")
    with _app.app_context():
        yield _app


@pytest.fixture
def client(app):
    return app.test_client()
