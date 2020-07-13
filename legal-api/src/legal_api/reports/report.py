# Copyright © 2019 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
# an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.
"""Produces a PDF output based on templates and JSON messages."""
import base64
import copy
import json
import os
from datetime import datetime
from http import HTTPStatus
from pathlib import Path

import pycountry
import requests
from flask import current_app, jsonify

from legal_api.utils.auth import jwt
from legal_api.utils.legislation_datetime import LegislationDatetime


class Report:  # pylint: disable=too-few-public-methods
    # TODO review pylint warning and alter as required
    """Service to create report outputs."""

    incorporation_filing_reports = {
        'certificate': {'filingDescription': 'Certificate of Incorporation', 'fileName': 'certificateOfIncorporation'},
        'noa': {'filingDescription': 'Notice of Article', 'fileName': 'incorporationApplication'}
    }

    def __init__(self, filing):
        """Create the Report instance."""
        self._filing = filing

    def get_pdf(self, report_type=None):
        """Render a pdf for the report."""
        headers = {
            'Authorization': 'Bearer {}'.format(jwt.get_token_auth_header()),
            'Content-Type': 'application/json'
        }

        data = {
            'reportName': self._get_report_filename(report_type),
            'template': "'" + base64.b64encode(bytes(self._get_template(report_type), 'utf-8')).decode() + "'",
            'templateVars': self._get_template_data(report_type)
        }
        response = requests.post(url=current_app.config.get('REPORT_SVC_URL'), headers=headers, data=json.dumps(data))

        if response.status_code != HTTPStatus.OK:
            return jsonify(message=str(response.content)), response.status_code

        return response.content, response.status_code

    def _get_report_filename(self, report_type=None):
        legal_entity_number = self._filing.filing_json['filing']['business']['identifier']
        filing_date = str(self._filing.filing_date)[:19]
        filing_description = self._get_primary_filing()['title']

        if self._filing.filing_type == 'incorporationApplication' and report_type:
            filing_description = Report.incorporation_filing_reports[report_type]['filingDescription']

        return '{}_{}_{}.pdf'.format(legal_entity_number, filing_date, filing_description).replace(' ', '_')

    def _get_primary_filing(self):
        filings = self._filing.FILINGS

        if len(filings) == 1:
            return next(iter(filings))

        return filings['annualReport']

    def _get_template(self, report_type=None):
        try:
            template_path = current_app.config.get('REPORT_TEMPLATE_PATH')
            template_code = Path(f'{template_path}/{self._get_template_filename(report_type)}').read_text()

            # substitute template parts
            template_code = self._substitute_template_parts(template_code)
        except Exception as err:
            current_app.logger.error(err)
            raise err

        return template_code

    @staticmethod
    def _substitute_template_parts(template_code):
        """Substitute template parts in main template.

        Template parts are marked by [[partname.html]] in templates.

        This functionality is restricted by:
        - markup must be exactly [[partname.html]] and have no extra spaces around file name
        - template parts can only be one level deep, ie: this rudimentary framework does not handle nested template
        parts. There is no recursive search and replace.

        :param template_code: string
        :return: template_code string, modified.
        """
        template_path = current_app.config.get('REPORT_TEMPLATE_PATH')
        template_parts = [
            'directors',
            'addresses',
            'certification',
            'footer',
            'logo',
            'macros',
            'style',
            'dissolution',
            'legalNameChange',
            'resolution',
            'certificate-of-incorporation/style',
            'certificate-of-incorporation/seal',
            'certificate-of-incorporation/registrarSignature',
            'certificate-of-incorporation/logo',
            'incorporation-application/addresses',
            'incorporation-application/directors',
            'incorporation-application/style',
            'incorporation-application/incorporator',
            'incorporation-application/completingParty',
            'incorporation-application/incorporationDetails',
            'incorporation-application/shareStructure',
            'incorporation-application/nameRequest'
        ]

        # substitute template parts - marked up by [[filename]]
        for template_part in template_parts:
            template_part_code = Path(f'{template_path}/template-parts/{template_part}.html').read_text()
            template_code = template_code.replace('[[{}.html]]'.format(template_part), template_part_code)

        return template_code

    @staticmethod
    def _get_environment():
        namespace = os.getenv('POD_NAMESPACE', '').lower()

        if namespace.endswith('dev'):
            return 'DEV'

        if namespace.endswith('test'):
            return 'TEST'

        return ''

    def _get_template_filename(self, report_type=None):
        if self._filing.filing_type == 'incorporationApplication' and report_type:
            file_name = Report.incorporation_filing_reports[report_type]['fileName']
            return '{}.html'.format(file_name)
        return '{}.html'.format(self._filing.filing_type)

    def _get_template_data(self, report_type=None):  # pylint: disable=too-many-branches
        filing = copy.deepcopy(self._filing.filing_json['filing'])
        if self._filing.filing_type == 'incorporationApplication':
            self._format_incorporation_data(filing, report_type)
        else:
            # set registered office address from either the COA filing or status quo data in AR filing
            try:
                self._set_addresses(filing)
            except KeyError:
                pass

            # set director list from either the COD filing or status quo data in AR filing
            try:
                self._set_directors(filing)
            except KeyError:
                pass

            self._set_dates(filing)

        self._set_meta_info(filing)
        return filing

    def _set_dates(self, filing):
        filing_datetime = LegislationDatetime.as_legislation_timezone(self._filing.filing_date)
        hour = filing_datetime.strftime('%I').lstrip('0')
        filing['filing_date_time'] = filing_datetime.strftime(f'%B %d, %Y {hour}:%M %p Pacific Time')
        # Get the effective date
        effective_date = filing_datetime if self._filing.effective_date is None \
            else self._filing.effective_date
        # TODO: best: custom date/time filters in the report-api. Otherwise: a subclass for filing-specific data.
        if self._filing.filing_type == 'annualReport':
            agm_date_str = filing.get('annualReport', {}).get('annualGeneralMeetingDate', None)
            if agm_date_str:
                agm_date = datetime.fromisoformat(agm_date_str)
                filing['agm_date'] = agm_date.strftime('%B %d, %Y')
                # for AR, the effective date is the AGM date
                filing['effective_date'] = agm_date.strftime('%B %d, %Y')
            else:
                filing['agm_date'] = 'No AGM'
        elif self._filing.filing_type in ('changeOfAddress', 'changeOfDirectors'):
            # for standalone filings, the effective date comes from the filing data
            filing['effective_date'] = effective_date.strftime('%B %d, %Y')

    def _set_directors(self, filing):
        if filing.get('changeOfDirectors'):
            filing['listOfDirectors'] = filing['changeOfDirectors']
        else:
            filing['listOfDirectors'] = {
                'directors': filing['annualReport']['directors']
            }
        # create helper lists of appointed and ceased directors
        directors = self._format_directors(filing['listOfDirectors']['directors'])
        filing['listOfDirectors']['directorsAppointed'] = [el for el in directors if 'appointed' in el['actions']]
        filing['listOfDirectors']['directorsCeased'] = [el for el in directors if 'ceased' in el['actions']]

    def _format_directors(self, directors):
        for director in directors:
            try:
                self._format_address(director['deliveryAddress'])
                self._format_address(director['mailingAddress'])
            except KeyError:
                pass
        return directors

    def _set_addresses(self, filing):
        if filing.get('changeOfAddress'):
            if filing.get('changeOfAddress').get('offices'):
                filing['registeredOfficeAddress'] = filing['changeOfAddress']['offices']['registeredOffice']
            else:
                filing['registeredOfficeAddress'] = filing['changeOfAddress']
        else:
            if filing.get('annualReport', {}).get('deliveryAddress'):
                filing['registeredOfficeAddress'] = {
                    'deliveryAddress': filing['annualReport']['deliveryAddress'],
                    'mailingAddress': filing['annualReport']['mailingAddress']
                }
            else:
                filing['registeredOfficeAddress'] = {
                    'deliveryAddress': filing['annualReport']['offices']['registeredOffice']['deliveryAddress'],
                    'mailingAddress': filing['annualReport']['offices']['registeredOffice']['mailingAddress']
                }
        delivery_address = filing['registeredOfficeAddress']['deliveryAddress']
        mailing_address = filing['registeredOfficeAddress']['mailingAddress']
        filing['registeredOfficeAddress']['deliveryAddress'] = self._format_address(delivery_address)
        filing['registeredOfficeAddress']['mailingAddress'] = self._format_address(mailing_address)

    @staticmethod
    def _format_address(address):
        country = address['addressCountry']
        country = pycountry.countries.search_fuzzy(country)[0].name
        address['addressCountry'] = country
        return address

    def _format_incorporation_data(self, filing, report_type):
        filing['header']['reportType'] = report_type
        filing['header']['filingId'] = self._filing.id
        filing_datetime = LegislationDatetime.as_legislation_timezone(self._filing.filing_date)
        effective_date_time = LegislationDatetime.as_legislation_timezone(self._filing.effective_date)
        effective_hour = effective_date_time.strftime('%I')
        filing_hour = filing_datetime.strftime('%I')
        filing['header']['effective_date_time'] = \
            effective_date_time.strftime(f'%B %-d, %Y at {effective_hour}:%M %p Pacific Time')
        filing['header']['filing_date_time'] = \
            filing_datetime.strftime(f'%B %-d, %Y at {filing_hour}:%M %p Pacific Time')
        filing['filing_date_time'] = filing_datetime.strftime(f'%B %d, %Y {filing_hour}:%M %p Pacific Time')
        self._format_address(filing['incorporationApplication']['offices']['registeredOffice']['deliveryAddress'])
        self._format_address(filing['incorporationApplication']['offices']['registeredOffice']['mailingAddress'])
        self._format_address(filing['incorporationApplication']['offices']['recordsOffice']['deliveryAddress'])
        self._format_address(filing['incorporationApplication']['offices']['recordsOffice']['mailingAddress'])
        self._format_directors(filing['incorporationApplication']['parties'])
        # create helper list for translations
        filing['listOfTranslations'] = filing['incorporationApplication']['nameTranslations']

    def _set_meta_info(self, filing):
        filing['environment'] = f'{self._get_environment()} FILING #{self._filing.id}'.lstrip()
        # Get source
        filing['source'] = self._filing.source
        # Appears in the Description section of the PDF Document Properties as Title.
        filing['meta_title'] = '{} on {}'.format(
            self._filing.FILINGS[self._filing.filing_type]['title'], filing['filing_date_time'])
        # Appears in the Description section of the PDF Document Properties as Subject.
        legal_name = self._filing.filing_json['filing']['business'].get('legalName', 'NA')
        filing['meta_subject'] = '{} ({})'.format(
            legal_name,
            self._filing.filing_json['filing']['business']['identifier'])
