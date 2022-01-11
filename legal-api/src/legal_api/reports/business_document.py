# Copyright © 2021 Province of British Columbia
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
import json
import os
from http import HTTPStatus
from pathlib import Path

import pycountry
import requests
from flask import current_app, jsonify

from legal_api.models import Alias, Business, CorpType
from legal_api.reports.registrar_meta import RegistrarInfo
from legal_api.resources.v2.business import get_addresses, get_directors
from legal_api.utils.auth import jwt
from legal_api.utils.legislation_datetime import LegislationDatetime


class BusinessDocument:  # pylint: disable=too-few-public-methods
    # TODO review pylint warning and alter as required
    """Service to create business summary output."""

    def __init__(self, business, document_key):
        """Create the Report instance."""
        self._business = business
        self._document_key = document_key
        self._report_date_time = LegislationDatetime.now()

    def get_pdf(self):
        """Render the business summary pdf."""
        headers = {
            'Authorization': 'Bearer {}'.format(jwt.get_token_auth_header()),
            'Content-Type': 'application/json'
        }
        data = {
            'reportName': self._get_report_filename(),
            'template': "'" + base64.b64encode(bytes(self._get_template(), 'utf-8')).decode() + "'",
            'templateVars': self._get_template_data()
        }
        response = requests.post(url=current_app.config.get('REPORT_SVC_URL'), headers=headers, data=json.dumps(data))
        if response.status_code != HTTPStatus.OK:
            return jsonify(message=str(response.content)), response.status_code
        return response.content, response.status_code

    def _get_report_filename(self):
        report_date = str(self._report_date_time)[:19]
        return '{}_{}_{}.pdf'.format(self._business.identifier, report_date, 'Summary').replace(' ', '_')

    def _get_template(self):
        try:
            template_path = current_app.config.get('REPORT_TEMPLATE_PATH')
            template_code = Path(f'{template_path}/businessSummary.html').read_text()
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
            'common/addresses',
            'common/businessDetails',
            'common/nameTranslation',
            'common/style',
            'footer',
            'logo',
            'macros',
            'notice-of-articles/directors'
        ]
        # substitute template parts - marked up by [[filename]]
        for template_part in template_parts:
            template_part_code = Path(f'{template_path}/template-parts/{template_part}.html').read_text()
            template_code = template_code.replace('[[{}.html]]'.format(template_part), template_part_code)
        return template_code

    def _get_template_data(self):
        business_json = {}
        business_json['reportType'] = self._document_key
        business_json['business'] = self._business.json()
        business_json['registrarInfo'] = {**RegistrarInfo.get_registrar_info(self._report_date_time)}
        self._set_directors(business_json)
        self._set_addresses(business_json)
        self._set_dates(business_json)
        self._set_description(business_json)
        self._set_meta_info(business_json)
        self._set_name_translations(business_json)
        return business_json

    def _set_description(self, business: dict):
        legal_type = self._business.legal_type
        corp_type = CorpType.find_by_id(legal_type)
        business['entityDescription'] = corp_type.full_desc
        act = {
            Business.LegalTypes.COOP.value: 'Cooperative Association Act'
        }  # This could be the legislation column from CorpType. Yet to discuss.
        business['entityAct'] = act.get(legal_type, 'Business Corporations Act')

    def _set_dates(self, business: dict):
        founding_datetime = LegislationDatetime.as_legislation_timezone(self._business.founding_date)
        business['formatted_founding_date_time'] = LegislationDatetime.format_as_report_string(founding_datetime)
        business['formatted_founding_date'] = founding_datetime.strftime('%B %-d, %Y')
        business['report_date_time'] = LegislationDatetime.format_as_report_string(self._report_date_time)

    def _set_addresses(self, business: dict):
        address_json = get_addresses(self._business.identifier).json
        for office_type in ['registeredOffice', 'recordsOffice']:
            if office_type in address_json:
                for key, value in address_json[office_type].items():
                    address_json[office_type][key] = BusinessDocument._format_address(value)
        business['offices'] = address_json

    def _set_directors(self, business: dict):
        directors_json = get_directors(self._business.identifier).json['directors']
        for director in directors_json:
            director['mailingAddress'] = BusinessDocument._format_address(director['mailingAddress'])
            director['deliveryAddress'] = BusinessDocument._format_address(director['deliveryAddress'])
        business['parties'] = directors_json

    def _set_name_translations(self, business: dict):
        aliases = Alias.find_by_type(self._business.id, 'TRANSLATION')
        business['listOfTranslations'] = [alias.json for alias in aliases]

    @staticmethod
    def _format_address(address):
        country = address['addressCountry']
        country = pycountry.countries.search_fuzzy(country)[0].name
        address['addressCountry'] = country
        address['addressCountryDescription'] = country
        return address

    def _set_meta_info(self, business: dict):
        business['environment'] = f'{self._get_environment()} BUSINESS #{self._business.identifier}'.lstrip()
        business['meta_title'] = 'Business Summary on {}'.format(business['report_date_time'])
        business['meta_subject'] = '{} ({})'.format(self._business.legal_name, self._business.identifier)

    @staticmethod
    def _get_environment():
        namespace = os.getenv('POD_NAMESPACE', '').lower()
        if namespace.endswith('dev'):
            return 'DEV'
        if namespace.endswith('test'):
            return 'TEST'
        return ''
