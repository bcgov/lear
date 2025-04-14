# Copyright © 2020 Province of British Columbia
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
"""Manages the offices for a business."""
from __future__ import annotations

from typing import Dict, List, Optional

from business_model.models import Business

from business_filer.filing_processors.filing_components import create_office


def update_offices(business: Business, offices_structure: Dict) -> Optional[List]:
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
        except:  # noqa:E722 pylint: disable=bare-except; catch all exceptions
            err.append(
                {'error_code': 'FILER_UNABLE_TO_DELETE_OFFICES',
                 'error_message': f"Filer: unable to delete offices for :'{business.identifier}'"}
            )
            return err

        try:
            for office_type, addresses in offices_structure.items():
                office = create_office(business, office_type, addresses)
                business.offices.append(office)
        except KeyError:
            err.append(
                {'error_code': 'FILER_UNABLE_TO_SAVE_OFFICES',
                 'error_message': f"Filer: unable to save new offices for :'{business.identifier}'"}
            )
    return err


def delete_existing_offices(business: Business):
    """Delete the existing offices for a business."""
    if existing_offices := business.offices.all():
        for office in existing_offices:
            business.offices.remove(office)
