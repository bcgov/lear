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
"""Common Business Details template tests."""
import pytest

from tests.unit.reports.templates import get_template


DETAILS_TEMPLATE = '/template-parts/common/businessDetails.html'

# A non-empty list just needs to be truthy; the changeOfDirectors branch only
# checks whether directors were appointed/ceased, it does not iterate them.
_A_DIRECTOR = [{'officer': {'firstName': 'Jane', 'lastName': 'Doe'}}]


def _render_cod(status='COMPLETED', appointed=None, ceased=None):
    """Render the common businessDetails part for a changeOfDirectors filing."""
    template = get_template(DETAILS_TEMPLATE)
    return template.render(
        header={'name': 'changeOfDirectors', 'status': status},
        business={'identifier': 'BC1234567', 'legalType': 'BC'},
        filing_date_time='June 1, 2026 at 12:00 pm Pacific time',
        effective_date='June 1, 2026',
        registrarInfo={'signature': '', 'name': 'Registrar of Companies'},
        listOfDirectors={
            'directors': (appointed or []) + (ceased or []),
            'directorsAppointed': appointed or [],
            'directorsCeased': ceased or [],
        },
    )


@pytest.mark.parametrize('test_name, appointed, ceased', [
    ('director appointed', _A_DIRECTOR, []),
    ('director ceased', [], _A_DIRECTOR),
    ('mixed appoint and cease', _A_DIRECTOR, _A_DIRECTOR),
])
def test_director_change_date_shown_when_director_added_or_removed(session, test_name, appointed, ceased):
    """Assert the Director Change Date shows when a director is added or removed."""
    rendered = _render_cod(appointed=appointed, ceased=ceased)
    assert 'Director Change Date:' in rendered
    assert 'June 1, 2026' in rendered


def test_director_change_date_hidden_for_name_or_address_only_change(session):
    """Assert the Director Change Date is hidden when only a name/address changed (no add/remove)."""
    rendered = _render_cod(appointed=[], ceased=[])
    assert 'Director Change Date:' not in rendered


def test_director_change_date_hidden_when_not_completed(session):
    """Assert the Director Change Date is hidden while the filing is not yet completed."""
    rendered = _render_cod(status='DRAFT', appointed=_A_DIRECTOR, ceased=[])
    assert 'Director Change Date:' not in rendered
