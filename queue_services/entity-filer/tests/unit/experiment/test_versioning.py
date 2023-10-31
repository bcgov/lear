import datetime

import pytest

from business_model import LegalEntity

SKIP_NON_MANUAL_RUN = True


@pytest.mark.skipif(SKIP_NON_MANUAL_RUN, reason="experiment - manual run")
def test_le_version(session):
    le = LegalEntity(legal_name="racoon-dog")
    le.save()

    le.dissolution_date = datetime.datetime.now()
    le.state = "HISTORICAL"
    le.save()

    session.delete(le)
    session.commit()

    # can check that the history is stored correctly
    print("stop")
