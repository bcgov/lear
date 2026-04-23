# Copyright © 2026 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
"""Unit tests for business_emailer.meta.filing.FilingMeta.

Most FilingMeta staticmethods are pure input/output (operate on dict-shaped
filing/business objects), so they are tested with SimpleNamespace stand-ins
instead of real SQLAlchemy models. The few methods that touch the DB
(`display_name`'s transaction_id branch, `get_corrected_filing_name`) use
patched versions of VersionService / FilingStorage.
"""
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from business_model.models import Business

from business_emailer.meta.filing import FilingMeta


def _filing(**kw):
    """Build a lightweight filing stand-in with sensible defaults."""
    defaults = {
        'filing_type': None,
        'filing_sub_type': None,
        'meta_data': None,
        'transaction_id': None,
        'filing_json': None,
        'json_legal_type': None,
    }
    defaults.update(kw)
    return SimpleNamespace(**defaults)


def _business(legal_type='BC', id=1):  # noqa: A002
    return SimpleNamespace(legal_type=legal_type, id=id)


# --------------------------------------------------------------------------- #
# get_effective_display_year — pure dict access                               #
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize('meta_data,expected', [
    ({'annualReport': {'annualReportFilingYear': 2024}}, '2024'),
    ({'annualReport': {'annualReportFilingYear': '2023'}}, '2023'),
    ({'annualReport': {}}, None),        # KeyError → None
    ({}, None),                          # KeyError → None
    (None, None),                        # TypeError → None
])
def test_get_effective_display_year(meta_data, expected):
    assert FilingMeta.get_effective_display_year(meta_data) == expected


# --------------------------------------------------------------------------- #
# alter_outputs_alteration — adds 'certificateOfNameChange' when name change  #
# --------------------------------------------------------------------------- #

def test_alter_outputs_alteration_adds_cert_on_name_change():
    filing = _filing(filing_type='alteration', meta_data={'alteration': {'toLegalName': 'new'}})
    outputs = {'noticeOfArticles'}
    result = FilingMeta.alter_outputs_alteration(filing, outputs)
    assert 'certificateOfNameChange' in result


def test_alter_outputs_alteration_no_change_when_no_name():
    filing = _filing(filing_type='alteration', meta_data={'alteration': {}})
    outputs = {'noticeOfArticles'}
    result = FilingMeta.alter_outputs_alteration(filing, outputs)
    assert 'certificateOfNameChange' not in result


def test_alter_outputs_alteration_noop_for_other_types():
    filing = _filing(filing_type='changeOfAddress', meta_data={'alteration': {'toLegalName': 'new'}})
    outputs = {'noticeOfArticles'}
    result = FilingMeta.alter_outputs_alteration(filing, outputs)
    assert 'certificateOfNameChange' not in result


# --------------------------------------------------------------------------- #
# alter_outputs_correction                                                    #
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize('correction_meta,expected_additions', [
    ({'toLegalName': 'new'}, {'certificateOfNameCorrection'}),
    ({'uploadNewRules': True}, {'certifiedRules'}),
    ({'uploadNewMemorandum': True}, {'certifiedMemorandum'}),
    ({'hasResolution': True}, {'specialResolution'}),
    ({'toLegalName': 'x', 'uploadNewRules': True, 'uploadNewMemorandum': True, 'hasResolution': True},
     {'certificateOfNameCorrection', 'certifiedRules', 'certifiedMemorandum', 'specialResolution'}),
    ({}, set()),
])
def test_alter_outputs_correction(correction_meta, expected_additions):
    filing = _filing(filing_type='correction', meta_data={'correction': correction_meta})
    outputs = set()
    result = FilingMeta.alter_outputs_correction(filing, _business(), outputs)
    assert expected_additions.issubset(result)


def test_alter_outputs_correction_noop_for_other_types():
    filing = _filing(filing_type='alteration', meta_data={'correction': {'toLegalName': 'new'}})
    outputs = set()
    result = FilingMeta.alter_outputs_correction(filing, _business(), outputs)
    assert 'certificateOfNameCorrection' not in result


# --------------------------------------------------------------------------- #
# alter_outputs_dissolution                                                   #
# --------------------------------------------------------------------------- #

def test_alter_outputs_dissolution_administrative_removes_cert():
    filing = _filing(filing_type='dissolution', filing_sub_type='administrative',
                     json_legal_type=Business.LegalTypes.COMP)
    outputs = {'certificateOfDissolution'}
    result = FilingMeta.alter_outputs_dissolution(filing, outputs)
    assert 'certificateOfDissolution' not in result


def test_alter_outputs_dissolution_coop_voluntary_removes_rules_and_memo():
    filing = _filing(filing_type='dissolution', filing_sub_type='voluntary',
                     json_legal_type=Business.LegalTypes.COOP)
    outputs = {'certificateOfDissolution', 'certifiedRules', 'certifiedMemorandum'}
    result = FilingMeta.alter_outputs_dissolution(filing, outputs)
    assert 'certifiedRules' not in result
    assert 'certifiedMemorandum' not in result
    assert 'certificateOfDissolution' in result  # not removed for voluntary


def test_alter_outputs_dissolution_noop_for_non_dissolution():
    filing = _filing(filing_type='alteration', filing_sub_type='administrative',
                     json_legal_type=Business.LegalTypes.COMP)
    outputs = {'certificateOfDissolution'}
    result = FilingMeta.alter_outputs_dissolution(filing, outputs)
    assert 'certificateOfDissolution' in result


# --------------------------------------------------------------------------- #
# alter_outputs_special_resolution                                            #
# --------------------------------------------------------------------------- #

def test_alter_outputs_special_resolution_with_name_change_and_new_rules():
    filing = _filing(
        filing_type='specialResolution',
        meta_data={'legalFilings': ['changeOfName'], 'alteration': {'uploadNewRules': True}})
    outputs = {'certifiedMemorandum', 'certifiedRules'}
    result = FilingMeta.alter_outputs_special_resolution(filing, outputs)
    assert 'certifiedMemorandum' not in result  # always removed
    assert 'certifiedRules' in result            # kept because uploadNewRules=True
    assert 'certificateOfNameChange' in result   # added because changeOfName


def test_alter_outputs_special_resolution_without_new_rules_removes_rules():
    filing = _filing(filing_type='specialResolution',
                     meta_data={'legalFilings': [], 'alteration': {}})
    outputs = {'certifiedMemorandum', 'certifiedRules'}
    result = FilingMeta.alter_outputs_special_resolution(filing, outputs)
    assert 'certifiedMemorandum' not in result
    assert 'certifiedRules' not in result
    assert 'certificateOfNameChange' not in result


def test_alter_outputs_special_resolution_noop_for_other_types():
    filing = _filing(filing_type='alteration',
                     meta_data={'legalFilings': ['changeOfName']})
    outputs = {'certifiedMemorandum'}
    result = FilingMeta.alter_outputs_special_resolution(filing, outputs)
    assert 'certifiedMemorandum' in result


# --------------------------------------------------------------------------- #
# alter_outputs — orchestrator                                                #
# --------------------------------------------------------------------------- #

def test_alter_outputs_composes_all_four(mocker):
    """alter_outputs should call each of the four alter_outputs_* helpers."""
    m_alt = mocker.patch.object(FilingMeta, 'alter_outputs_alteration', return_value='a')
    m_cor = mocker.patch.object(FilingMeta, 'alter_outputs_correction', return_value='b')
    m_sr = mocker.patch.object(FilingMeta, 'alter_outputs_special_resolution', return_value='c')
    m_dis = mocker.patch.object(FilingMeta, 'alter_outputs_dissolution', return_value='d')

    FilingMeta.alter_outputs(_filing(filing_type='alteration'), _business(), set())

    assert m_alt.called
    assert m_cor.called
    assert m_sr.called
    assert m_dis.called


# --------------------------------------------------------------------------- #
# get_static_documents                                                        #
# --------------------------------------------------------------------------- #

def test_get_static_documents_continuation_in_with_affidavit_and_files():
    filing = _filing(filing_type='continuationIn', meta_data={'continuationIn': {
        'affidavitFileKey': 'AFF123',
        'authorizationFiles': [
            {'fileKey': 'AUTH1', 'fileName': 'auth1.pdf'},
            {'fileKey': 'AUTH2', 'fileName': 'auth2.pdf'},
        ],
    }})
    result = FilingMeta.get_static_documents(filing, 'https://example/docs')
    assert len(result) == 3
    assert result[0] == {'name': 'Unlimited Liability Corporation Information',
                         'url': 'https://example/docs/AFF123'}
    assert result[1] == {'name': 'auth1.pdf', 'url': 'https://example/docs/AUTH1'}
    assert result[2] == {'name': 'auth2.pdf', 'url': 'https://example/docs/AUTH2'}


def test_get_static_documents_continuation_in_empty_meta():
    filing = _filing(filing_type='continuationIn', meta_data={'continuationIn': {}})
    assert FilingMeta.get_static_documents(filing, 'url') == []


def test_get_static_documents_noop_for_other_types():
    filing = _filing(filing_type='incorporationApplication',
                     meta_data={'continuationIn': {'affidavitFileKey': 'x'}})
    assert FilingMeta.get_static_documents(filing, 'url') == []


# --------------------------------------------------------------------------- #
# get_display_name                                                            #
# --------------------------------------------------------------------------- #

def test_get_display_name_simple_string():
    # "annualReport" has string displayName "Annual Report"
    assert FilingMeta.get_display_name('BC', 'annualReport') == 'Annual Report'


def test_get_display_name_dict_by_legal_type():
    # "incorporationApplication" has dict displayName keyed by legal_type
    assert FilingMeta.get_display_name('BC', 'incorporationApplication') == \
        'BC Limited Company Incorporation Application'
    assert FilingMeta.get_display_name('CP', 'incorporationApplication') == \
        'Incorporation Application'


def test_get_display_name_with_sub_type():
    # "dissolution" with "voluntary" sub-type has a dict displayName
    result = FilingMeta.get_display_name('BC', 'dissolution', 'voluntary')
    assert result == 'Voluntary Dissolution'
    # SP/GP map to "Statement of Dissolution"
    assert FilingMeta.get_display_name('SP', 'dissolution', 'voluntary') == \
        'Statement of Dissolution'


# --------------------------------------------------------------------------- #
# get_all_outputs                                                             #
# --------------------------------------------------------------------------- #

def test_get_all_outputs_matching_business_type():
    # "agmExtension" has additional outputs for BC
    result = FilingMeta.get_all_outputs('BC', 'agmExtension')
    assert result == ['letterOfAgmExtension']


def test_get_all_outputs_no_match_returns_empty():
    # "agmExtension" doesn't include SP in its types list
    result = FilingMeta.get_all_outputs('SP', 'agmExtension')
    assert result == []


def test_get_all_outputs_dissolution_coop_has_affidavit():
    # "dissolution" has additional outputs for CP including affidavit
    result = FilingMeta.get_all_outputs('CP', 'dissolution')
    assert 'certificateOfDissolution' in result
    assert 'affidavit' in result


# --------------------------------------------------------------------------- #
# display_name — most branches are pure (no transaction_id, no correction)   #
# --------------------------------------------------------------------------- #

def test_display_name_returns_colin_display_name_when_present():
    filing = _filing(filing_type='annualReport',
                     meta_data={'colinDisplayName': 'COLIN Imported Name'})
    assert FilingMeta.display_name(_business(), filing) == 'COLIN Imported Name'


def test_display_name_fallback_for_unknown_filing_type():
    """Unknown filing_type + no sub_type → capitalized word split fallback."""
    filing = _filing(filing_type='notAKnownFilingType', meta_data={})
    # "notAKnownFilingType" → "Not A Known Filing Type"
    assert FilingMeta.display_name(_business(), filing) == 'Not A Known Filing Type'


def test_display_name_annual_report_with_year():
    filing = _filing(filing_type='annualReport',
                     meta_data={'annualReport': {'annualReportFilingYear': 2024}})
    result = FilingMeta.display_name(_business(legal_type='BC'), filing)
    assert result == 'Annual Report (2024)'


def test_display_name_annual_report_without_year():
    filing = _filing(filing_type='annualReport', meta_data={})
    assert FilingMeta.display_name(_business(legal_type='BC'), filing) == 'Annual Report'


def test_display_name_dissolution_administrative():
    filing = _filing(filing_type='dissolution', filing_sub_type='administrative',
                     meta_data={'dissolution': {'dissolutionType': 'administrative'}})
    result = FilingMeta.display_name(_business(legal_type='BC'), filing)
    assert result == 'Administrative Dissolution'


def test_display_name_dissolution_voluntary_returns_none():
    """Voluntary dissolution doesn't match the 'administrative' branch, and the
    top-level FILINGS['dissolution'] entry has no `displayName`, so the function
    leaves `name` as None. Captures the current behaviour — consumers rely on
    get_display_name() (which does consult the sub_type dict) for voluntary."""
    filing = _filing(filing_type='dissolution', filing_sub_type='voluntary',
                     meta_data={'dissolution': {'dissolutionType': 'voluntary'}})
    result = FilingMeta.display_name(_business(legal_type='BC'), filing)
    assert result is None


def test_display_name_admin_freeze_unfreeze():
    filing = _filing(filing_type='adminFreeze',
                     meta_data={'adminFreeze': {'freeze': False}})
    assert FilingMeta.display_name(_business(), filing) == 'Admin Unfreeze'


def test_display_name_admin_freeze_frozen():
    filing = _filing(filing_type='adminFreeze',
                     meta_data={'adminFreeze': {'freeze': True}})
    assert FilingMeta.display_name(_business(), filing) == 'Admin Freeze'


def test_display_name_uses_versioned_business_when_transaction_id_present(mocker):
    """transaction_id → VersionService.get_business_revision_obj is consulted."""
    revision = SimpleNamespace(legal_type='CP', id=99)
    mocker.patch(
        'business_emailer.meta.filing.VersionService.get_business_revision_obj',
        return_value=revision)
    filing = _filing(filing_type='incorporationApplication', transaction_id=123)
    # legal_type on the *revision* is CP → "Incorporation Application" (CP variant)
    result = FilingMeta.display_name(_business(legal_type='BC'), filing)
    assert result == 'Incorporation Application'


# --------------------------------------------------------------------------- #
# get_corrected_filing_name — mocks FilingStorage.find_by_id                  #
# --------------------------------------------------------------------------- #

def test_get_corrected_filing_name_annual_report(mocker):
    """Correction of an annualReport → 'Correction - Annual Report (year)'."""
    corrected = _filing(
        filing_type='annualReport',
        meta_data={'annualReport': {'annualReportFilingYear': 2024}})
    mocker.patch(
        'business_emailer.meta.filing.FilingStorage.find_by_id', return_value=corrected)
    correction_filing = _filing(
        filing_type='correction',
        filing_json={'filing': {'correction': {
            'correctedFilingType': 'annualReport',
            'correctedFilingId': 42,
        }}})
    result = FilingMeta.get_corrected_filing_name(
        correction_filing, _business(legal_type='BC'), 'original')
    assert result == 'Correction - Annual Report (2024)'


def test_get_corrected_filing_name_unrelated_type_returns_original_name():
    """Non-handled corrected_filing_type just returns the input name."""
    correction_filing = _filing(
        filing_type='correction',
        filing_json={'filing': {'correction': {
            'correctedFilingType': 'alteration',
            'correctedFilingId': 42,
        }}})
    result = FilingMeta.get_corrected_filing_name(
        correction_filing, _business(legal_type='BC'), 'Alteration')
    assert result == 'Alteration'


def test_get_corrected_filing_name_recurses_through_chained_corrections(mocker):
    """correctedFilingType='correction' → recurse through the chain."""
    annual_report = _filing(
        filing_type='annualReport',
        meta_data={'annualReport': {'annualReportFilingYear': 2022}})
    middle_correction = _filing(
        filing_type='correction',
        filing_json={'filing': {'correction': {
            'correctedFilingType': 'annualReport',
            'correctedFilingId': 10,
        }}})

    def fake_find(fid):
        return {11: middle_correction, 10: annual_report}[fid]

    mocker.patch(
        'business_emailer.meta.filing.FilingStorage.find_by_id', side_effect=fake_find)
    outer = _filing(
        filing_type='correction',
        filing_json={'filing': {'correction': {
            'correctedFilingType': 'correction',
            'correctedFilingId': 11,
        }}})
    result = FilingMeta.get_corrected_filing_name(
        outer, _business(legal_type='BC'), 'original')
    assert result == 'Correction - Annual Report (2022)'


# --------------------------------------------------------------------------- #
# display_name correction branch (exercises get_corrected_filing_name)        #
# --------------------------------------------------------------------------- #

def test_display_name_correction_calls_get_corrected_filing_name(mocker):
    corrected = _filing(
        filing_type='annualReport',
        meta_data={'annualReport': {'annualReportFilingYear': 2024}})
    mocker.patch(
        'business_emailer.meta.filing.FilingStorage.find_by_id', return_value=corrected)
    correction = _filing(
        filing_type='correction',
        meta_data={},
        filing_json={'filing': {'correction': {
            'correctedFilingType': 'annualReport',
            'correctedFilingId': 42,
        }}})
    result = FilingMeta.display_name(_business(legal_type='BC'), correction)
    assert 'Correction' in result
