# Copyright © 2019 Province of British Columbia
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

"""The Test-Suite used to ensure that the Model objects are working correctly."""
import base64
import uuid

from freezegun import freeze_time
from registry_schemas.example_data import ANNUAL_REPORT
from sqlalchemy_continuum import versioning_manager
from legal_api.exceptions.error_messages import ErrorCode

from legal_api.models import (
    Address,
    Alias,
    LegalEntity,
    Comment,
    Filing,
    Office,
    Party,
    PartyRole,
    ShareClass,
    ShareSeries,
    User,
    db, ColinEntity, EntityRole,
)
from legal_api.models.colin_event_id import ColinEventId
from legal_api.utils.datetime import datetime, timezone
from tests import EPOCH_DATETIME, FROZEN_DATETIME


AR_FILING = {
    'filing': {
        'header': {
            'name': 'annualReport',
            'date': '2019-08-13'
        },
        'business': {
            'cacheId': 1,
            'foundingDate': '2007-04-08',
            'identifier': 'CP1234567',
            'legalName': 'legal name - CP1234567'
        },
        'annualReport': {
            'annualGeneralMeetingDate': '2019-04-08',
            'annualReportDate': '2019-04-08',
            'certifiedBy': 'full name',
            'email': 'no_one@never.get',
            'directors': [
                {
                    'officer': {
                        'firstName': 'Peter',
                        'lastName': 'Griffin',
                        'prevFirstName': 'Peter',
                        'prevMiddleInitial': 'G',
                        'prevLastName': 'Griffin'
                    },
                    'deliveryAddress': {
                        'streetAddress': 'street line 1',
                        'addressCity': 'city',
                        'addressCountry': 'country',
                        'postalCode': 'H0H0H0',
                        'addressRegion': 'BC'
                    },
                    'appointmentDate': '2018-01-01',
                    'cessationDate': None
                },
                {
                    'officer': {
                        'firstName': 'Joe',
                        'middleInitial': 'P',
                        'lastName': 'Swanson'
                    },
                    'deliveryAddress': {
                        'streetAddress': 'street line 1',
                        'additionalStreetAddress': 'street line 2',
                        'addressCity': 'city',
                        'addressCountry': 'UK',
                        'postalCode': 'H0H 0H0',
                        'addressRegion': 'SC'
                    },
                    'title': 'Treasurer',
                    'cessationDate': None,
                    'appointmentDate': '2018-01-01'
                }
            ],
            'deliveryAddress': {
                'streetAddress': 'delivery_address - address line one',
                'addressCity': 'delivery_address city',
                'addressCountry': 'delivery_address country',
                'postalCode': 'H0H0H0',
                'addressRegion': 'BC'
            },
            'mailingAddress': {
                'streetAddress': 'mailing_address - address line one',
                'addressCity': 'mailing_address city',
                'addressCountry': 'mailing_address country',
                'postalCode': 'H0H0H0',
                'addressRegion': 'BC'
            }
        }
    }
}


def factory_user(username: str, firstname: str = None, lastname: str = None):
    user = User()
    user.username = username
    user.firstname = firstname
    user.lastname = lastname
    user.save()
    return user


def factory_legal_entity(identifier=None,
                     founding_date=EPOCH_DATETIME,
                     last_ar_date=None,
                     entity_type=LegalEntity.EntityTypes.COOP.value,
                     state=LegalEntity.State.ACTIVE,
                     naics_code=None,
                     naics_desc=None,
                     admin_freeze=False,
                     first_name=None,
                     middle_initial=None,
                     last_name=None):
    """Create a business entity with a versioned business."""
    last_ar_year = None
    if last_ar_date:
        last_ar_year = last_ar_date.year

    legal_name = f'legal_name-{identifier}' if identifier else None
    legal_entity = LegalEntity(legal_name=legal_name,
                               founding_date=founding_date,
                               last_ar_date=last_ar_date,
                               last_ar_year=last_ar_year,
                               last_ledger_timestamp=EPOCH_DATETIME,
                               # dissolution_date=EPOCH_DATETIME,
                               entity_type=entity_type,
                               identifier=identifier,
                               tax_id='BN123456789',
                               fiscal_year_end_date=FROZEN_DATETIME,
                               state=state,
                               naics_code=naics_code,
                               naics_description=naics_desc,
                               admin_freeze=admin_freeze,
                               first_name=first_name,
                               middle_initial=middle_initial,
                               last_name=last_name)

    # Versioning business
    uow = versioning_manager.unit_of_work(db.session)
    uow.create_transaction(db.session)

    legal_entity.save()
    return legal_entity


def factory_legal_entity_mailing_address(legal_entity):
    """Create a business entity."""
    address = Address(
        city='Test City',
        street=f'{legal_entity.identifier}-Test Street',
        postal_code='T3S3T3',
        country='TA',
        region='BC',
        address_type=Address.MAILING
    )

    office = Office(
        office_type='registeredOffice'
    )

    office.addresses.append(address)
    legal_entity.offices.append(office)
    legal_entity.save()
    return legal_entity


def factory_filing(legal_entity, data_dict,
                   filing_date=FROZEN_DATETIME,
                   filing_type=None,
                   filing_sub_type=None):
    """Create a filing."""
    filing = Filing()
    filing.legal_entity_id = legal_entity.id
    filing.filing_date = filing_date
    filing.filing_json = data_dict
    if filing_type:
        filing._filing_type = filing_type
    if filing_sub_type:
        filing._filing_sub_type = filing_sub_type
    try:
        filing.save()
    except Exception as err:
        print(err)
    return filing


def factory_incorporation_filing(legal_entity, data_dict, filing_date=FROZEN_DATETIME, effective_date=FROZEN_DATETIME):
    """Create a filing."""
    filing = Filing()
    filing.legal_entity_id = legal_entity.id
    filing.filing_date = filing_date
    filing.effective_date = effective_date
    filing.filing_json = data_dict
    filing.save()
    return filing


def factory_completed_filing(legal_entity,
                             data_dict,
                             filing_date=FROZEN_DATETIME,
                             payment_token=None,
                             colin_id=None,
                             filing_type=None,
                             filing_sub_type=None):
    """Create a completed filing."""
    if not payment_token:
        payment_token = str(base64.urlsafe_b64encode(uuid.uuid4().bytes)).replace('=', '')

    with freeze_time(filing_date):

        filing = Filing()
        filing.legal_entity_id = legal_entity.id
        filing.filing_date = filing_date
        filing.filing_json = data_dict
        if filing_type:
            filing._filing_type = filing_type
        if filing_sub_type:
            filing._filing_sub_type = filing_sub_type
        filing.save()

        uow = versioning_manager.unit_of_work(db.session)
        transaction = uow.create_transaction(db.session)
        filing.transaction_id = transaction.id
        filing.payment_token = payment_token
        filing.effective_date = filing_date
        filing.payment_completion_date = filing_date
        if colin_id:
            colin_event = ColinEventId()
            colin_event.colin_event_id = colin_id
            colin_event.filing_id = filing.id
            colin_event.save()
        filing.save()
    return filing


def factory_pending_filing(legal_entity, data_dict, filing_date=FROZEN_DATETIME):
    """Create a pending filing."""
    filing = Filing()
    filing.legal_entity_id = legal_entity.id if legal_entity else None
    filing.filing_date = filing_date
    filing.filing_json = data_dict
    filing.payment_token = 2
    filing.save()
    return filing


def factory_error_filing(legal_entity, data_dict, filing_date=FROZEN_DATETIME):
    """Create an error filing."""
    filing = Filing()
    filing.legal_entity_id = legal_entity.id
    filing.filing_date = filing_date
    filing.filing_json = data_dict
    filing.save()
    filing.payment_token = 5
    filing.payment_completion_date = (datetime.now()).replace(tzinfo=timezone.utc)
    return filing


def factory_epoch_filing(legal_entity, filing_date=FROZEN_DATETIME):
    """Create an error filing."""
    filing = Filing()
    filing.legal_entity_id = legal_entity.id
    uow = versioning_manager.unit_of_work(db.session)
    transaction = uow.create_transaction(db.session)
    filing.transaction_id = transaction.id
    filing.filing_date = filing_date
    filing.filing_json = {'filing': {'header': {'name': 'lear_epoch'}}}
    filing.save()
    return filing


def factory_legal_entity_comment(legal_entity: LegalEntity = None, comment_text: str = 'some text', user: User = None):
    """Create a comment."""
    if not legal_entity:
        legal_entity =factory_legal_entity('CP1234567')

    c = Comment()
    c.legal_entity_id = legal_entity.id
    c.timestamp = EPOCH_DATETIME
    c.comment = comment_text
    if user:
        c.staff_id = user.id
    c.save()

    return c


def factory_comment(
        legal_entity: LegalEntity = None, filing: Filing = None, comment_text: str = 'some text', user: User = None):
    """Create a comment."""
    if not legal_entity:
        legal_entity =factory_legal_entity('CP1234567')

    if not filing:
        filing = factory_filing(legal_entity, ANNUAL_REPORT)

    c = Comment()
    c.filing_id = filing.id
    c.timestamp = EPOCH_DATETIME
    c.comment = comment_text
    if user:
        c.staff_id = user.id
    c.save()

    return c


def factory_party_role(delivery_address: Address,
                       mailing_address: Address,
                       officer: dict,
                       appointment_date: datetime,
                       cessation_date: datetime,
                       role_type: EntityRole.RoleTypes):
    """Create a role."""
    legal_entity = LegalEntity(
        first_name=officer['firstName'],
        last_name=officer['lastName'],
        middle_initial=officer['middleInitial'],
        entity_type=officer['partyType'],
        legal_name=officer['organizationName']
    )
    legal_entity.entity_delivery_address = delivery_address
    legal_entity.entity_mailing_address = mailing_address
    legal_entity.save()
    entity_role = EntityRole(
        role_type=role_type,
        appointment_date=appointment_date,
        cessation_date=cessation_date,
        related_entity_id=legal_entity.id
    )
    return entity_role


def factory_share_class(business_identifier: str):
    """Create a share class."""
    legal_entity =factory_legal_entity(business_identifier)
    share_class = ShareClass(
        name='Share Class 1',
        priority=1,
        max_share_flag=True,
        max_shares=1000,
        par_value_flag=True,
        par_value=0.852,
        currency='CAD',
        special_rights_flag=False,
        legal_entity_id=legal_entity.id
    )
    share_series_1 = ShareSeries(
        name='Share Series 1',
        priority=1,
        max_share_flag=True,
        max_shares=500,
        special_rights_flag=False
    )
    share_class.series.append(share_series_1)
    share_class.save()
    return share_class


def factory_incomplete_statuses(unknown_statuses:list = []):
    result = [Filing.Status.DRAFT.value,
                       Filing.Status.PENDING.value,
                       Filing.Status.PENDING_CORRECTION.value,
                       Filing.Status.ERROR.value,
                       Filing.Status.PAID.value]

    if unknown_statuses:
        result.extend(unknown_statuses)

    return result


def factory_address(address_type=Address.MAILING):
    """Create factory address."""
    address = Address(
        city='Test City',
        street=f'Test Street',
        postal_code='T3S3T3',
        country='TA',
        region='BC',
        address_type=address_type
    )
    address.save()
    return address
