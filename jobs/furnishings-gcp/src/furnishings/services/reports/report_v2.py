# Copyright © 2024 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
# an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.
"""Produces a PDF output for Furnishing based on templates and JSON messages.

NOTE: This is copied from legal-api.
It was decided not to turn this into a common service as it is only used in 2 places."""
import copy
import re
from enum import auto
from http import HTTPStatus
from pathlib import Path
from typing import Final

import google.auth.transport.requests
import google.oauth2.id_token
import requests
from flask import current_app
from jinja2 import Template

from business_model.models import Address, Business
from business_common.utils.base import BaseEnum
from business_common.utils.legislation_datetime import LegislationDatetime
from furnishings.services.mras_service import MrasService
from furnishings.services.reports.registrar_meta import RegistrarInfo


POSTAL_CODE_REGEX: Final = r'^[A-Z]\d[A-Z]\d[A-Z]\d$'
OUTPUT_DATE_FORMAT: Final = '%B %-d, %Y'
SINGLE_URI: Final = '/forms/chromium/convert/html'
HEADER_PATH: Final = '/template-parts/common/v2/header.html'
HEADER_MAIL_PATH: Final = '/template-parts/common/v2/headerMail.html'
FOOTER_PATH: Final = '/template-parts/common/v2/footer.html'
FOOTER_MAIL_PATH: Final = '/template-parts/common/v2/footerMail.html'
HEADER_TITLE_REPLACE: Final = '{{TITLE}}'
REPORT_META_DATA = {
    'marginTop': 1.93,
    'marginLeft': 0.4,
    'marginRight': 0.4,
    'marginBottom': 0.9,
    'printBackground': True
}
REPORT_FILES = {
    'index.html': '',
    'header.html': '',
    'footer.html': ''
}


class ReportV2:
    """Service to create Gotenberg document outputs."""

    def __init__(self, business=None, furnishing=None, document_key=None, variant=None):
        """Create ReportV2 instance."""
        self._furnishing = furnishing
        self._business = business
        self._document_key = document_key
        self._report_data = None
        self._report_date_time = LegislationDatetime.now()
        self._variant = variant

    def get_pdf(self):
        """Render the furnishing document pdf response."""
        headers = {}
        token = ReportV2.get_report_api_token()
        if token:
            headers['Authorization'] = 'Bearer {}'.format(token)
        url = current_app.config.get('REPORT_API_GOTENBERG_URL') + SINGLE_URI
        data = {
            'reportName': self._get_report_filename(),
            'template': self._get_template(),
            'templateVars': self._get_template_data()
        }
        files = self._get_report_files(data)
        response = requests.post(url=url, headers=headers, data=REPORT_META_DATA, files=files, timeout=1800.0)

        if response.status_code != HTTPStatus.OK:
            return None
        return response.content

    def set_report_data(self, business=None, furnishing=None, document_key=None):
        """Set report data."""
        self._business = business or self._business
        self._furnishing = furnishing or self._furnishing
        self._document_key = document_key or self._document_key

    def _get_report_filename(self):
        report_date = str(self._report_date_time)[:19]
        if self._document_key == ReportTypes.DISSOLUTION_COVER:
            return 'cover_{}.pdf'.format(report_date)
        return '{}_{}_{}.pdf'.format(self._business.identifier, report_date,
                                     ReportMeta.reports[self._document_key]['reportName']).replace(' ', '_')

    def _get_template(self):
        try:
            template_path = current_app.config.get('REPORT_TEMPLATE_PATH')
            template_file_name = ReportMeta.reports[self._document_key]['templateName']
            template_code = Path(f'{template_path}/{template_file_name}.html').read_text(encoding='UTF-8')
            # substitute template parts
            template_code = self._substitute_template_parts(template_code)
        except Exception as err:
            current_app.logger.error(err)
            raise err
        return template_code

    @staticmethod
    def _substitute_template_parts(template_code):
        template_path = current_app.config.get('REPORT_TEMPLATE_PATH')
        template_parts = [
            'common/v2/style',
            'common/v2/styleMail',
            'common/certificateRegistrarSignature'
        ]
        # substitute template parts - marked up by [[filename]]
        for template_part in template_parts:
            template_part_code = Path(f'{template_path}/template-parts/{template_part}.html')\
                .read_text(encoding='UTF-8')
            template_code = template_code.replace('[[{}.html]]'.format(template_part), template_part_code)
        return template_code

    def _get_template_data(self):
        # note that the cover template data should be set in service class
        if self._document_key == ReportTypes.DISSOLUTION:
            self._report_data = {}
            self._format_furnishing_data()
            self._set_meta_info()
            self._set_address()
            self._set_registrar_info()
            if self._business.legal_type != Business.LegalTypes.EXTRA_PRO_A.value:
                self._set_ep_registration()
        return self._report_data

    def _format_furnishing_data(self):
        self._report_data['furnishing'] = {
            'businessName': self._furnishing.business_name,
            'businessIdentifier': self._furnishing.business_identifier,
            'furnishingName': self._furnishing.furnishing_name.name
        }

        if self._furnishing.last_ar_date:
            last_ar_date = LegislationDatetime.as_legislation_timezone(self._furnishing.last_ar_date)
        else:
            last_ar_date = LegislationDatetime.as_legislation_timezone(self._business.founding_date)
        self._report_data['furnishing']['lastARDate'] = last_ar_date.strftime(OUTPUT_DATE_FORMAT)

        if self._furnishing.processed_date:
            processed_date = LegislationDatetime.as_legislation_timezone(self._furnishing.processed_date)
        else:
            processed_date = LegislationDatetime.as_legislation_timezone(self._report_date_time)
        self._report_data['furnishing']['processedDate'] = processed_date.strftime(OUTPUT_DATE_FORMAT)

    def _set_meta_info(self):
        if self._variant:
            self._report_data['variant'] = self._variant
        else:
            self._report_data['variant'] = 'default'

        title = ReportMeta.reports[self._document_key]['reportDescription']
        if self._document_key == ReportTypes.DISSOLUTION:
            if 'XPRO' in self._furnishing.furnishing_name.name:
                title = title.replace('{{REPORT_TYPE}}', 'CANCELLATION')
            else:
                title = title.replace('{{REPORT_TYPE}}', 'DISSOLUTION')
        self._report_data['title'] = title.upper()

    def _set_address(self):
        if (furnishing_address := Address.find_by(furnishings_id=self._furnishing.id)):
            furnishing_address = furnishing_address[0]
            self._report_data['furnishing']['mailingAddress'] = self._format_address(furnishing_address.json)

    @staticmethod
    def _format_address(address):
        postal_code = address['postalCode']
        if re.match(POSTAL_CODE_REGEX, postal_code):
            address['postalCode'] = postal_code[:3] + ' ' + postal_code[3:]
        return address

    def _set_registrar_info(self):
        if self._furnishing.processed_date:
            self._report_data['registrarInfo'] = {**RegistrarInfo.get_registrar_info(self._furnishing.processed_date)}
        else:
            self._report_data['registrarInfo'] = {**RegistrarInfo.get_registrar_info(self._report_date_time)}

    def _set_ep_registration(self):
        jurisdictions = MrasService.get_jurisdictions(self._furnishing.business_identifier)
        if jurisdictions:
            ep_registrations = [e['name'] for e in jurisdictions if e['id'] in ['AB', 'SK', 'MB']]
            ep_registrations.sort()
            self._report_data['furnishing']['foreignRegistrations'] = ep_registrations
        else:
            self._report_data['furnishing']['foreignRegistrations'] = []

    def _get_report_files(self, data):
        """Get gotenberg report generation source file data."""
        if self._document_key == ReportTypes.DISSOLUTION_COVER:
            return {'index.html': self._get_html_from_data(data)}
        title = self._report_data['title']
        files = copy.deepcopy(REPORT_FILES)
        files['index.html'] = self._get_html_from_data(data)
        if self._variant == 'default':
            files['header.html'] = self._get_html_from_path(HEADER_PATH, title)
            files['footer.html'] = self._get_html_from_path(FOOTER_PATH)
        else:
            files['header.html'] = self._get_html_from_path(HEADER_MAIL_PATH, title)
            files['footer.html'] = self._get_html_from_path(FOOTER_MAIL_PATH)

        return files

    @staticmethod
    def _get_html_from_data(data):
        """Get html by merging the template with the report data."""
        html_output = None
        try:
            template = Template(data['template'], autoescape=True)
            html_output = template.render(data['templateVars'])
        except Exception as err:
            current_app.logger.error('Error rendering HTML template: ' + str(err))
        return html_output

    @staticmethod
    def _get_html_from_path(path, title=None):
        html_template = None
        try:
            template_path = current_app.config.get('REPORT_TEMPLATE_PATH') + path
            html_template = Path(template_path).read_text(encoding='UTF-8')
            if title:
                html_template = html_template.replace(HEADER_TITLE_REPLACE, title)
        except Exception as err:
            current_app.logger.error(f'Error loading HTML template from path={template_path}: ' + str(err))
        return html_template

    @staticmethod
    def get_report_api_token():
        """Generate access token for Gotenberg Report API."""
        audience = current_app.config.get('REPORT_API_GOTENBERG_AUDIENCE')
        if not audience:
            return None
        auth_req = google.auth.transport.requests.Request()
        token = google.oauth2.id_token.fetch_id_token(auth_req, audience)
        current_app.logger.info('Obtained token for Gotenberg Report API.')
        return token


class ReportTypes(BaseEnum):
    """Render an Enum of the Gotenberg report types."""

    DISSOLUTION = auto()
    DISSOLUTION_COVER = auto()


class ReportMeta:
    """Helper class to maintain the report meta information."""

    reports = {
        ReportTypes.DISSOLUTION: {
            'reportName': 'dissoluion',
            'templateName': 'noticeOfDissolutionCommencement',
            'reportDescription': 'Notice of Commencement of {{REPORT_TYPE}}'
        },
        ReportTypes.DISSOLUTION_COVER: {
            'reportName': 'dissolution cover',
            'templateName': 'dissolutionCover',
            'reportDescription': 'Cover for Dissolution/Cancellation Letter'
        }
    }
