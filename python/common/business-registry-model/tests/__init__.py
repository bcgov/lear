import datetime
import time
from contextlib import contextmanager

from sqlalchemy import exc

EPOCH_DATETIME = datetime.datetime.utcfromtimestamp(0).replace(
    tzinfo=datetime.timezone.utc
)
FROZEN_DATETIME = datetime.datetime(2001, 8, 5, 7, 7, 58, 272362).replace(
    tzinfo=datetime.timezone.utc
)
TIMEZONE_OFFSET = time.timezone / 60 / 60 if time.timezone else 0


def has_expected_date_str_format(date_str: str, format: str) -> bool:
    "Determine if date string confirms to expected format"
    try:
        datetime.datetime.strptime(date_str, format)
    except ValueError:
        return False
    return True


@contextmanager
def nested_session(session):
    try:
        sess = session.begin_nested()
        yield sess
        sess.rollback()
    except AssertionError as err:
        raise err
    except exc.ResourceClosedError:
        # mean the close out of the transaction got fouled in pytest
        pass
    except Exception as err:
        raise err
    finally:
        pass
