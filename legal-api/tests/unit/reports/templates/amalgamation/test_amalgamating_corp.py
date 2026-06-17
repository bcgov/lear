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
"""Amalgamating Corp template tests."""
import pytest

from tests.unit.reports.templates import get_template


AMALGAMATING_CORP_TEMPLATE = '/template-parts/amalgamation/amalgamatingCorp.html'


def _render(amalgamating_businesses):
    """Render the amalgamatingCorp partial with the given business list."""
    template = get_template(AMALGAMATING_CORP_TEMPLATE)
    return template.render(amalgamatingBusinesses=amalgamating_businesses)


def test_render_amalgamating_corp_section_headers(session):
    """Assert that section and column headers are present."""
    businesses = [
        {'legalName': 'BC Company Ltd.', 'identifier': 'BC1234567', 'jurisdiction': 'British Columbia'}
    ]
    rendered = _render(businesses)

    assert 'Amalgamating Businesses Information' in rendered
    assert 'Amalgamating Business' in rendered
    assert 'Number In BC' in rendered
    assert 'Jurisdiction' in rendered


def test_render_amalgamating_corp_entity(session):
    """Assert that an entity renders legalName, identifier, and jurisdiction correctly."""
    businesses = [
        {'legalName': 'BC Company Ltd.', 'identifier': 'BC1234567', 'jurisdiction': 'British Columbia'}
    ]
    rendered = _render(businesses)

    assert 'BC Company Ltd.' in rendered
    assert 'BC1234567' in rendered
    assert 'British Columbia' in rendered


def test_render_amalgamating_corp_multiple_entities(session):
    """Assert that multiple entities each render their own row with distinct values."""
    businesses = [
        {'legalName': 'First Corp Ltd.', 'identifier': 'BC1111111', 'jurisdiction': 'British Columbia'},
        {'legalName': 'Second Holdings Inc.', 'identifier': 'AB-22222', 'jurisdiction': 'Alberta'},
        {'legalName': 'Third International Corp.', 'identifier': 'US-33333', 'jurisdiction': 'United States'},
    ]
    rendered = _render(businesses)

    for business in businesses:
        assert business['legalName'] in rendered
        assert business['identifier'] in rendered
        assert business['jurisdiction'] in rendered
