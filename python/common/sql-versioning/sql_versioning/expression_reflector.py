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
from sqlalchemy.sql.expression import bindparam

from .utils import version_table


class VersionExpressionReflector(sa.sql.visitors.ReplacingCloningVisitor):
    def __init__(self, parent, relationship):
        self.parent = parent
        self.relationship = relationship

    def replace(self, column):
        if not isinstance(column, sa.Column):
            return
        try:
            table = version_table(column.table)
        except KeyError:
            reflected_column = column
        else:
            reflected_column = table.c[column.name]
            if (
                column in self.relationship.local_columns and
                table == self.parent.__table__
            ):
                reflected_column = bindparam(
                    column.key,
                    getattr(self.parent, column.key)
                )

        return reflected_column

    def __call__(self, expr):
        return self.traverse(expr)
