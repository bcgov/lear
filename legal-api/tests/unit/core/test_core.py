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

import pytest


def test_node_json():
    """Assert that the node to managed diffs is working as designed."""
    from legal_api.core import Node
    node = Node(old_value=2, new_value='ten', path=['a', 'b'])
    assert node.json == {
        'oldValue': 2,
        'newValue': 'ten',
        'path': '/a/b'
    }


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
]


@ pytest.mark.parametrize('test_name, json1, json2, expected', TEST_JSON_DIFF)
def test_diff_block(test_name, json1, json2, expected):
    """Assert that the diff block gets created correctly."""
    from legal_api.core import diff_dict
    diff = diff_dict(json1, json2)

    ld = [d.json for d in diff]

    assert expected == ld


TEST_JSON_DIFF = [
    ('equal lists',  # test_name
     {'c': 'd', 'a': [{'id': 1, 'j': 'k'}]},
     {'c': 'd', 'a': [{'id': 1, 'j': 'k'}]},
     []  # expected
     ),
    ('same list',  # test_name
     {'c': 'd', 'a': [{'id': 1, 'j': 'k'}]},
     {'c': 'd', 'a': [{'id': 1, 'j': 'k'}]},
     []  # expected
     ),
    ('add list',  # test_name
     {'c': 'd', 'a': [{'id': 1, 'j': 'k'}]},
     {'c': 'd'},
     [
         {'oldValue': None,
          'newValue': [{'id': 1, 'j': 'k'}],
          'path': '/a'},
     ]  # expected
     ),
    ('different list',  # test_name
     {'c': 'd', 'a': [{'id': 1, 'j': 'k'}]},
     {'c': 'd', 'a': [{'id': 1, 'j': 'm'}]},
     [
         {'oldValue': 'm',
          'newValue': 'k',
          'path': '/a/1/j'},
     ]  # expected
     ),
    ('missing list',  # test_name
     {'c': 'd'},
     {'c': 'd', 'a': [{'id': 1, 'j': 'm'}]},
     [
         {'oldValue': [{'id': 1, 'j': 'm'}],
          'newValue': None,
          'path': '/a'},
     ]  # expected
     ),
    ('equal multi-row lists',  # test_name
     {'c': 'd', 'a': [{'id': 1, 'j': 'k'}, {'id': 2, 'm': 'n'}]},
     {'c': 'd', 'a': [{'id': 1, 'j': 'k'}, {'id': 2, 'm': 'n'}]},
     []  # expected
     ),
    ('different nested list',  # test_name
     {'c': 'd', 'a': [{'id': 1, 'j': 'm', 'n': [{'id': 1, 'o': 'p'}]}]},
     {'c': 'd', 'a': [{'id': 1, 'j': 'm', 'n': [{'id': 1, 'o': 'q'}]}]},
     [
         {'oldValue': 'q',
          'newValue': 'p',
          'path': '/a/1/n/1/o'},
     ]  # expected
     ),
    ('different nested  multi-row list',  # test_name
     {'c': 'd', 'a': [{'id': 1, 'j': 'k', 'n': [{'id': 1, 'o': 'p'}]}, {'id': 2, 'm': 'n'}]},
     {'c': 'd', 'a': [{'id': 1, 'j': 'k', 'n': [{'id': 1, 'o': 'q'}]}, {'id': 2, 'm': 'n'}]},
     [
         {'oldValue': 'q',
          'newValue': 'p',
          'path': '/a/1/n/1/o'},
     ]  # expected
     ),
    ('add row to list',  # test_name
     {'c': 'd', 'a': [{'id': 1, 'j': 'k'}, {'id': 2, 'm': 'n'}]},
     {'c': 'd', 'a': [{'id': 1, 'j': 'k'}]},
     [
         {'oldValue': None,
          'newValue': {'id': 2, 'm': 'n'},
          'path': '/a'},
     ]  # expected
     ),
    ('del row from list',  # test_name
     {'c': 'd', 'a': [{'id': 1, 'j': 'k'}]},
     {'c': 'd', 'a': [{'id': 1, 'j': 'k'}, {'id': 2, 'm': 'n'}]},
     [
         {'oldValue': {'id': 2, 'm': 'n'},
          'newValue': None,
          'path': '/a'},
     ]  # expected
     ),
    ('add multi-row to list',  # test_name
     {'c': 'd', 'a': [{'id': 1, 'j': 'k'}, {'id': 2, 'm': 'n'}, {'id': 3, 'o': 'p'}]},
     {'c': 'd', 'a': [{'id': 1, 'j': 'k'}]},
     [
         {'oldValue': None,
          'newValue': {'id': 2, 'm': 'n'},
          'path': '/a'},
         {'oldValue': None,
          'newValue': {'id': 3, 'o': 'p'},
          'path': '/a'},
     ]  # expected
     ),
    ('del multi-row to list',  # test_name
     {'c': 'd', 'a': [{'id': 1, 'j': 'k'}]},
     {'c': 'd', 'a': [{'id': 1, 'j': 'k'}, {'id': 2, 'm': 'n'}, {'id': 3, 'o': 'p'}]},
     [
         {'oldValue': {'id': 2, 'm': 'n'},
          'newValue': None,
          'path': '/a'},
         {'oldValue': {'id': 3, 'o': 'p'},
          'newValue': None,
          'path': '/a'},
     ]  # expected
     ),
    ('change nested  multi-row list',  # test_name
     {'c': 'e', 'a': [{'id': 1, 'j': 'k', 'n': [{'id': 1, 'o': 'p'}]}, {'id': 2, 'm': 'o'}]},
     {'c': 'd', 'a': [{'id': 1, 'j': 'l', 'n': [{'id': 1, 'o': 'q'}]}, {'id': 2, 'm': 'n'}]},
     [
         {'oldValue': 'd',
          'newValue': 'e',
          'path': '/c'},
         {'oldValue': 'l',
          'newValue': 'k',
          'path': '/a/1/j'},
         {'oldValue': 'q',
          'newValue': 'p',
          'path': '/a/1/n/1/o'},
         {'oldValue': 'n',
          'newValue': 'o',
          'path': '/a/2/m'},
     ]  # expected
     ),
    ('different elements in list',  # test_name
     {'c': 'd', 'a': [{'id': 1, 'j': 'm', 'n': [{'id': 1, 'o': 'p', 'r': 's'}]}]},
        {'c': 'd', 'a': [{'id': 1, 'j': 'm', 'n': [{'id': 1, 'o': 'p'}]}]},
        [
         {'oldValue': None,
          'newValue': 's',
          'path': '/a/1/n/1/r'},
     ]  # expected
     ),
]


@ pytest.mark.parametrize('test_name, json1, json2, expected', TEST_JSON_DIFF)
def test_diff_block_list_with_ids(test_name, json1, json2, expected):
    """Assert that the diff block gets created correctly."""
    from legal_api.core import diff_dict, diff_list_with_id
    try:
        diff = diff_dict(json1, json2, diff_list=diff_list_with_id)
    except Exception as err:
        print(err)

    ld = [d.json for d in diff]

    assert expected == ld
