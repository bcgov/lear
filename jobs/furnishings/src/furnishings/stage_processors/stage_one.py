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
"""Furnishings job procssing rules for stage one of involuntary dissolution."""
import uuid
from datetime import datetime

import pytz
import requests
from flask import Flask, current_app
from legal_api.models import Address, Batch, BatchProcessing, Business, Furnishing, db  # noqa: I001
from legal_api.services.bootstrap import AccountService
from legal_api.services.involuntary_dissolution import InvoluntaryDissolutionService
from legal_api.services.queue import QueueService
from legal_api.utils.datetime import datetime as datetime_util


class StageOneProcessor:
    """Processor for stage one of furnishings job."""

    def __init__(self, app, qsm):
        """Create stage one process helper instance."""
        self._app = app
        self._qsm = qsm

        self._second_notice_delay = app.config.get('SECOND_NOTICE_DELAY')
        self._email_grouping_identifier = None
        self._mail_grouping_identifier = None

    async def process(self, batch_processing: BatchProcessing):
        """Process batch_processing entry."""
        furnishings = Furnishing.find_by(
                batch_id=batch_processing.batch_id,
                business_id=batch_processing.business_id
                )
        if not furnishings:
            await self._send_first_round_notification(batch_processing, batch_processing.business)
        else:
            # send paper letter if business is still not in good standing after 5 days of email letter sent out
            valid_furnishing_names = [
                Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_AR,
                Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_TR,
                Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_AR_XPRO,
                Furnishing.FurnishingName.DISSOLUTION_COMMENCEMENT_NO_TR_XPRO
            ]
            tz = pytz.timezone('UTC')
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
                await self._send_second_round_notification(batch_processing)

    async def _send_first_round_notification(self, batch_processing: BatchProcessing, business: Business):
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
        if email:
            # send email letter
            new_furnishing = self._create_new_furnishing(
                batch_processing,
                eligible_details,
                Furnishing.FurnishingType.EMAIL,
                business.last_ar_date if business.last_ar_date else business.founding_date,
                business.legal_name,
                email
                )
            # notify emailer
            await self._send_email(new_furnishing)
        else:
            # send paper letter if business doesn't have email address
            new_furnishing = self._create_new_furnishing(
                batch_processing,
                eligible_details,
                Furnishing.FurnishingType.MAIL
            )

            mailing_address = business.mailing_address.one_or_none()
            if mailing_address:
                self._create_furnishing_address(mailing_address, new_furnishing.id)

            # TODO: create and add letter to either AR or transition pdf
            # TODO: send AR and transition pdf to BCMail+
            new_furnishing.status = Furnishing.FurnishingStatus.PROCESSED
            new_furnishing.processed_date = datetime.utcnow()

    async def _send_second_round_notification(self, batch_processing: BatchProcessing):
        """Send paper letter if business is still not in good standing after 5 days of email letter sent out."""
        _, eligible_details = InvoluntaryDissolutionService.check_business_eligibility(
            batch_processing.business_identifier,
            InvoluntaryDissolutionService.EligibilityFilters(exclude_in_dissolution=False)
        )

        if not eligible_details:
            return

        business = Business.find_by_identifier(batch_processing.business_identifier)
        new_furnishing = self._create_new_furnishing(
            batch_processing,
            eligible_details,
            Furnishing.FurnishingType.MAIL
        )

        mailing_address = business.mailing_address.one_or_none()
        if mailing_address:
            self._create_furnishing_address(mailing_address, new_furnishing.id)

        # TODO: create and add letter to either AR or transition pdf
        # TODO: send AR and transition pdf to BCMail+
        new_furnishing.status = Furnishing.FurnishingStatus.PROCESSED
        new_furnishing.processed_date = datetime.utcnow()

    def _create_new_furnishing(  # pylint: disable=too-many-arguments
            self,
            batch_processing: BatchProcessing,
            eligible_details: InvoluntaryDissolutionService.EligibilityDetails,
            furnishing_type: Furnishing.FurnishingType,
            last_ar_date: datetime,
            business_name: str,
            email: str = None
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

        grouping_identifier = self._get_grouping_identifier(furnishing_type)

        new_furnishing = Furnishing(
            furnishing_type=furnishing_type,
            furnishing_name=furnishing_name,
            batch_id=batch_processing.batch_id,
            business_id=batch_processing.business_id,
            business_identifier=batch_processing.business_identifier,
            created_date=datetime.utcnow(),
            last_modified=datetime.utcnow(),
            status=Furnishing.FurnishingStatus.QUEUED,
            grouping_identifier=grouping_identifier,
            last_ar_date=last_ar_date,
            business_name=business_name,
            email=email
        )
        new_furnishing.save()

        return new_furnishing

    def _create_furnishing_address(self, mailing_address: Address, furnishings_id: int) -> Address:
        """Clone business mailing address to be used by mail furnishings."""
        furnishing_address = Address(
            address_type=Address.FURNISHING,
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

    async def _send_email(self, furnishing: Furnishing):
        """Put email message on the queue for all email furnishing entries."""
        try:
            subject = self._app.config['NATS_EMAILER_SUBJECT']
            payload = {
                'specversion': '1.x-wip',
                'type': 'bc.registry.dissolution',
                'source': 'furnishingsJob',
                'id': str(uuid.uuid4()),
                'time': datetime.utcnow().isoformat(),
                'datacontenttype': 'application/json',
                'identifier': furnishing.business_identifier,
                'data': {
                    'furnishing': {
                        'type': 'INVOLUNTARY_DISSOLUTION',
                        'furnishingId': furnishing.id,
                        'furnishingName': furnishing.furnishing_name.name
                    }
                }
            }
            await self._qsm.publish_json_to_subject(payload, subject)
            self._app.logger.debug('Publish queue message %s: furnishing.id=%s', subject, furnishing.id)
        except Exception as err:
            self._app.logger.error('Queue Error: furnishing.id=%s, %s', furnishing.id, err, exc_info=True)

    def _get_grouping_identifier(self, furnishing_type: Furnishing.FurnishingType) -> int:
        """Return grouping identifier based on furnishing type."""
        if furnishing_type == Furnishing.FurnishingType.EMAIL:
            if not self._email_grouping_identifier:
                self._email_grouping_identifier = Furnishing.get_next_grouping_identifier()
            return self._email_grouping_identifier
        elif furnishing_type == Furnishing.FurnishingType.MAIL:
            if not self._mail_grouping_identifier:
                self._mail_grouping_identifier = Furnishing.get_next_grouping_identifier()
            return self._mail_grouping_identifier
        else:
            return None

    @staticmethod
    def _get_email_address_from_auth(identifier: str):
        """Return email address from auth for notification, return None if it doesn't have one."""
        token = AccountService.get_bearer_token()
        headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {token}'
        }

        contact_info = requests.get(
            f'{current_app.config.get("AUTH_URL")}/entities/{identifier}',
            headers=headers
        )
        contacts = contact_info.json()['contacts']
        if not contacts or not contacts[0]['email']:
            return None
        return contacts[0]['email']


async def process(app: Flask, qsm: QueueService):  # pylint: disable=redefined-outer-name
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

        processor = StageOneProcessor(app, qsm)

        for batch_processing in batch_processings:
            await processor.process(batch_processing)

    except Exception as err:
        app.logger.error(err)
