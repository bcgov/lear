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
