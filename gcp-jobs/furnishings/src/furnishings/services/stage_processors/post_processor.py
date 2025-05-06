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
import base64
import os
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from typing import Final

from flask import Flask, current_app
from jinja2 import Template
from paramiko.ssh_exception import AuthenticationException, NoValidConnectionsError

from business_common.utils.legislation_datetime import LegislationDatetime
from business_model.models import Furnishing, FurnishingGroup, XmlPayload
from furnishings.services.flags import Flags
from furnishings.sftp import SftpConnection

XML_DATE_FORMAT: Final = "%B %-d, %Y"


class XmlMeta:
    """Helper class to maintain the XML meta information."""

    furnishings = {  # noqa: RUF012
        Furnishing.FurnishingName.INTENT_TO_DISSOLVE: {
            "title": "Intent to Dissolve (B.C.)",
            "category": "INTENT TO DISSOLVE",
            "subcategory": "B.C.",
            "corp_class": "BC Company(s)",
            "description": (
                "The Registrar of Companies hereby gives notice that the following companies may, "
                "at any time after the expiration of one month from the date of publication of this notice, "
                "unless cause is shown to the contrary, "
                "be dissolved under section 422 of the Business Corporations Act."
            )
        },
        Furnishing.FurnishingName.INTENT_TO_DISSOLVE_XPRO: {
            "title": "Intent to Cancel Registrations (extraprovincial)",
            "category": "INTENT TO CANCEL REGISTRATIONS",
            "subcategory": "Extraprovincial",
            "corp_class": "Extraprovincial Company(s)",
            "description": (
                "The Registrar of Companies hereby gives notice that the following extraprovincial "
                "companies may, at any time after the expiration of one month from the date of publication "
                "of this notice, unless cause is shown to the contrary, have their registrations cancelled "
                "under section 422 of the Business Corporations Act"
            )
        },
        Furnishing.FurnishingName.CORP_DISSOLVED: {
            "title": "Dissolutions (B.C.)",
            "category": "DISSOLUTIONS",
            "subcategory": "B.C.",
            "corp_class": "BC Company(s)",
            "description": (
                "The Registrar of Companies hereby gives notice the following companies were dissolved under "
                "section 317, 422 or 423 of the Business Corporations Act."
            )
        },
        Furnishing.FurnishingName.CORP_DISSOLVED_XPRO: {
            "title": "Registrations Cancelled (extraprovincial)",
            "category": "REGISTRATIONS CANCELLED",
            "subcategory": "Extraprovincial",
            "corp_class": "Extraprovincial Company(s)",
            "description": (
                "The Registrar of Companies hereby gives notice that the registrations of the following "
                "extraprovincial companies have been cancelled under section 397 or 422 of the Business "
                "Corporations Act."
            )
        },
    }

    @staticmethod
    def get_info_by_name(name: Furnishing.FurnishingName) -> dict:
        """Return the furnishing category information as per furnishing name."""
        return XmlMeta.furnishings[name]


class PostProcessor:
    """Processor after stage run of furnishings job."""

    def __init__(self, app: Flask | None = None):
        """Create post process helper instance."""
        self._app = None
        self._furnishings_dict = None
        self._processed_date = None
        self._disable_bclaws_sftp = None
        self._bclaws_sftp_connection = None
        if app:
            self.init_app(app)
        
    
    def init_app(self, app: Flask):
        """Initialize for the Flask app instance."""
        self._app = app
        self._disable_bclaws_sftp = False
        with app.app_context():
            self._processed_date = LegislationDatetime.now()
            self._disable_bclaws_sftp = Flags.is_on("disable-dissolution-sftp-bclaws")

        # setup the sftp connection objects
        self._bclaws_sftp_connection = SftpConnection(
            username=app.config.get("BCLAWS_SFTP_USERNAME"),
            host=app.config.get("BCLAWS_SFTP_HOST"),
            port=app.config.get("BCLAWS_SFTP_PORT"),
            private_key=base64.b64decode(app.config.get("BCLAWS_SFTP_PRIVATE_KEY")).decode("utf-8"),
            private_key_algorithm=app.config.get("BCLAWS_SFTP_PRIVATE_KEY_ALGORITHM"),
            private_key_passphrase=app.config.get("BCLAWS_SFTP_PRIVATE_KEY_PASSPHRASE")
        )

    @staticmethod
    def _format_furnishings(furnishings_dict: dict, processed_date: datetime) -> dict:
        """Format furnishing details presented in XML file."""
        xml_data = {
            "furnishings": {}
        }
        for name, furnishings in furnishings_dict.items():
            xml_data["furnishings"][name] = XmlMeta.get_info_by_name(name)
            xml_data["furnishings"][name]["items"] = sorted(furnishings, key=lambda f: f.business_name)
        # we leave date and volume in XML blank
        xml_data["effective_date"] = processed_date.strftime(XML_DATE_FORMAT)
        return xml_data

    @staticmethod
    def _build_xml_data(xml_data: dict, processed_time: str):
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

    def update_furnishings_status(self, funishing_status, furnishing_group_id=None, notes=None):
        """Update furnishing entries after processing."""
        for furnishings in self._furnishings_dict.values():
            for furnishing in furnishings:
                if furnishing_group_id:
                    furnishing.furnishing_group_id = furnishing_group_id
                    furnishing.processed_date = datetime.now(UTC)

                if notes:
                    furnishing.notes = notes

                furnishing.status = funishing_status
                furnishing.last_modified = datetime.now(UTC)
                furnishing.save()

    def process(self):
        """Postprocess to generate and upload file to external resources (BC Laws)."""
        if not self._furnishings_dict:
            return

        # Create the XML data from the furnishings dict
        xml_data = self._format_furnishings(self._furnishings_dict, self._processed_date)
        self._app.logger.debug("Formatted furnishing details presented in XML file")

        # Skip rest of processing if sftp is disabled
        if self._disable_bclaws_sftp:
            self._app.logger.debug(f"disable-dissolution-sftp-bclaws flag on: {self._disable_bclaws_sftp}")
            return

        # SFTP to BC Laws
        payload = self._build_xml_data(xml_data, self._processed_date.strftime("%I:%M %p"))
        filename = f"QP_CORP_{LegislationDatetime.format_as_legislation_date(self._processed_date)}.xml"
        with self._bclaws_sftp_connection as client:
            resp = client.putfo(
                    fl=StringIO(payload),
                    remotepath=(
                        f'{self._app.config.get("BCLAWS_SFTP_STORAGE_DIRECTORY")}'
                        f'/{filename}'
                    )
                )
        self._app.logger.debug(f"Successfully uploaded {resp.st_size} bytes to BCLaws SFTP")

        # Save xml payload
        furnishing_group, _ = self._save_xml_payload(payload)
        self._app.logger.debug("Saved XML payload")

        # mark furnishing records processed
        self.update_furnishings_status(
            Furnishing.FurnishingStatus.PROCESSED,
            furnishing_group_id=furnishing_group.id
        )
        self._app.logger.debug(
            f"Furnishing records with group id: {furnishing_group.id} marked as processed")


    def post_process(self, furnishings_dict: dict):
        """Run postprocess after stage run to upload files to external resources."""
        try:
            self._furnishings_dict = furnishings_dict
            self.process()
        except AuthenticationException as err:
            notes = "SFTP Error: Unable to authenticate."
            self.update_furnishings_status(Furnishing.FurnishingStatus.FAILED, notes=notes)
            self._app.logger.error(err)
        except (OSError, NoValidConnectionsError) as err:
            notes = f"SFTP Error: {os.strerror(err.errno)}."
            self.update_furnishings_status(Furnishing.FurnishingStatus.FAILED, notes=notes)
            self._app.logger.error(err)
        except Exception as err:
            notes = "Unnexpected error during post-processing."
            self.update_furnishings_status(Furnishing.FurnishingStatus.FAILED, notes=notes)
            self._app.logger.error(err)
