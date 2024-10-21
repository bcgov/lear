# Copyright © 2024 Province of British Columbia
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
"""Utilities used for debugging."""
# TODO: remove this debugging utility file
import functools


def debug(func):
    """A decorator to print a message before and after a function call."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print(f'\033[34m--> Entering {func.__qualname__}()\033[0m')
        ret = func(*args, **kwargs)
        print(f'\033[34m<-- Exiting {func.__qualname__}()\033[0m')
        return ret
    return wrapper
