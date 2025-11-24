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

from collections.abc import MutableMapping, MutableSequence
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class Node:
    """A valid diff element."""

    path: list
    old_value: Any
    new_value: Any

    @property
    def json(self) -> dict | None:
        """Return the node in a json styled Dict."""
        return {
            "oldValue": self.old_value,
            "newValue": self.new_value,
            "path": "/".join(["", *self.path])
        }


def diff_dict(json1,
              json2,
              path: list[str] | None = None,
              ignore_keys: list[str] | None = None,
              diff_list_callback: Callable[[dict, dict, list, list], list | None] | None = None) \
        -> list[Node] | None:
    """Recursively create a diff record for a dict, based on the corrections JSONSchema definition."""
    diff = []
    path = path or []
    for key, value in json1.items():
        if ignore_keys and key in ignore_keys:
            continue

        if json2.get(key) is None and value is not None:
            diff.append(Node(old_value=None,
                             new_value=value,
                             path=[*path, key]))

        elif isinstance(value, MutableMapping):
            if d := diff_dict(json1=json1[key],
                              json2=json2[key],
                              path=[*path, key],
                              ignore_keys=ignore_keys,
                              diff_list_callback=diff_list):
                diff.extend(d)

        elif isinstance(value, MutableSequence):
            if (
                diff_list_callback and
                (d := diff_list_callback(json1[key], json2[key], [*path, key], ignore_keys))
            ):
                diff.extend(d)

        elif value != json2.get(key):
            diff.append(Node(old_value=json2.get(key),
                             new_value=value,
                             path=[*path, key]))

    for key in json2.keys() - json1.keys():
        diff.append(Node(old_value=json2.get(key),
                         new_value=None,
                         path=[*path, key]))

    return diff


def diff_list(json1,  # pylint: disable=too-many-branches; linter balking on := walrus
              json2,
              path: list[str] | None = None,
              ignore_keys: list[str] | None = None) \
        -> list[Node] | None:
    """Return the differences nodes between json1 & json2, being a list of dicts.

    JSON1 Rows missing an "id" will be marked as additions.
    JSON2 Rows missing an "id" are ignored.
    """
    if not (isinstance(json1, MutableSequence) or isinstance(json2, MutableSequence)):
        return None

    # if not json2
    if not json2:
        return [Node(
            old_value=None,
            new_value=json1,
            path=path if path else [""]
        )]

    diff = []
    memoize = []
    for row1 in json1:
        add_row = True
        if row1_id := row1.get("id"):
            for row2 in json2:
                if row1_id == row2.get("id"):
                    if d := diff_dict(row1, row2, [*path, str(row1_id)], ignore_keys, diff_list_callback=diff_list):
                        diff.extend(d)
                    memoize.append(row1_id)
                    add_row = False
                    break
        if add_row:
            diff.append(Node(
                old_value=None,
                new_value=row1,
                path=path if path else [""]
            ))

    json2_rows = [x.get("id") for x in json2]

    if deleted_rows := set(json2_rows).difference(memoize):
        for row in json2:
            if row.get("id", "") in deleted_rows:
                diff.append(Node(
                    old_value=row,
                    new_value=None,
                    path=path if path else [""]
                ))

    return diff
