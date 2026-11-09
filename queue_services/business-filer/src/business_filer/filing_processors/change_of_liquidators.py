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
"""File processing rules and actions for change of liquidators filings."""
import copy
from datetime import UTC, datetime

from business_model.models import BatchProcessing, Business, Filing, PartyRole
from business_model.utils.legislation_datetime import LegislationDatetime

from business_filer.common.services import InvoluntaryDissolutionService
from business_filer.filing_meta import FilingMeta
from business_filer.filing_processors.filing_components.filings import create_court_order
from business_filer.filing_processors.filing_components.offices import update_or_create_offices
from business_filer.filing_processors.filing_components.relationships import (
    cease_relationships,
    create_relationships,
    update_relationship_addresses,
)
from business_filer.services.utils import get_date


def _init_liquidation(business: Business, filing_meta: FilingMeta, filing_json: dict):
    """Put the business into liquidation."""
    if not business.in_liquidation:
        business.in_liquidation = True

        col_date = get_date(filing_json, "/filing/changeOfLiquidators/changeOfLiquidatorsDate")
        if col_date:
            date_str = col_date.isoformat()
        else:
            effective_dt = filing_meta.application_date or datetime.now(UTC)
            date_str = LegislationDatetime.format_as_legislation_date(effective_dt)

        business.in_liquidation_date = LegislationDatetime.as_utc_timezone_from_legislation_date_str(date_str)

        # withdraw any existing involuntary dissolution processing if it exists
        batch_details = InvoluntaryDissolutionService.get_in_dissolution_batch_processing(business.id)
        if batch_details:
            batch_processing, _ = batch_details
            batch_processing.status = BatchProcessing.BatchProcessingStatus.WITHDRAWN.value
            batch_processing.notes = "Moved into liquidation"
            batch_processing.last_modified = datetime.now(UTC)


def _update_last_lr_year(business: Business):
    """Update the business last liquidation report year."""
    if business.last_lr_year:
        business.last_lr_year += 1
    else:
        in_liquidation_date = LegislationDatetime.as_legislation_timezone(business.in_liquidation_date).date()
        business.last_lr_year = in_liquidation_date.year + 1


def _get_last_liquidation_report_date(business_id: int) -> str | None:
    """Retrieve the effective date string of the latest prior liquidationReport filing."""
    prior_lr = Filing.get_most_recent_filing(
        business_id=business_id,
        filing_type="changeOfLiquidators",
        filing_sub_type="liquidationReport",
    )
    if prior_lr and prior_lr.effective_date:
        return LegislationDatetime.as_legislation_timezone(prior_lr.effective_date).date().isoformat()
    return None


def _process_appointment_or_intent(
    business: Business,
    filing_rec: Filing,
    filing_meta: FilingMeta,
    relationships: list,
    offices: dict,
    filing_json: dict,
    was_in_liquidation: bool,
):
    """Process intentToLiquidate or appointLiquidator sub-types."""
    create_relationships(relationships, business, filing_rec)
    update_or_create_offices(business, offices)
    _init_liquidation(business, filing_meta, filing_json)

    col_meta = {}
    if not was_in_liquidation and business.in_liquidation and business.in_liquidation_date:
        col_meta["commencementDate"] = LegislationDatetime.as_legislation_timezone(
            business.in_liquidation_date
        ).date().isoformat()
    if last_lr_date := _get_last_liquidation_report_date(business.id):
        col_meta["lastLiquidationReportDate"] = last_lr_date
    if col_meta:
        filing_meta.change_of_liquidators = col_meta


def _process_cease(business: Business, filing_meta: FilingMeta, relationships: list):
    """Process ceaseLiquidator sub-type."""
    cease_relationships(relationships, business, [PartyRole.RoleTypes.LIQUIDATOR.value], filing_meta.application_date)
    if last_lr_date := _get_last_liquidation_report_date(business.id):
        filing_meta.change_of_liquidators = {"lastLiquidationReportDate": last_lr_date}


def _process_change_address(business: Business, filing_meta: FilingMeta, relationships: list, offices: dict):
    """Process changeAddressLiquidator sub-type."""
    update_relationship_addresses(relationships, business)
    update_or_create_offices(business, offices)
    if last_lr_date := _get_last_liquidation_report_date(business.id):
        filing_meta.change_of_liquidators = {"lastLiquidationReportDate": last_lr_date}


def _process_liquidation_report(business: Business, filing_meta: FilingMeta):
    """Process liquidationReport sub-type."""
    lr_date = business.next_lr_min_date
    _update_last_lr_year(business)
    if lr_date:
        filing_meta.change_of_liquidators = {
            "liquidationReportDate": lr_date.isoformat(),
            "liquidationReportYear": lr_date.year,
        }


def process(business: Business, filing_rec: Filing, filing_meta: FilingMeta):
    """Render the changeOfLiquidators onto the business model objects."""
    filing_json = copy.deepcopy(filing_rec.filing_json)
    relationships = filing_json["filing"]["changeOfLiquidators"].get("relationships", [])
    offices = filing_json["filing"]["changeOfLiquidators"].get("offices", {})

    was_in_liquidation = bool(business.in_liquidation)
    sub_type = filing_rec.filing_sub_type

    if sub_type in ["intentToLiquidate", "appointLiquidator"]:
        _process_appointment_or_intent(
            business, filing_rec, filing_meta, relationships, offices, filing_json, was_in_liquidation
        )
    elif sub_type == "ceaseLiquidator":
        _process_cease(business, filing_meta, relationships)
    elif sub_type == "changeAddressLiquidator":
        _process_change_address(business, filing_meta, relationships, offices)
    elif sub_type == "liquidationReport":
        _process_liquidation_report(business, filing_meta)

    # update court order, if any is present
    if court_order := filing_json["filing"]["changeOfLiquidators"].get("courtOrder"):
        create_court_order(filing_rec, court_order, filing_meta)
