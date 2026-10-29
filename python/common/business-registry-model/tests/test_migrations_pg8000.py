"""Run the migration chain on pg8000, the driver the Cloud Run migration job uses.

The rest of the suite upgrades through psycopg2 (testcontainers default), which hides driver
specific failures such as CONCURRENTLY statements ending up inside the implicit transaction
pg8000 opens before alembic switches to autocommit.
"""

import os

import pytest
from flask import Flask
from flask_migrate import Migrate, downgrade, upgrade
from sqlalchemy import create_engine, text

import business_model_migrations
from business_model.models import db as _db
from tests.conftest import postgres

FILINGS_INDEX_REVISION = "a7d3e9f1c2b8"
PRE_INDEX_REVISION = "a9d4c27e81f3"
FILINGS_INDEXES = [
    "ix_filings_parent_filing_id",
    "ix_filings_payment_id",
    "ix_colin_event_ids_filing_id",
    "ix_filings_colin_sync",
    "ix_filings_temp_reg",
    "ix_filings_withdrawn_filing_id",
]


def _index_validity(engine):
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT c.relname, x.indisvalid FROM pg_class c JOIN pg_index x ON x.indexrelid = c.oid "
                "WHERE c.relname = ANY(:names)"
            ),
            {"names": FILINGS_INDEXES},
        ).all()
    return dict(rows)


@pytest.fixture(scope="module")
def pg8000_app(database_service):
    """A second database on the test container, reached through pg8000 instead of psycopg2."""
    admin = create_engine(postgres.get_connection_url(), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text("DROP DATABASE IF EXISTS migrations_pg8000"))
        conn.execute(text("CREATE DATABASE migrations_pg8000"))
    admin.dispose()

    app = Flask(__name__)
    url = postgres.get_connection_url(driver="pg8000").rsplit("/", 1)[0] + "/migrations_pg8000"
    app.config["SQLALCHEMY_DATABASE_URI"] = url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    _db.init_app(app)
    Migrate(app, _db, directory=os.path.dirname(business_model_migrations.__file__))
    with app.app_context():
        yield app


def test_filings_index_migrations_round_trip_on_pg8000(pg8000_app):
    """CONCURRENTLY index builds and drops must run outside a transaction on pg8000 too."""
    assert "pg8000" in str(_db.engine.url)

    upgrade()
    assert _index_validity(_db.engine) == dict.fromkeys(FILINGS_INDEXES, True)

    downgrade(revision=PRE_INDEX_REVISION)
    assert _index_validity(_db.engine) == {}

    # a build interrupted by a job timeout leaves an invalid index behind; the rerun must replace it
    with _db.engine.connect() as conn:
        conn.execute(text("CREATE INDEX ix_filings_payment_id ON filings (payment_id) WHERE payment_id IS NOT NULL"))
        conn.execute(text("UPDATE pg_index SET indisvalid = false WHERE indexrelid = 'ix_filings_payment_id'::regclass"))
        conn.commit()
    assert _index_validity(_db.engine) == {"ix_filings_payment_id": False}

    upgrade()
    assert _index_validity(_db.engine) == dict.fromkeys(FILINGS_INDEXES, True)
