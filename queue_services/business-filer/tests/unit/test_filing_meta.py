from dataclasses import asdict

import pytest
from hypothesis import example, given
from hypothesis.strategies import text

from business_filer.filing_meta import to_camel, to_snake, FilingMeta


@pytest.mark.parametrize('test_type,input,expected',[
    ('_none', None, None),
    ('_base', '', ''),
    ('_simple', 'simple_test_case', 'simpleTestCase'),
])
def test_to_camel(test_type, input, expected):
    """Assert that snake_case is converted to camelCase."""
    assert to_camel(input) == expected


@given(f=text(min_size=1))
@example(f='simple_test_case')
def test_hypothesis_to_camel(f):
    """Assert that the hypothesis of any text is converted correctly."""
    output = to_camel(input)

    if output:
        assert isinstance(output, str)
        assert '_' not in output
        assert output

        if len(output):
            init_char = output[:1]
            assert init_char == init_char.lower()


@pytest.mark.parametrize('test_type,input,expected',[
    ('_none', None, None),
    ('_base', '', ''),
    ('_simple', 'simpleTestCase', 'simple_test_case'),
])
def test_to_snake(test_type, input, expected):
    """Assert that camelCase is converted to snake_case."""
    assert to_snake(input) == expected


@given(f=text(min_size=1))
@example(f='simpleTestCase')
def test_hypothesis_to_snake(f):
    """Assert that the hypothesis of any text is converted correctly."""
    output = to_snake(input)

    if output:
        assert isinstance(output, str)
        assert output == output.lower()

        if any(x.isupper() for x in output):
            assert '_' in output


def test_minimal_filing_meta():
    """Assert the minimal setup of the class is correct."""
    filing_name = 'incorporationApplication'
    filing_meta = FilingMeta()

    assert filing_meta
    assert asdict(filing_meta) == {'application_date': None,
                                   'legal_filings': []
                                   }
    assert filing_meta.asjson == {'applicationDate': None,
                                  'legalFilings': []
                                  }

def test_added_unknown_field():
    """Assert a field added to the dataclass is in the json output, but not in the std library asdict()."""
    filing_name = 'incorporationApplication'
    filing_meta = FilingMeta()

    filing_meta.unknown = 'an unknown field'

    assert filing_meta
    # should not have the field in the asdict view
    assert not asdict(filing_meta).get('unknown')
    assert asdict(filing_meta) == {'application_date': None,
                                   'legal_filings': []
                                   }

    # the field should be in the json property
    assert filing_meta.asjson.get('unknown')
    assert filing_meta.asjson == {'applicationDate': None,
                                  'legalFilings': [],
                                  'unknown': 'an unknown field'}

def test_added_filing_field():
    """Assert a field added to the dataclass is in the json output, but not in the std library asdict()."""
    filing_name = 'incorporationApplication'
    filing_meta = FilingMeta()

    setattr(filing_meta, to_snake(filing_name), {})

    assert filing_meta
    # should not have the field in the asdict view
    assert not asdict(filing_meta).get(filing_name)
    assert asdict(filing_meta) == {'application_date': None,
                                   'legal_filings': []
                                   }

    # the field should be in the json property
    assert filing_meta.asjson.get(filing_name) == {}
    assert filing_meta.asjson == {'applicationDate': None,
                                  'legalFilings': [],
                                  filing_name: {}}
