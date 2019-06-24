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

"""Tests to assure the ColinLastUpdate Class.

Test-Suite to ensure that the ColinLastUpdate Class is working as expected.
"""
from legal_api.models import ColinLastUpdate


def test_last_update(session):
    """Assert that a User can be stored in the service.

    Start with a blank database.
    """
    entry = ColinLastUpdate(last_update='2019-01-01', last_event_id=1234)

    session.add(entry)
    session.commit()

    assert entry.id is not None
