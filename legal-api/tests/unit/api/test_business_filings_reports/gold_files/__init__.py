# Copyright © 2019 Province of British Columbia
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
"""Test Suite for Reports using gold_files and the associated helper functions."""
import datetime
import inspect
import json
import os
from typing import Dict


__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))


def _retrieve_name(var):
    return var['filing']['header']['name']


def _get_json_sent_as_saved_example(var: object) -> Dict:
    """Return the example JSON sent to the Report Service."""
    try:
        example_name = _retrieve_name(var)
        with open(os.path.join(__location__, f'{example_name}.json')) as json_file:
            return json.load(json_file)
    except:  # noqa: E722; only used for testing purposes and we don't care why it failed.
        return {}


def matches_sent_snapshot(example, request_json, **ignore_keys):
    """Assert that the request_json matches the snapshot.

    The gold_file for the example is retrieved (the snapshot) and compared the the request_json.
    If they match, True is returned.
    If they do not match the request_json is dumped as new snapshot and an Exception is thrown.

    """
    gold_json = _get_json_sent_as_saved_example(example)

    if {**request_json, **ignore_keys} == {**gold_json, **ignore_keys}:
        return True

    new_snap_filename = _retrieve_name(example) + \
        datetime.datetime.utcnow().isoformat().translate(str.maketrans('T:.', '___'))
    with open(os.path.join(__location__, f'{new_snap_filename}.json'), 'w') as f:
        json.dump(request_json, f)

    raise Exception(f'new snapshot saved as: {new_snap_filename}')
