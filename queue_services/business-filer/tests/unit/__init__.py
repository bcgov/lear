# Copyright © 2025 Province of British Columbia
#
# Licensed under the BSD 3 Clause License, (the "License");
# you may not use this file except in compliance with the License.
# The template for the license can be found here
#    https://opensource.org/license/bsd-3-clause/
#
# Redistribution and use in source and binary forms,
# with or without modification, are permitted provided that the
# following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS “AS IS”
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
"""The Unit Tests and the helper routines."""
import base64
import uuid
from datetime import datetime
from contextlib import contextmanager

from datedelta import datedelta
from dateutil.parser import parse
from freezegun import freeze_time
from sqlalchemy import exc

from business_model.models import Batch, BatchProcessing, Filing, Resolution, ShareClass, ShareSeries, db
from business_model.models.colin_event_id import ColinEventId
from business_model.models.db import VersioningProxy
from business_filer.common.datetime import datetime, timezone
from tests import EPOCH_DATETIME, FROZEN_DATETIME


AR_FILING = {
    'filing': {
        'header': {
            'name': 'annualReport',
            'date': '2001-08-05',
            'certifiedBy': 'full name',
            'email': 'no_one@never.get'
        },
        'business': {
            'cacheId': 1,
            'foundingDate': '2007-04-08T00:00:00+00:00',
            'identifier': 'CP1234567',
            'last_agm_date': '2017-04-08',
            'legalName': 'legal name - CP1234567'
        },
        'annualReport': {
            'annualGeneralMeetingDate': '2018-04-08',
            'annualReportDate': '2018-04-08',
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

COA_FILING = {
    'filing': {
        'header': {
            'name': 'changeOfAddress',
            'date': '2019-07-30',
            'certifiedBy': 'full name',
            'email': 'no_one@never.get'
        },
        'business': {
            'cacheId': 1,
            'foundingDate': '2007-04-08T00:00:00+00:00',
            'identifier': 'CP1234567',
            'last_agm_date': '2018-04-08',
            'legalName': 'legal name - CP1234567'
        },
        'changeOfAddress': {
            'offices': {
                'registeredOffice': {
                    'deliveryAddress': {
                        'streetAddress': 'test lane',
                        'streetAddressAdditional': 'test line 1',
                        'addressCity': 'testcity',
                        'addressCountry': 'Canada',
                        'addressRegion': 'BC',
                        'postalCode': 'T3S T3R',
                        'deliveryInstructions': 'Test address delivery',
                        'actions': ['addressChanged']
                    },
                    'mailingAddress': {
                        'streetAddress': 'test lane',
                        'streetAddressAdditional': 'test line 1',
                        'addressCity': 'testcity',
                        'addressCountry': 'Canada',
                        'addressRegion': 'BC',
                        'postalCode': 'T3S T3R',
                        'deliveryInstructions': 'Test address mailing',
                        'actions': ['addressChanged']
                    },
                }
            }
        }
    }
}

COD_FILING = {
    'filing': {
        'header': {
            'name': 'changeOfDirectors',
            'date': '2019-07-29',
            'certifiedBy': 'full name',
            'email': 'no_one@never.get'
        },
        'business': {
            'cacheId': 1,
            'foundingDate': '2007-04-08T00:00:00+00:00',
            'identifier': 'CP1234567',
            'last_agm_date': '2018-04-08',
            'legalName': 'legal name - CP1234567'
        },
        'changeOfDirectors': {
            'directors': [
                {
                    'title': '',
                    'appointmentDate': '2017-01-01',
                    'cessationDate': None,
                    'officer': {
                        'firstName': 'director1',
                        'lastName': 'test1',
                        'middleInitial': 'd',
                    },
                    'deliveryAddress': {
                        'streetAddress': 'test lane',
                        'streetAddressAdditional': 'test line 1',
                        'addressCity': 'testcity',
                        'addressCountry': 'Canada',
                        'addressRegion': 'BC',
                        'postalCode': 'T3S T3R',
                        'deliveryInstructions': 'director1'
                    },
                    'actions': []
                },
                {
                    'title': 'title',
                    'appointmentDate': '2018-01-01',
                    'cessationDate': None,
                    'officer': {
                        'firstName': 'director2',
                        'lastName': 'test2',
                        'middleInitial': 'd',
                        'prevFirstName': 'shouldchange',
                        'prevMiddleInitial': '',
                        'prevLastName': 'shouldchange',
                    },
                    'deliveryAddress': {
                        'streetAddress': 'test lane',
                        'streetAddressAdditional': 'test line 1',
                        'addressCity': 'testcity',
                        'addressCountry': 'Canada',
                        'addressRegion': 'BC',
                        'postalCode': 'T3S T3R',
                        'deliveryInstructions': 'director2'
                    },
                    'actions': ['nameChanged']
                },
                {
                    'title': 'title',
                    'appointmentDate': '2019-01-01',
                    'cessationDate': '2019-08-01',
                    'officer': {
                        'firstName': 'director3',
                        'lastName': 'test3',
                        'middleInitial': 'd',
                    },
                    'deliveryAddress': {
                        'streetAddress': 'test lane',
                        'streetAddressAdditional': 'test line 1',
                        'addressCity': 'testcity',
                        'addressCountry': 'Canada',
                        'addressRegion': 'BC',
                        'postalCode': 'T3S T3R',
                        'deliveryInstructions': 'director3'
                    },
                    'actions': ['ceased']
                },
                {
                    'title': 'title',
                    'appointmentDate': '2019-01-01',
                    'cessationDate': None,
                    'officer': {
                        'firstName': 'director4',
                        'lastName': 'test4',
                        'middleInitial': 'd',
                    },
                    'deliveryAddress': {
                        'streetAddress': 'test lane',
                        'streetAddressAdditional': 'test line 1',
                        'addressCity': 'testcity',
                        'addressCountry': 'Canada',
                        'addressRegion': 'BC',
                        'postalCode': 'T3S T3R',
                        'deliveryInstructions': 'director4'
                    },
                    'actions': ['addressChanged']
                },
                {
                    'title': 'title',
                    'appointmentDate': '2019-01-01',
                    'cessationDate': None,
                    'officer': {
                        'firstName': 'director5',
                        'lastName': 'test5',
                        'middleInitial': 'd',
                    },
                    'deliveryAddress': {
                        'streetAddress': 'test lane',
                        'streetAddressAdditional': 'test line 1',
                        'addressCity': 'testcity',
                        'addressCountry': 'Canada',
                        'addressRegion': 'BC',
                        'postalCode': 'T3S T3R',
                        'deliveryInstructions': 'director5'
                    },
                    'actions': ['appointed']
                }
            ],
        }
    }
}

COD_FILING_TWO_ADDRESSES = {
    'filing': {
        'header': {
            'name': 'changeOfDirectors',
            'date': '2019-07-29',
            'certifiedBy': 'full name',
            'email': 'no_one@never.get'
        },
        'business': {
            'cacheId': 1,
            'foundingDate': '2007-04-08T00:00:00+00:00',
            'identifier': 'CP1234567',
            'last_agm_date': '2018-04-08',
            'legalName': 'legal name - CP1234567'
        },
        'changeOfDirectors': {
            'directors': [
                {
                    'title': '',
                    'appointmentDate': '2017-01-01',
                    'cessationDate': None,
                    'officer': {
                        'firstName': 'director1',
                        'lastName': 'test1',
                        'middleInitial': 'd',
                    },
                    'deliveryAddress': {
                        'streetAddress': 'test lane',
                        'streetAddressAdditional': 'test line 1',
                        'addressCity': 'testcity',
                        'addressCountry': 'Canada',
                        'addressRegion': 'BC',
                        'postalCode': 'T3S T3R',
                        'deliveryInstructions': 'director1'
                    },
                    'mailingAddress': {
                        'streetAddress': 'test mailing 1',
                        'streetAddressAdditional': 'test line 1',
                        'addressCity': 'testcity',
                        'addressCountry': 'Canada',
                        'addressRegion': 'BC',
                        'postalCode': 'T3S T3R',
                        'deliveryInstructions': 'director1'
                    },
                    'actions': []
                },
                {
                    'title': 'title',
                    'appointmentDate': '2018-01-01',
                    'cessationDate': None,
                    'officer': {
                        'firstName': 'director2',
                        'lastName': 'test2',
                        'middleInitial': 'd',
                        'prevFirstName': 'shouldchange',
                        'prevMiddleInitial': '',
                        'prevLastName': 'shouldchange',
                    },
                    'deliveryAddress': {
                        'streetAddress': 'test lane',
                        'streetAddressAdditional': 'test line 1',
                        'addressCity': 'testcity',
                        'addressCountry': 'Canada',
                        'addressRegion': 'BC',
                        'postalCode': 'T3S T3R',
                        'deliveryInstructions': 'director2'
                    },
                    'actions': []
                }
            ],
        }
    }
}

COMBINED_FILING = {
    'filing': {
        'header': {
            'name': 'annualReport',
            'date': '2019-07-28',
            'certifiedBy': 'full name',
            'email': 'no_one@never.get',
        },
        'business': {
            'cacheId': 1,
            'foundingDate': '2007-04-08T00:00:00+00:00',
            'identifier': 'CP1234567',
            'last_agm_date': '2018-04-08',
            'legalName': 'legal name - CP1234567'
        },
        'annualReport': {
            'annualGeneralMeetingDate': '2019-04-08',
            'annualReportDate': '2019-04-08',
            'directors': COD_FILING['filing']['changeOfDirectors']['directors'],
            'offices': COA_FILING['filing']['changeOfAddress']['offices']
        },
        'changeOfAddress': COA_FILING['filing']['changeOfAddress'],
        'changeOfDirectors': COD_FILING['filing']['changeOfDirectors']
    }
}


def create_filing(token=None, json_filing=None, business_id=None, filing_date=EPOCH_DATETIME, bootstrap_id: str = None):
    """Return a test filing."""
    from business_model.models import Filing
    filing = Filing()
    if token:
        filing.payment_token = str(token)
    filing.filing_date = filing_date

    if json_filing:
        filing.filing_json = json_filing
    if business_id:
        filing.business_id = business_id
    if bootstrap_id:
        filing.temp_reg = bootstrap_id

    filing.save()
    return filing


def create_business(identifier, legal_type=None, legal_name=None):
    """Return a test business."""
    from business_model.models import Address, Business
    business = Business()
    business.identifier = identifier
    business.legal_type = legal_type
    business.legal_name = legal_name
    business = create_business_address(business, Address.DELIVERY)
    # business = create_business_address(business, Address.MAILING)
    business.save()
    return business


def create_business_address(business, type):
    """Create an address."""
    from business_model.models import Address, Office
    address = Address(
        city='Test City',
        street=f'{business.identifier}-Test Street',
        postal_code='T3S3T3',
        country='TA',
        region='BC',
    )
    if type == 'mailing':
        address.address_type = Address.MAILING
    else:
        address.address_type = Address.DELIVERY

    office = Office(office_type='registeredOffice')
    office.addresses.append(address)
    business.offices.append(office)
    business.save()
    return business


def create_user(username='temp_user', firstname='firstname', lastname='lastname', sub='sub', iss='iss'):
    """Create a user."""
    from business_model.models import User

    new_user = User(
        username=username,
        firstname=firstname,
        lastname=lastname,
        sub=sub,
        iss=iss,
    )
    new_user.save()

    return new_user


def create_entity(identifier, legal_type, legal_name):
    """Return a test business."""
    from business_model.models import Address, Business
    business = Business()
    business.identifier = identifier
    business.legal_type = legal_type
    business.legal_name = legal_name
    business.save()
    return business


def create_office(business, office_type: str):
    """Create office."""
    from business_model.models import Address, Office
    office = Office(office_type=office_type)
    business.offices.append(office)
    business.save()
    return office


def create_alias(business, alias):
    """Create alias."""
    from business_model.models import Alias
    alias = Alias(alias=alias, type=Alias.AliasType.TRANSLATION.value)
    business.aliases.append(alias)
    business.save()
    return alias


def create_office_address(business, office, address_type):
    """Create an address."""
    from business_model.models import Address, Office
    address = Address(
        city='Test City',
        street=f'{business.identifier}-Test Street',
        postal_code='T3S3T3',
        country='TA',
        region='BC',
    )
    if address_type == 'mailing':
        address.address_type = Address.MAILING
    else:
        address.address_type = Address.DELIVERY
    office.addresses.append(address)
    business.save()
    return address


def create_party(party_json):
    """Create a director."""
    from business_model.models import Address, Party
    new_party = Party(
        first_name=party_json['officer'].get('firstName', '').upper(),
        last_name=party_json['officer'].get('lastName', '').upper(),
        middle_initial=party_json['officer'].get('middleInitial', '').upper()
    )
    if party_json.get('mailingAddress'):
        mailing_address = Address(
            street=party_json['mailingAddress']['streetAddress'],
            city=party_json['mailingAddress']['addressCity'],
            country='CA',
            postal_code=party_json['mailingAddress']['postalCode'],
            region=party_json['mailingAddress']['addressRegion'],
            delivery_instructions=party_json['mailingAddress'].get('deliveryInstructions', '').upper()
        )
        new_party.mailing_address = mailing_address
    if party_json.get('deliveryAddress'):
        delivery_address = Address(
            street=party_json['deliveryAddress']['streetAddress'],
            city=party_json['deliveryAddress']['addressCity'],
            country='CA',
            postal_code=party_json['deliveryAddress']['postalCode'],
            region=party_json['deliveryAddress']['addressRegion'],
            delivery_instructions=party_json['deliveryAddress'].get('deliveryInstructions', '').upper()
        )
        new_party.delivery_address = delivery_address
    new_party.save()
    return new_party


def create_party_role(business, party, roles, appointment_date):
    """Create a director."""
    from business_model.models import PartyRole
    for role in roles:
        party_role = PartyRole(
            role=role,
            party=party,
            appointment_date=appointment_date,
            cessation_date=None
        )
        business.party_roles.append(party_role)

    return business


def create_share_class(business,
                       no_of_shares=1,
                       no_of_series_in_each_share=2,
                       include_resolution_date=False):
    """Create a new share class and associated series."""
    for i in range(no_of_shares):
        share_class = ShareClass(
            name=f'{business.identifier} Share Class {i}',
            priority=1,
            max_share_flag=True,
            max_shares=100,
            par_value_flag=True,
            par_value=10,
            currency='CAD',
            special_rights_flag=False
        )

        share_class.series = []
        for j in range(no_of_series_in_each_share):
            share_series = ShareSeries(
                name=f'{business.identifier} Share {i} Series {j}',
                priority=1,
                max_share_flag=True,
                max_shares=50,
                special_rights_flag=False
            )
            share_class.series.append(share_series)

    business.share_classes.append(share_class)

    if include_resolution_date:
        resolution = Resolution(
            resolution_date=parse('2024-09-05').date(),
            resolution_type=Resolution.ResolutionType.SPECIAL.value
        )
        business.resolutions.append(resolution)

    business.save()


def factory_completed_filing(business, data_dict, filing_date=FROZEN_DATETIME, payment_token=None, colin_id=None):
    """Create a completed filing."""
    if not payment_token:
        payment_token = str(base64.urlsafe_b64encode(uuid.uuid4().bytes)).replace('=', '')

    with freeze_time(filing_date):

        filing = Filing()
        filing.business_id = business.id
        filing.filing_date = filing_date
        filing.filing_json = data_dict
        filing.save()

        transaction_id = VersioningProxy.get_transaction_id(db.session())
        filing.transaction_id = transaction_id
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


def factory_batch(batch_type=Batch.BatchType.INVOLUNTARY_DISSOLUTION,
                  status=Batch.BatchStatus.HOLD,
                  size=3,
                  notes=''):
    """Create a batch."""
    batch = Batch(
        batch_type=batch_type,
        status=status,
        size=size,
        notes=notes
    )
    batch.save()
    return batch


def factory_batch_processing(batch_id,
                             business_id,
                             identifier,
                             step=BatchProcessing.BatchProcessingStep.WARNING_LEVEL_1,
                             status=BatchProcessing.BatchProcessingStatus.PROCESSING,
                             created_date=datetime.utcnow(),
                             trigger_date=datetime.utcnow() + datedelta(days=42),
                             last_modified=datetime.utcnow(),
                             notes=''):
    """Create a batch processing entry."""
    batch_processing = BatchProcessing(
        batch_id=batch_id,
        business_id=business_id,
        business_identifier=identifier,
        step=step,
        status=status,
        created_date=created_date,
        trigger_date=trigger_date,
        last_modified=last_modified,
        notes=notes
    )
    batch_processing.meta_data = {}
    batch_processing.save()
    return batch_processing

@contextmanager
def nested_session(session):
    try:
        sess = session.begin_nested()
        yield sess
        sess.rollback()
    except AssertionError as err:
        raise err
    except exc.ResourceClosedError as err:  # noqa: F841
        # mean the close out of the transaction got fouled in pytest
        pass
    except Exception as err:
        raise err
    finally:
        pass