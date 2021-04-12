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
"""Name Translation template tests."""


from pathlib import Path

from flask import current_app
from jinja2 import Template


def test_no_rendering(session):
    """Test Company Name Translation(s) section should not rendered when no current translation nor previous ones."""
    template_path = current_app.config.get('REPORT_TEMPLATE_PATH')
    template_code = Path(f'{template_path}/template-parts/common/nameTranslation.html').read_text()
    template = Template(template_code)
    rendered = template.render(listOfTranslations=[], previousNameTranslations=[])
    assert 'Company Name Translation(s)' not in rendered


def test_render_none(session):
    """Test Company Name Translation(s) should render none when no current translation and there were previous ones."""
    template_path = current_app.config.get('REPORT_TEMPLATE_PATH')
    template_code = Path(f'{template_path}/template-parts/common/nameTranslation.html').read_text()
    template = Template(template_code)
    rendered = template.render(listOfTranslations=[], previousNameTranslations=['Une Grande Enterprise'])
    assert 'Company Name Translation(s)' in rendered
    assert 'Une Grande Enterprise' not in rendered
    assert 'NONE' in rendered


def test_render_translations(session):
    """Test Company Name Translation(s) should render when there are current translations."""
    template_path = current_app.config.get('REPORT_TEMPLATE_PATH')
    template_code = Path(f'{template_path}/template-parts/common/nameTranslation.html').read_text()
    template = Template(template_code)
    rendered = template.render(listOfTranslations=['Ma Enterprise'], previousNameTranslations=[])
    assert 'Company Name Translation(s)' in rendered
    assert 'Ma Enterprise' in rendered
