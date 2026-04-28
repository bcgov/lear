"""Tests for the simple message-building helpers in business_emailer.services."""
import pytest

from business_emailer.services import create_email_msg, create_filing_msg, create_gcp_filing_msg


@pytest.mark.parametrize("identifier", [1, 123, "BC1234567", 0, None])
def test_create_filing_msg(identifier):
    """Assert create_filing_msg wraps the identifier under filing.id."""
    assert create_filing_msg(identifier) == {"filing": {"id": identifier}}


@pytest.mark.parametrize("identifier", [1, 123, "BC1234567", 0, None])
def test_create_gcp_filing_msg(identifier):
    """Assert create_gcp_filing_msg wraps the identifier under filingMessage.filingIdentifier."""
    assert create_gcp_filing_msg(identifier) == {"filingMessage": {"filingIdentifier": identifier}}


@pytest.mark.parametrize("identifier,filing_type", [
    (1, "incorporationApplication"),
    (42, "dissolution"),
    ("BC1234567", "amalgamationApplication"),
    (None, None),
])
def test_create_email_msg(identifier, filing_type):
    """Assert create_email_msg builds an email payload with PAID option."""
    assert create_email_msg(identifier, filing_type) == {
        "email": {"filingId": identifier, "type": filing_type, "option": "PAID"},
    }
