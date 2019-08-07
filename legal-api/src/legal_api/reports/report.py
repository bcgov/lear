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

import base64
import json
import requests

from abc import ABC, abstractmethod
from flask import current_app, jsonify
from http import HTTPStatus
from pathlib import Path

from legal_api.utils.auth import jwt


class Report(ABC):
    def __init__(self, filing):
        self.filing = filing

    def get_pdf(self):
        headers = {
            'Authorization': 'Bearer {}'.format(jwt.get_token_auth_header()),
            'Content-Type': 'application/json'
        }

        data = {
            'report_name': self._get_report_filename(),
            'template': '\'' + base64.b64encode(bytes(self._get_template(), 'utf-8')).decode() + '\'',
            'template_vars': self._get_template_data()
        }

        response = requests.post(current_app.config.get('REPORT_SVC_URL'), headers=headers, data=json.dumps(data))

        if response.status_code != HTTPStatus.OK:
            return jsonify(message=str(response.content)), response.status_code

        return response.content, 200

    def _get_report_filename(self):
        legal_entity_number = self.filing.filing_json['filing']['business']['identifier']
        filing_date = str(self.filing.filing_date)[:19]
        filing_description = self._get_filing_description()

        return '{}_{}_{}.pdf'.format(legal_entity_number, filing_date, filing_description).replace(' ', '_')

    def _get_filing_description(self):
        return self._get_primary_filing()['title']

    def _get_primary_filing(self):
        filings = self.filing.FILINGS

        if len(filings) == 1:
            return next(iter(filings))

        return filings['annualReport']

    def _get_template(self):
        return Path('report-templates/{}'.format(self._get_template_filename())).read_text()

    @abstractmethod
    def _get_template_filename(self):
        pass

    @abstractmethod
    def _get_template_data(self):
        pass
