
from datetime import datetime

from legal_api import services
from legal_api.services import Colin


def test_business_valid_last_update(session):
    """Assert that the last_update is set and managed correctly."""
    identifier = 'CP7654321'

    business, status = Colin.get_business_by_identifier(identifier)

    print(business['business_info']['last_ledger_timestamp'], status)

    assert business['business_info']['last_ledger_timestamp'] == '2019-04-15T20:05:49.068272+00:00'


def test_business_none_last_update(session):
    """Assert that the last_update is set and managed correctly."""
    identifier = 'CP0000000'

    business, status = Colin.get_business_by_identifier(identifier)

    assert not business
    assert status == 404


def test_get_colin_by_name(session):
    """Assert that the last_update is set and managed correctly."""
    name = 'unique business name 1'

    business, status = Colin.get_business_by_legal_name(name)

    assert business is not None
    assert business['business_info']['legal_name'] == name
    assert status == 200


def test_get_colin_by_name_not_found(session):
    """Assert that the last_update is set and managed correctly."""
    name = 'not in the system'

    business, status = Colin.get_business_by_legal_name(name)

    assert business is None
    assert status == 404


def test_get_colin_by_name_no_connection(session, config):
    """Assert that the last_update is set and managed correctly."""
    from importlib import reload
    name = 'unique business name 1'

    orig_url = config.get('COLIN_URL')
    config.update(COLIN_URL='https://never.going.to.return')
    reload(services.colin)

    business, status = Colin.get_business_by_legal_name(name)

    config.update(COLIN_URL=orig_url)
    reload(services.colin)

    assert business is None
    assert status == 500
