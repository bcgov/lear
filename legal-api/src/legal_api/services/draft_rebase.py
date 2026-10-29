# Copyright © 2026 Province of British Columbia
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
"""Draft rebase service.

Reports what changed on a business between a draft filing's base transaction and the
current watermark, and classifies conflicts between those changes and the draft's edits.
Parties and name translations are matched by row id where both sides carry one (so a
rename stays one entity), falling back to natural keys because several filer paths
delete and recreate rows and new draft rows have no id yet; the other sections match
by natural keys only.
"""
from datetime import date, datetime
from typing import Final

from business_model.models import Alias, Business, Filing, PartyRole, Resolution, UserRoles, db
from business_model.models.db import Transaction
from legal_api.core.utils import diff_dict, diff_list
from legal_api.services.business_details_version import VersionedBusinessDetailsService

_ADDRESS_MATCH_FIELDS: Final = ("streetAddress", "streetAddressAdditional", "addressCity", "addressRegion",
                                "addressCountry", "postalCode", "deliveryInstructions")

SNAPSHOT_SECTIONS: Final = ("parties", "offices", "shareClasses", "nameTranslations", "resolutions")

# 'identifier' is the party id in the relationships shape; id churn is not a data change
DIFF_IGNORE_KEYS: Final = ["id", "identifier", "actions", "isEditing"]


def _norm_value(value):
    """Strip strings and collapse empties so '' and a missing key compare equal."""
    if isinstance(value, str):
        value = value.strip()
    return value if value not in ("", None) else None


def _norm_number(value):
    """Coerce numbers so 1, 1.0 and '1' compare equal."""
    try:
        return float(value) if value not in ("", None) else None
    except (TypeError, ValueError):
        return _norm_value(value)


def _norm_address(address: dict | None) -> tuple | None:
    if not address:
        return None
    return tuple(_norm_value(address.get(field)) for field in _ADDRESS_MATCH_FIELDS)


def _party_officer(row: dict) -> dict:
    """Return the person/org fields of a party row in any of its payload shapes."""
    return row.get("officer") or row.get("entity") or {}


def _party_name_key(row: dict) -> str | None:
    """Return the natural key of a party row: org name, or 'LAST, FIRST'."""
    officer = _party_officer(row)
    if org_name := _norm_value(officer.get("organizationName") or officer.get("businessName")):
        return str(org_name).upper()
    last_name = _norm_value(officer.get("lastName") or officer.get("familyName"))
    first_name = _norm_value(officer.get("firstName") or officer.get("givenName"))
    if not (last_name or first_name):
        return None
    return ", ".join(str(part).upper() for part in [last_name, first_name] if part)


def _party_roles(row: dict) -> set:
    """Return the row's active role names, normalized across payload shapes."""
    roles = set()
    if role := row.get("role"):
        roles.add(str(role).replace("_", " ").strip().lower())
    for role_json in row.get("roles") or []:
        if role_json.get("cessationDate"):
            continue
        if role_type := role_json.get("roleType"):
            roles.add(str(role_type).replace("_", " ").strip().lower())
    return roles


def _row_actions(row: dict) -> list:
    """Return the UI action tags on a draft row (ADDED/EDITED/REMOVED/...)."""
    actions = row.get("actions")
    if isinstance(actions, list):
        return actions
    if action := row.get("action"):
        return [action]
    return []


def _party_row_id(row: dict):
    """Return the row's party id across payload shapes.

    entity.identifier IS the party id in the person-roles shape; officer.identifier is
    NOT one — it is an org's business identifier. Snapshot rows (is_ia_or_after=False)
    carry the party id only at the top level, as a string.
    """
    if entity := row.get("entity"):
        return _int_or_none(entity.get("identifier"))
    officer = row.get("officer") or {}
    return _int_or_none(officer.get("id")) or _int_or_none(row.get("id"))


def _party_snapshot_to_relationship(row: dict) -> dict:
    """Convert a snapshot party row (officer shape) to the business-ui relationships shape.

    The report's party values go to Nuxt consumers, which only speak relationships.
    """
    if "entity" in row:
        return row
    officer = row.get("officer") or {}
    entity = {"identifier": _int_or_none(row.get("id"))}
    if organization_name := officer.get("organizationName"):
        entity["businessName"] = organization_name
        if business_identifier := officer.get("identifier"):
            entity["businessIdentifier"] = business_identifier
    else:
        entity["givenName"] = officer.get("firstName")
        entity["familyName"] = officer.get("lastName")
        if middle_initial := officer.get("middleInitial"):
            entity["middleInitial"] = middle_initial
    if email := officer.get("email"):
        entity["email"] = email

    relationship = {"entity": entity}
    for address_key in ("deliveryAddress", "mailingAddress"):
        if row.get(address_key):
            relationship[address_key] = row[address_key]
    if role := row.get("role"):
        role_type = " ".join(part.capitalize() for part in str(role).split("_"))
        relationship["roles"] = [{
            "id": role_type,  # diff_list pairs rows by id; same role compares in place
            "roleType": role_type,
            "appointmentDate": row.get("appointmentDate"),
            "cessationDate": row.get("cessationDate"),
        }]
    else:
        relationship["roles"] = row.get("roles") or []
    return relationship


def _party_entities(parties: list | None) -> dict:
    """Group party rows by row id (name key when absent); several roles become one entity."""
    entities = {}
    for row in parties or []:
        row_id = _party_row_id(row)
        name_key = _party_name_key(row)
        if (key := row_id if row_id is not None else name_key) is None:
            continue
        entity = entities.setdefault(key, {"json": row, "row_id": row_id, "name_key": name_key,
                                           "roles": set(), "actions": []})
        entity["roles"] |= _party_roles(row)
        entity["actions"].extend(_row_actions(row))
    for entity in entities.values():
        row = entity["json"]
        # the name is part of the norm (not only the key) so an id-paired rename still diffs
        entity["norm"] = (entity["name_key"],
                          tuple(sorted(entity["roles"])),
                          _norm_address(row.get("deliveryAddress")),
                          _norm_address(row.get("mailingAddress")))
    return entities


def _office_entities(offices: dict | None) -> dict:
    entities = {}
    for office_type, office in (offices or {}).items():
        if not isinstance(office, dict):
            continue
        entities[office_type] = {
            "json": office,
            "norm": (_norm_address(office.get("deliveryAddress")), _norm_address(office.get("mailingAddress"))),
            "actions": _row_actions(office)
        }
    return entities


def _share_class_norm(share_class: dict) -> tuple:
    return (
        _norm_value(share_class.get("name")),
        bool(share_class.get("hasMaximumShares")),
        _norm_number(share_class.get("maxNumberOfShares")),
        bool(share_class.get("hasParValue")),
        _norm_number(share_class.get("parValue")),
        _norm_value(share_class.get("currency")),
        bool(share_class.get("hasRightsOrRestrictions")),
        tuple(sorted((_share_series_norm(series) for series in share_class.get("series") or []), key=repr)),
    )


def _share_series_norm(series: dict) -> tuple:
    return (
        _norm_value(series.get("name")),
        bool(series.get("hasMaximumShares")),
        _norm_number(series.get("maxNumberOfShares")),
        bool(series.get("hasRightsOrRestrictions")),
    )


def _share_class_entities(share_classes: list | None) -> dict:
    entities = {}
    for row in share_classes or []:
        if not (name := _norm_value(row.get("name"))):
            continue
        entities[str(name).upper()] = {"json": row, "norm": _share_class_norm(row), "actions": _row_actions(row)}
    return entities


def _name_translation_entities(name_translations: list | None) -> dict:
    entities = {}
    for row in name_translations or []:
        if not isinstance(row, dict):
            continue
        name = _norm_value(row.get("name"))
        name_key = str(name).upper() if name else None
        row_id = _int_or_none(row.get("id"))
        if (key := row_id if row_id is not None else name_key) is None:
            continue
        entities[key] = {"json": row, "row_id": row_id, "name_key": name_key,
                         "norm": name_key, "actions": _row_actions(row)}
    return entities


def _norm_resolution_date(value) -> str:
    """Normalize a resolution date to ISO; snapshots render 'Month D, YYYY', drafts use ISO."""
    raw = str(value or "").strip()
    try:
        return date.fromisoformat(raw).isoformat()
    except ValueError:
        pass
    try:
        return datetime.strptime(raw, "%B %d, %Y").date().isoformat()
    except ValueError:
        return raw


def _resolution_entities(resolutions: list | None) -> dict:
    entities = {}
    for row in resolutions or []:
        if isinstance(row, dict):
            key = f'{_norm_resolution_date(row.get("date"))} ({row.get("type") or "SPECIAL"})'
            actions = _row_actions(row)
        else:  # resolutionDates payloads can be plain date strings
            key = f"{_norm_resolution_date(row)} (SPECIAL)"
            row = {"date": row}
            actions = []
        entities[key] = {"json": row, "norm": key, "actions": actions}
    return entities


# party roles each filing type manages (normalized as _party_roles produces them);
# snapshot/draft entities outside the scope are noise for that filing's diff
_FILING_PARTY_ROLE_SCOPE: Final = {
    "changeOfDirectors": {"director"},
    "changeOfLiquidators": {"liquidator"},
    "changeOfOfficers": {"ceo", "cfo", "president", "vice president", "chair",
                         "treasurer", "secretary", "assistant secretary", "other"},
    "changeOfReceivers": {"receiver"},
    "changeOfRegistration": {"partner", "proprietor"},
    "reviewImportedData": {"director"},
    "transition": {"director"},
}


def _party_role_scope(filing_type: str, legal_type: str) -> set | None:
    """Return the party roles the filing type manages; None means every role is in scope."""
    if filing_type == "correction":
        if legal_type in (Business.LegalTypes.SOLE_PROP.value, Business.LegalTypes.PARTNERSHIP.value):
            return {"partner", "proprietor"}
        return {"director", "custodian", "liquidator", "receiver"}
    return _FILING_PARTY_ROLE_SCOPE.get(filing_type)


def _scope_party_entities(entities: dict, scope_roles: set) -> dict:
    """Drop entities outside the role scope and re-norm the rest to their in-scope roles.

    Entities with no role data (legacy rows whose role is implied by the section) are kept.
    """
    scoped = {}
    for key, entity in entities.items():
        in_scope_roles = entity["roles"] & scope_roles
        if entity["roles"] and not in_scope_roles:
            continue
        if in_scope_roles != entity["roles"]:
            entity = {**entity, "roles": in_scope_roles,
                      "norm": (entity["norm"][0], tuple(sorted(in_scope_roles)), *entity["norm"][2:])}
        scoped[key] = entity
    return scoped


def _align_entities_by_row_id(base_entities: dict, current_entities: dict, draft_entities: dict) -> tuple:
    """Rekey entities so the same party pairs up across base, current and draft.

    Pairs by id where possible (a rename stays one entity) and by name when ids
    differ (delete+recreate id churn); duplicate same-named rows keep the id in the key.

    Example (entities shown as row_id/name_key; staff renamed id 101, draft added a Smith):
        base    {101: (101, "SMITH, JANE")}              -> {"DOE, JANE": ...}
        current {101: (101, "DOE, JANE")}                -> {"DOE, JANE": ...}
        draft   {101: (101, "SMITH, JANE"),              -> {"DOE, JANE": ...,
                 "SMITH, JANE": (None, "SMITH, JANE")}       "SMITH, JANE": ...}
    """
    # one name per id; the current snapshot's spelling wins
    display_names = {}
    for entities in (draft_entities, base_entities, current_entities):
        for entity in entities.values():
            if entity["row_id"] is not None and entity["name_key"]:
                display_names[entity["row_id"]] = entity["name_key"]

    # ambiguous = one dataset holds two rows with the same name (two real people);
    # the same name under different ids across datasets is id churn, not ambiguity
    ambiguous_names = set()
    for entities in (base_entities, current_entities, draft_entities):
        claimants = {}
        for entity in entities.values():
            name = display_names.get(entity["row_id"]) if entity["row_id"] is not None else entity["name_key"]
            if name:
                claimants[name] = claimants.get(name, 0) + 1
        ambiguous_names |= {name for name, count in claimants.items() if count > 1}

    def canonical_key(entity) -> str | None:
        if (row_id := entity["row_id"]) is None:
            return entity["name_key"]  # new row: bare name
        if (name := display_names.get(row_id)) is None:
            return f"#{row_id}"  # no name anywhere
        # ambiguous names pair by id, everything else pairs by name
        return f"{name} #{row_id}" if name in ambiguous_names else name

    return tuple(
        {key: entity for entity in entities.values() if (key := canonical_key(entity)) is not None}
        for entities in (base_entities, current_entities, draft_entities)
    )


_ID_MATCHED_SECTIONS: Final = ("parties", "nameTranslations")

_SECTION_ENTITY_BUILDERS: Final = {
    "parties": _party_entities,
    "offices": _office_entities,
    "shareClasses": _share_class_entities,
    "nameTranslations": _name_translation_entities,
    "resolutions": _resolution_entities,
}


class DraftRebaseService:
    """Build the changes/conflict report for a draft filing and guard stale submissions."""

    # draft JSON section key -> snapshot section, per filing type; types absent here have
    # no rebaseable sections (bootstrap filings are excluded from this feature entirely)
    FILING_SECTION_MAP: Final = {
        "alteration": {"shareStructure": "shareClasses", "nameTranslations": "nameTranslations"},
        "changeOfAddress": {"offices": "offices"},
        "changeOfDirectors": {"directors": "parties", "relationships": "parties"},
        "changeOfLiquidators": {"relationships": "parties"},
        "changeOfOfficers": {"relationships": "parties"},
        "changeOfReceivers": {"relationships": "parties"},
        "changeOfRegistration": {"parties": "parties", "relationships": "parties", "offices": "offices"},
        "reviewImportedData": {"relationships": "parties", "offices": "offices"},
        # types with two party keys carry them under the legacy key ('directors'/'parties')
        # or 'relationships' (business-ui shape); a draft only ever holds one of the two
        "correction": {"parties": "parties", "relationships": "parties", "offices": "offices",
                       "shareStructure": "shareClasses", "nameTranslations": "nameTranslations"},
        "transition": {"parties": "parties", "relationships": "parties", "offices": "offices",
                       "shareStructure": "shareClasses", "nameTranslations": "nameTranslations"},
    }

    @staticmethod
    def get_changes_report(business: Business, draft_filing: Filing) -> dict:
        """Return the changes and conflicts between the draft's base and the current business data."""
        # base = the state the draft was built on; watermark = the state now
        base_transaction_id = draft_filing.base_transaction_id or \
            DraftRebaseService.fallback_base_transaction_id(business, draft_filing)
        watermark_transaction_id = Filing.get_max_completed_transaction_id(business.id)

        report = {
            "baseTransactionId": base_transaction_id,
            "currentTransactionId": watermark_transaction_id,
            "upToDate": None,
            "interveningFilings": [],
            "businessChanges": {},
            "changedSections": [],
            "draftSections": [],
            "conflicts": [],
            "alreadyApplied": [],
            "staleIds": DraftRebaseService.find_stale_ids(business, draft_filing.filing_json),
        }

        if watermark_transaction_id is None:
            # no completed filing holds a transaction yet; nothing to diff against
            report["upToDate"] = True
            return report
        if base_transaction_id is None:
            # pre-anchor draft with no resolvable fallback
            return report

        # stale = a filing completed after the draft's base
        report["upToDate"] = base_transaction_id >= watermark_transaction_id
        draft_sections = DraftRebaseService._extract_draft_sections(draft_filing)
        report["draftSections"] = sorted(draft_sections.keys())
        if report["upToDate"]:
            return report

        report["interveningFilings"] = DraftRebaseService._intervening_filings_json(business, base_transaction_id)

        # the business at the two points in time, with parties in the relationships shape
        base_snapshot = VersionedBusinessDetailsService.get_company_details_at_transaction(
            base_transaction_id, business.id)
        current_snapshot = VersionedBusinessDetailsService.get_company_details_at_transaction(
            watermark_transaction_id, business.id)
        for snapshot in (base_snapshot, current_snapshot):
            snapshot["parties"] = [_party_snapshot_to_relationship(row)
                                   for row in snapshot.get("parties") or []]

        report["businessChanges"] = DraftRebaseService._business_changes(
            base_snapshot["business"], current_snapshot["business"])

        for section in SNAPSHOT_SECTIONS:
            build_entities = _SECTION_ENTITY_BUILDERS[section]
            base_entities = build_entities(base_snapshot.get(section))
            current_entities = build_entities(current_snapshot.get(section))
            draft_entities = build_entities(draft_sections.get(section))
            # parties: only the roles this filing type manages are in play
            if section == "parties" and \
                    (role_scope := _party_role_scope(draft_filing.filing_type, business.legal_type)):
                base_entities = _scope_party_entities(base_entities, role_scope)
                current_entities = _scope_party_entities(current_entities, role_scope)
                draft_entities = _scope_party_entities(draft_entities, role_scope)
            if section in _ID_MATCHED_SECTIONS:
                base_entities, current_entities, draft_entities = _align_entities_by_row_id(
                    base_entities, current_entities, draft_entities)

            intervening_changed = DraftRebaseService._changed_keys(base_entities, current_entities)
            if intervening_changed:
                report["changedSections"].append(section)

            draft_touched = DraftRebaseService._draft_touched_entities(
                draft_entities, base_entities, section in draft_sections)

            # both sides touched the same entity: same end value = alreadyApplied, else conflict
            for entity_key, (base_entity, current_entity) in intervening_changed.items():
                if (draft_entity := draft_touched.get(entity_key)) is None:
                    continue
                current_norm = current_entity["norm"] if current_entity else None
                if draft_entity["norm"] == current_norm:
                    report["alreadyApplied"].append({"section": section, "entityKey": entity_key})
                else:
                    report["conflicts"].append({
                        "section": section,
                        "entityKey": entity_key,
                        "rowId": next((entity["row_id"] for entity in (current_entity, base_entity, draft_entity)
                                       if entity and entity.get("row_id") is not None), None),  # current row wins
                        "paths": DraftRebaseService._entity_diff_paths(base_entity, current_entity),
                        "baseValue": base_entity["json"] if base_entity else None,
                        "currentValue": current_entity["json"] if current_entity else None,
                        "draftValue": draft_entity["json"],
                    })

        return report

    @staticmethod
    def find_stale_ids(business: Business, filing_json: dict) -> dict:
        """Return draft-embedded row ids that no longer exist on the business.

        Only the ids the filer dereferences in place matter: party ids
        (changeOfDirectors / officer-type / changeOfRegistration / correction),
        nameTranslations ids (aliases) and resolution ids.
        """
        party_ids, alias_ids, resolution_ids = DraftRebaseService._collect_embedded_ids(filing_json)
        stale = {"parties": [], "nameTranslations": [], "resolutions": []}
        if party_ids:
            party_query = db.session.query(PartyRole.party_id).filter(PartyRole.business_id == business.id)
            filing_type = (filing_json or {}).get("filing", {}).get("header", {}).get("name")
            if filing_type in ("changeOfDirectors", "reviewImportedData"):
                # these filers only accept active directors and raise on anything else;
                # the other filers dereference by Party.find_by_id, which works on ceased parties
                party_query = party_query \
                    .filter(PartyRole.role == PartyRole.RoleTypes.DIRECTOR.value) \
                    .filter(PartyRole.cessation_date.is_(None))
            live_ids = {row.party_id for row in party_query.distinct().all()}
            stale["parties"] = sorted(party_ids - live_ids)
        if alias_ids:
            live_ids = {row.id for row in db.session.query(Alias.id)
                        .filter(Alias.business_id == business.id).all()}
            stale["nameTranslations"] = sorted(alias_ids - live_ids)
        if resolution_ids:
            live_ids = {row.id for row in db.session.query(Resolution.id)
                        .filter(Resolution.business_id == business.id).all()}
            stale["resolutions"] = sorted(resolution_ids - live_ids)
        return stale

    @staticmethod
    def validate_no_stale_ids(business: Business, filing_json: dict) -> list:
        """Return per-path errors for stale embedded row ids; run before invoice creation."""
        filing_type = filing_json.get("filing", {}).get("header", {}).get("name")
        if filing_type not in DraftRebaseService.FILING_SECTION_MAP:
            return []
        stale = DraftRebaseService.find_stale_ids(business, filing_json)
        return [
            {"error": f"A {section} record in this filing (id {stale_id}) no longer exists on the business. "
                      "Reload the filing to pick up the current data and try again.",
             "path": f"/filing/{filing_type}/{section}"}
            for section, stale_ids in stale.items()
            for stale_id in stale_ids
        ]

    @staticmethod
    def fallback_base_transaction_id(business: Business, draft_filing: Filing):
        """Approximate the base for pre-anchor drafts: last completed transaction before the draft's save."""
        if not draft_filing.filing_date:
            return None
        row = db.session.query(Filing.transaction_id) \
            .join(Transaction, Transaction.id == Filing.transaction_id) \
            .filter(Filing.business_id == business.id) \
            .filter(Filing._status.in_([Filing.Status.COMPLETED.value,  # pylint: disable=protected-access
                                        Filing.Status.TOMBSTONE.value])) \
            .filter(Transaction.issued_at < draft_filing.filing_date) \
            .order_by(Filing.transaction_id.desc()).first()
        return row.transaction_id if row else None

    @staticmethod
    def _intervening_filings_json(business: Business, base_transaction_id: int) -> list:
        """Return the completed filings that landed after the base, oldest first."""
        # importing here to avoid circular dependencies
        # pylint: disable=import-outside-toplevel
        from legal_api.core.meta import FilingMeta

        return [{
            "filingId": filing.id,
            "name": filing.filing_type,
            "filingSubType": filing.filing_sub_type,
            "displayName": FilingMeta.get_display_name(business.legal_type,
                                                       filing.filing_type,
                                                       filing.filing_sub_type),
            "effectiveDate": filing.effective_date.isoformat() if filing.effective_date else None,
            "filedByStaff": filing.submitter_roles in [UserRoles.staff.value, UserRoles.system.value],
        } for filing in Filing.get_completed_filings_after_transaction(business.id, base_transaction_id)]

    @staticmethod
    def _business_changes(base_business: dict, current_business: dict) -> dict:
        """Compare the business fields that can invalidate a draft."""
        changes = {}
        for field in ("legalName", "legalType", "state"):
            base_value = base_business.get(field)
            current_value = current_business.get(field)
            changes[field] = None if base_value == current_value else \
                {"baseValue": base_value, "currentValue": current_value}
        return changes

    @staticmethod
    def _extract_draft_sections(draft_filing: Filing) -> dict:
        """Map the draft's JSON sections onto snapshot sections."""
        section_map = DraftRebaseService.FILING_SECTION_MAP.get(draft_filing.filing_type, {})
        filing_body = (draft_filing.filing_json or {}).get("filing", {}).get(draft_filing.filing_type, {}) or {}
        sections = {}
        for draft_key, snapshot_section in section_map.items():
            if (value := filing_body.get(draft_key)) is None:
                continue
            if draft_key == "shareStructure":
                if (value := value.get("shareClasses")) is None:
                    continue
            sections[snapshot_section] = value
        return sections

    @staticmethod
    def _changed_keys(base_entities: dict, current_entities: dict) -> dict:
        """Return {entity key: (base entity, current entity)} for entities the intervening filings changed."""
        changed = {}
        for key in base_entities.keys() | current_entities.keys():
            base_entity = base_entities.get(key)
            current_entity = current_entities.get(key)
            if base_entity is None or current_entity is None or base_entity["norm"] != current_entity["norm"]:
                changed[key] = (base_entity, current_entity)
        return changed

    @staticmethod
    def _draft_touched_entities(draft_entities: dict, base_entities: dict, section_present: bool) -> dict:
        """Return the entities the draft edits.

        Prefers the UI action tags embedded in the draft rows; falls back to a normalized
        diff against the base snapshot when a full-replacement section carries no tags.
        """
        if not section_present:
            return {}
        if any(entity["actions"] for entity in draft_entities.values()):
            return {key: entity for key, entity in draft_entities.items() if entity["actions"]}

        touched = {}
        for key, entity in draft_entities.items():
            base_entity = base_entities.get(key)
            if base_entity is None or base_entity["norm"] != entity["norm"]:
                touched[key] = entity
        for key in base_entities.keys() - draft_entities.keys():
            # section presence means full replacement: a missing base entity is a removal
            touched[key] = {"json": None, "norm": None, "actions": ["REMOVED"]}
        return touched

    @staticmethod
    def _entity_diff_paths(base_entity: dict | None, current_entity: dict | None) -> list:
        """Return the changed paths between the base and current versions of one entity."""
        if not (base_entity and current_entity):
            return []
        nodes = diff_dict(current_entity["json"], base_entity["json"],
                          ignore_keys=DIFF_IGNORE_KEYS, diff_list_callback=diff_list) or []
        return [node.json["path"] for node in nodes]

    @staticmethod
    def _collect_embedded_ids(filing_json: dict) -> tuple[set, set, set]:
        """Collect the integer row ids embedded in the filing's rebaseable sections."""
        filing_type = (filing_json or {}).get("filing", {}).get("header", {}).get("name")
        filing_body = (filing_json or {}).get("filing", {}).get(filing_type, {}) or {}

        party_ids, alias_ids, resolution_ids = set(), set(), set()
        section_map = DraftRebaseService.FILING_SECTION_MAP.get(filing_type, {})
        for draft_key, snapshot_section in section_map.items():
            if snapshot_section != "parties" or not (rows := filing_body.get(draft_key)):
                continue
            for row in rows:
                # stricter than _party_row_id: no top-level id fallback, since a
                # false positive here rejects the submission
                if entity := row.get("entity"):
                    row_id = _int_or_none(entity.get("identifier"))
                else:
                    row_id = _int_or_none((row.get("officer") or {}).get("id"))
                if row_id is not None:
                    party_ids.add(row_id)

        for row in filing_body.get("nameTranslations") or []:
            if isinstance(row, dict) and (row_id := _int_or_none(row.get("id"))) is not None:
                alias_ids.add(row_id)

        for row in (filing_body.get("shareStructure") or {}).get("resolutionDates") or []:
            if isinstance(row, dict) and (row_id := _int_or_none(row.get("id"))) is not None:
                resolution_ids.add(row_id)

        return party_ids, alias_ids, resolution_ids


def _int_or_none(value):
    """Return the value as an int, or None for new-row markers such as UUIDs."""
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
