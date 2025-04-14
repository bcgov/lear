# Copyright © 2021 Province of British Columbia
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
"""Track the meta information for a filing_submission.

Alternate to pydantic just using regular dataclass to track meta info
and custom serialization with the goodness of typing.

Also supporting the dynamic class behavior found in Python to make adoption easier.
"""
import re
from dataclasses import dataclass, field, fields
from datetime import date, datetime
from typing import Optional


def to_camel(string: str) -> Optional[str]:
    """Convert snake_case to camelCase.

    This does not strip punctuation or whitespace characters.
    """
    if not isinstance(string, str):
        return None

    return ''.join(word.lower() if idx == 0 else
                   word.capitalize()
                   for idx, word in enumerate(string.split('_')))


def to_snake(string: str) -> Optional[str]:
    """Convert camelCase to snake_case.

    This does not strip punctuation or whitespace characters.
    """
    if not isinstance(string, str):
        return None

    return re.sub(r'([A-Z])', r'_\1', string).lower()


def json_serial(obj):
    """JSON serializer for datetime and dates."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f'Type {type(obj)} not serializable')


@dataclass
class FilingMeta:
    """Holds the variable metadata about a filing."""

    application_date: Optional[datetime] = None
    legal_filings: list = field(default_factory=list)

    @property
    def asjson(self):
        """Return the json formatted dict for this instance."""
        d = {}
        for f in fields(self):
            d[to_camel(f.name)] = self.__dict__[f.name]

        if len(self.__dict__) != len(fields(self)):
            additional_fields = set(self.__dict__) - {x.name for x in fields(self)}
            for f in additional_fields:
                d[to_camel(f)] = self.__dict__[f]
        return d
