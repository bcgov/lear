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
"""The Unit Tests for business number email notification."""

from entity_emailer.email_processors import bn_notification


def test_bn_notificaton(app, session):
    """Assert that the bn email processor builds the email correctly."""
    # setup
    email_msg = {'email': {'type': 'bn'}}
    # test
    email = bn_notification.process(email_msg)
    # validate
    assert email == 'bn hardcoded'
