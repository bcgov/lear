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
from datetime import datetime, timezone
from http import HTTPStatus
from pathlib import Path

import requests
from flask import current_app, jsonify

from legal_api.utils.auth import jwt


class Report:  # pylint: disable=too-few-public-methods
    # TODO review pylint warning and alter as required
    """Service to create report outputs."""

    def __init__(self, filing):
        """Create the Report instance."""
        self._filing = filing

    def get_pdf(self):
        """Render a pdf for the report."""
        headers = {
            'Authorization': 'Bearer {}'.format(jwt.get_token_auth_header()),
            'Content-Type': 'application/json'
        }

        data = {
            'reportName': self._get_report_filename(),
            'template': "'" + base64.b64encode(bytes(self._get_template(), 'utf-8')).decode() + "'",
            'templateVars': self._get_template_data()
        }

        response = requests.post(current_app.config.get('REPORT_SVC_URL'), headers=headers, data=json.dumps(data))

        if response.status_code != HTTPStatus.OK:
            return jsonify(message=str(response.content)), response.status_code

        return response.content, response.status_code

    def _get_report_filename(self):
        legal_entity_number = self._filing.filing_json['filing']['business']['identifier']
        filing_date = str(self._filing.filing_date)[:19]
        filing_description = self._get_filing_description()

        return '{}_{}_{}.pdf'.format(legal_entity_number, filing_date, filing_description).replace(' ', '_')

    def _get_filing_description(self):
        return self._get_primary_filing()['title']

    def _get_primary_filing(self):
        filings = self._filing.FILINGS

        if len(filings) == 1:
            return next(iter(filings))

        return filings['annualReport']

    def _get_template(self):

        template_code = Path('report-templates/{}'.format(self._get_template_filename())).read_text()

        # substitute template parts
        template_code = self._substitute_template_parts(template_code)

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
        template_parts = [
            'directors',
            'addresses',
            'certification',
            'footer',
            'logo',
            'macros',
            'style',
        ]

        # substitute template parts - marked up by [[filename]]
        for template_part in template_parts:
            template_part_code = Path('report-templates/template-parts/{}.html'.format(template_part)).read_text()
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

    def _get_template_filename(self):
        return '{}.html'.format(self._filing.filing_type)

    def _get_template_data(self):
        filing = copy.deepcopy(self._filing.filing_json['filing'])

        # set registered office address from either the COA filing or status quo data in AR filing
        try:
            if filing.get('changeOfAddress'):
                filing['registeredOfficeAddress'] = filing['changeOfAddress']
            else:
                filing['registeredOfficeAddress'] = {
                    'deliveryAddress': filing['annualReport']['deliveryAddress'],
                    'mailingAddress': filing['annualReport']['mailingAddress']
                }

        except KeyError:
            pass

        # set director list from either the COD filing or status quo data in AR filing
        try:
            if filing.get('changeOfDirectors'):
                filing['listOfDirectors'] = filing['changeOfDirectors']
            else:
                filing['listOfDirectors'] = {
                    'directors': filing['annualReport']['directors']
                }

            # create helper lists of appointed and ceased directors
            directors = filing['listOfDirectors']['directors']
            filing['listOfDirectors']['directorsAppointed'] = [el for el in directors if 'appointed' in el['actions']]
            filing['listOfDirectors']['directorsCeased'] = [el for el in directors if 'ceased' in el['actions']]
        except KeyError:
            pass

        filing['environment'] = '{} FILING #{}'.format(self._get_environment(), self._filing.id)

        # Get the string for the filing date and time - do not use a leading zero on the hour (04:30 PM) as it looks
        # too much like the 24 hour 4:30 AM. Also, we can't use "%-I" on Windows.
        filing_datetime = self._filing.filing_date.replace(tzinfo=timezone.utc).astimezone(tz=None)
        hour = filing_datetime.strftime('%I').lstrip('0')
        filing['filing_date_time'] = filing_datetime.strftime('%B %d, %Y {}:%M %p Pacific Time'.format(hour))

        # Get the effective date - TODO 'effective date' doesn't exist yet but will in future; for now use filing date
        effective_date = self._filing.filing_date.replace(tzinfo=timezone.utc).astimezone(tz=None)

        # TODO: best: custom date/time filters in the report-api. Otherwise: a subclass for filing-specific data.
        if self._filing.filing_type == 'annualReport':
            agm_date = datetime.fromisoformat(filing['annualReport']['annualGeneralMeetingDate'])
            filing['agm_date'] = agm_date.strftime('%B %d, %Y')

            # for AR, the effective date is the AGM date
            filing['effective_date'] = filing_datetime.strftime('%B %d, %Y')

        elif self._filing.filing_type in ('changeOfAddress', 'changeOfDirectors'):
            # for standalone filings, the effective date comes from the filing data
            filing['effective_date'] = effective_date.strftime('%B %d, %Y')

        # Appears in the Description section of the PDF Document Properties as Title.
        filing['meta_title'] = '{} on {}'.format(
            self._filing.FILINGS[self._filing.filing_type]['title'], filing['filing_date_time'])

        # Appears in the Description section of the PDF Document Properties as Subject.
        filing['meta_subject'] = '{} ({})'.format(
            self._filing.filing_json['filing']['business']['legalName'],
            self._filing.filing_json['filing']['business']['identifier'])

        return filing
