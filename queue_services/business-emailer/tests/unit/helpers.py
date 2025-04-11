from string import ascii_letters, digits
from random import choices

from business_model.models import RegistrationBootstrap


def _generate_characters(length: int = 8):
    allowed_chars = ascii_letters + digits  # a-z, A-Z, 0-9
    return ''.join(choices(allowed_chars, k=length))


def generate_temp_filing():
    temp_identifier = 'Tb' + _generate_characters(8)
    temp_reg = RegistrationBootstrap()
    temp_reg._identifier = temp_identifier
    temp_reg.save()
    return temp_identifier
