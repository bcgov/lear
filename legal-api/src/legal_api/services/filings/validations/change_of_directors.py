# Copyright © 2019 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Validation for the Change of Directors filing."""
from http import HTTPStatus

from flask_babel import _ as babel  # importing camelcase '_' as a name

from business_common.utils.datetime import date, datetime
from business_common.utils.legislation_datetime import LegislationDatetime
from business_common.utils.relationship_director import map_relationship_actions
from business_model.models import Address, Business, Filing, PartyRole
from legal_api.errors import Error
from legal_api.services import flags
from legal_api.services.filings.validations.common_validations import (
    PARTY_NAME_MAX_LENGTH,
    validate_parties_addresses,
    validate_parties_countries,
    validate_relationships,
)

DIRECTOR_ROLE_TYPE = PartyRole.RoleTypes.DIRECTOR.value


def validate(business: Business, cod: dict) -> Error:
    """Validate the Change of Directors filing."""
    if not business or not cod:
        return Error(HTTPStatus.BAD_REQUEST, [{"error": babel("A valid business and filing are required.")}])

    cod_json = cod["filing"]["changeOfDirectors"]
    has_directors = bool(cod_json.get("directors"))
    has_relationships = bool(cod_json.get("relationships"))

    if has_directors and has_relationships:
        return Error(HTTPStatus.BAD_REQUEST, [{
            "error": babel("Only one of directors or relationships can be provided."),
            "path": "/filing/changeOfDirectors"
        }])
    if not has_directors and not has_relationships:
        return Error(HTTPStatus.BAD_REQUEST, [{
            "error": babel("Directors or relationships are required."),
            "path": "/filing/changeOfDirectors"
        }])

    msg = []

    if has_relationships:
        msg += validate_cod_relationships(business, cod)
    else:
        msg += validate_cessation_date(business, cod)
        msg += validate_appointment_date(business, cod)
        msg += validate_directors_name(cod)
        msg += validate_directors_addresses(business, cod)

    msg += validate_effective_date(business, cod)

    if msg:
        return Error(HTTPStatus.BAD_REQUEST, msg)
    return None

def get_cod_date_bounds(business: Business) -> tuple[date, date]:
    """Return (earliest_allowed_date_leg, today_leg) for COD date validation.

    When enable-backdated-cod flag is on, only the founding_date is used as the lower bound.
    When the flag is off, the earliest allowed date is last_cod_date (if present) or founding_date.
    """
    founding_date_leg = LegislationDatetime.as_legislation_timezone(business.founding_date).date()

    if flags.is_on("enable-backdated-cod") or not business.last_cod_date:
        earliest_allowed_date_leg = founding_date_leg
    else:
        earliest_allowed_date_leg = LegislationDatetime.as_legislation_timezone(business.last_cod_date).date()

    today_leg = LegislationDatetime.datenow()
    return earliest_allowed_date_leg, today_leg


def validate_cessation_date(business: Business, cod: dict) -> list:
    """Return error messages if a director's cessation date is invalid.

    Rules:
    - Cessation date must only be provided if "ceased" is present in actions.
    - Cessation date is required when "ceased" is in actions.
    - Cessation date cannot be in the future.
    - Cessation date cannot be before the most recent of:
        - the business founding date, or
        - the most recent Change of Directors filing date.
    """
    msg = []
    filing_type = "changeOfDirectors"
    directors = cod["filing"][filing_type]["directors"]

    earliest_allowed_date_leg, today_leg = get_cod_date_bounds(business)

    for idx, director in enumerate(directors):
        actions = director.get("actions", [])
        cessation_date = director.get("cessationDate")
        path = f"/filing/changeOfDirectors/directors/{idx}/cessationDate"

        is_ceased = "ceased" in actions

        # Cessation date provided but director is NOT ceased
        if cessation_date is not None and not is_ceased:
            msg.append({
                "error": babel("Cessation date must only be provided for a ceased director."),
                "path": path
            })
            continue

        # Director is ceased but cessation date is missing
        if is_ceased and not cessation_date:
            msg.append({
                "error": babel("Cessation date is required for ceased directors."),
                "path": path
            })
            continue

        # Validate cessation date when present and ceased
        if is_ceased and cessation_date:
            cessation_date_leg = date.fromisoformat(cessation_date)

            if cessation_date_leg > today_leg:
                msg.append({
                    "error": babel("Cessation date cannot be in the future."),
                    "path": path
                })

            if cessation_date_leg < earliest_allowed_date_leg:
                msg.append({
                    "error": babel(
                        "Cessation date cannot be before the business founding date "
                        "or the most recent Change of Directors filing."
                    ),
                    "path": path
                })

    return msg


def validate_appointment_date(business: Business, cod: dict) -> list:
    """Return error messages if a director's appointment date is invalid.

    Rules:
    - Appointment date cannot be in the future.
    - Appointment date cannot be before the most recent of:
        - the business founding date, or
        - the most recent Change of Directors filing date.
    """
    msg = []
    filing_type = "changeOfDirectors"
    directors = cod["filing"][filing_type]["directors"]

    earliest_allowed_date_leg, today_leg = get_cod_date_bounds(business)

    for idx, director in enumerate(directors):
        actions = director.get("actions", [])
        if "appointed" not in actions:
            continue

        appointment_date = director.get("appointmentDate")
        if not appointment_date:
            continue

        path = f"/filing/changeOfDirectors/directors/{idx}/appointmentDate"
        appointment_date_leg = date.fromisoformat(appointment_date)

        if appointment_date_leg > today_leg:
            msg.append({
                "error": babel("Appointment date cannot be in the future."),
                "path": path
            })

        if appointment_date_leg < earliest_allowed_date_leg:
            msg.append({
                "error": babel(
                    "Appointment date cannot be before the business founding date "
                    "or the most recent Change of Directors filing."
                ),
                "path": path
            })

    return msg

def validate_directors_addresses(business: Business, cod: dict) -> list:
    """Return an error message if the directors address are invalid.

    Address must contain a valid ISO-2 valid country.
    """
    msg = []

    filing_type = "changeOfDirectors"
    msg.extend(validate_parties_addresses(cod, filing_type, "directors"))

    directors = cod["filing"][filing_type]["directors"]

    # Note: 'postalCode' is intentionally excluded because postal code validation is handled separately
    # in the common validations via validate_parties_addresses.
    mailing_required_fields = [
        "streetAddress",
        "addressCity",
        "addressCountry",
    ]

    for idx, director in enumerate(directors):
        for address_type in Address.JSON_ADDRESS_TYPES:
            address = director.get(address_type)

            if not address:
                if business.legal_type in Business.CORPS:
                    msg.append({
                        "error": f"missing {address_type}",
                        "path": f"/filing/changeOfDirectors/directors/{idx}/{address_type}"
                    })
            elif address_type == Address.JSON_MAILING:
                for field in mailing_required_fields:
                    if not address.get(field):
                        msg.append({
                            "error": babel(f"Mailing address must include {field}."),
                            "path": f"/filing/changeOfDirectors/directors/{idx}/{address_type}/{field}"
                        })

    msg.extend(validate_parties_countries(cod, filing_type, "directors"))

    return msg


def validate_effective_date(business: Business, cod: dict) -> list:
    """Return an error or warning message based on the effective date validation rules.

    Rules: (text from the BA rules document)
        - The effective date of change cannot be in the future.
        - The effective date cannot be a date prior to their Incorporation Date.
        - The effective date of change cannot be a date that is farther in the past
            than a previous COD filing (standalone or AR).
        - The effective date can be the same effective date as another COD filing
            (standalone or AR). If this is the case:
        - COD filing that was filed most recently is the most current director information.
    """
    msg = []

    # get effective datetime string from filing
    try:
        effective_datetime_str = cod["filing"]["header"]["effectiveDate"]
    except KeyError:
        return [{"error": babel("No effective date provided.")}]

    # convert string to datetime
    try:
        effective_datetime_utc = datetime.fromisoformat(effective_datetime_str)
    except ValueError:
        return [{"error": babel("Invalid ISO format for effective date.")}]

    # check if effective datetime is in the future
    if effective_datetime_utc > datetime.utcnow():
        msg.append({"error": babel("Filing cannot have a future effective date.")})

    # convert to legislation timezone and then get date only
    effective_date_leg = LegislationDatetime.as_legislation_timezone(effective_datetime_utc).date()

    # check if effective date is before their incorporation date
    founding_date_leg = LegislationDatetime.as_legislation_timezone(business.founding_date).date()
    if effective_date_leg < founding_date_leg:
        msg.append({"error": babel("Effective date cannot be before businesses founding date.")})

    # check if effective date is before their most recent COD or AR date
    if not flags.is_on("enable-backdated-cod"):
        last_cod_filing = Filing.get_most_recent_legal_filing(business.id,
                                                              Filing.FILINGS["changeOfDirectors"]["name"])
        if last_cod_filing:
            last_cod_date_leg = LegislationDatetime.as_legislation_timezone(last_cod_filing.effective_date).date()
            if effective_date_leg < last_cod_date_leg:
                msg.append({"error": babel("Effective date cannot be before another Change of Directors filing.")})

    return msg

def validate_directors_name(cod: dict) -> list:
    """Return error messages if a director's name fields are invalid.

    Rules:
    - lastName is required (non-empty) for all directors.
    - prevLastName is required when "nameChanged" is in actions.
    - No leading or trailing whitespace.
    - All name fields have a maximum length of 30 characters.
    """
    msg = []
    filing_type = "changeOfDirectors"
    directors = cod["filing"][filing_type]["directors"]

    name_fields = ["firstName", "middleInitial", "lastName",
                   "prevFirstName", "prevMiddleInitial", "prevLastName"]
    name_changed_required_fields = ["prevLastName"]

    for idx, director in enumerate(directors):
        officer = director.get("officer", {})
        actions = director.get("actions", [])
        is_name_changed = "nameChanged" in actions

        for field in name_fields:
            value = officer.get(field)
            path = f"/filing/changeOfDirectors/directors/{idx}/officer/{field}"

            # lastName required (non-empty) is enforced by the schema
            # (business-schemas directors person lastName pattern).

            # Check prev first/last required when nameChanged
            if field in name_changed_required_fields and is_name_changed and (not value or not value.strip()):
                msg.append({
                    "error": babel(f"Director {field} is required when name has changed."),
                    "path": path
                })
                continue

            if value:
                # No leading or trailing whitespace
                if value != value.strip():
                    msg.append({
                        "error": babel(f"Director {field} cannot have leading or trailing whitespace."),
                        "path": path
                    })

                # Max length
                if len(value) > PARTY_NAME_MAX_LENGTH:
                    msg.append({
                        "error": babel(f"Director {field} cannot be longer than {PARTY_NAME_MAX_LENGTH} characters."),
                        "path": path
                    })

    return msg


def validate_cod_relationships(business: Business, cod: dict) -> list:
    """Validate a Change of Directors filing submitted in the relationships shape."""
    msg = []

    min_date, _today = get_cod_date_bounds(business)
    msg.extend(validate_relationships(business,
                                      cod,
                                      "changeOfDirectors",
                                      role_types=[PartyRole.RoleTypes.DIRECTOR],
                                      allow_new=True,
                                      allow_edits=True,
                                      role_types_for_colin_sync=[PartyRole.RoleTypes.DIRECTOR],
                                      min_date=min_date,
                                      min_date_reason=(
                                          "the business founding date "
                                          "or the most recent Change of Directors filing")))
    msg.extend(validate_relationship_actions(cod))
    msg.extend(validate_relationship_cessation_dates(cod))
    msg.extend(validate_parties_countries(cod, "changeOfDirectors", "relationships"))

    return msg


def validate_relationship_actions(cod: dict) -> list:
    """Return error messages if a relationship's explicit actions are inconsistent.

    Rules (relationships with no actions are skipped — change semantics are derived):
    - ADDED implies a new director: no entity identifier is allowed.
    - Edit/removal actions require an entity identifier (an existing director).
    - ADDED cannot be combined with an edit/removal action.
    """
    msg = []
    relationships = cod["filing"]["changeOfDirectors"]["relationships"]

    edit_actions = {"REMOVED", "NAME_CHANGED", "ADDRESS_CHANGED", "CHANGED"}

    for idx, relationship in enumerate(relationships):
        actions = set(relationship.get("actions") or [])
        if not actions:
            continue

        path = f"/filing/changeOfDirectors/relationships/{idx}/actions"
        identifier = relationship.get("entity", {}).get("identifier")
        edits = actions & edit_actions

        if "ADDED" in actions and edits:
            msg.append({
                "error": babel("ADDED cannot be combined with other director actions."),
                "path": path
            })
        elif "ADDED" in actions and identifier:
            msg.append({
                "error": babel("An added director cannot reference an existing director."),
                "path": path
            })
        elif edits and not identifier:
            msg.append({
                "error": babel("An entity identifier is required to change or cease a director."),
                "path": path
            })

    return msg


def validate_relationship_cessation_dates(cod: dict) -> list:
    """Return error messages if a Director role's cessation date is inconsistent.

    Date bounds checked by validate_relationships.
    Missing address and required mailing checked by schema validation
    """
    msg = []
    relationships = cod["filing"]["changeOfDirectors"]["relationships"]

    for idx, relationship in enumerate(relationships):
        actions = map_relationship_actions(relationship)
        is_ceased = "ceased" in actions

        for role_idx, role in enumerate(relationship.get("roles", [])):
            if (role.get("roleType") or "").lower() != DIRECTOR_ROLE_TYPE:
                continue

            cessation_date = role.get("cessationDate")
            cessation_path = f"/filing/changeOfDirectors/relationships/{idx}/roles/{role_idx}/cessationDate"

            if cessation_date is not None and not is_ceased:
                msg.append({
                    "error": babel("Cessation date must only be provided for a ceased director."),
                    "path": cessation_path
                })
            elif is_ceased and not cessation_date:
                msg.append({
                    "error": babel("Cessation date is required for ceased directors."),
                    "path": cessation_path
                })

    return msg
