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
"""Share structure template tests."""
from decimal import Decimal
from typing import Final

import pytest

from . import get_template


SHARE_STRUCTURE_TEMPLATE: Final = '/template-parts/common/shareStructure.html'


def _share_class(par_value, currency='USD', has_par_value=True, name='Class A', series=None):
    """Build a minimal share class dict for rendering."""
    return {
        'name': name,
        'hasMaximumShares': True,
        'maxNumberOfShares': 1000,
        'hasParValue': has_par_value,
        'parValue': par_value,
        'currency': currency,
        'currencyAdditional': '',
        'hasRightsOrRestrictions': False,
        'series': series or []
    }


def _render(share_classes, header_name='noticeOfArticles'):
    """Render the share structure partial. Defaults to a non-correction header."""
    template = get_template(SHARE_STRUCTURE_TEMPLATE)
    return template.render(
        shareClasses=share_classes,
        header={'name': header_name},
        labelAdded=lambda: '(Added)',
        labelCorrected=lambda: '(Corrected)'
    )


@pytest.mark.parametrize('par_value,currency,expected', [
    (1, 'USD', '$ 1.00'),
    (1.0, 'USD', '$ 1.00'),
    (1.5, 'CAD', '$ 1.50'),
    (Decimal('0.5'), 'AUD', '$ 0.50'),
    ('2', 'AUD', '$ 2.00'),
    (1000, 'CAD', '$ 1,000.00'),
    (1234567, 'USD', '$ 1,234,567.00'),
    (1111112321434241, 'USD', '$ 1,111,112,321,434,241.00'),
    ('1234567.5', 'AUD', '$ 1,234,567.50'),
])
def test_dollar_currency_formats_with_min_two_decimals_and_commas(session, par_value, currency, expected):
    """Dollar-denominated currencies render parValue padded to AT LEAST 2 decimals with $ prefix and thousands separators."""
    rendered = _render([_share_class(par_value, currency=currency)])
    assert expected in rendered


@pytest.mark.parametrize('par_value,currency,expected', [
    ('1.00000000002342', 'CAD', '$ 1.00000000002342'),
    ('1.234', 'CAD', '$ 1.234'),
    ('0.0001', 'USD', '$ 0.0001'),
    ('1234567.123456', 'AUD', '$ 1,234,567.123456'),
    ('0.000000000000000001', 'USD', '$ 0.000000000000000001'),
])
def test_dollar_currency_preserves_extra_decimals(session, par_value, currency, expected):
    """parValues with more than 2 decimal places must NOT be truncated — match UI's FormatDecimal behavior.

    Also covers the post-`_format_par_value` shape: tiny floats are converted to long fixed-point
    strings (no scientific notation) before reaching the template, so the template just splits on '.'.
    """
    rendered = _render([_share_class(par_value, currency=currency)])
    assert expected in rendered


@pytest.mark.parametrize('currency', ['EUR', 'GBP', 'JPY', 'INR'])
def test_non_dollar_currency_renders_raw_no_dollar_sign(session, currency):
    """Non-dollar currencies render the raw parValue and no $ prefix."""
    rendered = _render([_share_class(1.5, currency=currency)])
    assert '1.5' in rendered
    assert '$' not in rendered


def test_has_par_value_false_renders_no_par_value(session):
    """When hasParValue is False, render 'No Par Value' and no $ symbol."""
    rendered = _render([_share_class(par_value=None, has_par_value=False, currency='USD')])
    assert 'No Par Value' in rendered
    assert '$' not in rendered


def test_other_currency_with_additional_label(session):
    """OTHER currency with currencyAdditional renders the additional label and no $ prefix."""
    share_class = _share_class(1.5, currency='OTHER')
    share_class['currencyAdditional'] = 'XYZ'
    rendered = _render([share_class])
    assert 'XYZ' in rendered
    assert '$' not in rendered


def test_series_inherits_parent_share_class_par_value_format(session):
    """Series rows render parValue using parent share_class's currency, formatted the same way."""
    series = [{
        'name': 'Series 1',
        'hasMaximumShares': True,
        'maxNumberOfShares': 100,
        'hasRightsOrRestrictions': False,
    }]
    rendered = _render([_share_class(par_value=3, currency='USD', series=series)])
    assert rendered.count('$ 3.00') == 2
    assert 'Series 1' in rendered


def test_empty_share_classes_renders_nothing(session):
    """Empty shareClasses list should not render the section heading."""
    template = get_template(SHARE_STRUCTURE_TEMPLATE)
    rendered = template.render(shareClasses=[], header={'name': 'noticeOfArticles'})
    assert 'Authorized Share Structure' not in rendered


def test_section_heading_present_when_share_classes_exist(session):
    """Section heading appears when at least one share class exists."""
    rendered = _render([_share_class(par_value=1, currency='USD')])
    assert 'Authorized Share Structure' in rendered


@pytest.mark.parametrize('header_name', ['noticeOfArticles', 'correction'])
def test_par_value_formatting_consistent_across_header_types(session, header_name):
    """Par value formatting must not vary by report header type (correction vs non-correction)."""
    series = [{
        'name': 'Series 1',
        'hasMaximumShares': True,
        'maxNumberOfShares': 100,
        'hasRightsOrRestrictions': False,
    }]
    rendered = _render(
        [_share_class(par_value=1234.5, currency='CAD', series=series)],
        header_name=header_name
    )
    assert rendered.count('$ 1,234.50') == 2
