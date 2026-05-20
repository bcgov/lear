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
"""Templates tests."""
from pathlib import Path

from flask import current_app
from jinja2 import Template


def get_template(template):
    """Returns the template."""
    template_path = current_app.config.get('REPORT_TEMPLATE_PATH')
    template_code = Path(f'{template_path}{template}').read_text()
    return Template(template_code)
