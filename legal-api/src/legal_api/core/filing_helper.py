"""Helper function for filings."""


def is_special_resolution_correction(filing):
    """Check whether it is a special resolution correction."""
    # Check by using the Metadata, this is more permanent than the filing json.
    # This is used by reports and email (after the filer).
    if filing.meta_data and (correction_meta_data := filing.meta_data.get('correction')):
        # Note these come from the corrections filer.
        sr_correction_meta_data_keys = ['hasResolution', 'memorandumInResolution', 'rulesInResolution',
                                        'uploadNewRules', 'toCooperativeAssociationType', 'toLegalName']
        for key in sr_correction_meta_data_keys:
            if key in correction_meta_data:
                return True
    return False
