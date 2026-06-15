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
"""Test-Suite to ensure that the Report utils are working as expected."""
import pytest

from legal_api.reports.utils import get_amalg_formatted_jurisdiction


@pytest.mark.parametrize(
    'test_name, identifier, country_code, region_code, expected',
    [
        ('ca-bc-province', 'BC1234567', 'CA', 'BC', 'British Columbia'),
        ('ca-on-province', 'BC1234567', 'CA', 'ON', 'Ontario'),
        ('ca-federal-uppercase', 'BC1234567', 'CA', 'FEDERAL', 'Federal'),
        ('ca-federal-lowercase', 'BC1234567', 'CA', 'federal', 'Federal'),
        ('ca-federal-mixedcase', 'BC1234567', 'CA', 'Federal', 'Federal'),
        ('us-with-region', 'BC1234567', 'US', 'WA', 'United States'),
        ('us-no-region', 'BC1234567', 'US', None, 'United States'),
        ('gb-no-region', 'BC1234567', 'GB', None, 'United Kingdom'),
        ('ca-invalid-region-falls-back-to-country', 'BC1234567', 'CA', 'ZZ', 'Canada'),
    ],
)
def test_get_amalg_formatted_jurisdiction_happy_paths(
        app, test_name, identifier, country_code, region_code, expected):
    """Assert that the correct jurisdiction label is returned for valid country and region inputs."""
    with app.app_context():
        result = get_amalg_formatted_jurisdiction(identifier, country_code, region_code)

    assert result == expected


@pytest.mark.parametrize(
    'test_name, identifier, country_code, region_code',
    [
        ('ca-region-none-triggers-attribute-error', 'BC1234567', 'CA', None),
        ('unknown-country-code', 'BC1234567', 'XX', None),
        ('empty-country-code', 'BC1234567', None, None),
    ],
)
def test_get_amalg_formatted_jurisdiction_error_paths(
        app, test_name, identifier, country_code, region_code):
    """Assert that N/A is returned and no exception is raised when an AttributeError occurs internally."""
    with app.app_context():
        result = get_amalg_formatted_jurisdiction(identifier, country_code, region_code)

    assert result == 'N/A'
