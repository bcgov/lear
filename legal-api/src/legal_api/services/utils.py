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

import dpath
import pycountry

# ISO-2 codes of countries that do not use postal codes; mirrors the frontend address rules.
NO_POSTAL_CODE_COUNTRY_CODES = {
    "AO", "AG", "AW", "BS", "BZ", "BJ", "BM", "BO", "BQ", "BW", "BF", "BI",
    "CM", "CF", "TD", "KM", "CG", "CD", "CK", "CI", "CW", "DJ", "DM", "GQ",
    "ER", "FJ", "TF", "GA", "GM", "GH", "GD", "GY", "HM", "HK",
    "KI", "KP", "LY", "MO", "MW", "ML", "MR", "NR",
    "AN", "NU", "QA", "RW", "KN", "ST", "SC", "SL", "SX", "SB", "SO", "SR", "SY",
    "TL", "TG", "TK", "TO", "TT", "TV", "UG", "AE", "VU", "YE", "ZW"
}


def is_postal_code_required(country: str) -> bool:
    """Return whether an address in ``country`` must carry a postal code.

    Only countries that resolve to a code in NO_POSTAL_CODE_COUNTRY_CODES are exempt; a missing or
    unrecognised country is treated as requiring one.
    """
    if not country:
        return True
    try:
        country_code = pycountry.countries.search_fuzzy(country)[0].alpha_2
    except LookupError:
        return True
    return country_code not in NO_POSTAL_CODE_COUNTRY_CODES


def get_date(filing: dict, path: str) -> date:
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
        raw = dpath.get(filing, path)
        return date.fromisoformat(raw)
    except (IndexError, KeyError, TypeError, ValueError):
        return None


def get_str(filing: dict, path: str) -> str:
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
        raw = dpath.get(filing, path)
        return str(raw)
    except (IndexError, KeyError, TypeError, ValueError):
        return None


def get_bool(filing: dict, path: str) -> str:
    """Extract a boolean from the JSON filing, at the provided path.

    Args:
        filing (Dict): A valid registry_schema filing.
        path (str): The path to the property.
    """
    try:
        raw = dpath.get(filing, path)
        return bool(raw)
    except (IndexError, KeyError, TypeError, ValueError):
        return None


def get_int(filing: dict, path: str) -> str:
    """Extract int from the JSON filing, at the provided path.

    Args:
        filing (Dict): A valid registry_schema filing.
        path (str): The path to the property.
    """
    try:
        raw = dpath.get(filing, path)
        return int(raw)
    except (IndexError, KeyError, TypeError, ValueError):
        return None
