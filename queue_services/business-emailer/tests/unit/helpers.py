from datetime import timedelta
from string import ascii_letters, digits
from random import choices

from business_model.models import RegistrationBootstrap
from tests import EPOCH_DATETIME

def _generate_characters(length: int = 8):
    allowed_chars = ascii_letters + digits  # a-z, A-Z, 0-9
    return ''.join(choices(allowed_chars, k=length))


def generate_temp_filing():
    temp_identifier = 'Tb' + _generate_characters(8)
    temp_reg = RegistrationBootstrap()
    temp_reg._identifier = temp_identifier
    temp_reg.save()
    return temp_identifier


def make_future_effective(filing):
    """Set effective_date to 5 days after payment so is_future_effective is True."""
    filing.effective_date = EPOCH_DATETIME + timedelta(days=5)
    filing.save()
    return filing


def make_non_future_effective(filing):
    """Set effective_date == payment_completion_date so is_future_effective is False."""
    filing.effective_date = filing.payment_completion_date
    filing.save()
    return filing
