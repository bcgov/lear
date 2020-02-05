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
"""The schemas and utilities to use them are maintained in this module.

TODO: This should be pulled out to a common library.
"""
from .utils import get_schema, get_schema_store, validate
from .version import __version__


__all__ = ['get_schema', 'get_schema_store', 'validate', '__version__']
