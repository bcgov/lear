# Copyright © 2019 Province of British Columbia
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Create Oracle database connection.

These will get initialized by the application.
"""

import cx_Oracle
from flask import current_app, _app_ctx_stack


class OracleDB(object):
    """Oracle database connection object for re-use in application."""

    def __init__(self, app=None):
        """initializer, supports setting the app context on instantiation"""
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Setup for the extension.

        :param app: Flask app
        :return: naked
        """
        self.app = app
        app.teardown_appcontext(self.teardown)

    def teardown(self, exception):
        """Oracle session pool cleans up after itself."""
        ctx = _app_ctx_stack.top
        if hasattr(ctx, 'oracle_pool'):
            ctx.oracle_pool.close()

    def _create_pool(self):
        """Create the cx_oracle connection pool from the Flask Config Environment.

        :return: an instance of the OCI Session Pool
        """
        # this uses the builtin session / connection pooling provided by
        # the Oracle OCI driver
        # setting threaded =True wraps the underlying calls in a Mutex
        # so we don't have to that here

        def InitSession(conn, requestedTag):
            cursor = conn.cursor()
            cursor.execute("alter session set TIME_ZONE = 'America/Vancouver'")

        return cx_Oracle.SessionPool(user=current_app.config.get('ORACLE_USER'),
                                     password=current_app.config.get('ORACLE_PASSWORD'),
                                     dsn='{0}:{1}/{2}'.format(current_app.config.get('ORACLE_HOST'),
                                                              current_app.config.get('ORACLE_PORT'),
                                                              current_app.config.get('ORACLE_DB_NAME')),
                                     min=1,
                                     max=10,
                                     increment=1,
                                     connectiontype=cx_Oracle.Connection,
                                     threaded=True,
                                     getmode=cx_Oracle.SPOOL_ATTRVAL_NOWAIT,
                                     waitTimeout=1500,
                                     timeout=3600,
                                     sessionCallback=InitSession)

    @property
    def connection(self):
        """Connection property of the NROService.

        If this is running in a Flask context,
        then either get the existing connection pool or create a new one
        and then return an acquired session
        :return: cx_Oracle.connection type
        """
        ctx = _app_ctx_stack.top
        if ctx is not None:
            if not hasattr(ctx, 'oracle_pool'):
                ctx._oracle_pool = self._create_pool()
            return ctx._oracle_pool.acquire()


# export instance of this class
db = OracleDB()
