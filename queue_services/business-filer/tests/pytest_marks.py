# Copyright © 2020 Province of British Columbia
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
"""decorators used to skip/run pytests based on local setup."""
import os

import pytest
from dotenv import find_dotenv, load_dotenv


# this will load all the envars from a .env file located in the project root (api)
load_dotenv(find_dotenv())


colin_api_integration = pytest.mark.skipif((os.getenv('RUN_COLIN_API', False) is False),
                                           reason='requires access to COLIN API')

integration_affiliation = pytest.mark.skipif((os.getenv('RUN_AFFILIATION_TESTS', False) is False),
                                             reason='Account affiliation tests are only run when requested.')

integration_namex_api = pytest.mark.skipif((os.getenv('RUN_NAMEX_API', False) is False),
                                           reason='NameX tests are only run when requested.')

skip_in_pod = pytest.mark.skipif((os.getenv('POD_TESTING', False) is False), reason='Skip test when running in pod')
