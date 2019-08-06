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
"""Test Suite to ensure the legal task schema is valid.

This suite should have at least 1 test for filing and todo task items.
"""

from registry_schemas import validate


def test_valid_task_todo():
    """Assert that the schema accepts a valid todo task."""
    task = {
        'task': {
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
        },
        'order': 2,
        'enabled': False
    }

    is_valid, errors = validate(task, 'task')

    # if errors:
    #     for err in errors:
    #         print(err.message)
    print(errors)

    assert is_valid


def test_valid_task_filing():
    """Assert that the schema accepts a valid filing task."""
    task = {
        'task': {
            'filing': {
                'annualReport': {
                    'annualGeneralMeetingDate': '2018-07-15',
                    'certifiedBy': 'full1 name1',
                    'email': 'no_one@never.get'
                },
                'business': {
                    'cacheId': 1,
                    'foundingDate': '2007-04-08',
                    'identifier': 'CP0002098',
                    'lastLedgerTimestamp': '2019-04-15T20:05:49.068272+00:00',
                    'legalName': 'Legal Name - CP0002098'
                },
                'header': {
                    'date': '2017-06-06',
                    'filingId': 1,
                    'name': 'annualReport',
                    'status': 'DRAFT'
                }
            }
        },
        'order': 1,
        'enabled': True
    }

    is_valid, errors = validate(task, 'task')

    # if errors:
    #     for err in errors:
    #         print(err.message)
    print(errors)

    assert is_valid


def test_invalid_task_neither():
    """Assert that the schema rejects an invalid task."""
    task = {
        'task': {
            'invalid': {
                'foo': 'abc',
                'bar': '123'
            }
        },
        'order': 2,
        'enabled': False
    }

    is_valid, errors = validate(task, 'task')

    # if errors:
    #     for err in errors:
    #         print(err.message)
    print(errors)

    assert not is_valid


def test_invalid_task_missing_order():
    """Assert that the schema rejects a task missing the 'order' property."""
    task = {
        'task': {
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
        },
        'enabled': False
    }

    is_valid, errors = validate(task, 'task')

    # if errors:
    #     for err in errors:
    #         print(err.message)
    print(errors)

    assert not is_valid


def test_invalid_task_missing_enabled():
    """Assert that the schema rejects a task missing the 'enabled' property."""
    task = {
        'task': {
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
        },
        'order': 2
    }

    is_valid, errors = validate(task, 'task')

    # if errors:
    #     for err in errors:
    #         print(err.message)
    print(errors)

    assert not is_valid
