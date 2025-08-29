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


integration_affiliation = pytest.mark.skipif((os.getenv('RUN_AFFILIATION_TESTS', False) is False),
                                             reason='Account affiliation tests are only run when requested.')

integration_authorization = pytest.mark.skipif(
    (os.getenv('RUN_AUTHORIZATION_TESTS', False) is False),
    reason='Test requiring authorization service run when RUN_AUTHORIZATION_TESTS is set.')

integration_colin = pytest.mark.skipif((os.getenv('RUN_COLIN_TESTS', False) is False),
                                       reason='COLIN tests are only run when requested.')

integration_nats = pytest.mark.skipif((os.getenv('RUN_NATS_TESTS', False) is False),
                                      reason='NATS tests are only run when requested.')

integration_payment = pytest.mark.skipif((os.getenv('RUN_PAYMENT_TESTS', False) is False),
                                         reason='Test requiring payment service run when RUN_PAYMENT_TESTS is set.')

integration_reports = pytest.mark.skipif((os.getenv('RUN_REPORT_TESTS', False) is False),
                                         reason='Report tests are only run when requested.')

integration_namerequests = pytest.mark.skipif((os.getenv('RUN_NAMEREQUESTS_TESTS', False) is False),
                                              reason='Name request tests are only run when requested.')

not_github_ci = pytest.mark.skipif((os.getenv('NOT_GITHUB_CI', False) is False),
                                   reason='Does not pass on github ci.')

todo_tech_debt = pytest.mark.skipif((os.getenv('TECH_DEBT', False) is False),
                                   reason='Does not run tech debt tests.')

api_v1 = pytest.mark.skipif((os.getenv('API_V1', False) is False),
                                   reason='Version 1 of API.')

api_v2 = pytest.mark.skipif((os.getenv('API_V2', False) is False),
                                   reason='Version 2 of API.')
