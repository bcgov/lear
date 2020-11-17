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
"""This has the core domain used by the application."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, MutableMapping, MutableSequence, Optional


@dataclass
class Node:
    """A valid diff element."""

    path: List
    old_value: Any
    new_value: Any

    @property
    def json(self) -> Optional[Dict]:
        """Return the node in a json styled Dict."""
        return {
            'oldValue': self.old_value,
            'newValue': self.new_value,
            'path': '/'.join([''] + self.path)
        }


def diff_dict(json1,
              json2,
              path: List[str] = None,
              ignore_keys: List[str] = None,
              diff_list: Callable[[dict, dict, List, List], Optional[List]] = None) \
        -> Optional[List[Node]]:
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
            if d := diff_dict(json1=json1[key],
                              json2=json2[key],
                              path=path + [key],
                              ignore_keys=ignore_keys,
                              diff_list=diff_list):
                diff.extend(d)

        elif isinstance(value, MutableSequence):
            if diff_list:
                if d := diff_list(json1[key], json2[key], path + [key], ignore_keys):
                    diff.extend(d)

        elif value != json2.get(key):
            diff.append(Node(old_value=json2.get(key),
                             new_value=value,
                             path=path + [key]))

    for key in json2.keys() - json1.keys():
        diff.append(Node(old_value=json2.get(key),
                         new_value=None,
                         path=path + [key]))

    return diff


def diff_list_with_id(json1,  # pylint: disable=too-many-branches; linter balking on := walrus
                      json2,
                      path: List[str] = None,
                      ignore_keys: List[str] = None) \
        -> Optional[List[Node]]:
    """Return the differences nodes between json1 & json2, being a list of dicts.

    Every dict is assumed to have a ID that is unique at the list level.
    """
    if not (isinstance(json1, MutableSequence) or isinstance(json2, MutableSequence)):
        return None

    # if not json2
    if not json2:
        return [Node(
            old_value=None,
            new_value=json1,
            path=[''] if not path else path
        )]

    diff = []
    memoize = []
    for row1 in json1:
        if not (row1_id := row1.get('id')):  # pylint: disable=superfluous-parens; linter confused by the walrus :=
            continue

        dict2 = None
        for row2 in json2:
            if row1_id == row2.get('id'):
                dict2 = row2
                break

        if dict2:
            if d := diff_dict(row1, dict2, path + [str(row1_id)], ignore_keys, diff_list=diff_list_with_id):
                diff.extend(d)
        else:
            diff.append(Node(
                old_value=None,
                new_value=row1,
                path=[''] if not path else path
            ))
        memoize.append(row1_id)

    if len(memoize) < len(json2):
        for row in json2:
            if row_id := row.get('id', None):
                if row_id not in memoize:
                    diff.append(Node(
                        old_value=row,
                        new_value=None,
                        path=[''] if not path else path
                    ))

    return diff
