import json
from collections import MutableMapping, MutableSequence
from dataclasses import dataclass, field
from typing import Any, Dict, List

import pytest


@dataclass
class node:
    path: List
    old_value: Any
    new_value: Any

    @property
    def json(self) -> Dict:
        return {
            'oldValue': self.old_value,
            'newValue': self.new_value,
            'path': '/'.join([''] + self.path)
        }


def del_keys(data, key: str):
    leaves = [str, int, bool]
    keys = key.split('/')
    keys.remove('')
    for k in keys:
        if v := data.get(k):
            pass
        else:
            break
    return data


def diff_dict(json1, json2, path: List[str] = None, ignore_keys: List[str] = None) -> List[node]:
    diff = []
    path = path or []
    for key, value in json1.items():
        if ignore_keys and key in ignore_keys:
            continue

        if not json2.get(key):
            diff.append(node(old_value=None,
                             new_value=value,
                             path=path + [key]))

        elif isinstance(value, MutableMapping):
            if d := diff_dict(json1[key], json2[key], path + [key], ignore_keys):
                diff.extend(d)

        elif isinstance(value, MutableSequence):
            if d := diff_list(json1[key], json2[key], path + [key], ignore_keys):
                diff.extend(d)

        elif value != json2.get(key):
            diff.append(node(old_value=json2.get(key),
                             new_value=value,
                             path=path + [key]))

    for key in (json2.keys() - json1.keys()):
        diff.append(node(old_value=json2.get(key),
                         new_value=None,
                         path=path + [key]))

    return diff

    def diff_list(json1, json2, path: List[str] = None, ignore_keys: List[str] = None) -> List[node]:
        """Return the diff of lists."""
        diff = []
        for item in json1:
            if isinstance(item, MutableMapping):
                if rv := del_key_in_dict(item, keys):
                    modified_list.append(rv)
            elif isinstance(item, MutableSequence):
                if rv := scan_list(item, keys):
                    modified_list.append(rv)
            else:
                try:
                    if item not in keys:
                        modified_list.append(item)
                except:  # noqa: E722
                    modified_list.append(item)
        return modified_list


def diff_block(json1, json2, ignore_keys: List[str] = None):
    diff_json = []
    if diff_nodes := diff_dict(json1, json2, ignore_keys):
        for n in diff_nodes:
            diff_json.append(n.json)

    return diff_json


TEST_JSON_DIFF = [
    # equal
    ('equal',  # test_name
     {"c": "d", "a": "b", "b": {"c": "d", "a": {"c": "d", "a": "b"}}},  # json1
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
    ('equal lists',  # test_name
     {"c": "d", "a": [{'j': 'k'}]},
     {"c": "d", "a": [{'j': 'k'}]},
     []  # expected
     ),
    ('equal unordered lists',  # test_name
     {"c": "d", "a": [{'j': 'k'}, {'m': 'n'}]},
     {"c": "d", "a": [{'m': 'n'}, {'j': 'k'}]},
     []  # expected
     ),
]


@ pytest.mark.parametrize('test_name, json1, json2, expected', TEST_JSON_DIFF)
def test_diff_block(test_name, json1, json2, expected):

    diff = diff_block(json1, json2)

    assert expected == diff
