"""Helper function for filings."""

from typing import Dict


def is_special_resolution_correction_by_meta_data(filing):
    """Check whether it is a special resolution correction."""
    # Check by using the meta_data, this is more permanent than the filing json.
    # This is used by reports (after the filer).
    if filing.meta_data and (correction_meta_data := filing.meta_data.get("correction")):
        # Note these come from the corrections filer.
        sr_correction_meta_data_keys = [
            "hasResolution",
            "memorandumInResolution",
            "rulesInResolution",
            "uploadNewRules",
            "uploadNewMemorandum",
            "toCooperativeAssociationType",
            "toLegalName",
        ]
        for key in sr_correction_meta_data_keys:
            if key in correction_meta_data:
                return True
    return False


def is_special_resolution_correction_by_filing_json(filing: Dict):
    """Check whether it is a special resolution correction."""
    # Note this relies on the filing data once. This is acceptable inside of the filer (which runs once)
    # and emailer (runs on PAID which is before the filer and runs on COMPLETED).
    # For filing data that persists in the database, attempt to use the meta_data instead.
    sr_correction_keys = [
        "rulesInResolution",
        "resolution",
        "rulesFileKey",
        "memorandumFileKey",
        "memorandumInResolution",
        "cooperativeAssociationType",
    ]
    for key in sr_correction_keys:
        if key in filing.get("correction"):
            return True
    if "requestType" in filing.get("correction", {}).get("nameRequest", {}):
        return True
    return False
