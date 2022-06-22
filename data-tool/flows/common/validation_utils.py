import prefect
import pycountry
import re

from .custom_exceptions import CustomException

def validate_address(row_dict: dict):
    logger = prefect.context.get("logger")

    if not (country_typ_cd := row_dict.get('country_typ_cd', None)):
        logger.error(f'no country typ cd in address: {row_dict}')
        raise CustomException('no country typ cd in address', row_dict)

    results = pycountry.countries.search_fuzzy(country_typ_cd)
    if not results or len(results) == 0:
        logger.error(f'invalid country typ cd in address: {row_dict}')
        raise CustomException('invalid country typ cd in address', row_dict)


def validate_business(row_dict: dict):
    logger = prefect.context.get("logger")

    naics_code = row_dict.get('naics_code', None)
    naics_desc = row_dict.get('naics_desc', None)

    if not naics_code or len(naics_code) == 0:
        logger.error(f'no naics code: {row_dict}')
        raise CustomException('no naics code', row_dict)

    if len(naics_code) > 0 and len(naics_code) < 6:
        logger.error(f'naics code is less than 6 digits: {row_dict}')
        raise CustomException('naics code is less than 6 digits', row_dict)

    if naics_code and (not naics_desc or len(naics_desc) == 0):
        logger.error(f'naics code but no naics desc: {row_dict}')
        raise CustomException('naics code but no naics desc', row_dict)

    if naics_desc and len(naics_desc) > 300:
        logger.error(f'naics desc greater than length 300: {row_dict}')
        raise CustomException('naics desc greater than length 300', row_dict)

    naics_desc_pattern = r'\[NAICS-\d{6}\]'
    matches = re.search(naics_desc_pattern, naics_desc, flags=re.IGNORECASE)
    if matches:
        logger.error(f'naics desc should not contain naics code: {row_dict}')
        raise CustomException('naics desc should not contain naics code', row_dict)
