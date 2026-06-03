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
from typing import Final

import pytest

from . import get_template


title: Final = 'Company Name Translation(s)'
NAME_TRANSLATION_TEMPLATE = '/template-parts/common/nameTranslation.html'


@pytest.mark.parametrize('list_of_translations,previous_translations', [
    ([{'name': 'Ma Enterprise'}], []),
    ([], [{'name': 'Ma Enterprise'}]),
    ([], [])])
def test_render_translations(session, list_of_translations, previous_translations):
    """Test Company Name Translation(s) rendering."""
    template = get_template(NAME_TRANSLATION_TEMPLATE)
    rendered = template.render(listOfTranslations=list_of_translations,
                               previousNameTranslations=previous_translations,
                               header={'name': ''})
    if len(list_of_translations):
        assert title in rendered
        assert list_of_translations[0]['name'] in rendered
        assert 'NONE' not in rendered
    elif len(previous_translations):
        assert title in rendered
        assert previous_translations[0]['name'] not in rendered
        assert 'NONE' in rendered
    else:
        assert title not in rendered
