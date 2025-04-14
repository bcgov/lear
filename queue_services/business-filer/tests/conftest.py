# # Copyright © 2019 Province of British Columbia
# #
# # Licensed under the Apache License, Version 2.0 (the "License");
# # you may not use this file except in compliance with the License.
# # You may obtain a copy of the License at
# #
# #     http://www.apache.org/licenses/LICENSE-2.0
# #
# # Unless required by applicable law or agreed to in writing, software
# # distributed under the License is distributed on an "AS IS" BASIS,
# # WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# # See the License for the specific language governing permissions and
# # limitations under the License.
# """Common setup and fixtures for the pytest suite used by this service."""
# import asyncio
# import datetime
# import json
# import os
# import random
# import time
# from contextlib import contextmanager

# import business_model_migrations
# import pytest
# import requests
# from flask import Flask, current_app
# from flask_migrate import Migrate, upgrade
# from business_filer import db as _db
# from flask_jwt_oidc import JwtManager
# # from business_filer import jwt as _jwt
# from ldclient.integrations.test_data import TestData
# from sqlalchemy import event, text
# from sqlalchemy.schema import DropConstraint, MetaData
# from testcontainers.postgres import PostgresContainer

# from business_filer.config import TestConfig
# from business_filer import create_app

# from . import FROZEN_DATETIME

# postgres = PostgresContainer("postgres:16-alpine")

# @contextmanager
# def not_raises(exception):
#     """Corallary to the pytest raises builtin.

#     Assures that an exception is NOT thrown.
#     """
#     try:
#         yield
#     except exception:
#         raise pytest.fail(f'DID RAISE {exception}')


# # fixture to freeze utcnow to a fixed date-time
# @pytest.fixture
# def freeze_datetime_utcnow(monkeypatch):
#     """Fixture to return a static time for utcnow()."""
#     class _Datetime:
#         @classmethod
#         def utcnow(cls):
#             return FROZEN_DATETIME

#     monkeypatch.setattr(datetime, 'datetime', _Datetime)


# # @pytest.fixture(scope='session')
# # def app():
# #     """Return a session-wide application configured in TEST mode."""
# #     # _app = create_app('testing')
# #     _app = Flask(__name__)
# #     _app.config.from_object(get_named_config('testing'))
# #     _db.init_app(_app)

# #     return _app


# @pytest.fixture(scope="session")
# def ld(request):
#     """LaunchDarkly TestData source."""
#     td = TestData.data_source()
#     with open("flags.json") as file:
#         data = file.read()
#         test_flags: dict[str, dict] = json.loads(data)
#         for flag_name, flag_value in test_flags["flagValues"].items():
#             # NOTE: should check if isinstance dict and if so, apply each variation
#             td.update(td.flag(flag_name).variation_for_all(flag_value))
#     yield td


# @pytest.fixture(scope="session")
# def app(ld):
#     """Return a session-wide application configured in TEST mode."""
#     _app = create_app("testing", ld_test_data=ld)

#     with _app.app_context():
#         yield _app


# @pytest.fixture
# def config(app):
#     """Return the application config."""
#     return app.config


# @pytest.fixture(scope='session')
# def client(app):  # pylint: disable=redefined-outer-name
#     """Return a session-wide Flask test client."""
#     return app.test_client()


# @pytest.fixture(scope='session')
# def jwt(app):
#     """Return a session-wide jwt manager."""
#     _jwt = JwtManager()
#     def get_roles(a_dict):
#         return a_dict['realm_access']['roles']  # pragma: no cover
#     app.config['JWT_ROLE_CALLBACK'] = get_roles
#     _jwt.init_app(app)

#     return _jwt


# @pytest.fixture(scope='session')
# def client_ctx(app):  # pylint: disable=redefined-outer-name
#     """Return session-wide Flask test client."""
#     with app.test_client() as _client:
#         yield _client


# @pytest.fixture(scope='function')
# def account(app):
#     """Create an account to be used for testing."""
#     import uuid
#     from business_filer.services import AccountService
#     with app.app_context():
#         account_url = current_app.config.get('ACCOUNT_SVC_AFFILIATE_URL')
#         account_url = account_url[:account_url.rfind('{') - 1]

#         org_data = json.dumps({'name': str(uuid.uuid4())})
#         token = AccountService.get_bearer_token()

#         # with app.app_context():
#         rv = requests.post(
#             url=account_url,
#             data=org_data,
#             headers={**AccountService.CONTENT_TYPE_JSON,
#                      'Authorization': AccountService.BEARER + token},
#             timeout=20
#         )

#         account_id = rv.json()['id']

#         yield account_id

#         rv = requests.delete(url=f'{account_url}/{account_id}',
#                              headers={'Authorization': AccountService.BEARER + token},
#                              timeout=20
#                              )
#         print(rv)


# @pytest.fixture(scope='function')
# def client_id():
#     """Return a unique client_id that can be used in tests."""
#     _id = random.SystemRandom().getrandbits(0x58)
# #     _id = (base64.urlsafe_b64encode(uuid.uuid4().bytes)).replace('=', '')

#     return f'client-{_id}'

# @pytest.fixture(scope="session", autouse=True)
# def database(request):
#     postgres.start()

#     def remove_container():
#         postgres.stop()

#     request.addfinalizer(remove_container)

# @pytest.fixture(scope='session')
# def session(database, app):
#     """Clear DB and build tables"""
#     # POSTGRES_URL = get_db_uri()
#     # engine = create_engine(POSTGRES_URL)

#     # # create tables
#     # Base.metadata.drop_all(engine)
#     # Base.metadata.create_all(engine)

#     # Session = sessionmaker(bind=engine)
#     # session = Session()
    
#     # yield session
    
#     # # cleanup
#     # session.close()
#     # Base.metadata.drop_all(engine)

#     # with app.app_context():
#     # database_uri=app.config.get("SQLALCHEMY_DATABASE_URI")
#     # engine = create_engine(POSTGRES_URL)
#     # Session = sessionmaker(bind=engine)

#     try:
#         the_path = business_model_migrations.__file__
#         dir_path = os.path.dirname(business_model_migrations.__file__)

#         Migrate(app, _db, directory=dir_path)
#         upgrade()
#     except Exception as err:
#         print(err)

#     sess = _db.session()
#     sess.execute(text("SET TIME ZONE 'UTC';"))

#     yield sess
    

# # @pytest.fixture(scope='session')
# # def db(app):  # pylint: disable=redefined-outer-name, invalid-name
# #     """Return a session-wide initialised database.

# #     Drops all existing tables - Meta follows Postgres FKs
# #     """
# #     with app.app_context():
# #         # Clear out any existing tables
# #         metadata = MetaData(_db.engine)
# #         metadata.reflect()
# #         metadata.drop_all()
# #         _db.drop_all()

# #         sequence_sql = """SELECT sequence_name FROM information_schema.sequences
# #                           WHERE sequence_schema='public'
# #                        """

# #         sess = _db.session()
# #         for seq in [name for (name,) in sess.execute(text(sequence_sql))]:
# #             try:
# #                 sess.execute(text('DROP SEQUENCE public.%s ;' % seq))
# #                 print('DROP SEQUENCE public.%s ' % seq)
# #             except Exception as err:  # pylint: disable=broad-except
# #                 print(f'Error: {err}')
# #         sess.commit()

# #         # ############################################
# #         # There are 2 approaches, an empty database, or the same one that the app will use
# #         #     create the tables
# #         #     _db.create_all()
# #         # or
# #         # Use Alembic to load all of the DB revisions including supporting lookup data
# #         # This is the path we'll use in legal_api!!

# #         # even though this isn't referenced directly, it sets up the internal configs that upgrade needs
# #         legal_api_dir = os.path.abspath('..').replace('queue_services', 'legal-api')
# #         legal_api_dir = os.path.join(legal_api_dir, 'migrations')
# #         Migrate(app, _db, directory=legal_api_dir)
# #         upgrade()

# #         return _db


# # @pytest.fixture(scope='function')
# # def session(app, db):  # pylint: disable=redefined-outer-name, invalid-name
# #     """Return a function-scoped session."""
# #     with app.app_context():
# #         conn = db.engine.connect()
# #         txn = conn.begin()

# #         options = dict(bind=conn, binds={})
# #         sess = db.create_scoped_session(options=options)

# #         # For those who have local databases on bare metal in local time.
# #         # Otherwise some of the returns will come back in local time and unit tests will fail.
# #         # The current DEV database uses UTC.
# #         sess.execute("SET TIME ZONE 'UTC';")
# #         sess.commit()

# #         # establish  a SAVEPOINT just before beginning the test
# #         # (http://docs.sqlalchemy.org/en/latest/orm/session_transaction.html#using-savepoint)
# #         sess.begin_nested()

# #         @event.listens_for(sess(), 'after_transaction_end')
# #         def restart_savepoint(sess2, trans):  # pylint: disable=unused-variable
# #             # Detecting whether this is indeed the nested transaction of the test
# #             if trans.nested and not trans._parent.nested:  # pylint: disable=protected-access
# #                 # Handle where test DOESN'T session.commit(),
# #                 sess2.expire_all()
# #                 sess.begin_nested()

# #         db.session = sess

# #         sql = text('select 1')
# #         sess.execute(sql)

# #         yield sess

# #         # Cleanup
# #         sess.remove()
# #         # This instruction rollsback any commit that were executed in the tests.
# #         txn.rollback()
# #         conn.close()


# @pytest.fixture
# def create_mock_coro(mocker, monkeypatch):
#     """Return a mocked coroutine, and optionally patch-it in."""
#     def _create_mock_patch_coro(to_patch=None):
#         mock = mocker.Mock()

#         async def _coro(*args, **kwargs):
#             return mock(*args, **kwargs)

#         if to_patch:  # <-- may not need/want to patch anything
#             monkeypatch.setattr(to_patch, _coro)
#         return mock, _coro

#     return _create_mock_patch_coro
