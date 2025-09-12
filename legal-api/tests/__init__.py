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
"""The Test Suites to ensure that the service is built and operating correctly."""
import datetime
import time
from collections.abc import MutableMapping, MutableSequence
from typing import Dict, List

from .pytest_marks import (
    api_v1,
    api_v2,
    integration_affiliation,
    integration_authorization,
    integration_colin,
    integration_namerequests,
    integration_payment,
    integration_reports,
    todo_tech_debt,
    not_github_ci,
)


EPOCH_DATETIME = datetime.datetime.utcfromtimestamp(0).replace(tzinfo=datetime.timezone.utc)
FROZEN_DATETIME = datetime.datetime(2001, 8, 5, 7, 7, 58, 272362).replace(tzinfo=datetime.timezone.utc)
FROZEN_2018_DATETIME = datetime.datetime(2018, 12, 25, 0, 0, 50, 0).replace(tzinfo=datetime.timezone.utc)
TIMEZONE_OFFSET=time.timezone/60/60 if time.timezone else 0


def add_years(d, years):
    """Return a date that's `years` years after the date (or datetime).

    Return the same calendar date (month and day) in the destination year,
    if it exists, otherwise use the following day
    (thus changing February 29 to February 28).
    """
    try:
        return d.replace(year=d.year + years)
    except ValueError:
        return d + (datetime.date(d.year + years, 3, 1) - datetime.date(d.year, 3, 1))


def strip_keys_from_dict(orig_dict: Dict, keys: List) -> Dict:
    """Return a deep copy of the dict with the keys stripped out."""
    def del_key_in_dict(orig_dict, keys):
        """Remove keys from dictionaires."""
        modified_dict = {}
        for key, value in orig_dict.items():
            if key not in keys:
                if isinstance(value, MutableMapping):  # or
                    modified_dict[key] = del_key_in_dict(value, keys)
                elif isinstance(value, MutableSequence):
                    if rv := scan_list(value, keys):
                        modified_dict[key] = rv
                else:
                    modified_dict[key] = value  # or copy.deepcopy(value) if a copy is desired for non-dicts.
        return modified_dict

    def scan_list(orig_list, keys):
        """Remove keys from lists."""
        modified_list = []
        for item in orig_list:
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

    key_set = set(keys)
    return del_key_in_dict(orig_dict, key_set)
