"""Utils used in this application."""
from enum import Enum

from flask import json


def format_date(value):
    """Return value as string."""
    return_value = None
    if value:
        return_value = str(value)
    return return_value


def format_boolean(value):
    """Return value as boolean."""
    return_value = None
    if value is not None:
        return_value = value
    return return_value


def format_non_date(value):
    """Return non-date value as string."""
    return_value = None
    if value:
        return_value = value
    return return_value


def format_json(value):
    """Return json as string.

    If we have a JSON value (like a filing) we can't save it as a JSON string because flask jsonify will escape
    everything.
    """
    return_value = None
    # for some reason sql_alchemy returns this as a list of strings?
    # --> mystery solved: the app was doing loads before saving, so it didn't need to be loaded after
    # if value and len(value) > 0:
    #     logging.warning(type(value))
    #     return_value = json.loads(value[0])
    if value:
        return_value = json.dumps(value)
    return return_value


class SheetName(Enum):
    """Render an Enum of the names of the sheets."""

    BUSINESS = 'Businesses'
    BUSINESS_ADDRESS = 'Business_Addresses'
    DIRECTOR = 'Directors'
    DIRECTOR_ADDRESS = 'Director_Addresses'
    FILING = 'Filings'
