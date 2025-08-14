from document_record_service import DOCUMENT_CLASSES, DOCUMENT_TYPES, DocumentClasses


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

def get_document_type(filing_type: str, legal_type: str) -> str:
    """
    Returns the document type based on the given filing type and legal type.

    If the filing type maps to a string, it returns that string.
    If the filing type maps to a dict, it uses the document class derived from the legal type
    to look up the corresponding document type.
    If no matching document type is found, it falls back to the 'systemIsTheRecord' type.

    Args:
        filing_type (str): The type of filing (e.g., 'annualReport', 'correction', etc.).
        legal_type (str): The legal entity type (e.g., 'BC', 'ULC', etc.).

    Returns:
        str: The resolved document type.
    """
    document_type = DOCUMENT_TYPES.get(filing_type, '')
    if isinstance(document_type, str):
        return document_type if document_type else DOCUMENT_TYPES.get('systemIsTheRecord')
    elif isinstance(document_type, dict):
        document_class = get_document_class(legal_type)
        doc_type = document_type.get(document_class, '')    
        return doc_type if doc_type else DOCUMENT_TYPES.get('systemIsTheRecord')
