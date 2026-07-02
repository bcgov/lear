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
"""Business Details (business-summary) template tests."""
import pytest

from tests.unit.reports.templates import get_template


DETAILS_TEMPLATE = '/template-parts/business-summary/businessDetails.html'


@pytest.mark.parametrize('has_receiver', [True, False])
def test_render_summary_has_receivers(session, has_receiver):
    """Assert receiver flag is rendered correctly"""
    template = get_template(DETAILS_TEMPLATE)
    business = {'legalType': 'BC'}

    if has_receiver:
        rendered = template.render(business=business, receivers={'name': 'test receiver'})
        rendered = " ".join(rendered.split())
        expected = '<div class="mt-2"> <span class="section-sub-title">Receiver: </span> <span class="section-data">Yes</span> </div>'
        assert expected in rendered
    else:
        rendered = template.render(business=business, receivers=[])
        rendered = " ".join(rendered.split())
        expected = '<div class="mt-2"> <span class="section-sub-title">Receiver: </span> <span class="section-data">No</span> </div>'
        assert expected in rendered
