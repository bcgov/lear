# Copyright © 2026 Province of British Columbia
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
"""Seed a local database with a business ready for manual draft-rebase testing.

Creates a BC company with two directors, an officer, a registered office, a share
class, a name translation and a resolution; one completed filing (the watermark);
and a user-filed changeOfDirectors draft (relationships shape) anchored to it that
moves Jane Smith to Nanaimo. With --staff-filing, a second filing then completes
under the draft (Jane moved to Vancouver, filed by staff), so the draft is stale
and GET .../changes reports a conflict right away.

Usage (from the legal-api root, against a migrated db your env points at):
    eval $(poetry env activate)
    python scripts/manual_db_scripts/seed_draft_rebase_business.py [--identifier BC0871234] [--staff-filing]
"""
import argparse
import copy
import random
import sys
import uuid
from datetime import UTC, datetime

from business_model.models import (
    Address,
    Alias,
    Business,
    Filing,
    Office,
    Party,
    PartyRole,
    Resolution,
    ShareClass,
    ShareSeries,
    db,
)
from business_model.models.db import VersioningProxy
from registry_schemas.example_data import ANNUAL_REPORT

from legal_api import create_app


def _address(city, street, address_type):
    return Address(address_type=address_type, street=street, city=city,
                   region="BC", country="CA", postal_code="V8V 8V8")


def _add_party(business, first, last, city, role, street="1234 Main St"):
    party = Party(first_name=first, last_name=last, party_type=Party.PartyTypes.PERSON.value,
                  delivery_address=_address(city, street, Address.DELIVERY),
                  mailing_address=_address(city, street, Address.MAILING))
    party.save()
    PartyRole(role=role, appointment_date=datetime.now(UTC),
              party_id=party.id, business_id=business.id).save()
    return party


def _complete_filing(business, filing_json, submitter_roles=None):
    """Save a filing and walk it to COMPLETED, minting its transaction (the watermark)."""
    filing = Filing()
    filing.business_id = business.id
    filing.filing_date = datetime.now(UTC)
    filing.filing_json = filing_json
    filing.save()

    filing.transaction_id = VersioningProxy.get_transaction_id(db.session())
    filing.payment_token = uuid.uuid4().hex
    filing.payment_completion_date = datetime.now(UTC)
    filing.effective_date = filing.filing_date
    if submitter_roles:
        filing.submitter_roles = submitter_roles
    filing.save()
    return filing


def _relationship(party, city, actions=None):
    row = {
        "entity": {"identifier": party.id, "givenName": party.first_name, "familyName": party.last_name},
        "roles": [{"roleType": "Director"}],
        "deliveryAddress": {"streetAddress": "1234 Main St", "addressCity": city,
                            "addressRegion": "BC", "addressCountry": "CA", "postalCode": "V8V 8V8"},
        "mailingAddress": {"streetAddress": "1234 Main St", "addressCity": city,
                           "addressRegion": "BC", "addressCountry": "CA", "postalCode": "V8V 8V8"},
    }
    if actions:
        row["actions"] = actions
    return row


def _user_draft(business, jane):
    """A business-ui-shaped COD draft editing Jane's address, anchored at the watermark."""
    filing_json = {"filing": {
        "header": {"name": "changeOfDirectors", "date": datetime.now(UTC).date().isoformat(),
                   "certifiedBy": "seed script"},
        "business": {"identifier": business.identifier, "legalType": business.legal_type},
        "changeOfDirectors": {"relationships": [_relationship(jane, "Nanaimo", actions=["ADDRESS_CHANGED"])]},
    }}
    filing = Filing()
    filing.business_id = business.id
    filing.filing_date = datetime.now(UTC)
    filing.filing_json = filing_json
    filing.base_transaction_id = Filing.get_max_completed_transaction_id(business.id)
    filing.submitter_roles = "public_user"
    filing.save()
    return filing


def seed(identifier, staff_filing):
    if Business.find_by_identifier(identifier):
        sys.exit(f"{identifier} already exists; pick another --identifier")

    # versioned business with a registered office
    VersioningProxy.get_transaction_id(db.session())
    business = Business(legal_name=f"DRAFT REBASE TEST - {identifier}", identifier=identifier,
                        legal_type=Business.LegalTypes.COMP.value, state=Business.State.ACTIVE,
                        founding_date=datetime.now(UTC))
    for office_type, street in (("registeredOffice", "500 Government St"),
                                ("recordsOffice", "501 Government St")):
        office = Office(office_type=office_type)
        office.addresses.append(_address("Victoria", street, Address.DELIVERY))
        office.addresses.append(_address("Victoria", street, Address.MAILING))
        business.offices.append(office)
    business.save()

    jane = _add_party(business, "Jane", "Smith", "Victoria", PartyRole.RoleTypes.DIRECTOR.value)
    bob = _add_party(business, "Bob", "Lee", "Burnaby", PartyRole.RoleTypes.DIRECTOR.value)
    pat = _add_party(business, "Pat", "Officer", "Vancouver", PartyRole.RoleTypes.CEO.value)

    Alias(alias="ABC GMBH", type=Alias.AliasType.TRANSLATION.value, business_id=business.id).save()
    Resolution(resolution_date=datetime.now(UTC).date(), resolution_type="SPECIAL",
               business_id=business.id).save()
    share_class = ShareClass(name="Class A Shares", priority=1, max_share_flag=True, max_shares=1000,
                             par_value_flag=False, special_rights_flag=False, business_id=business.id)
    share_class.series.append(ShareSeries(name="Series 1", priority=1, max_share_flag=True,
                                          max_shares=500, special_rights_flag=False))
    share_class.save()

    # the watermark the draft anchors to
    ar = copy.deepcopy(ANNUAL_REPORT)
    ar["filing"]["business"]["identifier"] = identifier
    ar["filing"]["business"]["legalName"] = business.legal_name
    base_filing = _complete_filing(business, ar)

    draft = _user_draft(business, jane)

    staff = None
    if staff_filing:
        # staff change under the draft: Jane moves, the draft is now stale and conflicted
        jane.delivery_address.city = "Vancouver"
        jane.delivery_address.save()
        staff = _complete_filing(business, copy.deepcopy(ar), submitter_roles="staff")

    watermark = Filing.get_max_completed_transaction_id(business.id)
    print(f"\nSeeded {identifier} (business id {business.id})")
    print(f"  directors: Jane Smith (party {jane.id}, Victoria), Bob Lee (party {bob.id}, Burnaby)")
    print(f"  officer:   Pat Officer (party {pat.id}, ceo) — out of scope for a COD draft")
    print(f"  base filing: id {base_filing.id}, transaction {base_filing.transaction_id}")
    print(f"  user draft:  id {draft.id} (changeOfDirectors, relationships shape, Jane -> Nanaimo)")
    print(f"               base_transaction_id={draft.base_transaction_id}, submitter_roles=public_user")
    if staff:
        print(f"  staff filing: id {staff.id}, transaction {staff.transaction_id} (Jane -> Vancouver, staff)")
    print(f"  watermark: {watermark}\n")
    print("Try:")
    print(f"  GET /api/v2/businesses/{identifier}/filings/{draft.id}/changes")
    print(f"  GET /api/v2/businesses/{identifier}/tasks")
    print(f"  PUT /api/v2/businesses/{identifier}/filings/{draft.id}?draft=true&baseTransactionId={watermark}")
    print("\nReminders:")
    print("  - enforcement needs 'draftRebaseChecks' in the 'enable-new-feature' flag (flags.json locally)")
    print("  - the staff bypass needs 'enable-staff-draft-filing-bypass' to list the filing type")
    print("  - UI testing needs the business affiliated to your account in auth")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--identifier", default=f"BC{random.randint(3000000, 3999999)}")
    parser.add_argument("--staff-filing", action="store_true",
                        help="complete a staff filing under the draft so /changes shows a conflict")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        seed(args.identifier, args.staff_filing)
