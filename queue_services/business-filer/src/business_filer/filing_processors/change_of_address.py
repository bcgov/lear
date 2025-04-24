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
"""File processing rules and actions for the change of address."""
from datetime import UTC

from business_model.models import BatchProcessing, Business
from datedelta import datedelta

from business_filer.common.datetime import datetime
from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors.filing_components import create_address, update_address


def process(business: Business, filing: dict, filing_meta: FilingMeta, flag_on: bool):
    """Render the change_of_address onto the business model objects."""
    offices = filing["changeOfAddress"]["offices"]

    business.last_coa_date = filing_meta.application_date

    for item in offices:
        office = business.offices.filter_by(office_type=item).one_or_none()
        for key, new_address in offices[item].items():
            k = key.replace("Address", "")
            address = office.addresses.filter_by(address_type=k).one_or_none()
            if address:
                update_address(address, new_address)
            else:
                address = create_address(new_address, k)
                office.addresses.append(address)

    if flag_on and business.in_dissolution:
        batch_processings = BatchProcessing.find_by(business_id=business.id)
        for batch_processing in batch_processings:
            if batch_processing.status not in [
                BatchProcessing.BatchProcessingStatus.COMPLETED,
                BatchProcessing.BatchProcessingStatus.WITHDRAWN
            ] and datetime.now(UTC) + datedelta(days=60) > batch_processing.trigger_date:
                batch_processing.trigger_date = datetime.now(UTC) + datedelta(days=62)
                batch_processing.meta_data = {
                    **batch_processing.meta_data,
                    "changeOfAddressDelay": True
                }
                batch_processing.last_modified = datetime.now(UTC)
