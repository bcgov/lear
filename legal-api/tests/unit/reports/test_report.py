# Copyright © 2019 Province of British Columbia
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

"""Test-Suite to ensure that the Report class is working as expected."""
import copy
from contextlib import suppress
from pathlib import Path
from unittest.mock import patch

import pytest
from flask import current_app
from registry_schemas.example_data import (
    ANNUAL_REPORT,
    CHANGE_OF_ADDRESS,
    CHANGE_OF_DIRECTORS,
    CHANGE_OF_DIRECTORS_MAILING,
    CHANGE_OF_NAME,
    CORP_CHANGE_OF_ADDRESS,
    CORRECTION_COMBINED_AR,
    FILING_HEADER,
    INCORPORATION_FILING_TEMPLATE,
    SPECIAL_RESOLUTION,
    TRANSITION_FILING_TEMPLATE,
)

from legal_api.reports.report import Report
from tests.unit.models import factory_business, factory_completed_filing  # noqa:E501,I001


def create_report(identifier, entity_type, report_type, template):
    """Create an instance of the Report class."""
    if template.get('filing'):
        filing_json = copy.deepcopy(template)
    else:
        filing_json = copy.deepcopy(FILING_HEADER)
        filing_json['filing'][f'{report_type}'] = copy.deepcopy(template)
    filing_json['filing']['business']['identifier'] = identifier
    filing_json['filing']['business']['legalType'] = entity_type
    filing_json['filing']['header']['name'] = report_type

    business = factory_business(identifier=identifier, entity_type=entity_type)
    if report_type == 'correction':
        original_filing_json = copy.deepcopy(filing_json)
        original_filing_json['filing']['header']['name'] = filing_json['filing']['correction']['correctedFilingType']
        del original_filing_json['filing']['correction']
        original_filing = factory_completed_filing(business, original_filing_json)
        filing_json['filing']['correction']['correctedFilingId'] = original_filing.id
    filing = factory_completed_filing(business, filing_json)

    report = Report(filing)
    report._business = business
    report._report_key = report_type
    if report._report_key == 'correction':
        report._report_key = report._filing.filing_json['filing']['correction']['correctedFilingType']

    return report


def populate_business_info_to_filing(report):
    """Assert _populate_business_info_to_filing works as expected."""
    report._populate_business_info_to_filing(report._filing, report._business)
    filing_json = report._filing.filing_json
    assert filing_json['filing']['business']['formatted_founding_date_time']
    assert filing_json['filing']['business']['formatted_founding_date']


def set_dates(report):
    """Assert _set_dates works as expected."""
    filing_json = report._filing.filing_json
    report._set_dates(filing_json)
    assert filing_json['filing_date_time']
    assert filing_json['effective_date_time']
    assert filing_json['effective_date']
    assert filing_json['recognition_date_time']
    # TODO: figure out why this fails and improve test/code
    # if report._report_key == 'annualReport':
    #     assert filing_json['agm_date']
    # if report_type == 'correction':
    #     assert filing_json['original_filing_date_time']


def substitute_template_parts(report):
    """Assert _substitute_template_parts works as expected."""
    template_path = current_app.config.get('REPORT_TEMPLATE_PATH')
    template_code = Path(f'{template_path}/{report._get_template_filename()}').read_text()
    # substitute template parts
    template_code = report._substitute_template_parts(template_code)
    assert template_code


def set_description(report):
    """Assert _set_description works as expected."""
    filing_json = report._filing.filing_json
    report._set_description(filing_json)
    assert filing_json.get('entityDescription')


def set_registrar_info(report):
    """Assert _set_registrar_info works as expected."""
    filing_json = report._filing.filing_json
    report._set_registrar_info(filing_json)
    assert filing_json.get('registrarInfo')


def set_tax_id(report):
    """Assert _set_tax_id works as expected."""
    filing_json = report._filing.filing_json
    report._set_tax_id(filing_json)
    assert filing_json.get('taxId')


def set_addresses(report):
    """Assert _set_addresses works as expected."""
    filing_json = report._filing.filing_json

    with suppress(KeyError):
        with patch.object(report, '_format_address', return_value=None):
            report._set_addresses(filing_json['filing'])

    assert filing_json['filing'].get('registeredOfficeAddress')
    if report._business.legal_type == 'BEN' and report._report_key == 'changeOfAddress':
        assert filing_json['filing'].get('recordsOfficeAddress')


def set_meta_info(report):
    """Assert _set_meta_info works as expected."""
    filing_json = report._filing.filing_json
    report._set_meta_info(filing_json)
    assert filing_json.get('environment')
    assert filing_json.get('source')
    assert filing_json.get('meta_title')
    assert filing_json.get('meta_subject')


@pytest.mark.parametrize(
    'test_name, identifier, entity_type, report_type, template',
    [
        ('CP AR', 'CP1234567', 'CP', 'annualReport', ANNUAL_REPORT),
        ('CP COA', 'CP1234567', 'CP', 'changeOfAddress', CHANGE_OF_ADDRESS),
        ('CP COD', 'CP1234567', 'CP', 'changeOfDirectors', CHANGE_OF_DIRECTORS),
        ('CP COR combined AR', 'CP1234567', 'CP', 'correction', CORRECTION_COMBINED_AR),
        ('CP CON', 'CP1234567', 'CP', 'changeOfName', CHANGE_OF_NAME),
        ('CP SR', 'CP1234567', 'CP', 'specialResolution', SPECIAL_RESOLUTION),
        ('BEN AR', 'BC1234567', 'BEN', 'annualReport', ANNUAL_REPORT),
        ('BEN COA', 'BC1234567', 'BEN', 'changeOfAddress', CORP_CHANGE_OF_ADDRESS),
        ('BEN COD', 'BC1234567', 'BEN', 'changeOfDirectors', CHANGE_OF_DIRECTORS_MAILING),
        ('BEN INC', 'BC1234567', 'BEN', 'incorporationApplication', INCORPORATION_FILING_TEMPLATE),
        ('BEN TRANS', 'BC1234567', 'BEN', 'transition', TRANSITION_FILING_TEMPLATE),
    ]
)
def test_get_pdf(session, test_name, identifier, entity_type, report_type, template):
    """Assert all filings can be returned as a PDF."""
    # TODO: add checks on set_directors, noa
    # setup
    report = create_report(identifier=identifier, entity_type=entity_type, report_type=report_type, template=template)

    # verify
    populate_business_info_to_filing(report)
    set_dates(report)
    substitute_template_parts(report)
    set_description(report)
    set_registrar_info(report)
    set_meta_info(report)

    if report_type in ['annualReport', 'changeOfAddress']:
        set_addresses(report)

    if report._business.legal_type != 'CP':
        set_tax_id(report)

    filename = report._get_report_filename()
    assert filename
    template = report._get_template()
    assert template
