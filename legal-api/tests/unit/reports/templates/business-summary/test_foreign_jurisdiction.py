# Copyright (c) 2026, Province of British Columbia

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.

# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.

# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""Foreign Jurisdiction template tests."""
import pytest

from tests.unit.reports.templates import get_template


FOREIGN_JUR_TEMPLATE = '/template-parts/business-summary/foreignJurisdiction.html'


@pytest.mark.parametrize('foreign_jurisdiction', [
    {
        'legal_name': 'Test Business Summary Foreign Jur with expro',
        'identifier': 'ALB-12345',
        'incorporation_date': 'November 10, 2023',
        'jurisdiction': 'Alberta, Canada',
        'expro_identifier': 'A1234567',
        'expro_legal_name': 'Test Expro Name'
    },
    {
        'legal_name': 'Test Business Summary Foreign Jur no expro',
        'identifier': 'ON-12345',
        'incorporation_date': 'November 11, 2023',
        'jurisdiction': 'Ontario, Canada'
    }
])
def test_render_foreign_jurisdiction(session, foreign_jurisdiction):
    """Test Foreign Jurisdiction rendering."""
    template = get_template(FOREIGN_JUR_TEMPLATE)
    rendered = template.render(continuationIn={'foreignJurisdiction': foreign_jurisdiction})

    assert 'Previous Jurisdiction Information' in rendered
    assert 'Name in Previous Jurisdiction' in rendered
    assert 'Identifying Number in Previous Jurisdiction' in rendered
    assert 'Date of Incorporation, Continuation or <br> Amalgamation in Previous Jurisdiction' in rendered
    assert foreign_jurisdiction['legal_name'] in rendered
    assert foreign_jurisdiction['identifier'] in rendered
    assert foreign_jurisdiction['incorporation_date'] in rendered
    assert foreign_jurisdiction['jurisdiction'] in rendered

    if foreign_jurisdiction.get('expro_identifier'):
        assert 'Previous Extraprovincial Registration in B.C.' in rendered
        assert foreign_jurisdiction['expro_identifier'] in rendered
        assert foreign_jurisdiction['expro_legal_name'] in rendered
    else:
        assert 'Previous Extraprovincial Registration in B.C.' not in rendered
