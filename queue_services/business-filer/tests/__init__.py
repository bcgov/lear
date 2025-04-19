# Copyright © 2025 Province of British Columbia
#
# Licensed under the BSD 3 Clause License, (the "License");
# you may not use this file except in compliance with the License.
# The template for the license can be found here
#    https://opensource.org/license/bsd-3-clause/
#
# Redistribution and use in source and binary forms,
# with or without modification, are permitted provided that the
# following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS”
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
"""The Test Suites to ensure that the service is built and operating correctly."""
import copy
import datetime
from collections.abc import MutableMapping, MutableSequence
from typing import Dict, List



EPOCH_DATETIME = datetime.datetime.utcfromtimestamp(0)
FROZEN_DATETIME = datetime.datetime(2001, 8, 5, 7, 7, 58, 272362)


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
