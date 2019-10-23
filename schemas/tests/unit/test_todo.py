# Copyright © 2019 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Test Suite to ensure the legal todo schema is valid.

This suite should have at least 1 test for the annualReport todo item.
"""

from registry_schemas import validate


def test_valid_todo():
    """Assert that the schema accepts a valid todo item."""
    todo = {
        'todo': {
            'business': {
                'cacheId': 1,
                'foundingDate': '2007-04-08',
                'identifier': 'CP0002098',
                'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
                'legalName': 'Legal Name - CP0002098'
            },
            'header': {
                'name': 'annualReport',
                'ARFilingYear': 2019,
                'status': 'NEW'
            }
        }
    }

    is_valid, errors = validate(todo, 'todo')

    # if errors:
    #     for err in errors:
    #         print(err.message)
    print(errors)

    assert is_valid


def test_invalid_todo_name():
    """Assert that the schema rejects a todo item with an invalid name."""
    todo = {
        'invalid': {
            'business': {
                'cacheId': 1,
                'foundingDate': '2007-04-08',
                'identifier': 'CP0002098',
                'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
                'legalName': 'Legal Name - CP0002098'
            },
            'header': {
                'name': 'annualReport',
                'ARFilingYear': 2019,
                'status': 'NEW'
            }
        }
    }

    is_valid, errors = validate(todo, 'todo')

    # if errors:
    #     for err in errors:
    #         print(err.message)
    print(errors)

    assert not is_valid


def test_invalid_todo_missing_business():
    """Assert that the schema rejects a todo item missing the 'business' object."""
    todo = {
        'todo': {
            'header': {
                'name': 'annualReport',
                'ARFilingYear': 2019,
                'status': 'NEW'
            }
        }
    }

    is_valid, errors = validate(todo, 'todo')

    # if errors:
    #     for err in errors:
    #         print(err.message)
    print(errors)

    assert not is_valid


def test_invalid_todo_missing_header():
    """Assert that the schema rejects a todo item missing the 'header' object."""
    todo = {
        'todo': {
            'business': {
                'cacheId': 1,
                'foundingDate': '2007-04-08',
                'identifier': 'CP0002098',
                'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
                'legalName': 'Legal Name - CP0002098'
            }
        }
    }

    is_valid, errors = validate(todo, 'todo')

    # if errors:
    #     for err in errors:
    #         print(err.message)
    print(errors)

    assert not is_valid


def test_invalid_todo_invalid_header():
    """Assert that the schema rejects a todo item with a missing 'header' property."""
    todo = {
        'todo': {
            'business': {
                'cacheId': 1,
                'foundingDate': '2007-04-08',
                'identifier': 'CP0002098',
                'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
                'legalName': 'Legal Name - CP0002098'
            },
            'header': {
                'ARFilingYear': 2019,
                'status': 'NEW'
            }
        }
    }

    is_valid, errors = validate(todo, 'todo')

    # if errors:
    #     for err in errors:
    #         print(err.message)
    print(errors)

    assert not is_valid
