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
"""Common utilities used by the services."""
from datetime import date
from typing import Dict

import dpath.util


def get_date(filing: Dict, path: str) -> date:
    """Extract a date from the JSON filing, at the provided path.

    Args:
        filing (Dict): A valid registry_schema filing.
        path (str): The path to the date, which is in ISO Format.

    Examples:
        >>>get_date(
            filing={'filing':{'header':{'date': '2001-08-05'}}},
            path='filing/header/date')
        date(2001, 8, 5)

    """
    try:
        raw = dpath.util.get(filing, path)
        return date.fromisoformat(raw)
    except (IndexError, KeyError, TypeError, ValueError):
        return None


def get_str(filing: Dict, path: str) -> str:
    """Extract a str from the JSON filing, at the provided path.

    Args:
        filing (Dict): A valid registry_schema filing.
        path (str): The path to the date, which is in ISO Format.

    Examples:
        >>>get_str(
            filing={'filing':{'header':{'name': 'annualReport'}}},
            path='filing/header/name')
        'annualReport'

    """
    try:
        raw = dpath.util.get(filing, path)
        return str(raw)
    except (IndexError, KeyError, TypeError, ValueError):
        return None


def get_bool(filing: Dict, path: str) -> str:
    """Extract a boolean from the JSON filing, at the provided path.

    Args:
        filing (Dict): A valid registry_schema filing.
        path (str): The path to the property.
    """
    try:
        raw = dpath.util.get(filing, path)
        return bool(raw)
    except (IndexError, KeyError, TypeError, ValueError):
        return None


def get_int(filing: Dict, path: str) -> str:
    """Extract int from the JSON filing, at the provided path.

    Args:
        filing (Dict): A valid registry_schema filing.
        path (str): The path to the property.
    """
    try:
        raw = dpath.util.get(filing, path)
        return int(raw)
    except (IndexError, KeyError, TypeError, ValueError):
        return None
