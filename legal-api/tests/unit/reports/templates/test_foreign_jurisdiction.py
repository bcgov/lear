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
"""Foreign Jurisdiction template tests."""

from pathlib import Path

import pytest
from flask import current_app
from jinja2 import Template


def get_template():
    """Returns the template."""
    template_path = current_app.config.get('REPORT_TEMPLATE_PATH')
    template_code = Path(f'{template_path}/template-parts/continuation/foreignJurisdiction.html').read_text()
    return Template(template_code)


@pytest.mark.parametrize('foreign_jurisdiction', [
    # Case 1: region provided — should display region, not country
    {
        'legalName': 'Acme Corp International',
        'identifier': 'A-12345',
        'incorporationDate': 'January 15, 2020',
        'region': 'Alberta',
        'country': 'Canada',
    },
    # Case 2: no region — should display country
    {
        'legalName': 'Global Holdings Ltd.',
        'identifier': 'GH-99999',
        'incorporationDate': 'March 10, 2018',
        'region': '',
        'country': 'United Kingdom',
    },
    # Case 3: region is None — should display country
    {
        'legalName': 'Pacific Trading Inc.',
        'identifier': 'PT-00001',
        'incorporationDate': 'July 1, 2015',
        'region': None,
        'country': 'Australia',
    },
])
def test_render_foreign_jurisdiction(session, foreign_jurisdiction):
    """Test Foreign Jurisdiction rendering."""
    template = get_template()
    rendered = template.render(foreignJurisdiction=foreign_jurisdiction)

    # Static fields always present
    assert 'Previous Jurisdiction Information' in rendered
    assert foreign_jurisdiction['legalName'] in rendered
    assert foreign_jurisdiction['identifier'] in rendered
    assert foreign_jurisdiction['incorporationDate'] in rendered

    # Conditional: region vs country
    if foreign_jurisdiction.get('region'):
        assert foreign_jurisdiction['region'] in rendered
    else:
        assert foreign_jurisdiction['country'] in rendered
