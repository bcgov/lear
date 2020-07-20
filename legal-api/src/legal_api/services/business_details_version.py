# Copyright © 2020 Province of British Columbia
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

"""This provides the service for getting business details as of a filing."""
from datetime import datetime

import pycountry
from sqlalchemy import or_
from sqlalchemy_continuum import version_class

from legal_api.models import Address, Business, Filing, Party, PartyRole, ShareClass, db


class VersionedBusinessDetailsService:
    """Provides service for getting business details as of a filing."""

    @staticmethod
    def get_company_details_revision(filing_id, business_id) -> dict:
        """Consolidates company details upto the given transaction id of a filing."""
        company_profile_json = {}
        business = Business.find_by_internal_id(business_id)
        filing = Filing.find_by_id(filing_id)
        company_profile_json['business'] = business.json()
        company_profile_json['parties'] = \
            VersionedBusinessDetailsService.get_party_role_revision(filing.transaction_id, business_id)
        company_profile_json['offices'] = \
            VersionedBusinessDetailsService.get_office_revision(filing.transaction_id, business)
        company_profile_json['shareClasses'] = \
            VersionedBusinessDetailsService.get_share_class_revision(filing.transaction_id, business_id)
        return company_profile_json

    @staticmethod
    def get_office_revision(transaction_id, business) -> dict:
        """Consolidates all office changes upto the given transaction id."""
        offices_json = {}
        address_version = version_class(Address)

        for office in business.offices.all():
            offices_json[office.office_type] = {}
            addresses_list = db.session.query(address_version) \
                .filter(address_version.transaction_id <= transaction_id) \
                .filter(address_version.office_id == office.id) \
                .filter(or_(address_version.end_transaction_id == None,  # pylint: disable=singleton-comparison # noqa: E711,E501;
                            address_version.end_transaction_id > transaction_id)) \
                .order_by(address_version.transaction_id).all()
            for address in addresses_list:
                offices_json[office.office_type][f'{address.address_type}Address'] = \
                    VersionedBusinessDetailsService.address_revision_json(address)

        return offices_json

    @staticmethod
    def get_party_role_revision(transaction_id, business_id) -> dict:
        """Consolidates all party changes upto the given transaction id."""
        party_role_version = version_class(PartyRole)
        party_roles = db.session.query(party_role_version)\
            .filter(party_role_version.transaction_id <= transaction_id) \
            .filter(party_role_version.business_id == business_id) \
            .filter(or_(party_role_version.end_transaction_id == None,   # pylint: disable=singleton-comparison # noqa: E711,E501;
                        party_role_version.end_transaction_id > transaction_id)) \
            .order_by(party_role_version.transaction_id).all()
        parties = []
        for party_role in party_roles:
            if party_role.cessation_date is None:
                party_role_json = VersionedBusinessDetailsService.party_role_revision_json(party_role)
                parties.append(party_role_json)
        return parties

    @staticmethod
    def get_share_class_revision(transaction_id, business_id) -> dict:
        """Consolidates all share classes upto the given transaction id."""
        share_class_version = version_class(ShareClass)
        share_classes_list = db.session.query(share_class_version) \
            .filter(share_class_version.transaction_id <= transaction_id) \
            .filter(share_class_version.business_id == business_id) \
            .filter(or_(share_class_version.end_transaction_id == None,  # pylint: disable=singleton-comparison # noqa: E711,E501;
                        share_class_version.end_transaction_id > transaction_id)) \
            .order_by(share_class_version.transaction_id).all()
        share_classes = []
        for share_class in share_classes_list:
            share_class_json = VersionedBusinessDetailsService.share_class_revision_json(share_class)
            share_classes.append(share_class_json)
        return share_classes

    @staticmethod
    def party_role_revision_json(party_role_revision) -> dict:
        """Return the party member as a json object."""
        cessation_date = datetime.date(party_role_revision.cessation_date).isoformat()\
            if party_role_revision.cessation_date else None
        party = {
            **VersionedBusinessDetailsService.party_revision_json(party_role_revision.party),
            'appointmentDate': datetime.date(party_role_revision.appointment_date).isoformat(),
            'cessationDate': cessation_date,
            'role': party_role_revision.role
        }
        return party

    @staticmethod
    def party_revision_json(party_revision) -> dict:
        """Return the party member as a json object."""
        if party_revision.party_type == Party.PartyTypes.PERSON.value:
            member = {
                'officer': {
                    'firstName': party_revision.first_name,
                    'lastName': party_revision.last_name
                }
            }
            if party_revision.title:
                member['title'] = party_revision.title
            if party_revision.middle_initial:
                member['officer']['middleInitial'] = party_revision.middle_initial
        else:
            member = {
                'officer': {'organizationName': party_revision.organization_name}
            }
        if party_revision.delivery_address:
            member_address = VersionedBusinessDetailsService.address_revision_json(party_revision.delivery_address)
            if 'addressType' in member_address:
                del member_address['addressType']
            member['deliveryAddress'] = member_address
        if party_revision.mailing_address:
            member_mailing_address = \
                VersionedBusinessDetailsService.address_revision_json(party_revision.mailing_address)
            if 'addressType' in member_mailing_address:
                del member_mailing_address['addressType']
            member['mailingAddress'] = member_mailing_address
        else:
            if party_revision.delivery_address:
                member['mailingAddress'] = member['deliveryAddress']
        return member

    @staticmethod
    def address_revision_json(address_revision):
        """Return a dict of this object, with keys in JSON format."""
        country_description = ''
        if address_revision.country:
            country_description = pycountry.countries.search_fuzzy(address_revision.country)[0].name
        return {
            'streetAddress': address_revision.street,
            'streetAddressAdditional': address_revision.street_additional,
            'addressType': address_revision.address_type,
            'addressCity': address_revision.city,
            'addressRegion': address_revision.region,
            'addressCountry': address_revision.country,
            'addressCountryDescription': country_description,
            'postalCode': address_revision.postal_code,
            'deliveryInstructions': address_revision.delivery_instructions
        }

    @staticmethod
    def share_class_revision_json(share_class_revision) -> dict:
        """Return the share_class as a json object."""
        share_class = {
            'id': share_class_revision.id,
            'name': share_class_revision.name,
            'priority': share_class_revision.priority,
            'hasMaximumShares': share_class_revision.max_share_flag,
            'maxNumberOfShares': share_class_revision.max_shares,
            'hasParValue': share_class_revision.par_value_flag,
            'parValue': share_class_revision.par_value,
            'currency': share_class_revision.currency,
            'hasRightsOrRestrictions': share_class_revision.special_rights_flag
        }

        series = []
        for share_series in share_class_revision.series:
            series.append(VersionedBusinessDetailsService.share_class_revision_json(share_series))
        share_class['series'] = series

        return share_class

    @staticmethod
    def share_series_revision_json(share_series_revision) -> dict:
        """Return the share series revision as a json object."""
        share_series = {
            'id': share_series_revision.id,
            'name': share_series_revision.name,
            'priority': share_series_revision.priority,
            'hasMaximumShares': share_series_revision.max_share_flag,
            'maxNumberOfShares': share_series_revision.max_shares,
            'hasRightsOrRestrictions': share_series_revision.special_rights_flag
        }
        return share_series
