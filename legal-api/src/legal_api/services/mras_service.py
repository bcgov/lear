# Copyright © 2024 Province of British Columbia
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
"""This provides the service for MRAS API calls."""
from http import HTTPStatus

import requests
from flask import current_app
from lxml import etree


class MrasService:
    """Provides services to use MRAS APIs."""

    NAMESPACE = {'mras': 'http://mras.ca/schema/v1'}

    @staticmethod
    def get_jurisdictions(identifier: str):
        """Return foreign jurisdiction info for the given BC corps."""
        try:
            mras_url = f'{current_app.config.get("MRAS_SVC_URL")}/api/v1/xpr/jurisdictions/{identifier}'
            headers = {
                'x-api-key': current_app.config.get('MRAS_SVC_API_KEY'),
                'Accept': 'application/xml'
            }
            response = requests.get(
                mras_url,
                headers=headers
            )

            if response.status_code != HTTPStatus.OK:
                return None

            xml_content = etree.fromstring(response.content)  # pylint: disable=c-extension-no-member
            registered_jurisdictions_info = xml_content.xpath(
                './/mras:Jurisdiction[mras:TargetProfileID]',
                namespaces=MrasService.NAMESPACE
                )
            results = []
            for j in registered_jurisdictions_info:
                info = {
                    'id': j.find('.//mras:JurisdictionID', namespaces=MrasService.NAMESPACE).text,
                    'name': j.find('.//mras:NameEn', namespaces=MrasService.NAMESPACE).text,
                    'nameFr': j.find('.//mras:NameFr', namespaces=MrasService.NAMESPACE).text,
                    'redirectUrl': j.find('.//mras:RedirectUrl', namespaces=MrasService.NAMESPACE).text,
                    'targetProfileId': j.find('.//mras:TargetProfileID', namespaces=MrasService.NAMESPACE).text
                }
                results.append(info)
            return results
        except Exception as err:
            current_app.logger.error(err)
            return None
