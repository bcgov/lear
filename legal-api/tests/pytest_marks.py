# Copyright © 2019 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""This creates the pymarks for the integrations used by the Legal API.

The database used by the LegalAPI is not considered an integration, as it is fully
owned and managed by the API.

The other integrations only run if their environment variables are set,
in others words they fail open and will not run.
"""
import os

import pytest
from dotenv import find_dotenv, load_dotenv


# this will load all the envars from a .env file located in the project root (api)
load_dotenv(find_dotenv())


integration_nats = pytest.mark.skipif((os.getenv('RUN_NATS_TESTS', False) is False),
                                      reason='NATS tests are only run when requested.')

integration_sentry = pytest.mark.skipif((os.getenv('SENTRY_DSN', False) is False),
                                        reason='SENTRY tests run when SENTRY_DSN is set.')

integration_payment = pytest.mark.skipif((os.getenv('RUN_PAYMENT_TESTS', False) is False),
                                         reason='Test requiring payment service run when RUN_PAYMENT_TESTS is set.')

integration_authorization = pytest.mark.skipif(
    (os.getenv('RUN_AUTHORIZATION_TESTS', False) is False),
    reason='Test requiring authorization service run when RUN_AUTHORIZATION_TESTS is set.')

not_github_ci = pytest.mark.skipif((os.getenv('NOT_GITHUB_CI', False) is False),
                                   reason='Does not pass on github ci.')
