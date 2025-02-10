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
"""Constants for legal api."""

from enum import Enum


BOB_DATE = '2019-03-08'

class DocumentClassEnum(Enum):
    CORP = 'CORP'
    COOP = 'COOP'

class DocumentTypeEnum(Enum):
    CNTO = 'CNTO',
    DIRECTOR_AFFIDAVIT = 'DIRECTOR_AFFIDAVIT'
    CORP_AFFIDAVIT = 'CORP_AFFIDAVIT'
    COOP_MEMORANDUM = 'COOP_MEMORANDUM'
    COOP_RULES = 'COOP_RULES'