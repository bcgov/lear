# Copyright © 2020 Province of British Columbia
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
"""The Test Suites to ensure that the diff blocks are created correctly."""
from __future__ import annotations

from collections import MutableMapping, MutableSequence
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pytest


@dataclass
class Node:
    """A valid diff element."""

    path: List
    old_value: Any
    new_value: Any

    @property
    def json(self) -> Dict:
        """Return the node in a json styled Dict."""
        return {
            'oldValue': self.old_value,
            'newValue': self.new_value,
            'path': '/'.join([''] + self.path)
        }


def diff_dict(json1, json2, path: List[str] = None, ignore_keys: List[str] = None) -> Optional[List[Node]]:
    """Recursively create a diff record for a dict, based on the corrections JSONSchema definition."""
    diff = []
    path = path or []
    for key, value in json1.items():
        if ignore_keys and key in ignore_keys:
            continue

        if not json2.get(key):
            diff.append(Node(old_value=None,
                             new_value=value,
                             path=path + [key]))

        elif isinstance(value, MutableMapping):
            if d := diff_dict(json1[key], json2[key], path + [key], ignore_keys):
                diff.extend(d)

        elif isinstance(value, MutableSequence):
            if d := diff_list(json1[key], json2[key], path + [key], ignore_keys):
                diff.extend(d)

        elif value != json2.get(key):
            diff.append(Node(old_value=json2.get(key),
                             new_value=value,
                             path=path + [key]))

    for key in (json2.keys() - json1.keys()):
        diff.append(Node(old_value=json2.get(key),
                         new_value=None,
                         path=path + [key]))

    return diff


def diff_list(json1, json2, path: List[str] = None, ignore_keys: List[str] = None) -> Optional[List[Node]]:
    """Return the diff of lists."""
    diff = []
    for item in json1:
        if isinstance(item, MutableMapping):
            pass
        elif isinstance(item, MutableSequence):
            pass
        else:
            pass
    return diff


def diff_block(json1, json2, ignore_keys: List[str] = None):
    """Create the 'diff' block used in a correction filing, based on the JSONSchema for corrections."""
    diff_json = []
    if diff_nodes := diff_dict(json1, json2, ignore_keys):
        for n in diff_nodes:
            diff_json.append(n.json)

    return diff_json


TEST_JSON_DIFF = [
    # equal
    ('equal',  # test_name
     {'c': 'd', 'a': 'b', 'b': {'c': 'd', 'a': {'c': 'd', 'a': 'b'}}},  # json1
     {'a': 'b', 'b': {'a': {'a': 'b', 'c': 'd'}, 'c': 'd'}, 'c': 'd'},  # json2
     []  # expected
     ),
    ('simple equal',  # test_name
     {'a': 'b'},
     {'a': 'b'},
     []  # expected
     ),
    ('simple NOT equal',  # test_name
     {'a': 'b'},
     {'a': 'c'},
     [{
         'oldValue': 'c',
         'newValue': 'b',
         'path': '/a'
     }, ]
     ),
    ('nested equal',  # test_name
     {'a': 'b', 'b': {'a1', 'b1'}},
     {'a': 'b', 'b': {'a1', 'b1'}},
     []
     ),
    ('nested NOT equal',  # test_name
     {'a': 'b', 'b': {'a1': 'b2'}},
     {'a': 'b', 'b': {'a1': 'b1'}},
     [{
         'oldValue': 'b1',
         'newValue': 'b2',
         'path': '/b/a1'
     }, ]
     ),
    ('2 nested NOT equal',  # test_name
     {'a': 'b', 'b': {'a1': 'b1', 'a2': {'a3': 'b3'}}},
     {'a': 'b', 'b': {'a1': 'b1', 'a2': {'a3': 'b4'}}},
     [{
         'oldValue': 'b4',
         'newValue': 'b3',
         'path': '/b/a2/a3'
     }, ]
     ),
    ('3 nested NOT equal',  # test_name
     {'a': 'c', 'b': {'aa': {'aaa': 'bc'}, 'bb': {'bbb': 'b3'}}},
     {'a': 'b', 'b': {'aa': {'aaa': 'b2'}, 'bb': {'bbb': 'b3'}}},
     [
         {'oldValue': 'b',
             'newValue': 'c',
             'path': '/a'},
         {'oldValue': 'b2',
             'newValue': 'bc',
             'path': '/b/aa/aaa'},
     ]
     ),
    ('nested missing',  # test_name
     {'a': 'c', 'b': {'aa': {'aaa': 'bc'}}},
     {'a': 'b', 'b': {'aa': {'aaa': 'bc'}, 'bb': {'bbb': 'b3'}}},
     [
         {'oldValue': 'b',
             'newValue': 'c',
             'path': '/a'},
         {'oldValue': {'bbb': 'b3'},
             'newValue': None,
             'path': '/b/bb'},
     ]
     ),
    ('nested added',  # test_name
     {'a': 'b', 'b': {'aa': {'aaa': 'bc'}, 'bb': {'bbb': 'b3'}}},
     {'a': 'c', 'b': {'aa': {'aaa': 'bc'}}},
     [
         {'oldValue': 'c',
             'newValue': 'b',
             'path': '/a'},
         {'oldValue': None,
             'newValue': {'bbb': 'b3'},
             'path': '/b/bb'},
     ]
     ),
    # ('equal lists',  # test_name
    #  {'c': 'd', 'a': [{'j': 'k'}]},
    #  {'c': 'd', 'a': [{'j': 'k'}]},
    #  []  # expected
    #  ),
    # ('equal unordered lists',  # test_name
    #  {'c': 'd', 'a': [{'j': 'k'}, {'m': 'n'}]},
    #  {'c': 'd', 'a': [{'m': 'n'}, {'j': 'k'}]},
    #  []  # expected
    #  ),
]


@ pytest.mark.parametrize('test_name, json1, json2, expected', TEST_JSON_DIFF)
def test_diff_block(test_name, json1, json2, expected):
    """Assert that the diff block gets created correctly."""
    diff = diff_block(json1, json2)

    assert expected == diff
