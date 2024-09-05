# Copyright © 2024 Province of British Columbia
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
"""Furnishings job processing rules after stage runs of involuntary dissolution."""
from datetime import datetime
from pathlib import Path
from typing import Final

from flask import Flask, current_app
from jinja2 import Template
from legal_api.models import Furnishing, FurnishingGroup, XmlPayload
from legal_api.utils.legislation_datetime import LegislationDatetime


XML_DATE_FORMAT: Final = '%B %-d, %Y'


class PostProcessor:
    """Processor after stage run of furnishings job."""

    def __init__(self, app, furnishings_dict):
        """Create post process helper instance."""
        self._app = app
        self._furnishings_dict = furnishings_dict
        self._xml_data = {}
        self._processed_date = LegislationDatetime.now()

    def _set_meta_info(self):
        """Set meta information for XML file."""
        # we leave date and volume in XML blank
        self._xml_data['effective_date'] = self._processed_date.strftime(XML_DATE_FORMAT)

    def _format_furnishings(self):
        """Format furnishing details presented in XML file."""
        self._xml_data['furnishings'] = {}
        for name, furnishings in self._furnishings_dict.items():
            self._xml_data['furnishings'][name] = XmlMeta.get_info_by_name(name)
            self._xml_data['furnishings'][name]['items'] = sorted(furnishings, key=lambda f: f.business_name)

    @staticmethod
    def _build_xml_data(xml_data, processed_time):
        """Build XML payload."""
        template = Path(
            f'{current_app.config.get("XML_TEMPLATE_PATH")}/gazette-notice.xml'
        ).read_text()
        jinja_template = Template(template, autoescape=True)

        return jinja_template.render(xml_data, processed_time=processed_time)

    @staticmethod
    def _save_xml_payload(payload):
        """Save XML payload."""
        xml_payload = XmlPayload(payload=payload)
        xml_payload.save()
        furnishing_group = FurnishingGroup(xml_payload_id=xml_payload.id)
        furnishing_group.save()
        return furnishing_group, xml_payload

    def _update_furnishings_status(self, furnishing_group_id):
        """Update furnishing entries after processing."""
        for furnishings in self._furnishings_dict.values():
            for furnishing in furnishings:
                furnishing.furnishing_group_id = furnishing_group_id
                furnishing.status = Furnishing.FurnishingStatus.PROCESSED
                furnishing.processed_date = datetime.utcnow()
                furnishing.last_modified = datetime.utcnow()
                furnishing.save()

    def process(self):
        """Postprocess to generate and upload file to external resources (BC Laws)."""
        if not self._furnishings_dict:
            return

        self._format_furnishings()
        self._app.logger.debug('Formatted furnishing details presented in XML file')
        self._set_meta_info()
        payload = self._build_xml_data(self._xml_data, self._processed_date.strftime('%I:%M %p'))
        furnishing_group, _ = self._save_xml_payload(payload)
        self._app.logger.debug('Saved XML payload')
        # TODO: SFTP to BC Laws

        # mark furnishing records processed
        self._update_furnishings_status(furnishing_group.id)
        self._app.logger.debug(
            f'furnishing records with group id: {furnishing_group.id} marked as processed')


class XmlMeta:
    """Helper class to maintain the XML meta information."""

    furnishings = {
        Furnishing.FurnishingName.INTENT_TO_DISSOLVE: {
            'title': 'Intent to Dissolve (B.C.)',
            'category': 'INTENT TO DISSOLVE',
            'subcategory': 'B.C.',
            'corp_class': 'BC Company(s)',
            'description': (
                'The Registrar of Companies hereby gives notice that the following companies may, '
                'at any time after the expiration of one month from the date of publication of this notice, '
                'unless cause is shown to the contrary, '
                'be dissolved under section 422 of the Business Corporations Act.'
            )
        },
        Furnishing.FurnishingName.INTENT_TO_DISSOLVE_XPRO: {
            'title': 'Intent to Cancel Registrations (extraprovincial)',
            'category': 'INTENT TO CANCEL REGISTRATIONS',
            'subcategory': 'Extraprovincial',
            'corp_class': 'Extraprovincial Company(s)',
            'description': (
                'The Registrar of Companies hereby gives notice that the following extraprovincial '
                'companies may, at any time after the expiration of one month from the date of publication '
                'of this notice, unless cause is shown to the contrary, have their registrations cancelled '
                'under section 422 of the Business Corporations Act'
            )
        },
        Furnishing.FurnishingName.CORP_DISSOLVED: {
            'title': 'Dissolutions (B.C.)',
            'category': 'DISSOLUTIONS',
            'subcategory': 'B.C.',
            'corp_class': 'BC Company(s)',
            'description': (
                'The Registrar of Companies hereby gives notice the following companies were dissolved under '
                'section 317, 422 or 423 of the Business Corporations Act.'
            )
        },
        Furnishing.FurnishingName.CORP_DISSOLVED_XPRO: {
            'title': 'Registrations Cancelled (extraprovincial)',
            'category': 'REGISTRATIONS CANCELLED',
            'subcategory': 'Extraprovincial',
            'corp_class': 'Extraprovincial Company(s)',
            'description': (
                'The Registrar of Companies hereby gives notice that the registrations of the following '
                'extraprovincial companies have been cancelled under section 397 or 422 of the Business '
                'Corporations Act.'
            )
        },
    }

    @staticmethod
    def get_info_by_name(name: Furnishing.FurnishingName) -> dict:
        """Return the furnishing category information as per furnishing name."""
        return XmlMeta.furnishings[name]


def process(app: Flask, furnishings_dict: dict):
    """Run postprocess after stage run to upload files to external resources."""
    try:
        processor = PostProcessor(app, furnishings_dict)
        processor.process()
    except Exception as err:
        app.logger.error(err)
