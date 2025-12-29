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
"""Manages the offices for a business."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from business_model.models import Business, Office

from business_filer.filing_processors.filing_components import create_address, create_office, update_address


def update_offices(business: Business, offices_structure: dict) -> list | None:
    """Manage the office for a business.

    Assumption: The structure has already been validated, upon submission.

    Other errors are recorded and will be managed out of band.
    """
    if not business:
        # if nothing is passed in, we don't care and it's not an error
        return None

    err = []

    if offices_structure:
        try:
            delete_existing_offices(business)
        except:
            err.append(
                {"error_code": "FILER_UNABLE_TO_DELETE_OFFICES",
                 "error_message": f"Filer: unable to delete offices for :'{business.identifier}'"}
            )
            return err

        try:
            for office_type, addresses in offices_structure.items():
                office = create_office(business, office_type, addresses)
                business.offices.append(office)
        except KeyError:
            err.append(
                {"error_code": "FILER_UNABLE_TO_SAVE_OFFICES",
                 "error_message": f"Filer: unable to save new offices for :'{business.identifier}'"}
            )
    return err


def delete_existing_offices(business: Business):
    """Delete the existing offices for a business."""
    if existing_offices := business.offices.all():
        for office in existing_offices:
            business.offices.remove(office)


def update_or_create_offices(business: Business, offices: dict[str, dict[str, dict[str, str]]]) -> list | None:
    """Update existing or create offices for a business.

    Assumption: The structure has already been validated, upon submission.

    Other errors are recorded and will be managed out of band.
    """

    err = []

    try:
        for office_type, addresses in offices.items():
            office: Office = business.offices.filter_by(office_type=office_type).one_or_none()
            if office:
                for key, new_address in addresses.items():
                    address_type = key.replace("Address", "")
                    address = office.addresses.filter_by(address_type=address_type).one_or_none()
                    if address:
                        update_address(address, new_address)
                    else:
                        address = create_address(new_address, address_type)
                        office.addresses.append(address)
            else:
                office = create_office(business, office_type, addresses)

            business.offices.append(office)

    except KeyError:
        err.append(
            {"error_code": "FILER_UNABLE_TO_SAVE_OFFICES",
                "error_message": f"Filer: unable to save new offices for :'{business.identifier}'"}
        )
    return err
