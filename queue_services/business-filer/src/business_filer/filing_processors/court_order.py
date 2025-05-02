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
"""File processing rules and actions for the court order filing."""
from contextlib import suppress
from datetime import datetime

from business_model.models import Business, Document, DocumentType, Filing

from business_filer.filing_meta import FilingMeta


def process(business: Business, court_order_filing: Filing, filing: dict, filing_meta: FilingMeta):
    """Render the court order filing into the business model objects."""
    court_order_filing.court_order_file_number = filing["courtOrder"].get("fileNumber")
    court_order_filing.court_order_effect_of_order = filing["courtOrder"].get("effectOfOrder")
    court_order_filing.order_details = filing["courtOrder"].get("orderDetails")

    with suppress(IndexError, KeyError, TypeError, ValueError):
        court_order_filing.court_order_date = datetime.fromisoformat(filing["courtOrder"].get("orderDate"))

    if file_key := filing["courtOrder"].get("fileKey"):
        document = Document()
        document.type = DocumentType.COURT_ORDER.value
        document.file_key = file_key
        document.business_id = business.id
        document.filing_id = court_order_filing.id
        business.documents.append(document)
