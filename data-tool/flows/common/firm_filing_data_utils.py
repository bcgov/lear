

def get_certified_by(filing_data: dict):
    user_id = filing_data.get('u_user_id')
    if user_id:
        first_name = filing_data.get('u_first_name')
        middle_name = filing_data.get('u_middle_name')
        last_name = filing_data.get('u_last_name')
        if first_name or middle_name or last_name:
            result = f'{first_name} {middle_name} {last_name}'
            result = result.replace('  ', ' ')
            return result
        return user_id

    return ''


def get_street_additional(addr_line_2: str, addr_line_3: str):
    addr_line_2 = addr_line_2 if addr_line_2 else ''
    addr_line_2 = addr_line_2.strip()
    addr_line_3 = addr_line_3 if addr_line_3 else ''
    result = f'{addr_line_2} {addr_line_3}'
    result = result.strip()
    return result


def get_party_role_type(corp_type_cd: str, role_type: str):
    if role_type == 'FCP':
        return 'Completing Party'
    elif role_type == 'FIO' or role_type == 'FBO':
        if corp_type_cd == 'SP':
            return 'Proprietor'
        elif corp_type_cd == 'GP':
            return 'Partner'
        else:
            return None
    else:
        return None


def get_party_type(filing_party_data: dict):
    corp_party_business_name = filing_party_data['cp_business_name']
    if corp_party_business_name:
        return 'organization'

    return 'person'


def get_is_paper_only(filing_data: dict):
    if (ods_type_cd := filing_data['f_ods_type']) and \
            ods_type_cd == 'P':
        return True

    return False
