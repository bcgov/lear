# Copyright © 2025 Province of British Columbia
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
import sqlalchemy as sa
from contextlib import suppress


def version_class(obj):
    """Return the version class associated with a model.

    :param obj: The object to get the version class for.
    :return: The version class or None if not found.
    """
    with suppress(Exception):
        versioned_class = obj.__versioned_cls__
        print(f'\033[32mVersioned Class={versioned_class}\033[0m')
        return versioned_class
    return None


def version_table(table):
    """
    Return associated version table for given SQLAlchemy Table object.

    :param table: SQLAlchemy Table object
    """
    if table.schema:
        return table.metadata.tables[
            table.schema + '.' + table.name + '_version'
        ]
    elif table.metadata.schema:
        return table.metadata.tables[
            table.metadata.schema + '.' + table.name + '_version'
        ]
    else:
        return table.metadata.tables[
            table.name + '_version'
        ]


class VersioningClauseAdapter(sa.sql.visitors.ReplacingCloningVisitor):
    def replace(self, col):
        if isinstance(col, sa.Column):
            table = version_table(col.table)
            return table.c.get(col.key)


def adapt_columns(expr):
    return VersioningClauseAdapter().traverse(expr)
