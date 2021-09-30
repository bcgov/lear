# Copyright © 2021 Province of British Columbia.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tests to assure that the alembic setup is correct.

Test-Suite to ensure that Alembic and Migration are working as expected.
"""
from alembic.config import Config
from alembic.script import ScriptDirectory

from tests.conftest import not_raises

def test_for_no_branches_in_versions():
    config = Config()
    config.set_main_option("script_location", "migrations")
    script = ScriptDirectory.from_config(config)

    with not_raises(Exception):
        script.get_current_head()