from typing import Dict, Optional

import dpath.util

def get_str_from_json_filing(filing: Dict, path: str) -> Optional[str]:
    """Extract a str from the JSON filing, at the provided path.

    Args:
        data (Dict): A valid registry_schema filing.
        path (str): The path to the date, which is in ISO Format.

    Examples:
        >>>get_str_from_json_filing(
            filing={'filing':{'header':{'name': 'annualReport'}}},
            path='filing/header/name')
        'annualReport'

    """
    get_str(filing, path)

@DeprecationWarning
def get_str(filing: Dict, path: str) -> Optional[str]:
    """Extract a str from the JSON filing, at the provided path.

    Args:
        filing (Dict): A valid registry_schema filing.
        path (str): The path to the date, which is in ISO Format.

    Examples:
        >>>get_str(
            filing={'filing':{'header':{'name': 'annualReport'}}},
            path='filing/header/name')
        'annualReport'

    """
    try:
        raw = dpath.util.get(filing, path)
        return str(raw)
    except (IndexError, KeyError, TypeError, ValueError):
        return None
