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
"""Tests to assure the draft rebase service.

Test-Suite to ensure that the draft rebase entity matching, stale-id guard and changes report work as expected.
"""
import time
from datetime import UTC, date, datetime, timedelta

import pytest

from business_model.models import Address, Alias, Filing, Party, PartyRole, Resolution
from legal_api.services.draft_rebase import (
    DraftRebaseService,
    _align_entities_by_row_id,
    _name_translation_entities,
    _party_entities,
    _party_role_scope,
    _party_row_id,
    _resolution_entities,
    _scope_party_entities,
)
from registry_schemas.example_data import ANNUAL_REPORT
from tests.unit.models import factory_business, factory_completed_filing, factory_filing


# ---------------------------------------------------------------------------
# row builders: snapshot rows mirror party_role_revision_json (is_ia_or_after=False);
# draft rows mirror the legacy (officer.id) and person-roles (entity.identifier) payloads
# ---------------------------------------------------------------------------
def snap(pid, first, last, city, role='director'):
    """Return a person snapshot row; the party id is only at the top level, as a string."""
    return {'officer': {'firstName': first, 'lastName': last, 'partyType': 'person'},
            'id': str(pid),
            'role': role,
            'deliveryAddress': {'streetAddress': '1 St', 'addressCity': city}}


def snap_org(pid, name, identifier, city, role='partner'):
    """Return an organization snapshot row; officer.identifier is the org's business identifier."""
    return {'officer': {'organizationName': name, 'partyType': 'organization', 'identifier': identifier},
            'id': str(pid),
            'role': role,
            'deliveryAddress': {'streetAddress': '1 St', 'addressCity': city}}


def party(pid, first, last, city, roles=('director',), actions=None, entity_shape=False):
    """Return a draft row in the legacy officer.id or the person-roles entity.identifier shape."""
    if entity_shape:
        row = {'entity': {'identifier': pid, 'givenName': first, 'familyName': last}}
    else:
        row = {'officer': {'id': pid, 'firstName': first, 'lastName': last}}
    row['roles'] = [{'roleType': role} for role in roles]
    row['deliveryAddress'] = {'streetAddress': '1 St', 'addressCity': city}
    if actions:
        row['actions'] = actions
    return row


def classify(base_rows, current_rows, draft_rows, builder=_party_entities, section_present=True, scope=None):
    """Run the same pipeline as get_changes_report for one section and return its classification."""
    base, current, draft = (builder(rows) for rows in (base_rows, current_rows, draft_rows))
    if scope:
        base, current, draft = (_scope_party_entities(entities, scope) for entities in (base, current, draft))
    base, current, draft = _align_entities_by_row_id(base, current, draft)
    changed = DraftRebaseService._changed_keys(base, current)
    touched = DraftRebaseService._draft_touched_entities(draft, base, section_present)
    conflicts, already = [], []
    for key, (_, current_entity) in changed.items():
        if (draft_entity := touched.get(key)) is None:
            continue
        current_norm = current_entity['norm'] if current_entity else None
        (already if draft_entity['norm'] == current_norm else conflicts).append(key)
    return changed, touched, conflicts, already


# ---------------------------------------------------------------------------
# id-first pairing
# ---------------------------------------------------------------------------
def test_rename_pairs_by_snapshot_top_level_id():
    """Assert a rename between base and current pairs as one entity via the top-level string id."""
    changed, touched, conflicts, already = classify(
        [snap(101, 'Jane', 'Smith', 'Victoria')],
        [snap(101, 'Jane', 'Doe', 'Victoria')],
        [party(101, 'Jane', 'Smith', 'Nanaimo', actions=['EDITED'], entity_shape=True)])

    assert set(changed) == {'DOE, JANE'}
    assert set(touched) == {'DOE, JANE'}
    assert conflicts == ['DOE, JANE']
    assert not already
    base_entity, current_entity = changed['DOE, JANE']
    assert base_entity['row_id'] == current_entity['row_id'] == 101


def test_id_churn_degrades_to_name_matching_without_phantom_change():
    """Assert different ids with the same name pair by name so no change is reported."""
    changed, touched, conflicts, already = classify(
        [snap(101, 'Jane', 'Smith', 'Victoria')],
        [snap(348, 'Jane', 'Smith', 'Victoria')],
        [party(101, 'Jane', 'Smith', 'Nanaimo', actions=['EDITED'])])

    assert not changed
    assert set(touched) == {'SMITH, JANE'}
    assert not conflicts


def test_id_churn_with_real_edit_gives_single_name_keyed_conflict():
    """Assert id churn plus a real intervening edit is one conflict keyed by the bare name."""
    changed, touched, conflicts, already = classify(
        [snap(101, 'Jane', 'Smith', 'Victoria')],
        [snap(348, 'Jane', 'Smith', 'Vancouver')],
        [party(101, 'Jane', 'Smith', 'Nanaimo', actions=['EDITED'])])

    assert conflicts == ['SMITH, JANE']
    assert not already


def test_duplicate_names_are_disambiguated_by_id():
    """Assert same-name parties get ' #<id>' keys so an edit to one is not a conflict on the other."""
    changed, touched, conflicts, already = classify(
        [snap(101, 'Jane', 'Smith', 'Victoria'), snap(102, 'Jane', 'Smith', 'Burnaby')],
        [snap(101, 'Jane', 'Smith', 'Victoria'), snap(102, 'Jane', 'Smith', 'Surrey')],
        [party(101, 'Jane', 'Smith', 'Nanaimo', actions=['EDITED'], entity_shape=True)])

    assert set(changed) == {'SMITH, JANE #102'}
    assert set(touched) == {'SMITH, JANE #101'}
    assert not conflicts
    assert not already


def test_duplicate_names_conflict_when_same_party_edited_on_both_sides():
    """Assert the id-suffixed key still conflicts when the draft edits the party staff changed."""
    changed, touched, conflicts, already = classify(
        [snap(101, 'Jane', 'Smith', 'Victoria'), snap(102, 'Jane', 'Smith', 'Burnaby')],
        [snap(101, 'Jane', 'Smith', 'Victoria'), snap(102, 'Jane', 'Smith', 'Surrey')],
        [party(102, 'Jane', 'Smith', 'Nanaimo', actions=['EDITED'])])

    assert conflicts == ['SMITH, JANE #102']


def test_draft_added_row_stays_separate_bare_name_entity():
    """Assert a uuid-identified draft row keeps the bare name while the existing party is id-suffixed."""
    changed, touched, conflicts, already = classify(
        [snap(101, 'Jane', 'Smith', 'Victoria')],
        [snap(101, 'Jane', 'Smith', 'Surrey')],
        [party(101, 'Jane', 'Smith', 'Victoria', entity_shape=True),
         party('4fa2-uuid', 'Jane', 'Smith', 'Kelowna', actions=['ADDED'], entity_shape=True)])

    assert set(changed) == {'SMITH, JANE #101'}
    assert set(touched) == {'SMITH, JANE'}
    assert touched['SMITH, JANE']['row_id'] is None
    assert not conflicts


def test_alias_renamed_by_both_sides_is_one_conflict_keyed_by_current_name():
    """Assert an alias renamed by staff and the draft pairs by id into one conflict."""
    changed, touched, conflicts, already = classify(
        [{'id': '7', 'name': 'ABC GMBH', 'type': 'TRANSLATION'}],
        [{'id': '7', 'name': 'ABC GMBH CORRECTED', 'type': 'TRANSLATION'}],
        [{'id': 7, 'name': 'ABC LIMITED', 'actions': ['EDITED']}],
        builder=_name_translation_entities)

    assert set(changed) == {'ABC GMBH CORRECTED'}
    assert conflicts == ['ABC GMBH CORRECTED']
    assert changed['ABC GMBH CORRECTED'][1]['row_id'] == 7


def test_alias_without_id_matches_by_name():
    """Assert alias rows without ids (new rows) match by upper-cased name."""
    changed, touched, conflicts, already = classify(
        [{'name': 'abc gmbh'}],
        [{'name': 'ABC GMBH'}],
        [{'name': 'Abc Gmbh', 'actions': ['EDITED']}],
        builder=_name_translation_entities)

    assert not changed
    assert set(touched) == {'ABC GMBH'}


# ---------------------------------------------------------------------------
# draft-touched classification
# ---------------------------------------------------------------------------
def test_untagged_full_replacement_conflicts_with_staff_edit():
    """Assert an untagged draft that omits a base party counts it as REMOVED, conflicting with a staff edit."""
    changed, touched, conflicts, already = classify(
        [snap(101, 'Jane', 'Smith', 'Victoria'), snap(102, 'Bob', 'Lee', 'Burnaby')],
        [snap(101, 'Jane', 'Smith', 'Vancouver'), snap(102, 'Bob', 'Lee', 'Burnaby')],
        [party(102, 'Bob', 'Lee', 'Burnaby')])

    assert set(changed) == set(touched) == {'SMITH, JANE'}
    assert touched['SMITH, JANE']['actions'] == ['REMOVED']
    assert touched['SMITH, JANE']['json'] is None
    assert conflicts == ['SMITH, JANE']


def test_untagged_full_replacement_only_touches_differing_rows():
    """Assert untagged rows identical to the base are not considered touched."""
    changed, touched, conflicts, already = classify(
        [snap(101, 'Jane', 'Smith', 'Victoria'), snap(102, 'Bob', 'Lee', 'Burnaby')],
        [snap(101, 'Jane', 'Smith', 'Victoria'), snap(102, 'Bob', 'Lee', 'Burnaby')],
        [party(101, 'Jane', 'Smith', 'Victoria'), party(102, 'Bob', 'Lee', 'Surrey')])

    assert set(touched) == {'LEE, BOB'}


def test_action_tags_take_precedence_over_diffing():
    """Assert only tagged rows count as touched once any draft row carries actions."""
    changed, touched, conflicts, already = classify(
        [snap(101, 'Jane', 'Smith', 'Victoria'), snap(102, 'Bob', 'Lee', 'Burnaby')],
        [snap(101, 'Jane', 'Smith', 'Victoria'), snap(102, 'Bob', 'Lee', 'Burnaby')],
        [party(101, 'Jane', 'Smith', 'Nanaimo'),
         party(102, 'Bob', 'Lee', 'Surrey', actions=['EDITED'])])

    assert set(touched) == {'LEE, BOB'}


def test_section_absent_from_draft_touches_nothing():
    """Assert a draft without the section reports no touched entities."""
    changed, touched, conflicts, already = classify(
        [snap(101, 'Jane', 'Smith', 'Victoria')],
        [snap(101, 'Jane', 'Smith', 'Vancouver')],
        [],
        section_present=False)

    assert set(changed) == {'SMITH, JANE'}
    assert touched == {}
    assert not conflicts


def test_removed_by_staff_and_edited_by_draft_is_conflict_with_no_paths():
    """Assert a party removed from current but edited by the draft conflicts."""
    changed, touched, conflicts, already = classify(
        [snap(101, 'Jane', 'Smith', 'Victoria')],
        [],
        [party(101, 'Jane', 'Smith', 'Nanaimo', actions=['EDITED'])])

    assert conflicts == ['SMITH, JANE']
    assert DraftRebaseService._entity_diff_paths(*changed['SMITH, JANE']) == []


# ---------------------------------------------------------------------------
# role scoping
# ---------------------------------------------------------------------------
@pytest.mark.parametrize('filing_type,legal_type,expected', [
    ('changeOfDirectors', 'BC', {'director'}),
    ('reviewImportedData', 'BC', {'director'}),
    ('transition', 'BEN', {'director'}),
    ('changeOfRegistration', 'SP', {'partner', 'proprietor'}),
    ('correction', 'SP', {'partner', 'proprietor'}),
    ('correction', 'GP', {'partner', 'proprietor'}),
    ('correction', 'BC', {'director', 'custodian', 'liquidator', 'receiver'}),
    ('correction', 'CP', {'director', 'custodian', 'liquidator', 'receiver'}),
    ('alteration', 'BC', None),
    ('changeOfAddress', 'BC', None),
])
def test_party_role_scope(filing_type, legal_type, expected):
    """Assert the party roles in scope per filing type and legal type."""
    assert _party_role_scope(filing_type, legal_type) == expected


def test_scope_drops_out_of_scope_entities():
    """Assert entities whose roles are all out of scope are dropped."""
    entities = _party_entities([snap(101, 'Jane', 'Smith', 'Victoria'),
                                snap(201, 'Pat', 'Officer', 'Burnaby', role='ceo')])

    scoped = _scope_party_entities(entities, {'director'})

    assert list(scoped) == [101]


def test_scope_reduces_multi_role_entity_norm_to_in_scope_roles():
    """Assert a multi-role entity keeps only in-scope roles in its roles and norm."""
    entities = _party_entities([snap(101, 'Jane', 'Smith', 'Victoria', role='director'),
                                snap(101, 'Jane', 'Smith', 'Victoria', role='ceo')])
    assert entities[101]['roles'] == {'director', 'ceo'}

    scoped = _scope_party_entities(entities, {'director'})

    assert scoped[101]['roles'] == {'director'}
    assert scoped[101]['norm'][1] == ('director',)
    assert entities[101]['norm'][1] == ('ceo', 'director')  # the input entity is not mutated


def test_scope_keeps_entities_without_role_data():
    """Assert legacy rows with no role data survive scoping untouched."""
    entities = _party_entities([{'officer': {'id': 5, 'firstName': 'A', 'lastName': 'B'}}])

    scoped = _scope_party_entities(entities, {'director'})

    assert scoped == entities


def test_officer_only_change_is_invisible_to_directors_draft():
    """Assert an intervening change to an officer-role party yields no change for a directors draft."""
    changed, touched, conflicts, already = classify(
        [snap(101, 'Jane', 'Smith', 'Victoria'), snap(201, 'Pat', 'Officer', 'Burnaby', role='ceo')],
        [snap(101, 'Jane', 'Smith', 'Victoria'), snap(201, 'Pat', 'Officer', 'Surrey', role='ceo')],
        [party(101, 'Jane', 'Smith', 'Victoria')],
        scope=_party_role_scope('changeOfDirectors', 'BC'))

    assert not changed
    assert not touched
    assert not conflicts


def test_multi_role_person_scoped_to_directors_is_already_applied():
    """Assert a multi-role person whose director edit matches current is alreadyApplied, not a conflict."""
    changed, touched, conflicts, already = classify(
        [snap(101, 'Jane', 'Smith', 'Victoria', role='director'),
         snap(101, 'Jane', 'Smith', 'Victoria', role='ceo')],
        [snap(101, 'Jane', 'Smith', 'Vancouver', role='director'),
         snap(101, 'Jane', 'Smith', 'Vancouver', role='ceo')],
        [party(101, 'Jane', 'Smith', 'Vancouver', actions=['EDITED'])],
        scope=_party_role_scope('changeOfDirectors', 'BC'))

    assert set(changed) == {'SMITH, JANE'}
    assert not conflicts
    assert already == ['SMITH, JANE']


# ---------------------------------------------------------------------------
# normalization and row ids
# ---------------------------------------------------------------------------
@pytest.mark.parametrize('snapshot_date,draft_date', [
    ('May 1, 2024', '2024-05-01'),
    ('December 25, 2023', '2023-12-25'),
])
def test_resolution_dates_normalize_to_same_key(snapshot_date, draft_date):
    """Assert snapshot 'Month D, YYYY' dates and draft ISO dates produce the same resolution key."""
    snapshot_keys = set(_resolution_entities([{'id': 1, 'date': snapshot_date, 'type': 'SPECIAL'}]))
    draft_keys = set(_resolution_entities([draft_date]))

    assert snapshot_keys == draft_keys
    assert snapshot_keys == {f'{draft_date} (SPECIAL)'}


def test_resolution_entities_keep_dict_rows_and_tags():
    """Assert dict resolution rows carry their type and action tags into the entity."""
    entities = _resolution_entities([{'date': '2024-05-01', 'type': 'SPECIAL', 'actions': ['ADDED']}])

    assert entities['2024-05-01 (SPECIAL)']['actions'] == ['ADDED']


@pytest.mark.parametrize('row,expected', [
    (snap(55, 'A', 'B', 'X'), 55),
    ({'officer': {'id': 12, 'firstName': 'A', 'lastName': 'B'}}, 12),
    ({'entity': {'identifier': 34, 'givenName': 'C', 'familyName': 'D'}}, 34),
    ({'entity': {'identifier': '4fa2-uuid', 'givenName': 'C', 'familyName': 'D'}}, None),
    ({'officer': {'organizationName': 'ACME', 'identifier': '123456789'}}, None),
    ({'officer': {'organizationName': 'ACME', 'identifier': '123456789'}, 'id': '77'}, 77),
    (snap_org(55, 'ACME HOLDINGS', '123456789', 'Victoria'), 55),
])
def test_party_row_id(row, expected):
    """Assert the party id is read from the right place for each payload shape."""
    assert _party_row_id(row) == expected


def test_org_business_identifier_is_not_mistaken_for_a_party_id():
    """Assert an org party with a numeric business identifier pairs by its top-level id with no change."""
    changed, touched, conflicts, already = classify(
        [snap_org(55, 'ACME HOLDINGS', '123456789', 'Victoria')],
        [snap_org(55, 'ACME HOLDINGS', '123456789', 'Victoria')],
        [])

    assert not changed


@pytest.mark.parametrize('filing_type,draft_key', [
    ('changeOfDirectors', 'relationships'),
    ('changeOfRegistration', 'relationships'),
    ('correction', 'relationships'),
    ('reviewImportedData', 'relationships'),
    ('transition', 'relationships'),
    ('changeOfDirectors', 'directors'),
    ('changeOfRegistration', 'parties'),
    ('correction', 'parties'),
    ('transition', 'parties'),
])
def test_filing_section_map_maps_party_keys_to_parties(filing_type, draft_key):
    """Assert the party draft keys of each filing type map onto the parties snapshot section."""
    assert DraftRebaseService.FILING_SECTION_MAP[filing_type][draft_key] == 'parties'


def test_collect_embedded_ids_reads_officer_id_and_entity_identifier_only():
    """Assert only officer.id and entity.identifier are collected, never an org business identifier or row id."""
    filing_json = {'filing': {'header': {'name': 'changeOfRegistration'},
                              'changeOfRegistration': {'parties': [
                                  {'officer': {'organizationName': 'ACME', 'identifier': '123456789'}, 'id': 999},
                                  {'officer': {'id': 12, 'firstName': 'A', 'lastName': 'B'}},
                                  {'entity': {'identifier': 34, 'givenName': 'C', 'familyName': 'D'}},
                                  {'entity': {'identifier': 'uuid-new', 'givenName': 'E', 'familyName': 'F'}},
                              ]}}}

    party_ids, alias_ids, resolution_ids = DraftRebaseService._collect_embedded_ids(filing_json)

    assert party_ids == {12, 34}
    assert not alias_ids
    assert not resolution_ids


def test_collect_embedded_ids_collects_alias_and_resolution_ids():
    """Assert nameTranslations ids and shareStructure resolutionDates ids are collected."""
    filing_json = {'filing': {'header': {'name': 'alteration'},
                              'alteration': {'nameTranslations': [{'id': 7, 'name': 'A'}, {'name': 'new'}],
                                             'shareStructure': {'resolutionDates': [{'id': 3, 'date': '2024-05-01'},
                                                                                    '2024-06-01']}}}}

    party_ids, alias_ids, resolution_ids = DraftRebaseService._collect_embedded_ids(filing_json)

    assert not party_ids
    assert alias_ids == {7}
    assert resolution_ids == {3}


def test_collect_embedded_ids_ignores_unmapped_filing_types():
    """Assert party rows of a filing type without a section map are not collected."""
    filing_json = {'filing': {'header': {'name': 'annualReport'},
                              'annualReport': {'parties': [{'officer': {'id': 12}}]}}}

    assert DraftRebaseService._collect_embedded_ids(filing_json) == (set(), set(), set())


# ---------------------------------------------------------------------------
# DB-backed helpers
# ---------------------------------------------------------------------------
IDENTIFIER = 'BC1234567'


def _filing_json(filing_type, body, identifier=IDENTIFIER):
    return {'filing': {'header': {'name': filing_type, 'date': '2024-01-01', 'certifiedBy': 'tester'},
                       'business': {'identifier': identifier, 'legalType': 'BC'},
                       filing_type: body}}


def _address(city):
    """Return the draft address that matches what _add_party writes."""
    return {'streetAddress': '1 St', 'addressCity': city, 'addressCountry': 'CA', 'postalCode': 'V8V8V8'}


def _add_party(business, first, last, city='Victoria', role=PartyRole.RoleTypes.DIRECTOR.value, cessation_date=None):
    """Create a versioned person party with a delivery address and one role on the business."""
    address = Address(city=city, street='1 St', postal_code='V8V8V8', country='CA',
                      address_type=Address.DELIVERY)
    person = Party(first_name=first, last_name=last, party_type=Party.PartyTypes.PERSON.value,
                   delivery_address=address)
    person.save()
    party_role = PartyRole(role=role, appointment_date=datetime.now(UTC), cessation_date=cessation_date,
                           party_id=person.id, business_id=business.id)
    party_role.save()
    return person, party_role


def _complete(business):
    """Complete a filing, advancing the business's watermark to a fresh transaction."""
    return factory_completed_filing(business, ANNUAL_REPORT)


def _draft(business, filing_type, body, base_transaction_id):
    """Create a draft filing stamped with the given base transaction."""
    filing = factory_filing(business, _filing_json(filing_type, body))
    filing.base_transaction_id = base_transaction_id
    filing.save()
    return filing


def _draft_director(party_id, first, last, city, actions=None):
    row = {'officer': {'id': party_id, 'firstName': first, 'lastName': last},
           'roles': [{'roleType': 'Director'}],
           'deliveryAddress': _address(city),
           'mailingAddress': _address(city)}
    if actions:
        row['actions'] = actions
    return row


# ---------------------------------------------------------------------------
# find_stale_ids / validate_no_stale_ids
# ---------------------------------------------------------------------------
def test_find_stale_ids_flags_party_ids_not_on_the_business(session):
    """Assert party ids absent from the business are stale and live ids are not."""
    business = factory_business(IDENTIFIER, entity_type='BC')
    live, _ = _add_party(business, 'Jane', 'Smith')
    other_business = factory_business('BC7654321', entity_type='BC')
    other_party, _ = _add_party(other_business, 'Bob', 'Lee')
    filing_json = _filing_json('correction', {'parties': [_draft_director(live.id, 'Jane', 'Smith', 'Victoria'),
                                                          _draft_director(other_party.id, 'Bob', 'Lee', 'Victoria'),
                                                          _draft_director(999999, 'No', 'Body', 'Victoria')]})

    stale = DraftRebaseService.find_stale_ids(business, filing_json)

    assert stale == {'parties': sorted([other_party.id, 999999]), 'nameTranslations': [], 'resolutions': []}


@pytest.mark.parametrize('test_name,filing_type,role,ceased,expect_stale', [
    ('cod-active-director', 'changeOfDirectors', 'director', False, False),
    ('cod-ceased-director', 'changeOfDirectors', 'director', True, True),
    ('cod-non-director', 'changeOfDirectors', 'custodian', False, True),
    ('rid-active-director', 'reviewImportedData', 'director', False, False),
    ('rid-ceased-director', 'reviewImportedData', 'director', True, True),
    ('correction-ceased-director', 'correction', 'director', True, False),
    ('correction-non-director', 'correction', 'custodian', False, False),
])
def test_find_stale_ids_party_liveness_by_filing_type(session, test_name, filing_type, role, ceased, expect_stale):
    """Assert director-only filers check active directors while other filings check existence."""
    business = factory_business(IDENTIFIER, entity_type='BC')
    person, _ = _add_party(business, 'Jane', 'Smith', role=role,
                           cessation_date=datetime.now(UTC) if ceased else None)
    body_key = {'changeOfDirectors': 'directors', 'reviewImportedData': 'relationships'}.get(filing_type, 'parties')
    filing_json = _filing_json(filing_type, {body_key: [_draft_director(person.id, 'Jane', 'Smith', 'Victoria')]})

    stale = DraftRebaseService.find_stale_ids(business, filing_json)

    assert stale['parties'] == ([person.id] if expect_stale else [])


def test_find_stale_ids_checks_alias_and_resolution_rows(session):
    """Assert nameTranslations ids are checked against Alias rows and resolution ids against Resolution rows."""
    business = factory_business(IDENTIFIER, entity_type='BEN')
    alias = Alias(alias='ABC GMBH', type=Alias.AliasType.TRANSLATION.value, business_id=business.id)
    alias.save()
    resolution = Resolution(resolution_date=date(2024, 5, 1), resolution_type='SPECIAL', business_id=business.id)
    resolution.save()
    filing_json = _filing_json('alteration', {
        'nameTranslations': [{'id': alias.id, 'name': 'ABC GMBH'}, {'id': 888888, 'name': 'GONE'}],
        'shareStructure': {'resolutionDates': [{'id': resolution.id, 'date': '2024-05-01'},
                                               {'id': 777777, 'date': '2024-06-01'}]}})

    stale = DraftRebaseService.find_stale_ids(business, filing_json)

    assert stale == {'parties': [], 'nameTranslations': [888888], 'resolutions': [777777]}


def test_find_stale_ids_is_empty_when_draft_has_no_embedded_ids(session):
    """Assert a draft whose new rows carry no ids has nothing stale."""
    business = factory_business(IDENTIFIER, entity_type='BC')
    filing_json = _filing_json('correction', {'parties': [_draft_director('uuid-new', 'Jane', 'Smith', 'Victoria')]})

    assert DraftRebaseService.find_stale_ids(business, filing_json) == \
        {'parties': [], 'nameTranslations': [], 'resolutions': []}


def test_validate_no_stale_ids_ignores_filing_types_outside_the_section_map(session):
    """Assert filing types without rebaseable sections are never rejected."""
    business = factory_business(IDENTIFIER, entity_type='BC')

    assert DraftRebaseService.validate_no_stale_ids(business, _filing_json('annualReport', {})) == []


def test_validate_no_stale_ids_returns_per_path_errors(session):
    """Assert each stale id yields an error dict pointing at its filing section path."""
    business = factory_business(IDENTIFIER, entity_type='BEN')
    filing_json = _filing_json('alteration', {'nameTranslations': [{'id': 888888, 'name': 'GONE'}],
                                              'shareStructure': {'resolutionDates': [{'id': 777777}]}})

    errors = DraftRebaseService.validate_no_stale_ids(business, filing_json)

    assert [error['path'] for error in errors] == ['/filing/alteration/nameTranslations',
                                                   '/filing/alteration/resolutions']
    assert 'id 888888' in errors[0]['error']
    assert 'id 777777' in errors[1]['error']


def test_validate_no_stale_ids_is_empty_when_ids_are_live(session):
    """Assert a draft referencing live rows passes the guard."""
    business = factory_business(IDENTIFIER, entity_type='BC')
    person, _ = _add_party(business, 'Jane', 'Smith')
    filing_json = _filing_json('changeOfDirectors',
                               {'directors': [_draft_director(person.id, 'Jane', 'Smith', 'Victoria')]})

    assert DraftRebaseService.validate_no_stale_ids(business, filing_json) == []


# ---------------------------------------------------------------------------
# fallback_base_transaction_id
# ---------------------------------------------------------------------------
def test_fallback_base_is_latest_completed_transaction_before_draft_date(session):
    """Assert the fallback is the transaction of the last completed filing issued before the draft's save."""
    business = factory_business(IDENTIFIER, entity_type='BC')
    first = _complete(business)
    second = _complete(business)
    time.sleep(0.05)
    draft_date = datetime.now(UTC)
    time.sleep(0.05)
    _complete(business)  # landed after the draft was saved
    draft = factory_filing(business, _filing_json('correction', {}), filing_date=draft_date)

    base = DraftRebaseService.fallback_base_transaction_id(business, draft)

    assert base == second.transaction_id
    assert base > first.transaction_id


def test_fallback_base_ignores_completed_filings_of_other_businesses(session):
    """Assert only the draft's own business is considered."""
    business = factory_business(IDENTIFIER, entity_type='BC')
    other_business = factory_business('BC7654321', entity_type='BC')
    _complete(other_business)
    draft = factory_filing(business, _filing_json('correction', {}),
                           filing_date=datetime.now(UTC) + timedelta(days=1))

    assert DraftRebaseService.fallback_base_transaction_id(business, draft) is None


def test_fallback_base_is_none_when_all_completed_filings_postdate_the_draft(session):
    """Assert no candidate is returned when the draft predates every completed filing."""
    business = factory_business(IDENTIFIER, entity_type='BC')
    _complete(business)
    draft = factory_filing(business, _filing_json('correction', {}),
                           filing_date=datetime.now(UTC) - timedelta(days=1))

    assert DraftRebaseService.fallback_base_transaction_id(business, draft) is None


def test_fallback_base_is_none_without_a_draft_filing_date(session):
    """Assert a draft with no filing_date has no fallback."""
    business = factory_business(IDENTIFIER, entity_type='BC')
    _complete(business)

    assert DraftRebaseService.fallback_base_transaction_id(business, Filing()) is None


# ---------------------------------------------------------------------------
# get_changes_report against real versioned rows
# ---------------------------------------------------------------------------
def test_report_pairs_a_rename_as_one_conflict_with_row_id(session):
    """Assert a staff rename plus a draft edit of the same party is one parties conflict carrying the row id."""
    business = factory_business(IDENTIFIER, entity_type='BC')
    person, _ = _add_party(business, 'Jane', 'Smith')
    base_filing = _complete(business)
    person.last_name = 'Doe'
    person.save()
    _complete(business)
    draft = _draft(business, 'changeOfDirectors',
                   {'directors': [_draft_director(person.id, 'Jane', 'Smith', 'Nanaimo', actions=['EDITED'])]},
                   base_filing.transaction_id)

    report = DraftRebaseService.get_changes_report(business, draft)

    assert report['upToDate'] is False
    assert report['changedSections'] == ['parties']
    assert len(report['conflicts']) == 1
    conflict = report['conflicts'][0]
    assert conflict['section'] == 'parties'
    assert conflict['entityKey'] == 'DOE, JANE'
    assert conflict['rowId'] == person.id
    assert conflict['baseValue']['entity']['familyName'] == 'Smith'
    assert conflict['currentValue']['entity']['familyName'] == 'Doe'
    assert conflict['currentValue']['entity']['identifier'] == person.id
    assert conflict['currentValue']['roles'][0]['roleType'] == 'Director'
    assert conflict['draftValue']['deliveryAddress']['addressCity'] == 'Nanaimo'
    assert not report['alreadyApplied']


def test_report_degrades_id_churn_to_name_matching(session):
    """Assert a party re-created under a new id with identical data is not reported as changed."""
    business = factory_business(IDENTIFIER, entity_type='BC')
    original, original_role = _add_party(business, 'Jane', 'Smith')
    base_filing = _complete(business)
    original_role.cessation_date = datetime.now(UTC)
    original_role.save()
    recreated, _ = _add_party(business, 'Jane', 'Smith')
    _complete(business)
    assert recreated.id != original.id
    draft = _draft(business, 'changeOfDirectors',
                   {'directors': [_draft_director(original.id, 'Jane', 'Smith', 'Nanaimo', actions=['EDITED'])]},
                   base_filing.transaction_id)

    report = DraftRebaseService.get_changes_report(business, draft)

    assert report['upToDate'] is False
    assert 'parties' not in report['changedSections']
    assert report['conflicts'] == []


def test_report_ignores_officer_changes_for_a_directors_draft(session):
    """Assert an intervening change to an officer-role party does not surface in a directors draft."""
    business = factory_business(IDENTIFIER, entity_type='BC')
    director, _ = _add_party(business, 'Jane', 'Smith')
    officer, _ = _add_party(business, 'Pat', 'Officer', role=PartyRole.RoleTypes.CEO.value)
    base_filing = _complete(business)
    officer.delivery_address.city = 'Surrey'
    officer.delivery_address.save()
    _complete(business)
    draft = _draft(business, 'changeOfDirectors',
                   {'directors': [_draft_director(director.id, 'Jane', 'Smith', 'Victoria')]},
                   base_filing.transaction_id)

    report = DraftRebaseService.get_changes_report(business, draft)

    assert report['upToDate'] is False
    assert report['changedSections'] == []
    assert report['conflicts'] == []


def test_report_marks_matching_draft_edit_as_already_applied(session):
    """Assert a draft edit equal to the current value is alreadyApplied rather than a conflict."""
    business = factory_business(IDENTIFIER, entity_type='BC')
    person, _ = _add_party(business, 'Jane', 'Smith')
    base_filing = _complete(business)
    person.delivery_address.city = 'Nanaimo'
    person.delivery_address.save()
    _complete(business)
    draft = _draft(business, 'changeOfDirectors',
                   {'directors': [_draft_director(person.id, 'Jane', 'Smith', 'Nanaimo', actions=['EDITED'])]},
                   base_filing.transaction_id)

    report = DraftRebaseService.get_changes_report(business, draft)

    assert report['conflicts'] == []
    assert report['alreadyApplied'] == [{'section': 'parties', 'entityKey': 'SMITH, JANE'}]


def test_report_is_up_to_date_when_there_are_no_completed_filings(session):
    """Assert a business without completed filings reports upToDate with nothing to diff."""
    business = factory_business(IDENTIFIER, entity_type='BC')
    draft = _draft(business, 'changeOfDirectors', {'directors': []}, None)

    report = DraftRebaseService.get_changes_report(business, draft)

    assert report['upToDate'] is True
    assert report['currentTransactionId'] is None
    assert report['conflicts'] == []
