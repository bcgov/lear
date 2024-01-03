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
"""The Unit Tests and the helper routines."""
import base64
import uuid
from contextlib import contextmanager

import sqlalchemy
from freezegun import freeze_time
from entity_filer.utils.datetime import datetime, timezone
from tests import EPOCH_DATETIME, FROZEN_DATETIME
from business_model import db, Filing
from business_model.models.colin_event_id import ColinEventId

AR_FILING = {
    "filing": {
        "header": {
            "name": "annualReport",
            "date": "2001-08-05",
            "certifiedBy": "full name",
            "email": "no_one@never.get",
        },
        "business": {
            "cacheId": 1,
            "foundingDate": "2007-04-08T00:00:00+00:00",
            "identifier": "CP1234567",
            "last_agm_date": "2017-04-08",
            "legalName": "legal name - CP1234567",
        },
        "annualReport": {
            "annualGeneralMeetingDate": "2018-04-08",
            "annualReportDate": "2018-04-08",
            "directors": [
                {
                    "officer": {
                        "firstName": "Peter",
                        "lastName": "Griffin",
                        "prevFirstName": "Peter",
                        "prevMiddleInitial": "G",
                        "prevLastName": "Griffin",
                    },
                    "deliveryAddress": {
                        "streetAddress": "street line 1",
                        "addressCity": "city",
                        "addressCountry": "country",
                        "postalCode": "H0H0H0",
                        "addressRegion": "BC",
                    },
                    "appointmentDate": "2018-01-01",
                    "cessationDate": None,
                },
                {
                    "officer": {
                        "firstName": "Joe",
                        "middleInitial": "P",
                        "lastName": "Swanson",
                    },
                    "deliveryAddress": {
                        "streetAddress": "street line 1",
                        "additionalStreetAddress": "street line 2",
                        "addressCity": "city",
                        "addressCountry": "UK",
                        "postalCode": "H0H 0H0",
                        "addressRegion": "SC",
                    },
                    "title": "Treasurer",
                    "cessationDate": None,
                    "appointmentDate": "2018-01-01",
                },
            ],
            "deliveryAddress": {
                "streetAddress": "delivery_address - address line one",
                "addressCity": "delivery_address city",
                "addressCountry": "delivery_address country",
                "postalCode": "H0H0H0",
                "addressRegion": "BC",
            },
            "mailingAddress": {
                "streetAddress": "mailing_address - address line one",
                "addressCity": "mailing_address city",
                "addressCountry": "mailing_address country",
                "postalCode": "H0H0H0",
                "addressRegion": "BC",
            },
        },
    }
}

COA_FILING = {
    "filing": {
        "header": {
            "name": "changeOfAddress",
            "date": "2019-07-30",
            "certifiedBy": "full name",
            "email": "no_one@never.get",
        },
        "business": {
            "cacheId": 1,
            "foundingDate": "2007-04-08T00:00:00+00:00",
            "identifier": "CP1234567",
            "last_agm_date": "2018-04-08",
            "legalName": "legal name - CP1234567",
        },
        "changeOfAddress": {
            "offices": {
                "registeredOffice": {
                    "deliveryAddress": {
                        "streetAddress": "test lane",
                        "streetAddressAdditional": "test line 1",
                        "addressCity": "testcity",
                        "addressCountry": "Canada",
                        "addressRegion": "BC",
                        "postalCode": "T3S T3R",
                        "deliveryInstructions": "Test address delivery",
                        "actions": ["addressChanged"],
                    },
                    "mailingAddress": {
                        "streetAddress": "test lane",
                        "streetAddressAdditional": "test line 1",
                        "addressCity": "testcity",
                        "addressCountry": "Canada",
                        "addressRegion": "BC",
                        "postalCode": "T3S T3R",
                        "deliveryInstructions": "Test address mailing",
                        "actions": ["addressChanged"],
                    },
                }
            }
        },
    }
}

COD_FILING = {
    "filing": {
        "header": {
            "name": "changeOfDirectors",
            "date": "2019-07-29",
            "certifiedBy": "full name",
            "email": "no_one@never.get",
        },
        "business": {
            "cacheId": 1,
            "foundingDate": "2007-04-08T00:00:00+00:00",
            "identifier": "CP1234567",
            "last_agm_date": "2018-04-08",
            "legalName": "legal name - CP1234567",
        },
        "changeOfDirectors": {
            "directors": [
                {
                    "title": "",
                    "appointmentDate": "2017-01-01",
                    "cessationDate": None,
                    "officer": {
                        "firstName": "director1",
                        "lastName": "test1",
                        "middleInitial": "d",
                    },
                    "deliveryAddress": {
                        "streetAddress": "test lane",
                        "streetAddressAdditional": "test line 1",
                        "addressCity": "testcity",
                        "addressCountry": "Canada",
                        "addressRegion": "BC",
                        "postalCode": "T3S T3R",
                        "deliveryInstructions": "director1",
                    },
                    "actions": [],
                },
                {
                    "title": "title",
                    "appointmentDate": "2018-01-01",
                    "cessationDate": None,
                    "officer": {
                        "firstName": "director2",
                        "lastName": "test2",
                        "middleInitial": "d",
                        "prevFirstName": "shouldchange",
                        "prevMiddleInitial": "",
                        "prevLastName": "shouldchange",
                    },
                    "deliveryAddress": {
                        "streetAddress": "test lane",
                        "streetAddressAdditional": "test line 1",
                        "addressCity": "testcity",
                        "addressCountry": "Canada",
                        "addressRegion": "BC",
                        "postalCode": "T3S T3R",
                        "deliveryInstructions": "director2",
                    },
                    "actions": ["nameChanged"],
                },
                {
                    "title": "title",
                    "appointmentDate": "2019-01-01",
                    "cessationDate": "2019-08-01",
                    "officer": {
                        "firstName": "director3",
                        "lastName": "test3",
                        "middleInitial": "d",
                    },
                    "deliveryAddress": {
                        "streetAddress": "test lane",
                        "streetAddressAdditional": "test line 1",
                        "addressCity": "testcity",
                        "addressCountry": "Canada",
                        "addressRegion": "BC",
                        "postalCode": "T3S T3R",
                        "deliveryInstructions": "director3",
                    },
                    "actions": ["ceased"],
                },
                {
                    "title": "title",
                    "appointmentDate": "2019-01-01",
                    "cessationDate": None,
                    "officer": {
                        "firstName": "director4",
                        "lastName": "test4",
                        "middleInitial": "d",
                    },
                    "deliveryAddress": {
                        "streetAddress": "test lane",
                        "streetAddressAdditional": "test line 1",
                        "addressCity": "testcity",
                        "addressCountry": "Canada",
                        "addressRegion": "BC",
                        "postalCode": "T3S T3R",
                        "deliveryInstructions": "director4",
                    },
                    "actions": ["addressChanged"],
                },
                {
                    "title": "title",
                    "appointmentDate": "2019-01-01",
                    "cessationDate": None,
                    "officer": {
                        "firstName": "director5",
                        "lastName": "test5",
                        "middleInitial": "d",
                    },
                    "deliveryAddress": {
                        "streetAddress": "test lane",
                        "streetAddressAdditional": "test line 1",
                        "addressCity": "testcity",
                        "addressCountry": "Canada",
                        "addressRegion": "BC",
                        "postalCode": "T3S T3R",
                        "deliveryInstructions": "director5",
                    },
                    "actions": ["appointed"],
                },
            ],
        },
    }
}

COD_FILING_TWO_ADDRESSES = {
    "filing": {
        "header": {
            "name": "changeOfDirectors",
            "date": "2019-07-29",
            "certifiedBy": "full name",
            "email": "no_one@never.get",
        },
        "business": {
            "cacheId": 1,
            "foundingDate": "2007-04-08T00:00:00+00:00",
            "identifier": "CP1234567",
            "last_agm_date": "2018-04-08",
            "legalName": "legal name - CP1234567",
        },
        "changeOfDirectors": {
            "directors": [
                {
                    "title": "",
                    "appointmentDate": "2017-01-01",
                    "cessationDate": None,
                    "officer": {
                        "firstName": "director1",
                        "lastName": "test1",
                        "middleInitial": "d",
                    },
                    "deliveryAddress": {
                        "streetAddress": "test lane",
                        "streetAddressAdditional": "test line 1",
                        "addressCity": "testcity",
                        "addressCountry": "Canada",
                        "addressRegion": "BC",
                        "postalCode": "T3S T3R",
                        "deliveryInstructions": "director1",
                    },
                    "mailingAddress": {
                        "streetAddress": "test mailing 1",
                        "streetAddressAdditional": "test line 1",
                        "addressCity": "testcity",
                        "addressCountry": "Canada",
                        "addressRegion": "BC",
                        "postalCode": "T3S T3R",
                        "deliveryInstructions": "director1",
                    },
                    "actions": [],
                },
                {
                    "title": "title",
                    "appointmentDate": "2018-01-01",
                    "cessationDate": None,
                    "officer": {
                        "firstName": "director2",
                        "lastName": "test2",
                        "middleInitial": "d",
                        "prevFirstName": "shouldchange",
                        "prevMiddleInitial": "",
                        "prevLastName": "shouldchange",
                    },
                    "deliveryAddress": {
                        "streetAddress": "test lane",
                        "streetAddressAdditional": "test line 1",
                        "addressCity": "testcity",
                        "addressCountry": "Canada",
                        "addressRegion": "BC",
                        "postalCode": "T3S T3R",
                        "deliveryInstructions": "director2",
                    },
                    "actions": [],
                },
            ],
        },
    }
}

COMBINED_FILING = {
    "filing": {
        "header": {
            "name": "annualReport",
            "date": "2019-07-28",
            "certifiedBy": "full name",
            "email": "no_one@never.get",
        },
        "business": {
            "cacheId": 1,
            "foundingDate": "2007-04-08T00:00:00+00:00",
            "identifier": "CP1234567",
            "last_agm_date": "2018-04-08",
            "legalName": "legal name - CP1234567",
        },
        "annualReport": {
            "annualGeneralMeetingDate": "2019-04-08",
            "annualReportDate": "2019-04-08",
            "directors": COD_FILING["filing"]["changeOfDirectors"]["directors"],
            "offices": COA_FILING["filing"]["changeOfAddress"]["offices"],
        },
        "changeOfAddress": COA_FILING["filing"]["changeOfAddress"],
        "changeOfDirectors": COD_FILING["filing"]["changeOfDirectors"],
    }
}


def create_filing(
    token,
    json_filing=None,
    business_id=None,
    filing_date=EPOCH_DATETIME,
    bootstrap_id: str = None,
):
    """Return a test filing."""
    from business_model import Filing

    filing = Filing()
    filing.payment_token = str(token)
    filing.filing_date = filing_date

    if json_filing:
        # filing.filing_json = json_filing
        filing._filing_json = json_filing
        filing._filing_type = (
            json_filing.get("filing", {}).get("header", {}).get("name")
        )
        filing._filing_sub_type = filing.get_filings_sub_type(
            filing._filing_type, json_filing
        )
    if business_id:
        filing.legal_entity_id = business_id
    if bootstrap_id:
        filing.temp_reg = bootstrap_id

    filing.save()
    return filing


def create_business(identifier, legal_type=None, legal_name=None):
    """Return a test business."""
    from business_model import Address, LegalEntity

    business = LegalEntity()
    business.identifier = identifier
    business.entity_type = legal_type
    business.legal_name = legal_name
    business = create_business_address(business, Address.DELIVERY)
    # business = create_business_address(business, Address.MAILING)
    business.save()
    return business


def create_business_address(business, type):
    """Create an address."""
    from business_model import Address, Office

    address = Address(
        city="Test City",
        street=f"{business.identifier}-Test Street",
        postal_code="T3S3T3",
        country="TA",
        region="BC",
    )
    if type == "mailing":
        address.address_type = Address.MAILING
    else:
        address.address_type = Address.DELIVERY

    office = Office(office_type="registeredOffice")
    office.addresses.append(address)
    business.offices.append(office)
    business.save()
    return business


def create_user(
    username="temp_user",
    firstname="firstname",
    lastname="lastname",
    sub="sub",
    iss="iss",
):
    """Create a user."""
    from business_model import User

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
    """Return a test legal entity."""
    from business_model import Address, LegalEntity

    legal_entity = LegalEntity()
    legal_entity.entity_type = legal_type
    if legal_entity.entity_type == LegalEntity.EntityTypes.PERSON.value:
        legal_entity.first_name = "my"
        legal_entity.last_name = "self"
    legal_entity.legal_name = legal_name
    legal_entity.identifier = identifier
    legal_entity.save()
    return legal_entity


def create_office(business, office_type: str):
    """Create office."""
    from business_model import Address, Office

    office = Office(office_type=office_type)
    business.offices.append(office)
    business.save()
    return office


def create_alias(business, alias):
    """Create alias."""
    from business_model import Alias

    alias = Alias(alias=alias, type=Alias.AliasType.TRANSLATION.value)
    business.aliases.append(alias)
    business.save()
    return alias


def create_office_address(business, office, address_type):
    """Create an address."""
    from business_model import Address, Office

    address = Address(
        city="Test City",
        street=f"{business.identifier}-Test Street",
        postal_code="T3S3T3",
        country="TA",
        region="BC",
    )
    if address_type == "mailing":
        address.address_type = Address.MAILING
    else:
        address.address_type = Address.DELIVERY
    office.addresses.append(address)
    business.save()
    return address


def create_entity_person(party_json):
    """Create a director."""
    from business_model import Address, LegalEntity

    new_party = LegalEntity(
        first_name=party_json["officer"].get("firstName", "").upper(),
        last_name=party_json["officer"].get("lastName", "").upper(),
        middle_initial=party_json["officer"].get("middleInitial", "").upper(),
        entity_type=LegalEntity.EntityTypes.PERSON,
    )
    if party_json.get("mailingAddress"):
        mailing_address = Address(
            street=party_json["mailingAddress"]["streetAddress"],
            city=party_json["mailingAddress"]["addressCity"],
            country="CA",
            postal_code=party_json["mailingAddress"]["postalCode"],
            region=party_json["mailingAddress"]["addressRegion"],
            delivery_instructions=party_json["mailingAddress"]
            .get("deliveryInstructions", "")
            .upper(),
        )
        new_party.entity_mailing_address = mailing_address
    if party_json.get("deliveryAddress"):
        delivery_address = Address(
            street=party_json["deliveryAddress"]["streetAddress"],
            city=party_json["deliveryAddress"]["addressCity"],
            country="CA",
            postal_code=party_json["deliveryAddress"]["postalCode"],
            region=party_json["deliveryAddress"]["addressRegion"],
            delivery_instructions=party_json["deliveryAddress"]
            .get("deliveryInstructions", "")
            .upper(),
        )
        new_party.entity_delivery_address = delivery_address
    new_party.save()
    return new_party


def create_entity_role(business, party, roles, appointment_date):
    """Create a role for an entity."""
    from business_model import EntityRole

    for role in roles:
        party_role = EntityRole(
            appointment_date=appointment_date,
            cessation_date=None,
            change_filing_id=None,
            delivery_address_id=None,
            filing_id=None,
            # legal_entity_id=business.id,
            mailing_address_id=None,
            related_colin_entity_id=None,
            related_entity_id=party.id if party else None,
            role_type=role,
        )
        business.entity_roles.append(party_role)

    return business


def factory_completed_filing(
    legal_entity,
    data_dict,
    filing_date=FROZEN_DATETIME,
    payment_token=None,
    colin_id=None,
):
    """Create a completed filing."""
    if not payment_token:
        payment_token = str(base64.urlsafe_b64encode(uuid.uuid4().bytes)).replace(
            "=", ""
        )

    with freeze_time(filing_date):
        filing = Filing()
        filing.legal_entity_id = legal_entity.id
        filing.filing_date = filing_date
        filing.filing_json = data_dict
        filing.save()

        filing.payment_token = payment_token
        filing.effective_date = filing_date
        filing.payment_completion_date = filing_date
        if colin_id:
            colin_event = ColinEventId()
            colin_event.colin_event_id = colin_id
            colin_event.filing_id = filing.id
            colin_event.save()
        filing.save()

        legal_entity.change_filing_id = filing.id
        legal_entity.save()

    return filing


@contextmanager
def nested_session(session):
    try:
        sess = session.begin_nested()
        yield sess
        sess.rollback()
    except sqlalchemy.exc.ResourceClosedError:
        print("couldn't rollback, as the session is closed.")
    except Exception as err:
        print(err)
        raise Exception() from err
    finally:
        pass
