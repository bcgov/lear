from document_record_service import DOCUMENT_CLASSES, DocumentClasses


def get_document_class(legal_type):
    """
    Return the corresponding document class for a given legal type.

    If the legal type is not found in the DOCUMENT_CLASSES mapping,
    defaults to the CORP document class.

    Args:
        legal_type (str): The legal type of the business (e.g., 'CP', 'SP').

    Returns:
        str: The corresponding document class (e.g., 'COOP', 'FIRM', 'CORP').
    """

    document_class = DOCUMENT_CLASSES.get(legal_type, "")

    return document_class if document_class else DocumentClasses.CORP.value
