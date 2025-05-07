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
"""Furnishings job processing rules for stage one of involuntary dissolution."""
import base64
import uuid
from datetime import UTC, datetime
from http import HTTPStatus
from io import BytesIO

import pytz
import requests
from flask import Flask, current_app
from simple_cloudevent import SimpleCloudEvent, to_queue_message

from business_account.AccountService import AccountService
from business_common.utils.datetime import datetime as datetime_util
from business_model.models import Address, Batch, BatchProcessing, Business, Furnishing, db
from dissolution_service import InvoluntaryDissolutionService
from furnishings.services.flags import Flags
from furnishings.services.furnishing_documents_service import FurnishingDocumentsService
from furnishings.services.reports.report_v2 import ReportTypes
from furnishings.sftp import SftpConnection
from gcp_queue import GcpQueue


class StageOneProcessor:
    """Processor for stage one of furnishings job."""

    def __init__(self, app: Flask | None = None, queue: GcpQueue | None = None):
        """Create stage one process helper instance."""
        self._app = None
        self._qsm = None

        self._email_furnishing_group_id = None
        self._mail_furnishing_group_id = None

        self._bc_mail_furnishings = []
        self._xpro_mail_furnishings = []
        self._bc_letters = None
        self._xpro_letters = None
        self._disable_bcmail_sftp = None

        self._bcmail_sftp_connection = None

        if app and queue:
            self.init_app(app, queue)
    
    def init_app(self, app: Flask, queue: GcpQueue):
        """Initialize for the Flask app instance."""
        self._app = app
        self._qsm = queue
        self._second_notice_delay = app.config.get("SECOND_NOTICE_DELAY")
        with app.app_context():
            self._disable_bcmail_sftp = Flags.is_on("disable-dissolution-sftp-bcmail")

        # setup the sftp connection objects
        self._bcmail_sftp_connection = SftpConnection(
            username=app.config.get("BCMAIL_SFTP_USERNAME"),
            host=app.config.get("BCMAIL_SFTP_HOST"),
            port=app.config.get("BCMAIL_SFTP_PORT"),
            private_key=base64.b64decode(app.config.get("BCMAIL_SFTP_PRIVATE_KEY")).decode("utf-8"),
            private_key_algorithm=app.config.get("BCMAIL_SFTP_PRIVATE_KEY_ALGORITHM"),
            private_key_passphrase=app.config.get("BCMAIL_SFTP_PRIVATE_KEY_PASSPHRASE")
        )

    def process(self):
        """Run process to manage and track notifications for dissolution stage one process."""
        try:
            batch_processings = (
                db.session.query(BatchProcessing)
                .filter(BatchProcessing.status == BatchProcessing.BatchProcessingStatus.PROCESSING)
                .filter(BatchProcessing.step == BatchProcessing.BatchProcessingStep.WARNING_LEVEL_1)
                .filter(Batch.id == BatchProcessing.batch_id)
                .filter(Batch.batch_type == Batch.BatchType.INVOLUNTARY_DISSOLUTION)
                .filter(Batch.status == Batch.BatchStatus.PROCESSING)
            ).all()
            for batch_processing in batch_processings:
                self.process_batch(batch_processing)
            self.generate_paper_letters()
            self.process_paper_letters()

        except (OSError, Exception) as err:
            current_app.logger.error(err)

    def process_batch(self, batch_processing: BatchProcessing):
        """Process batch_processing entry."""
        furnishings = Furnishing.find_by(
                batch_id=batch_processing.batch_id,
                business_id=batch_processing.business_id
                )
        if not furnishings:
            self._send_first_round_notification(batch_processing, batch_processing.business)
        else:
            # send paper letter if business is still not in good standing after 5 days of email letter sent out
            valid_furnishing_names = [
                Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_AR,
                Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_TR,
                Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_AR_XPRO,
                Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_TR_XPRO
            ]
            tz = pytz.timezone("UTC")
            today_date = tz.localize(datetime.today())

            has_elapsed_email_entry = any(
                furnishing.furnishing_type == Furnishing.FurnishingType.EMAIL
                and datetime_util.add_business_days(furnishing.created_date, self._second_notice_delay) < today_date
                and furnishing.furnishing_name in valid_furnishing_names
                for furnishing in furnishings
            )
            has_mail_entry = any(
                furnishing.furnishing_type == Furnishing.FurnishingType.MAIL
                and furnishing.furnishing_name in valid_furnishing_names
                for furnishing in furnishings
            )

            if has_elapsed_email_entry and not has_mail_entry:
                self._send_second_round_notification(batch_processing)

    def generate_paper_letters(self):
        """Generate merged paper letter with cover for BC/XPRO businesses."""
        self._app.logger.debug("Start generating batch letters.")
        try:
            document_service = FurnishingDocumentsService(ReportTypes.DISSOLUTION, "greyscale")
            if self._bc_mail_furnishings:
                self._app.logger.debug("Start generating BC batch letter.")
                self._bc_letters = document_service.get_merged_furnishing_document(self._bc_mail_furnishings)
                self._app.logger.debug("Finish generating BC batch letter.")
            if self._xpro_mail_furnishings:
                self._app.logger.debug("Start generating XPRO batch letter.")
                self._xpro_letters = document_service.get_merged_furnishing_document(self._xpro_mail_furnishings)
                self._app.logger.debug("Finish generating XPRO batch letter.")
        except Exception as e:
            self._app.logger.error(f"Error generating batch letters: {e}")
        self._app.logger.debug("Finish generating batch letters.")

    def upload_to_sftp(self, client, data, filename):
        """SFTP data to targeted destination."""
        return client.putfo(
            fl=BytesIO(data),
            remotepath=f'{self._app.config.get("BCMAIL_SFTP_STORAGE_DIRECTORY")}/{filename}'
        )

    def update_notes_and_status(self, furnishings_list, funishing_status, furnishing_notes=None):
        """Update the notes and status of furnishing entries in a list."""
        for furnishing in furnishings_list:
            furnishing.notes = furnishing_notes
            furnishing.status = funishing_status
            furnishing.processed_date = datetime.now(UTC)
            furnishing.save()

    def process_paper_letters(self):
        """Process the generated paper letts of BC and XPRO businesses (SFTP)."""
        # Skip SFTPing PDF files to BCMail+ if flag is on
        if self._disable_bcmail_sftp:
            self._app.logger.debug(f"disable-dissolution-sftp-bcmail flag on: {self._disable_bcmail_sftp}")
            return

        current_date = datetime_util.now()
        if self._bc_mail_furnishings:
            try:
                filename = current_date.strftime("DIS1_LETTER_BC_%b.%d.%Y.pdf")
                # SFTP BC batch letter PDF to BCMail+
                with self._bcmail_sftp_connection as client:
                    resp = self.upload_to_sftp(client, self._bc_letters, filename)
                self.update_notes_and_status(
                    self._bc_mail_furnishings,
                    Furnishing.FurnishingStatus.PROCESSED,
                    "SFTP of BC batch letter was a success."
                )
                self._app.logger.debug(f"Successfully uploaded {resp.st_size} bytes to BCMAIL+ SFTP (BC letter)")
            except Exception as err:
                self.update_notes_and_status(
                    self._bc_mail_furnishings,
                    Furnishing.FurnishingStatus.FAILED,
                    "SFTP error of BC batch letter."
                )
                self._app.logger.debug(f"SFTP error of BC batch letter: {err}")

        if self._xpro_mail_furnishings:
            try:
                filename = current_date.strftime("DIS1_LETTER_EP_%b.%d.%Y.pdf")
                # SFTP XPRO batch letter PDF to BCMail+
                with self._bcmail_sftp_connection as client:
                    resp = self.upload_to_sftp(client, self._xpro_letters, filename)
                self.update_notes_and_status(
                    self._xpro_mail_furnishings,
                    Furnishing.FurnishingStatus.PROCESSED,
                    "SFTP of XPRO batch letter was a success."
                )
                self._app.logger.debug(f"Successfully uploaded {resp.st_size} bytes to BCMAIL+ SFTP (XPRO letter)")
            except Exception as err:
                self.update_notes_and_status(
                    self._xpro_mail_furnishings,
                    Furnishing.FurnishingStatus.FAILED,
                    "SFTP error of XPRO batch letter."
                )
                self._app.logger.debug(f"SFTP error of XPRO batch letter: {err}")

    def _send_first_round_notification(self, batch_processing: BatchProcessing, business: Business):
        """Process first round of notification(email/letter)."""
        _, eligible_details = InvoluntaryDissolutionService.check_business_eligibility(
            batch_processing.business_identifier,
            InvoluntaryDissolutionService.EligibilityFilters(exclude_in_dissolution=False)
        )
        if not eligible_details:
            return
        # send email/letter notification for the first time
        email = self._get_email_address_from_auth(batch_processing.business_identifier)
        business = Business.find_by_identifier(batch_processing.business_identifier)
        new_furnishing = self._create_new_furnishing(
                batch_processing,
                eligible_details,
                Furnishing.FurnishingType.EMAIL,
                business.last_ar_date if business.last_ar_date else business.founding_date,
                business.legal_name,
                email
                )
        self._app.logger.debug(
            f"New furnishing has been created for {business.identifier} with ID (first round): {new_furnishing.id}")

        mailing_address = business.mailing_address.one_or_none()
        if mailing_address:
            self._create_furnishing_address(mailing_address, new_furnishing.id)
            self._app.logger.debug(f"Created address (first round) with furnishing ID: {new_furnishing.id}")

        if email:
            # send email letter
            self._send_email(new_furnishing)
            self._app.logger.debug(
                f"Successfully put email message on the queue for furnishing entry with ID: {new_furnishing.id}")
        else:
            # send paper letter if business doesn't have email address
            new_furnishing.furnishing_type = Furnishing.FurnishingType.MAIL
            new_furnishing.save()
            self._app.logger.debug(f"Changed furnishing type to MAIL for funishing with ID: {new_furnishing.id}")

            if business.legal_type == Business.LegalTypes.EXTRA_PRO_A.value:
                self._xpro_mail_furnishings.append(new_furnishing)
            else:
                self._bc_mail_furnishings.append(new_furnishing)

            new_furnishing.save()

    def _send_second_round_notification(self, batch_processing: BatchProcessing):
        """Send paper letter if business is still not in good standing after 5 days of email letter sent out."""
        _, eligible_details = InvoluntaryDissolutionService.check_business_eligibility(
            batch_processing.business_identifier,
            InvoluntaryDissolutionService.EligibilityFilters(exclude_in_dissolution=False)
        )

        if not eligible_details:
            return

        business: Business = Business.find_by_identifier(batch_processing.business_identifier)
        new_furnishing = self._create_new_furnishing(
            batch_processing,
            eligible_details,
            Furnishing.FurnishingType.MAIL,
            business.last_ar_date if business.last_ar_date else business.founding_date,
            business.legal_name
        )
        self._app.logger.debug(
            f"New furnishing has been created for {business.identifier} with ID (second round): {new_furnishing.id}")

        mailing_address = business.mailing_address.one_or_none()
        if mailing_address:
            self._create_furnishing_address(mailing_address, new_furnishing.id)
            self._app.logger.debug(f"Created address (second round) with furnishing ID: {new_furnishing.id}")

        if business.legal_type == Business.LegalTypes.EXTRA_PRO_A.value:
            self._xpro_mail_furnishings.append(new_furnishing)
        else:
            self._bc_mail_furnishings.append(new_furnishing)

        new_furnishing.save()

    def _create_new_furnishing(  # noqa: PLR0913
            self,
            batch_processing: BatchProcessing,
            eligible_details: InvoluntaryDissolutionService.EligibilityDetails,
            furnishing_type: Furnishing.FurnishingType,
            last_ar_date: datetime,
            business_name: str,
            email: str | None = None
            ) -> Furnishing:
        """Create new furnishing entry."""
        business = batch_processing.business
        if business.legal_type == Business.LegalTypes.EXTRA_PRO_A.value:
            furnishing_name = (
                Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_TR_XPRO
                if eligible_details.transition_overdue
                else Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_AR_XPRO
            )
        else:
            furnishing_name = (
                Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_TR
                if eligible_details.transition_overdue
                else Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_AR
            )

        furnishing_group_id = self._get_furnishing_group_id(furnishing_type)

        new_furnishing = Furnishing(
            furnishing_type=furnishing_type,
            furnishing_name=furnishing_name,
            batch_id=batch_processing.batch_id,
            business_id=batch_processing.business_id,
            business_identifier=batch_processing.business_identifier,
            created_date=datetime.now(UTC),
            last_modified=datetime.now(UTC),
            status=Furnishing.FurnishingStatus.QUEUED,
            furnishing_group_id=furnishing_group_id,
            last_ar_date=last_ar_date,
            business_name=business_name,
            email=email
        )
        new_furnishing.save()

        return new_furnishing

    def _create_furnishing_address(self, mailing_address: Address, furnishings_id: int) -> Address:
        """Clone business mailing address to be used by mail furnishings."""
        furnishing_address = Address(
            address_type=mailing_address.address_type,
            street=mailing_address.street,
            street_additional=mailing_address.street_additional,
            city=mailing_address.city,
            region=mailing_address.region,
            country=mailing_address.country,
            postal_code=mailing_address.postal_code,
            delivery_instructions=mailing_address.delivery_instructions,
            furnishings_id=furnishings_id
        )
        furnishing_address.save()

        return furnishing_address

    def _send_email(self, furnishing: Furnishing):
        """Put email message on the queue for all email furnishing entries."""
        try:
            topic = self._app.config["BUSINESS_EMAILER_TOPIC"]
            ce = SimpleCloudEvent(
                id=str(uuid.uuid4()),
                source="furnishingsJob",
                subject="filing",
                time=datetime.now(UTC),
                type="bc.registry.dissolution",
                data={
                    "furnishing": {
                        "type": "INVOLUNTARY_DISSOLUTION",
                        "furnishingId": furnishing.id,
                        "furnishingName": furnishing.furnishing_name.name
                    }
                }
            )
            self._qsm.publish(topic, to_queue_message(ce))
            self._app.logger.debug("Publish queue message %s: furnishing.id=%s", topic, furnishing.id)
        except Exception as err:
            self._app.logger.error("Queue Error: furnishing.id=%s, %s", furnishing.id, err, exc_info=True)

    def _get_furnishing_group_id(self, furnishing_type: Furnishing.FurnishingType) -> int:
        """Return furnishing group id based on furnishing type."""
        if furnishing_type == Furnishing.FurnishingType.EMAIL:
            if not self._email_furnishing_group_id:
                self._email_furnishing_group_id = Furnishing.get_next_furnishing_group_id()
            return self._email_furnishing_group_id
        elif furnishing_type == Furnishing.FurnishingType.MAIL:
            if not self._mail_furnishing_group_id:
                self._mail_furnishing_group_id = Furnishing.get_next_furnishing_group_id()
            return self._mail_furnishing_group_id
        else:
            return None

    @staticmethod
    def _get_email_address_from_auth(identifier: str):
        """Return email address from auth for notification, return None if it doesn't have one."""
        token = AccountService.get_bearer_token()
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {token}"
        }

        url = f'{current_app.config["AUTH_SVC_URL"]}/entities/{identifier}'
        try:
            contact_info = requests.get(url, headers=headers)
            contact_info.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == HTTPStatus.NOT_FOUND:
                current_app.logger.info(f"No entity found for identifier: {identifier}")
            else:
                current_app.logger.error(f"HTTP error occurred: {e}, URL: {url}, Status code: {e.response.status_code}")
            return None
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"Request failed: {e}, URL: {url}")
            return None

        contacts = contact_info.json().get("contacts", [])
        if not contacts or not contacts[0].get("email"):
            return None
        return contacts[0]["email"]
