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

from legal_api.models import (
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


class VersionedBusinessDetailsService:
    """Provides service for getting business details as of a filing."""

    @staticmethod
    def get_revision(filing_type, filing_id, business_id):
        """Consolidates based on filing type upto the given transaction id of a filing."""
        if filing_type == 'incorporationApplication':
            return VersionedBusinessDetailsService.get_ia_revision(filing_id, business_id)
        elif filing_type == 'changeOfDirectors':
            pass
        elif filing_type == 'changeOfAddress':
            pass
        elif filing_type == 'annualReport':
            pass
        elif filing_type == 'correction':
            pass
        elif filing_type == 'alteration':
            pass

        # Temperory
        filing = Filing.find_by_id(filing_id)
        return filing.json

    @staticmethod
    def get_ia_revision(filing_id, business_id) -> dict:
        """Consolidates incorporation application upto the given transaction id of a filing."""
        ia_json = {}
        business = Business.find_by_internal_id(business_id)
        filing = Filing.find_by_id(filing_id)

        ia_json['header'] = VersionedBusinessDetailsService.get_header_revision(filing)
        ia_json['business'] = \
            VersionedBusinessDetailsService.get_business_revision(filing.transaction_id, business)
        ia_json['incorporationApplication'] = {}
        ia_json['incorporationApplication']['offices'] = \
            VersionedBusinessDetailsService.get_office_revision(filing.transaction_id, business_id)
        ia_json['incorporationApplication']['parties'] = \
            VersionedBusinessDetailsService.get_party_role_revision(filing.transaction_id, business_id)
        ia_json['incorporationApplication']['nameRequest'] = \
            VersionedBusinessDetailsService.get_name_request_revision(filing)
        ia_json['incorporationApplication']['contactPoint'] = \
            VersionedBusinessDetailsService.get_contact_point_revision(filing)
        ia_json['incorporationApplication']['shareStructure'] = {}
        ia_json['incorporationApplication']['shareStructure']['shareClasses'] = \
            VersionedBusinessDetailsService.get_share_class_revision(filing.transaction_id, business_id)
        ia_json['incorporationApplication']['nameTranslations'] = {}
        ia_json['incorporationApplication']['nameTranslations']['new'] = \
            VersionedBusinessDetailsService.get_name_translations_revision(filing.transaction_id, business_id)
        ia_json['incorporationApplication']['incorporationAgreement'] = \
            VersionedBusinessDetailsService.get_incorporation_agreement_json(filing)
        return ia_json

    @staticmethod
    def get_header_revision(filing) -> dict:
        """Retrieve header from filing."""
        return filing.json['filing']['header']

    @staticmethod
    def get_company_details_revision(filing_id, business_id) -> dict:
        """Consolidates company details upto the given transaction id of a filing."""
        company_profile_json = {}
        business = Business.find_by_internal_id(business_id)
        filing = Filing.find_by_id(filing_id)
        company_profile_json['business'] = \
            VersionedBusinessDetailsService.get_business_revision(filing.transaction_id, business)
        company_profile_json['parties'] = \
            VersionedBusinessDetailsService.get_party_role_revision(filing.transaction_id, business_id)
        company_profile_json['offices'] = \
            VersionedBusinessDetailsService.get_office_revision(filing.transaction_id, business_id)
        company_profile_json['shareClasses'] = \
            VersionedBusinessDetailsService.get_share_class_revision(filing.transaction_id, business_id)
        company_profile_json['nameTranslations'] = \
            VersionedBusinessDetailsService.get_name_translations_revision(filing.transaction_id, business_id)
        company_profile_json['resolutions'] = \
            VersionedBusinessDetailsService.get_resolution_dates_revision(filing.transaction_id, business_id)
        return company_profile_json

    @staticmethod
    def get_business_revision(transaction_id, business) -> dict:
        """Consolidates the business info as of a particular transaction."""
        business_version = version_class(Business)
        business_revision = db.session.query(business_version) \
            .filter(business_version.transaction_id <= transaction_id) \
            .filter(business_version.operation_type != 2) \
            .filter(business_version.id == business.id) \
            .filter(or_(business_version.end_transaction_id == None,  # pylint: disable=singleton-comparison # noqa: E711,E501;
                        business_version.end_transaction_id > transaction_id)) \
            .order_by(business_version.transaction_id).one_or_none()
        return VersionedBusinessDetailsService.business_revision_json(business_revision, business.json())

    @staticmethod
    def get_office_revision(transaction_id, business_id) -> dict:
        """Consolidates all office changes upto the given transaction id."""
        offices_json = {}
        address_version = version_class(Address)
        offices_version = version_class(Office)

        offices = db.session.query(offices_version) \
            .filter(offices_version.transaction_id <= transaction_id) \
            .filter(offices_version.operation_type != 2) \
            .filter(offices_version.business_id == business_id) \
            .filter(or_(offices_version.end_transaction_id == None,  # pylint: disable=singleton-comparison # noqa: E711,E501;
                        offices_version.end_transaction_id > transaction_id)) \
            .order_by(offices_version.transaction_id).all()

        for office in offices:
            offices_json[office.office_type] = {}
            addresses_list = db.session.query(address_version) \
                .filter(address_version.transaction_id <= transaction_id) \
                .filter(address_version.operation_type != 2) \
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
            .filter(party_role_version.operation_type != 2) \
            .filter(party_role_version.business_id == business_id) \
            .filter(or_(party_role_version.end_transaction_id == None,   # pylint: disable=singleton-comparison # noqa: E711,E501;
                        party_role_version.end_transaction_id > transaction_id)) \
            .order_by(party_role_version.transaction_id).all()
        parties = []
        for party_role in party_roles:
            if party_role.cessation_date is None:
                party_role_json = VersionedBusinessDetailsService.party_role_revision_json(transaction_id, party_role)
                parties.append(party_role_json)
        return parties

    @staticmethod
    def get_share_class_revision(transaction_id, business_id) -> dict:
        """Consolidates all share classes upto the given transaction id."""
        share_class_version = version_class(ShareClass)
        share_classes_list = db.session.query(share_class_version) \
            .filter(share_class_version.transaction_id <= transaction_id) \
            .filter(share_class_version.operation_type != 2) \
            .filter(share_class_version.business_id == business_id) \
            .filter(or_(share_class_version.end_transaction_id == None,  # pylint: disable=singleton-comparison # noqa: E711,E501;
                        share_class_version.end_transaction_id > transaction_id)) \
            .order_by(share_class_version.transaction_id).all()
        share_classes = []
        for share_class in share_classes_list:
            share_class_json = VersionedBusinessDetailsService.share_class_revision_json(share_class)
            share_class_json['series'] = VersionedBusinessDetailsService.get_share_series_revision(transaction_id,
                                                                                                   share_class.id)
            share_classes.append(share_class_json)
        return share_classes

    @staticmethod
    def get_share_series_revision(transaction_id, share_class_id) -> dict:
        """Consolidates all share series under the share class upto the given transaction id."""
        share_series_version = version_class(ShareSeries)
        share_series_list = db.session.query(share_series_version) \
            .filter(share_series_version.transaction_id <= transaction_id) \
            .filter(share_series_version.operation_type != 2) \
            .filter(share_series_version.share_class_id == share_class_id) \
            .filter(or_(share_series_version.end_transaction_id == None,  # pylint: disable=singleton-comparison # noqa: E711,E501;
                        share_series_version.end_transaction_id > transaction_id)) \
            .order_by(share_series_version.transaction_id).all()
        share_series_arr = []
        for share_series in share_series_list:
            share_series_json = VersionedBusinessDetailsService.share_series_revision_json(share_series)
            share_series_arr.append(share_series_json)
        return share_series_arr

    @staticmethod
    def get_name_translations_revision(transaction_id, business_id) -> dict:
        """Consolidates all name translations upto the given transaction id."""
        name_translations_version = version_class(Alias)
        name_translations_list = db.session.query(name_translations_version) \
            .filter(name_translations_version.transaction_id <= transaction_id) \
            .filter(name_translations_version.operation_type != 2) \
            .filter(name_translations_version.business_id == business_id) \
            .filter(name_translations_version.type == 'TRANSLATION') \
            .filter(or_(name_translations_version.end_transaction_id == None,  # pylint: disable=singleton-comparison # noqa: E711,E501;
                        name_translations_version.end_transaction_id > transaction_id)) \
            .order_by(name_translations_version.transaction_id).all()
        name_translations_arr = []
        for name_translation in name_translations_list:
            name_translation_json = VersionedBusinessDetailsService.name_translations_json(name_translation)
            name_translations_arr.append(name_translation_json)
        return name_translations_arr

    @staticmethod
    def get_resolution_dates_revision(transaction_id, business_id) -> dict:
        """Consolidates all resolutions upto the given transaction id."""
        resolution_version = version_class(Resolution)
        resolution_list = db.session.query(resolution_version) \
            .filter(resolution_version.transaction_id <= transaction_id) \
            .filter(resolution_version.operation_type != 2) \
            .filter(resolution_version.business_id == business_id) \
            .filter(resolution_version.resolution_type == 'SPECIAL') \
            .filter(or_(resolution_version.end_transaction_id == None,  # pylint: disable=singleton-comparison # noqa: E711,E501;
                        resolution_version.end_transaction_id > transaction_id)) \
            .order_by(resolution_version.transaction_id).all()
        resolutions_arr = []
        for resolution in resolution_list:
            resolution_json = VersionedBusinessDetailsService.resolution_json(resolution)
            resolutions_arr.append(resolution_json)
        return resolutions_arr

    @staticmethod
    def party_role_revision_json(transaction_id, party_role_revision) -> dict:
        """Return the party member as a json object."""
        cessation_date = datetime.date(party_role_revision.cessation_date).isoformat()\
            if party_role_revision.cessation_date else None
        party_revision = VersionedBusinessDetailsService.get_party_revision(transaction_id, party_role_revision)
        party = {
            **VersionedBusinessDetailsService.party_revision_json(transaction_id, party_revision),
            'appointmentDate': datetime.date(party_role_revision.appointment_date).isoformat(),
            'cessationDate': cessation_date,
            'role': party_role_revision.role
        }
        return party

    @staticmethod
    def get_party_revision(transaction_id, party_role_revision) -> dict:
        """Consolidates all party changes upto the given transaction id."""
        party_version = version_class(Party)
        party = db.session.query(party_version) \
            .filter(party_version.transaction_id <= transaction_id) \
            .filter(party_version.operation_type != 2) \
            .filter(party_version.id == party_role_revision.party_id) \
            .filter(or_(party_version.end_transaction_id == None,  # pylint: disable=singleton-comparison # noqa: E711,E501;
                        party_version.end_transaction_id > transaction_id)) \
            .order_by(party_version.transaction_id).one_or_none()
        return party

    @staticmethod
    def party_revision_json(transaction_id, party_revision) -> dict:
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
        if party_revision.delivery_address_id:
            member_address = VersionedBusinessDetailsService.address_revision_json(
                VersionedBusinessDetailsService.get_address_revision
                (transaction_id, party_revision.delivery_address_id))
            if 'addressType' in member_address:
                del member_address['addressType']
            member['deliveryAddress'] = member_address
        if party_revision.mailing_address_id:
            member_mailing_address = \
                VersionedBusinessDetailsService.address_revision_json(
                    VersionedBusinessDetailsService.get_address_revision
                    (transaction_id, party_revision.mailing_address_id))
            if 'addressType' in member_mailing_address:
                del member_mailing_address['addressType']
            member['mailingAddress'] = member_mailing_address
        else:
            if party_revision.delivery_address:
                member['mailingAddress'] = member['deliveryAddress']
        return member

    @staticmethod
    def get_address_revision(transaction_id, address_id) -> dict:
        """Consolidates all party changes upto the given transaction id."""
        address_version = version_class(Address)
        address = db.session.query(address_version) \
            .filter(address_version.transaction_id <= transaction_id) \
            .filter(address_version.operation_type != 2) \
            .filter(address_version.id == address_id) \
            .filter(or_(address_version.end_transaction_id == None,  # pylint: disable=singleton-comparison # noqa: E711,E501;
                        address_version.end_transaction_id > transaction_id)) \
            .order_by(address_version.transaction_id).one_or_none()
        return address

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

    @staticmethod
    def name_translations_json(name_translation_revision) -> dict:
        """Return the name translation revision as a json object."""
        name_translation = {
            'id': name_translation_revision.id,
            'alias': name_translation_revision.alias,
            'type': name_translation_revision.type
        }
        return name_translation

    @staticmethod
    def resolution_json(resolution_revision) -> dict:
        """Return the resolution revision as a json object."""
        resolution = {
            'id': resolution_revision.id,
            'date': resolution_revision.resolution_date.strftime('%B %-d, %Y'),
            'type': resolution_revision.resolution_type
        }
        return resolution

    @staticmethod
    def business_revision_json(business_revision, business_json):
        """Return the business revision as a json object."""
        business_json['hasRestrictions'] = business_revision.restriction_ind
        if business_revision.dissolution_date:
            business_json['dissolutionDate'] = datetime.date(business_revision.dissolution_date).isoformat()
        else:
            business_json['dissolutionDate'] = None
        if business_revision.tax_id:
            business_json['taxId'] = business_revision.tax_id
        return business_json

    @staticmethod
    def get_incorporation_agreement_json(filing):
        """Return incorporation agreement from filing json."""
        return filing.json['filing'].get('incorporationAgreement', {})

    @staticmethod
    def get_name_request_revision(filing):
        """Return name request from filing json."""
        return filing.json['filing'].get('nameRequest', {})

    @staticmethod
    def get_contact_point_revision(filing):
        """Return contact point from filing json."""
        return filing.json['filing'].get('contactPoint', {})
