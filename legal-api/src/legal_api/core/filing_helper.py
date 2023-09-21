"""Helper function for filings."""


from typing import Dict


def is_special_resolution_correction_by_filing_json(filing: Dict):
    """Check whether it is a special resolution correction."""
    # Note this relies on the filing data once. This is acceptable inside of the filer (which runs once)
    # and emailer (runs on PAID which is before the filer and runs on COMPLETED).
    # For filing data that persists in the database, attempt to use the meta_data instead.
    sr_correction_keys = ['rulesInResolution', 'resolution', 'rulesFileKey',
                          'memorandumInResolution', 'cooperativeAssociationType', 'offices']
    for key in sr_correction_keys:
        if key in filing.get('correction'):
            return True
    if 'requestType' in filing.get('correction', {}).get('nameRequest', {}):
        return True
    return False
