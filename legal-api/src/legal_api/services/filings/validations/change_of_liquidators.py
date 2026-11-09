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
"""Validation for the Change of Liquidators filing."""
from datetime import date
from http import HTTPStatus

from flask_babel import _

from business_common.utils.legislation_datetime import LegislationDatetime
from business_model.models import Business, PartyRole
from legal_api.errors import Error
from legal_api.services.filings.validations.common_validations import get_date, validate_offices, validate_relationships


def validate(business: Business, filing_json: dict) -> Error | None:
    """Validate the Change of Liquidators filing."""
    filing_type = "changeOfLiquidators"
    filing_data = filing_json["filing"][filing_type]
    filing_sub_type = filing_data.get("type")

    msg = []

    msg.extend(_validate_liquidation_date(business, filing_json, filing_type, filing_sub_type))

    if filing_data.get("relationships"):
        msg.extend(_validate_liquidator_relationships(business, filing_json, filing_type, filing_sub_type))

    if filing_data.get("offices"):
        allowed_offices = []
        required_offices = []
        if filing_sub_type in ["intentToLiquidate", "changeAddressLiquidator"]:
            allowed_offices = ["liquidationRecordsOffice"]
            if filing_sub_type == "intentToLiquidate":
                required_offices = ["liquidationRecordsOffice"]
        elif filing_sub_type == "appointLiquidator" and not business.in_liquidation:
            allowed_offices = ["liquidationRecordsOffice"]
            required_offices = ["liquidationRecordsOffice"]

        msg.extend(validate_offices(filing_json, filing_type, allowed_offices, required_offices, True))

    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)
    return None


def _check_required_liquidator_dates(
    business: Business,
    relationships: list[dict],
    filing_type: str,
    filing_sub_type: str | None,
) -> list:
    """Check required appointment and cessation dates for liquidators."""
    msg = []
    base_path = f"/filing/{filing_type}/relationships"
    for rel_idx, rel in enumerate(relationships):
        roles = rel.get("roles", [])
        for role_idx, role in enumerate(roles):
            role_path = f"{base_path}/{rel_idx}/roles/{role_idx}"
            if filing_sub_type in ["appointLiquidator", "intentToLiquidate"]:
                if not role.get("appointmentDate"):
                    msg.append({
                        "error": _("Appointment date is required for this filing."),
                        "path": f"{role_path}/appointmentDate",
                    })
            elif filing_sub_type == "ceaseLiquidator":
                cessation_str = role.get("cessationDate")
                if not cessation_str:
                    msg.append({
                        "error": _("Cessation date is required for this filing."),
                        "path": f"{role_path}/cessationDate",
                    })
                elif entity_id := rel.get("entity", {}).get("identifier"):
                    msg.extend(_validate_cease_not_before_appointment(business, entity_id, cessation_str, role_path))
    return msg


def _sanitize_relationships_for_validation(
    raw_relationships: list[dict],
    filing_sub_type: str | None,
) -> list[dict]:
    """Sanitize relationship roles by stripping dates irrelevant to the filing sub-type."""
    sanitized_relationships = []
    for rel in raw_relationships:
        sanitized_rel = {**rel}
        if "roles" in rel:
            sanitized_roles = []
            for role in rel["roles"]:
                cleaned_role = {**role}
                if filing_sub_type in ["appointLiquidator", "intentToLiquidate"]:
                    cleaned_role.pop("cessationDate", None)
                elif filing_sub_type == "ceaseLiquidator":
                    cleaned_role.pop("appointmentDate", None)
                elif filing_sub_type == "changeAddressLiquidator":
                    cleaned_role.pop("appointmentDate", None)
                    cleaned_role.pop("cessationDate", None)
                sanitized_roles.append(cleaned_role)
            sanitized_rel["roles"] = sanitized_roles
        sanitized_relationships.append(sanitized_rel)
    return sanitized_relationships


def _validate_liquidator_relationships(
    business: Business,
    filing_json: dict,
    filing_type: str,
    filing_sub_type: str | None,
) -> list:
    """Validate relationships and role dates for changeOfLiquidators."""
    allow_new = filing_sub_type in ["appointLiquidator", "intentToLiquidate"]
    allow_edits = filing_sub_type in ["ceaseLiquidator", "changeAddressLiquidator"]

    raw_relationships = filing_json["filing"][filing_type].get("relationships", [])

    msg = _check_required_liquidator_dates(business, raw_relationships, filing_type, filing_sub_type)

    sanitized_relationships = _sanitize_relationships_for_validation(raw_relationships, filing_sub_type)
    sanitized_filing = {
        **filing_json,
        "filing": {
            **filing_json["filing"],
            filing_type: {
                **filing_json["filing"][filing_type],
                "relationships": sanitized_relationships,
            },
        },
    }

    msg.extend(validate_relationships(
        business,
        sanitized_filing,
        filing_type,
        [PartyRole.RoleTypes.LIQUIDATOR],
        allow_new,
        allow_edits,
    ))

    return msg


def _validate_cease_not_before_appointment(
    business: Business, entity_id: str, cessation_str: str, role_path: str
) -> list:
    """Validate that cessation date is not before existing appointment date."""
    msg = []
    try:
        cess_date = date.fromisoformat(str(cessation_str).strip())
    except (ValueError, TypeError):
        return msg

    try:
        party_id = int(entity_id)
    except (ValueError, TypeError):
        return msg

    roles = PartyRole.get_party_roles_by_party_id(business.id, party_id)
    liquidator_roles = [r for r in roles if r.role == PartyRole.RoleTypes.LIQUIDATOR.value and not r.cessation_date]
    for r in liquidator_roles:
        if r.appointment_date:
            appt_date = LegislationDatetime.as_legislation_timezone(r.appointment_date).date()
            if cess_date < appt_date:
                msg.append({
                    "error": _("Cessation date cannot be before appointment date."),
                    "path": f"{role_path}/cessationDate",
                })
    return msg


def _validate_liquidation_date(
    business: Business,
    filing_json: dict,
    filing_type: str = "changeOfLiquidators",
    filing_sub_type: str | None = None
) -> list:
    """Validate changeOfLiquidatorsDate for standard and correction filings."""
    msg = []
    date_path = f"/filing/{filing_type}/changeOfLiquidatorsDate"
    liquidation_date = get_date(filing_json, date_path)

    # Required for appointLiquidator when the business is not yet in liquidation
    is_correction = filing_type == "correction"
    if (
        filing_sub_type == "appointLiquidator"
        and not business.in_liquidation
        and not is_correction
        and not liquidation_date
    ):
        msg.append({
            "error": _("'changeOfLiquidatorsDate' is required when business is not yet in liquidation."),
            "path": date_path
        })
        return msg

    if liquidation_date:
        today = LegislationDatetime.datenow()
        if liquidation_date > today:
            msg.append({
                "error": _("'changeOfLiquidatorsDate' cannot be in the future."),
                "path": date_path
            })

    return msg