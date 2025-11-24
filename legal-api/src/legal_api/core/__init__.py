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
from typing import Any, Callable, Optional

from .business import BusinessIdentifier, BusinessType
from .filing import Filing
from .meta import FILINGS, FilingMeta

__all__ = (
    "FILINGS",
    "BusinessIdentifier",
    "BusinessType",
    "Filing",
    "FilingMeta",
)
