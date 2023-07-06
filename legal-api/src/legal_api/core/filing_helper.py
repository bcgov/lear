"""Helper function for filings."""
from typing import Dict

from legal_api.models.business import Business


def is_special_resolution_correction(filing: Dict, business, original_filing):
    """Check whether it is a special resolution correction."""
    # Avoid circular import.
    from legal_api.core.filing import Filing  # pylint: disable=import-outside-toplevel
    corrected_filing_type = filing['correction'].get('correctedFilingType')

    if isinstance(business, Business) and business.legal_type != Business.LegalTypes.COOP.value:
        return False
    if isinstance(business, dict) and business.get('legalType') != Business.LegalTypes.COOP.value:
        return False
    if corrected_filing_type == 'specialResolution':
        return True
    if corrected_filing_type not in ('specialResolution', 'correction'):
        return False
    if not original_filing:
        return False

    # Find the next original filing in the chain of corrections
    filing = original_filing.filing_json['filing']
    original_filing = Filing.find_by_id(filing['correction']['correctedFilingId'])
    return is_special_resolution_correction(filing, business, original_filing)
