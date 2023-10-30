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
"""File processing rules and actions for Special Resolution filings."""
from typing import Dict

from dateutil.parser import parse

# from entity_queue_common.service_utils import logger
from business_model import LegalEntity, Filing, Resolution


def process(business: LegalEntity, filing: Dict, filing_rec: Filing):
    """Render the special resolution filing unto the model objects."""
    print("Processing Special Resolution : %s", filing)
    if resolution_filing := filing.get("specialResolution"):
        resolution = Resolution(
            resolution=resolution_filing.get("resolution"),
            resolution_type=Resolution.ResolutionType.SPECIAL.value,
            resolution_sub_type=filing_rec.filing_type,
        )

        if signatory := resolution_filing.get("signatory"):
            signatory_le = LegalEntity(
                first_name=signatory.get("givenName").upper()
                if signatory.get("givenName")
                else None,
                last_name=signatory.get("familyName", "").upper(),
                middle_initial=signatory.get("additionalName").upper()
                if signatory.get("additionalName")
                else None,
                entity_type=LegalEntity.EntityTypes.PERSON,
            )
            resolution.signing_legal_entity = signatory_le

        if resolution_filing.get("resolutionDate"):
            resolution.resolution_date = parse(
                resolution_filing.get("resolutionDate")
            ).date()
        if resolution_filing.get("signingDate"):
            resolution.signing_date = parse(resolution_filing.get("signingDate")).date()

        business.resolutions.append(resolution)
