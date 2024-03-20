# Copyright © 2022 Province of British Columbia
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
"""File processing rules and actions for the admin freeze filing."""

from typing import Dict

import dpath
from business_model import Filing, LegalEntity

from entity_filer.exceptions import DefaultException
from entity_filer.filing_meta import FilingMeta


def process(business: LegalEntity, filing: Dict, filing_rec: Filing, filing_meta: FilingMeta):
    """Render the admin freeze filing unto the model objects."""
    if not (admin_freeze_filing := filing.get("adminFreeze")):
        print("Could not find adminFreeze in: %s", filing)
        raise DefaultException(f"legal_filing:adminFreeze missing from {filing}")

    print("processing adminFreeze: %s", filing)

    freeze = bool(dpath.util.get(admin_freeze_filing, "/freeze"))
    filing_rec.order_details = admin_freeze_filing.get("details")
    business.admin_freeze = freeze

    filing_meta.admin_freeze = {}
    filing_meta.admin_freeze = {**filing_meta.admin_freeze, **{"freeze": freeze}}
