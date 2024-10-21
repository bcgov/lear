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
"""Versioning extension for SQLAlchemy."""
from .debugging import debug
from .versioning import (Base, TransactionFactory, TransactionManager,
                         Versioned, disable_versioning, enable_versioning,
                         version_class)

__all__ = (
    "Base",
    "TransactionFactory",
    "TransactionManager",
    "Versioned",
    "debug",
    "disable_versioning",
    "enable_versioning",
    "version_class"
)
