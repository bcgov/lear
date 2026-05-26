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
"""Share structure template tests."""
from typing import Final

import pytest

from registry_schemas.example_data import INCORPORATION

from . import get_template


COMPLETING_PARTY_CORP_TEMPLATE: Final = '/template-parts/incorporation-application/completingPartyCorp.html'
COMPLETING_PARTY_COOP_TEMPLATE: Final = '/template-parts/incorporation-application/completingPartyCoop.html'


@pytest.mark.parametrize('test_name,template_path', [
    ('coop', COMPLETING_PARTY_COOP_TEMPLATE),
    ('corp', COMPLETING_PARTY_CORP_TEMPLATE)
])
def test_completing_party_template(session, test_name, template_path):
    """Completing party template renders as expected for coops and corps."""
    certified_by = "Test Certified"

    # assert incorporation data from schema is what we expect
    parties = INCORPORATION["parties"]
    assert parties
    completing_party = next((party for party in parties if any(role for role in party["roles"] if role["roleType"] == "Completing Party")), None) 
    assert completing_party
    first_name = completing_party["officer"]["firstName"]
    middle_name = completing_party["officer"]["lastName"]
    last_name = completing_party["officer"]["lastName"]
    completing_party_name = f"{first_name} {middle_name} {last_name}".replace("  ", "")
    assert completing_party_name != certified_by

    # Render and verify template info
    template = get_template(template_path)
    rendered = template.render(
        parties=parties,
        header={"certifiedBy": certified_by}
    )
    if template_path == COMPLETING_PARTY_COOP_TEMPLATE:
        assert "Mailing Address" in rendered
        assert completing_party["mailingAddress"]["streetAddress"] in rendered
        assert "Completing Party Statement" in rendered
        assert f'<span class="capitalize-text">{first_name}</span>' in rendered
        assert f'<span class="capitalize-text">{middle_name}</span>' in rendered
        assert f'<span class="capitalize-text">{last_name}</span>' in rendered
        assert "certify that I have relevant knowledge" in rendered
        assert certified_by.upper() not in rendered
    else:
        assert "Completing Party Statement" in rendered
        assert f'<span class="capitalize-text">{certified_by}</span>' in rendered
        assert "the completing party, have examined the incorporation agreement and articles applicable to the company" in rendered
        assert completing_party_name not in rendered
        assert "Mailing Address" not in rendered
