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
"""Manages the  names of a Business."""
from contextlib import suppress

from business_common.utils import datetime
from business_model.models import Business, CourtOrder, Filing
from business_model.models.types.filings import FilingTypes
from flask_babel import _ as babel

from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors.filing_components import documents
from business_filer.services.utils import is_same_str


def create_court_order(filing: Filing,
                       court_order: dict,
                       filing_meta: FilingMeta = None,
                       new_business: Business = None) -> dict | None:
    """Create a court order."""
    if not (file_number := court_order.get("fileNumber")):
        return None

    court_order_obj = CourtOrder(
        file_number=file_number,
        effect_of_order=court_order.get("effectOfOrder"),
        order_details=court_order.get("orderDetails"),
    )
    with suppress(IndexError, KeyError, TypeError, ValueError):
        court_order_obj.order_date = datetime.fromisoformat(court_order.get("orderDate"))

    court_order_meta = {"fileNumber": file_number}
    if court_order_obj.effect_of_order:
        court_order_meta["effectOfOrder"] = court_order_obj.effect_of_order
    if court_order.get("orderDate"):
        court_order_meta["orderDate"] = court_order.get("orderDate")
    if filing.filing_type == FilingTypes.COURTORDER:
        # Only add order details for court orders
        court_order_meta["orderDetails"] = court_order_obj.order_details

    if filing_meta:
        filing_meta.court_order = court_order_meta

    if new_business:
        court_order_obj.filing_id = filing.id
        new_business.court_orders.append(court_order_obj)
    else:
        court_order_obj.business_id = filing.business_id
        filing.court_orders.append(court_order_obj)

    return court_order_meta


def update_court_orders(business: Business,
                        court_orders: list[dict],
                        filing_meta: FilingMeta) -> None:
    """Update court orders."""
    if not business:
        return {"error": babel("Business is required before a court order can be created.")}

    court_orders_meta = []
    for court_order in court_orders:
        filing = Filing.find_by_id(court_order.get("filingId"))
        file_number = court_order.get("fileNumber")
        effect_of_order = court_order.get("effectOfOrder")
        order_details = court_order.get("orderDetails")
        has_changed = False
        court_order_meta = {"filingId": filing.id}
        if court_order_id := court_order.get("id"):
            court_order_obj = CourtOrder.get_by_id(court_order_id)

            if not is_same_str(court_order_obj.file_number, file_number):
                court_order_meta["fileNumber"] = file_number
                has_changed = True
            if not is_same_str(court_order_obj.effect_of_order, effect_of_order):
                court_order_meta["effectOfOrder"] = effect_of_order
                has_changed = True
            if not is_same_str(court_order_obj.order_details, order_details):
                court_order_meta["orderDetails"] = order_details
                has_changed = True

            court_order_obj.file_number = file_number
            court_order_obj.effect_of_order = effect_of_order
            court_order_obj.order_details = order_details
            filing.court_orders.append(court_order_obj)
        else:
            court_order_meta = {
                **court_order_meta,
                **create_court_order(filing, court_order)
            }
            has_changed = True

        documents_changed = update_court_order_documents(court_order, filing, business, court_order_meta)
        if has_changed or documents_changed:
            # Only add court order if there are any changes
            court_orders_meta.append(court_order_meta)

    if court_orders_meta:
        filing_meta.court_orders = court_orders_meta


def update_court_order_documents(court_order: dict, filing: Filing, business: Business, court_order_meta: dict) -> bool:
    """Update court order documents if the filing is a court order."""
    if (
            filing.filing_type != FilingTypes.COURTORDER or
            "files" not in court_order
    ):
        return False

    documents_changed = False
    files = court_order.get("files", [])
    new_files = []
    if court_order_documents := filing.documents.all():
        existing_file_keys = [document.file_key for document in court_order_documents]
        new_files = [file for file in files if file.get("fileKey") not in existing_file_keys]
        deleted_documents = [
            document
            for document in court_order_documents
            if document.file_key not in [file.get("fileKey") for file in files]
        ]
        if deleted_documents:
            for document in deleted_documents:
                filing.documents.remove(document)
            documents_changed = True
    else:
        new_files = files

    if new_files:
        file_list = documents.create_filing_documents(new_files, business, filing)
        court_order_meta["files"] = file_list
        documents_changed = True
    return documents_changed
