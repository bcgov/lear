
def get_custom_corp_names():
    """This is used to provide custom corp names for corp names where things like backslash couldn't be added
       in the source database."""

    corp_name_mapping_dict = {
        'FM0151616': 'REAL\TIME SYSTEMS',
        'FM0236781': 'TEAM HOME\RV MAINTENANCE',
        'FM0185321': '\I-YEN 1995 BUSINESS DEVELOPMENT CONSULTING CO.',
        'FM0259938': 'EURO\BEAN CAFFE COMPANY',
        'FM0249302': 'B:\PROMPT> SYSTEMS',
        'FM0446106': 'FRASER\DOYLE HOLDINGS',
        'FM0270319': 'AON\RUBEN-WINKLER ENTERTAINMENT INSURANCE         BROKERS',
        'FM0344562': 'T1\\',
        'FM0344563': 'TBWA\VANCOUVER',
        'FM0285081': 'RE\MAX RON NEAL & ASSOCIATES',
        'FM0303834': 'R\M DELIVERY SERVICES',
        'FM0789778': 'NO\W/IRE STUDIOS',
        'FM0535825': 'BURNABY INSULATION\SPI',
        'FM0749012': 'AB\BC CONSULTING'
    }
    return corp_name_mapping_dict
