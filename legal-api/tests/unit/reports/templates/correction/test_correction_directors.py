# Copyright © 2026 Province of British Columbia
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
"""Correction Directors template tests."""
import pytest

from tests.unit.reports.templates import get_template

@pytest.mark.parametrize(
    'name_changed, previous_name, expect_former_name, expect_label_corrected',
    [
        (True, 'NORMAN, MATHEW JONATHAN', True, True),
        (False, 'NORMAN, MATHEW JONATHAN', False, False),
        (True, '', False, True),
        (True, None, False, True),
    ]
)
def test_render_correction_directors_name(
    session,
    name_changed,
    previous_name,
    expect_former_name,
    expect_label_corrected
):
    """Test former name and labelCorrected rendering."""
    template_path = '/template-parts/correction/directors.html'
    template = get_template(template_path)

    party = {
        'officer': {
            'id': '1178718',
            'firstName': 'MATHEW',
            'middleName': 'UPDATED',
            'lastName': 'NORMAN',
            'partyType': 'person'
        },
        'deliveryAddress': {
            'streetAddress': '51063 Zander Pl',
            'addressCity': 'Chilliwack',
            'addressRegion': 'BC',
            'postalCode': 'V4Z 0C1',
            'addressCountry': 'Canada'
        },
        'mailingAddress': {
            'streetAddress': '51063 Zander Pl',
            'addressCity': 'Chilliwack',
            'addressRegion': 'BC',
            'postalCode': 'V4Z 0C1',
            'addressCountry': 'Canada'
        },
        'roles': [{'roleType': 'Director', 'appointmentDate': '2018-05-31'}],
        'nameChanged': name_changed
    }

    if previous_name is not None:
        party['previousName'] = previous_name

    rendered = template.render(
        parties=[party],
        partyChange=True,
        effective_date='October 21, 2026',
        labelCorrected=lambda: 'Corrected',
        labelAdded=lambda: 'Added'
    )

    if expect_former_name:
        assert f'(Formerly {previous_name})' in rendered
        assert 'director-former-name' in rendered
    else:
        assert 'director-former-name' not in rendered
        if previous_name:
            assert f'(Formerly {previous_name})' not in rendered

    if expect_label_corrected:
        assert 'Corrected' in rendered
    else:
        assert 'Corrected' not in rendered
