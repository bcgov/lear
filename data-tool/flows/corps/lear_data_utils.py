from datetime import datetime

from legal_api.models import Party, PartyRole, Business, Office, Address, Filing, User
from legal_api.models.colin_event_id import ColinEventId

from .event_filing_service import NewBusinessEventFilings, OtherEventFilings
from flows.common.filing_data_utils import get_is_paper_only, get_effective_date


def get_party_match(db: any, party_dict: dict, corp_num: str):
    query = db.session.query(Party) \
            .join(PartyRole) \
            .join(Business) \
            .filter(Business.identifier == corp_num) \
            .filter(PartyRole.business_id == Business.id) \
            .filter(PartyRole.cessation_date == None) \
            .filter(Party.party_type == party_dict['partyType']) \
            .filter(Party.first_name == party_dict['firstName']) \
            .filter(Party.last_name == party_dict['lastName']) \
            .filter(Party.middle_initial == party_dict['middleName']) \
            .filter(Party.organization_name == party_dict['organizationName']) \
            .filter(Party.identifier == party_dict['identifier'])

    if email := party_dict.get('email', None):
        query = query.filter(PartyRole.email == email)

    if appointment_date := party_dict['appointmentDate']:
        query = query.filter(PartyRole.appointment_date == appointment_date)

    result = query.one_or_none()
    return result


def get_business_office_match(db: any, office_type: str, corp_num: str):
    query = db.session.query(Office) \
        .join(Business) \
        .filter(Business.identifier == corp_num) \
        .filter(Office.office_type == office_type) \
        .filter(Office.deactivated_date == None)

    result = query.one_or_none()
    return result


def populate_filing_json_from_lear(db: any, event_filing_data: dict, business: Business):
    filing_type = event_filing_data['data']['target_lear_filing_type']
    event_filing_type = event_filing_data['data']['event_file_type']
    filing_json = event_filing_data['filing_json']

    if NewBusinessEventFilings.has_value(event_filing_type):
        return

    # if CorrectionEventFilings.has_value(event_filing_type):
    #     correction_json = filing_json['filing']['correction']
    #     colin_event_id = correction_json['corrected_filing_event_id']
    #     colin_event = get_colin_event(db, colin_event_id)
    #     filing_id = colin_event.filing_id
    #     correction_json['correctedFilingId'] = filing_id
    #     query =  db.session.query(Filing).filter(Filing.id == filing_id)
    #     corrected_filing = query.one_or_none()
    #     correction_json['correctedFilingDate'] = corrected_filing.filing_date.strftime('%Y-%m-%d')
    #     del correction_json['corrected_filing_event_id']

    business_json = filing_json['filing']['business']
    corp_num = business_json['identifier']
    business_json['legalName'] = business.legal_name
    business_json['foundingDate'] = business.founding_date.isoformat()

    if OtherEventFilings.FILE_ANNBC == event_filing_type:
        directors_json = filing_json['filing'][filing_type].get('directors', [])
        for director_json in directors_json:
            populate_director_json_from_lear(db, corp_num, director_json, business)
    else:
        parties_json = filing_json['filing'][filing_type].get('parties', [])
        for party_json in parties_json:
            populate_party_json_from_lear(db, corp_num, party_json, business)

    offices_json = filing_json['filing'][filing_type].get('offices', None)
    if offices_json:
        populate_office_json_from_lear(db, corp_num, offices_json, 'recordsOffice')
        populate_office_json_from_lear(db, corp_num, offices_json, 'registeredOffice')


def populate_office_json_from_lear(db: any, corp_num: str, offices_json: dict, office_type: str):
    office_json = offices_json.get(office_type, None)
    if not office_json:
        return

    office = get_business_office_match(db, office_type, corp_num)

    if office:
        mailing_address = office.addresses \
            .filter(Address.address_type == 'mailing') \
            .one_or_none()
        if mailing_address:
            office_json['mailingAddress']['id'] = mailing_address.id

        delivery_address = office.addresses \
            .filter(Address.address_type == 'delivery') \
            .one_or_none()
        if delivery_address:
            office_json['deliveryAddress']['id'] = delivery_address.id

def populate_party_json_from_lear(db: any, corp_num: str, party_json: dict , business: Business):
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


def populate_director_json_from_lear(db: any, corp_num: str, director_json: dict , business: Business):
    if (officer := director_json['officer']) and (prev_colin_party := officer.get('prev_colin_party', None)):
        prev_party_match = get_party_match(db, prev_colin_party, corp_num)
        officer['id'] = prev_party_match.id

        if director_json.get('mailingAddress') and (mailing_addr := prev_party_match.mailing_address):
            director_json['mailingAddress']['id'] = mailing_addr.id
        if director_json.get('deliveryAddress') and (delivery_addr := prev_party_match.delivery_address):
            director_json['deliveryAddress']['id'] = delivery_addr.id

        if not director_json['appointmentDate']:
            party_roles = PartyRole.get_party_roles_by_party_id(business.id, prev_party_match.id)
            party_role =  party_roles[0]
            appointment_dt_str = party_role.appointment_date.strftime('%Y-%m-%d')
            director_json['appointmentDate'] = appointment_dt_str

        del officer['prev_colin_party']


def get_colin_event(db: any, event_id: int):
    colin_event_id_obj = \
        db.session.query(ColinEventId).filter(ColinEventId.colin_event_id == event_id).one_or_none()
    return colin_event_id_obj


def populate_filing(business: Business, event_filing_data: dict, filing_data: dict):
    target_lear_filing_type = filing_data['target_lear_filing_type']
    filing_json = event_filing_data['filing_json']
    effective_date = get_effective_date(filing_data)

    filing = Filing()
    filing.skip_status_listener = True
    filing.effective_date = effective_date
    filing._status = Filing.Status.PENDING.value
    filing._filing_json = filing_json
    filing._filing_type = target_lear_filing_type
    filing.filing_date = effective_date
    filing._completion_date = effective_date
    filing.business_id = business.id if business else None
    filing.source = Filing.Source.COLIN.value
    filing.paper_only = get_is_paper_only(filing_data)

    return filing


def get_firm_affiliation_passcode(business: Business):
    """Return a firm passcode for a given business identifier."""
    pass_code = None
    end_date = datetime.utcnow().date()
    party_roles = PartyRole.get_party_roles(business.id, end_date)

    if len(party_roles) == 0:
        return pass_code

    party = party_roles[0].party

    if party.party_type == 'organization':
        pass_code = party.organization_name
    else:
        pass_code = party.last_name + ', ' + party.first_name
        if hasattr(party, 'middle_initial') and party.middle_initial:
            pass_code = pass_code + ' ' + party.middle_initial

    return pass_code
