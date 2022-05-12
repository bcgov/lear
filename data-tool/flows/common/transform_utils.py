import re

from .validation_utils import validate_address, validate_business
from legal_api.models import Address, Business

def transform_address(row_dict: dict):
    validate_address(row_dict)
    addr_line_1, addr_line_2 = transform_address_lines(row_dict.get('addr_line_1'),
                                                       row_dict.get('addr_line_2'),
                                                       row_dict.get('addr_line_3'))
    addr = Address(address_type='mailing',
                   street=addr_line_1,
                   street_additional=addr_line_2,
                   city=row_dict.get('city'),
                   country=row_dict.get('country_typ_cd'),
                   delivery_instructions='PREFECT ETL FLOW TEST!!!!')

    return addr

def transform_address_lines(addr_line_1:str, addr_line_2:str, addr_line_3:str):
    if addr_line_3:
        addr_line_2 = f'{addr_line_2} {addr_line_3}'

    return addr_line_1, addr_line_2


def transform_business(row_dict: dict):
    validate_business(row_dict)

    naics_code, naics_desc = transform_naics(row_dict)
    corp_name = row_dict.get('corp_name')
    legal_name = f'{corp_name} - PREFECT ETL FLOW TEST'
    business = Business(_identifier=row_dict.get('corp_num'),
                        legal_name=legal_name,
                        legal_type=row_dict.get('corp_type_cd'),
                        naics_code=naics_code,
                        naics_description=naics_desc)

    return business


def transform_naics(row_dict: dict):
    naics_code = row_dict.get('naics_code')
    naics_desc = row_dict.get('naics_desc')

    pattern = r'\[NAICS-\d{6}\]'
    naics_desc = re.sub(pattern, '', naics_desc).strip()

    return naics_code, naics_desc
