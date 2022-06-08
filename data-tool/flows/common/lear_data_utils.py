from legal_api.models import Party, PartyRole, Business, Office, Address
from .event_filing_service import REGISTRATION_EVENT_FILINGS


def get_party_match(db: any, party_dict: dict, corp_num: str):
    query = db.session.query(Party) \
            .join(PartyRole) \
            .join(Business) \
            .filter(Business.identifier == corp_num) \
            .filter(PartyRole.business_id == Business.id) \
            .filter(Party.party_type == party_dict['partyType']) \
            .filter(Party.email == party_dict['email']) \
            .filter(Party.first_name == party_dict['firstName']) \
            .filter(Party.last_name == party_dict['lastName']) \
            .filter(Party.middle_initial == party_dict['middleName']) \
            .filter(Party.organization_name == party_dict['organizationName']) \
            .filter(Party.identifier == party_dict['identifier'])
    result = query.one_or_none()
    return result


def populate_filing_json_from_lear(db: any, event_filing_data: dict, business: Business):

    filing_type = event_filing_data['data']['target_lear_filing_type']
    event_filing_type = event_filing_data['data']['event_file_type']
    filing_json = event_filing_data['filing_json']

    if REGISTRATION_EVENT_FILINGS.has_value(event_filing_type):
        return

    parties_json = filing_json['filing'][filing_type].get('parties', [])
    business_office_json = filing_json['filing'][filing_type].get('offices', {}).get('businessOffice', None)

    business_json = filing_json['filing']['business']
    corp_num = business_json['identifier']
    business_json['legalName'] = business.legal_name
    business_json['foundingDate'] = business.founding_date.isoformat()

    for party_json in parties_json:
        if (officer := party_json['officer']) and (prev_colin_party := officer.get('prev_colin_party', None)):
            prev_party_match = get_party_match(db, prev_colin_party, corp_num)
            officer['id'] = prev_party_match.id

            if party_json.get('mailingAddress') and (mailing_addr := prev_party_match.mailing_address):
                party_json['mailingAddress']['id'] = mailing_addr.id
            if party_json.get('deliveryAddress') and (delivery_addr := prev_party_match.delivery_address):
                party_json['deliveryAddress']['id'] = delivery_addr.id

            if not party_json['roles'][0]['appointmentDate']:
                party_roles = PartyRole.get_party_roles_by_party_id(business.id, prev_party_match.id)
                party_role =  party_roles[0]
                appointment_dt_str = party_role.appointment_date.strftime('%Y-%m-%d')
                party_json['roles'][0]['appointmentDate'] = appointment_dt_str

            del officer['prev_colin_party']

    if business_office_json:

        business = Business.find_by_identifier(corp_num)
        business_office = business.offices \
            .filter(Office.office_type == 'businessOffice') \
            .one_or_none()

        mailing_address = business_office.addresses \
            .filter(Address.address_type == 'mailing') \
            .one_or_none()
        if mailing_address:
            business_office_json['mailingAddress']['id'] = mailing_address.id

        delivery_address = business_office.addresses \
            .filter(Address.address_type == 'delivery') \
            .one_or_none()
        if delivery_address:
            business_office_json['deliveryAddress']['id'] = delivery_address.id







