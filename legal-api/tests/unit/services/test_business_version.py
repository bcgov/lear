# Copyright © 2023 Province of British Columbia
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
"""Tests for the Minio service.

Test suite to ensure that the data can be retrived from history table.
"""
from sql_versioning import history_cls, versioned_session

from legal_api.models import Filing, LegalEntity, OfficeType, db
from legal_api.services.business_details_version import VersionedBusinessDetailsService
from legal_api.utils import datetime
from tests.unit.models import factory_legal_entity, factory_offices


def test_get_business_revision_obj(session):
    """Make sure the legal entity version data can be retrieved."""
    versioned_session(db.session)

    ia_filing = Filing(_filing_type="incorporationApplication")
    ia_filing.save()
    legal_entity = factory_legal_entity(identifier="BC1234567", entity_type="BEN", change_filing_id=ia_filing.id)

    dissolution_filing = Filing(_filing_type="dissolution")
    dissolution_filing.save()
    legal_entity.change_filing_id = dissolution_filing.id
    legal_entity.state = legal_entity.State.HISTORICAL
    legal_entity.state_filing_id = dissolution_filing.id
    legal_entity.save()

    legal_entity_version = history_cls(legal_entity)
    le_revision = db.session.query(legal_entity_version).filter(legal_entity_version.id == legal_entity.id).all()
    assert len(le_revision) == 1

    dissolution_le = VersionedBusinessDetailsService.get_business_revision_obj(dissolution_filing, legal_entity.id)
    assert dissolution_le.state == legal_entity.State.HISTORICAL

    ia_le = VersionedBusinessDetailsService.get_business_revision_obj(ia_filing, legal_entity.id)
    assert ia_le.state == legal_entity.State.ACTIVE


def test_find_last_value_from_business_revision(session):
    """Make sure the legal entity version data can be retrieved with last value of
    dissolution_date or restoration_expiry_date."""
    versioned_session(db.session)

    ia_filing = Filing(_filing_type="incorporationApplication")
    ia_filing.save()
    legal_entity = factory_legal_entity(identifier="BC1234567", entity_type="BEN", change_filing_id=ia_filing.id)

    dissolution_date = datetime.datetime.utcnow()
    dissolution_filing = Filing(_filing_type="dissolution")
    dissolution_filing.save()
    legal_entity.change_filing_id = dissolution_filing.id
    legal_entity.state = legal_entity.State.HISTORICAL
    legal_entity.dissolution_date = dissolution_date
    legal_entity.state_filing_id = dissolution_filing.id
    legal_entity.save()

    restoration_expiry_date = datetime.datetime.utcnow()
    limited_restoration_filing = Filing(_filing_type="restoration", _filing_sub_type="limitedRestoration")
    limited_restoration_filing.save()
    # before updating limitedRestoration
    dissolution_le = VersionedBusinessDetailsService.find_last_value_from_business_revision(
        limited_restoration_filing, legal_entity, is_dissolution_date=True
    )
    assert dissolution_le.state == legal_entity.State.HISTORICAL
    assert dissolution_le.dissolution_date == dissolution_date

    legal_entity.change_filing_id = limited_restoration_filing.id
    legal_entity.state = legal_entity.State.ACTIVE
    legal_entity.restoration_expiry_date = restoration_expiry_date
    legal_entity.dissolution_date = None
    legal_entity.state_filing_id = limited_restoration_filing.id
    legal_entity.save()

    # after updating limitedRestoration
    dissolution_le = VersionedBusinessDetailsService.find_last_value_from_business_revision(
        limited_restoration_filing, legal_entity, is_dissolution_date=True
    )
    assert dissolution_le.state == legal_entity.State.HISTORICAL
    assert dissolution_le.dissolution_date == dissolution_date

    full_restoration_filing = Filing(_filing_type="restoration", _filing_sub_type="limitedRestorationToFull")
    full_restoration_filing.save()

    # before updating limitedRestorationToFull
    limited_restoration_le = VersionedBusinessDetailsService.find_last_value_from_business_revision(
        full_restoration_filing, legal_entity, is_restoration_expiry_date=True
    )
    assert limited_restoration_le.state == legal_entity.State.ACTIVE
    assert limited_restoration_le.restoration_expiry_date == restoration_expiry_date

    legal_entity.change_filing_id = full_restoration_filing.id
    legal_entity.restoration_expiry_date = None
    legal_entity.save()

    # after updating limitedRestorationToFull
    limited_restoration_le = VersionedBusinessDetailsService.find_last_value_from_business_revision(
        full_restoration_filing, legal_entity, is_restoration_expiry_date=True
    )
    assert limited_restoration_le.state == legal_entity.State.ACTIVE
    assert limited_restoration_le.restoration_expiry_date == restoration_expiry_date

    # final status
    le = VersionedBusinessDetailsService.get_business_revision_obj(full_restoration_filing, legal_entity.id)
    assert le.state == legal_entity.State.ACTIVE
    assert le.restoration_expiry_date is None
    assert le.dissolution_date is None


def test_get_office_revision(session):
    """Make sure the office version data can be retrieved."""
    versioned_session(db.session)

    # incorporation application
    ia_effective_date = datetime.datetime.utcnow()
    ia_filing = Filing(_filing_type="incorporationApplication", effective_date=ia_effective_date)
    ia_filing.save()
    legal_entity = factory_legal_entity(identifier="BC1234567", entity_type="BEN", change_filing_id=ia_filing.id)
    factory_offices(legal_entity, office_types=[OfficeType.REGISTERED, OfficeType.RECORDS], change_filing=ia_filing)
    legal_entity.save()

    # alteration
    alt_effective_date = datetime.datetime.utcnow()
    alt_filing = Filing(_filing_type="alteration", effective_date=alt_effective_date)
    alt_filing.save()

    if existing_offices := legal_entity.offices.all():
        for office in existing_offices:
            if office.office_type == OfficeType.RECORDS:
                office.deactivated_date = alt_effective_date
            office.change_filing_id = alt_filing.id
            db.session.add(office)
            if existing_address := office.addresses.all():
                for address in existing_address:
                    address.change_filing_id = alt_filing.id
                    db.session.add(address)
            db.session.commit()

            if office.office_type == OfficeType.RECORDS:
                db.session.delete(office)
                db.session.commit()

    # dissolution
    dis_effective_date = datetime.datetime.utcnow()
    dis_filing = Filing(_filing_type="dissolution", effective_date=dis_effective_date)
    dis_filing.save()

    if existing_offices := legal_entity.offices.all():
        for office in existing_offices:
            office.change_filing_id = dis_filing.id
            db.session.add(office)

            if existing_address := office.addresses.all():
                for address in existing_address:
                    address.change_filing_id = dis_filing.id
                    db.session.add(address)
        db.session.commit()

    factory_offices(legal_entity, office_types=[OfficeType.CUSTODIAL], change_filing=dis_filing)
    legal_entity.save()
    ia_offices_version = VersionedBusinessDetailsService.get_office_revision(ia_filing, legal_entity.id)
    assert ia_offices_version
    assert len(ia_offices_version) == 2
    assert all(office_type in [OfficeType.REGISTERED, OfficeType.RECORDS] for office_type in ia_offices_version.keys())
    for office_type in [OfficeType.REGISTERED, OfficeType.RECORDS]:
        assert (
            ia_offices_version[office_type]["deliveryAddress"]["streetAddress"]
            == f"incorporationApplication {office_type} Delivery Street"
        )
        assert (
            ia_offices_version[office_type]["mailingAddress"]["streetAddress"]
            == f"incorporationApplication {office_type} Mailing Street"
        )

    alt_offices_version = VersionedBusinessDetailsService.get_office_revision(alt_filing, legal_entity.id)
    assert alt_offices_version
    assert len(alt_offices_version) == 1  # OfficeType.RECORDS deleted in alteration filing
    assert all(office_type in [OfficeType.REGISTERED] for office_type in alt_offices_version.keys())
    for office_type in [OfficeType.REGISTERED]:
        assert (
            alt_offices_version[office_type]["deliveryAddress"]["streetAddress"]
            == f"incorporationApplication {office_type} Delivery Street"
        )
        assert (
            alt_offices_version[office_type]["mailingAddress"]["streetAddress"]
            == f"incorporationApplication {office_type} Mailing Street"
        )

    dis_offices_version = VersionedBusinessDetailsService.get_office_revision(dis_filing, legal_entity.id)
    assert dis_offices_version
    assert len(dis_offices_version) == 2
    assert all(
        office_type in [OfficeType.REGISTERED, OfficeType.CUSTODIAL] for office_type in dis_offices_version.keys()
    )

    assert (
        dis_offices_version[OfficeType.REGISTERED]["deliveryAddress"]["streetAddress"]
        == f"incorporationApplication {OfficeType.REGISTERED} Delivery Street"
    )
    assert (
        dis_offices_version[OfficeType.REGISTERED]["mailingAddress"]["streetAddress"]
        == f"incorporationApplication {OfficeType.REGISTERED} Mailing Street"
    )

    assert (
        dis_offices_version[OfficeType.CUSTODIAL]["deliveryAddress"]["streetAddress"]
        == f"dissolution {OfficeType.CUSTODIAL} Delivery Street"
    )
    assert (
        dis_offices_version[OfficeType.CUSTODIAL]["mailingAddress"]["streetAddress"]
        == f"dissolution {OfficeType.CUSTODIAL} Mailing Street"
    )
