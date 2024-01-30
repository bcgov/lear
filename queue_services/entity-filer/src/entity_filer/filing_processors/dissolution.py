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
"""File processing rules and actions for Dissolution and Liquidation filings."""
from contextlib import suppress
from typing import Dict

import dpath
import sentry_sdk

# from entity_filer.exceptions import DefaultException, logger
from business_model import LegalEntity, Document, Filing

# from business_model.document import DocumentType
from business_model.models.filing import DissolutionTypes

# from legal_api.services.minio import MinioService
# from legal_api.services.pdf_service import RegistrarStampData
from entity_filer.utils.legislation_datetime import LegislationDatetime
from entity_filer.exceptions import BusinessException, get_error_message, ErrorCode

from entity_filer.filing_meta import FilingMeta
from entity_filer.filing_processors.filing_components import create_office, filings
from entity_filer.filing_processors.filing_components.parties import merge_all_parties

# from entity_filer.utils import replace_file_with_certified_copy


def process(business: LegalEntity, filing: Dict, filing_rec: Filing, filing_meta: FilingMeta):
    """Render the dissolution filing unto the model objects."""
    if not (dissolution_filing := filing.get("dissolution")):
        print("Could not find Dissolution in: %s", filing)
        raise BusinessException(
            f"legal_filing:Dissolution missing from {filing}",
            get_error_message(ErrorCode.GENERAL_UNRECOVERABLE_ERROR, **{"filing_id": filing_rec.id}),
        )

    print("processing dissolution: %s", filing)

    filing_meta.dissolution = {}
    dissolution_type = dpath.util.get(filing, "/dissolution/dissolutionType")

    # hasLiabilities can be derived from dissolutionStatementType
    # FUTURE: remove hasLiabilities from schema
    # has_liabilities = filing['dissolution'].get('hasLiabilities')

    # should we save dissolution_statement_type in businesses table?
    # dissolution_statement_type = filing['dissolution'].get('dissolutionStatementType')
    dissolution_date = filing_rec.effective_date
    if dissolution_type == DissolutionTypes.VOLUNTARY and business.entity_type in (
        LegalEntity.EntityTypes.SOLE_PROP.value,
        LegalEntity.EntityTypes.PARTNERSHIP.value,
    ):
        dissolution_date_str = dissolution_filing.get("dissolutionDate")
        dissolution_date = LegislationDatetime.as_utc_timezone_from_legislation_date_str(dissolution_date_str)
    business.dissolution_date = dissolution_date

    business.state = LegalEntity.State.HISTORICAL
    business.state_filing_id = filing_rec.id

    # add custodial party if in filing
    if parties := dissolution_filing.get("parties"):
        merge_all_parties(business, filing_rec, {"parties": parties})

    # add custodial office if provided
    if custodial_office := dissolution_filing.get("custodialOffice"):
        if office := create_office(business, "custodialOffice", custodial_office):
            business.offices.append(office)
        else:
            print("Could not create custodial office for Dissolution in: %s", filing)
            sentry_sdk.print(
                f"Queue Error: Could not create custodial office for Dissolution filing:{filing.id}",
                level="error",
            )

    filing_rec.order_details = dissolution_filing.get("details")

    # update court order, if any is present
    with suppress(IndexError, KeyError, TypeError):
        court_order_json = dpath.util.get(dissolution_filing, "/courtOrder")
        filings.update_filing_court_order(filing_rec, court_order_json)

    if business.entity_type == LegalEntity.EntityTypes.COOP:
        _update_cooperative(dissolution_filing, business, filing_rec, dissolution_type)

    with suppress(IndexError, KeyError, TypeError):
        filing_meta.dissolution = {
            **filing_meta.dissolution,
            "dissolutionType": dissolution_type,
            "dissolutionDate": LegislationDatetime.format_as_legislation_date(business.dissolution_date),
        }


def _update_cooperative(dissolution_filing: Dict, business: LegalEntity, filing: Filing, dissolution_type):
    """Update COOP data.

    This should not be updated for administrative dissolution
    """
    # TODO remove tis?
    pass
    # if dissolution_type == DissolutionTypes.ADMINISTRATIVE:
    #     return

    # # create certified copy for affidavit document
    # affidavit_file_key = dissolution_filing.get('affidavitFileKey')
    # affidavit_file = MinioService.get_file(affidavit_file_key)
    # registrar_stamp_data = RegistrarStampData(filing.effective_date, business.identifier)

    # replace_file_with_certified_copy(affidavit_file.data, business, affidavit_file_key, registrar_stamp_data)

    # document = Document()
    # document.type = DocumentType.AFFIDAVIT.value
    # document.file_key = affidavit_file_key
    # document.business_id = business.id
    # document.filing_id = filing.id
    # business.documents.append(document)


def post_process(business: LegalEntity, filing: Filing, correction: bool = False):  # pylint: disable=W0613
    """Post processing activities for incorporations.

    THIS SHOULD NOT ALTER THE MODEL
    """
