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
from enum import Enum

from .expression_reflector import VersionExpressionReflector
from .utils import adapt_columns, version_class


class Operation(Enum):
    INSERT = 0
    UPDATE = 1
    DELETE = 2


class RelationshipBuilder(object):
    def __init__(self, model, property_):
        self.property = property_
        self.model = model

    def one_to_many_subquery(self, obj):
        tx_column = "transaction_id"

        remote_alias = sa.orm.aliased(self.remote_cls)
        primary_keys = [
            getattr(remote_alias, column.name) for column
            in sa.inspect(remote_alias).mapper.columns
            if column.primary_key and column.name != tx_column
        ]

        return sa.exists(
            sa.select(1).where(
                sa.and_(
                    getattr(remote_alias, tx_column) <=
                    getattr(obj, tx_column),
                    *[
                        getattr(remote_alias, pk.name) ==
                        getattr(self.remote_cls, pk.name)
                        for pk in primary_keys
                    ]
                )
            ).group_by(
                *primary_keys
            ).having(
                sa.func.max(getattr(remote_alias, tx_column)) ==
                getattr(self.remote_cls, tx_column)
            ).correlate(self.local_cls, self.remote_cls)
        )

    def many_to_one_subquery(self, obj):
        tx_column = "transaction_id"
        reflector = VersionExpressionReflector(obj, self.property)
        subquery = sa.select(
            sa.func.max(getattr(self.remote_cls, tx_column))
        ).where(
            sa.and_(
                getattr(self.remote_cls, tx_column) <=
                getattr(obj, tx_column),
                reflector(self.property.primaryjoin)
            )
        )
        subquery = subquery.scalar_subquery()

        return getattr(self.remote_cls, tx_column) == subquery

    def query(self, obj):
        session = sa.orm.object_session(obj)
        return (
            session.query(self.remote_cls)
            .filter(
                self.criteria(obj)
            )
        )

    def process_query(self, query):
        """
        Process given SQLAlchemy Query object depending on the associated
        RelationshipProperty object.

        :param query: SQLAlchemy Query object
        """
        if self.property.lazy == 'dynamic':
            return query
        if self.property.uselist is False:
            return query.first()
        return query.all()

    def criteria(self, obj):
        direction = self.property.direction

        if self.versioned:
            if direction.name == 'ONETOMANY':
                return self.one_to_many_criteria(obj)
            # TODO: Get many-to-many relationships working
            # elif direction.name == 'MANYTOMANY':
            #     return self.many_to_many_criteria(obj)
            elif direction.name == 'MANYTOONE':
                return self.many_to_one_criteria(obj)
        else:
            reflector = VersionExpressionReflector(obj, self.property)
            return reflector(self.property.primaryjoin)

    def many_to_many_criteria(self, obj):
        """
        Returns the many-to-many query.

        Looks up remote items through associations and for each item returns
        returns the last version with a transaction less than or equal to the
        transaction of `obj`. This must hold true for both the association and
        the remote relation items.

        Example
        -------
        Select all tags of article with id 3 and transaction 5

        .. code-block:: sql

        SELECT tags_version.*
        FROM tags_version
        WHERE EXISTS (
            SELECT 1
            FROM article_tag_version
            WHERE article_id = 3
            AND tag_id = tags_version.id
            AND operation_type != 2
            AND EXISTS (
                SELECT 1
                FROM article_tag_version as article_tag_version2
                WHERE article_tag_version2.tag_id = article_tag_version.tag_id
                AND article_tag_version2.tx_id <= 5
                GROUP BY article_tag_version2.tag_id
                HAVING
                    MAX(article_tag_version2.tx_id) =
                    article_tag_version.tx_id
            )
        )
        AND EXISTS (
            SELECT 1
            FROM tags_version as tags_version_2
            WHERE tags_version_2.id = tags_version.id
            AND tags_version_2.tx_id <= 5
            GROUP BY tags_version_2.id
            HAVING MAX(tags_version_2.tx_id) = tags_version.tx_id
        )
        AND operation_type != 2
        """
        return sa.and_(
            self.association_subquery(obj),
            self.one_to_many_subquery(obj),
            self.remote_cls.operation_type != Operation.DELETE.value
        )

    def many_to_one_criteria(self, obj):
        """Returns the many-to-one query.

        Returns the item on the 'one' side with the highest transaction id
        as long as it is less or equal to the transaction id of the `obj`.

        Example
        -------
        Look up the Article of a Tag with article_id = 4 and
        transaction_id = 5

        .. code-block:: sql

        SELECT *
        FROM articles_version
        WHERE id = 4
        AND transaction_id = (
            SELECT max(transaction_id)
            FROM articles_version
            WHERE transaction_id <= 5
            AND id = 4
        )
        AND operation_type != 2

        """
        reflector = VersionExpressionReflector(obj, self.property)
        return sa.and_(
            reflector(self.property.primaryjoin),
            self.many_to_one_subquery(obj),
            self.remote_cls.operation_type != Operation.DELETE.value
        )

    def one_to_many_criteria(self, obj):
        """
        Returns the one-to-many query.

        For each item on the 'many' side, returns its latest version as long as
        the transaction of that version is less than equal of the transaction
        of `obj`.

        Example
        -------
        Using the Article-Tags relationship, where we look for tags of
        article_version with id = 3 and transaction = 5 the sql produced is

        .. code-block:: sql

        SELECT tags_version.*
        FROM tags_version
        WHERE tags_version.article_id = 3
        AND tags_version.operation_type != 2
        AND EXISTS (
            SELECT 1
            FROM tags_version as tags_version_last
            WHERE tags_version_last.transaction_id <= 5
            AND tags_version_last.id = tags_version.id
            GROUP BY tags_version_last.id
            HAVING
                MAX(tags_version_last.transaction_id) =
                tags_version.transaction_id
        )

        """
        reflector = VersionExpressionReflector(obj, self.property)
        return sa.and_(
            reflector(self.property.primaryjoin),
            self.one_to_many_subquery(obj),
            self.remote_cls.operation_type != Operation.DELETE.value
        )

    @property
    def reflected_relationship(self):
        """
        Builds a reflected one-to-many, one-to-one and many-to-one
        relationship between two version classes.
        """
        @property
        def relationship(obj):
            query = self.query(obj)
            return self.process_query(query)
        return relationship

    def association_subquery(self, obj):
        """
        Returns an EXISTS clause that checks if an association exists for given
        SQLAlchemy declarative object. This query is used by
        many_to_many_criteria method.

        Example query:

        .. code-block:: sql

        EXISTS (
            SELECT 1
            FROM article_tag_version
            WHERE article_id = 3
            AND tag_id = tags_version.id
            AND operation_type != 2
            AND EXISTS (
                SELECT 1
                FROM article_tag_version as article_tag_version2
                WHERE article_tag_version2.tag_id = article_tag_version.tag_id
                AND article_tag_version2.tx_id <=5
                AND article_tag_version2.article_id = 3
                GROUP BY article_tag_version2.tag_id
                HAVING
                    MAX(article_tag_version2.tx_id) =
                    article_tag_version.tx_id
            )
        )

        :param obj: SQLAlchemy declarative object
        """

        tx_column = "transaction_id"
        join_column = self.property.primaryjoin.right.name
        object_join_column = self.property.primaryjoin.left.name
        reflector = VersionExpressionReflector(obj, self.property)

        association_table_alias = self.association_version_table.alias()
        association_cols = [
            association_table_alias.c[association_col.name]
            for _, association_col
            in self.remote_to_association_column_pairs
        ]

        association_exists = sa.exists(
            sa.select(1).where(
                sa.and_(
                    association_table_alias.c[tx_column] <=
                    getattr(obj, tx_column),
                    association_table_alias.c[join_column] == getattr(obj, object_join_column),
                    *[association_col ==
                      self.association_version_table.c[association_col.name]
                      for association_col
                      in association_cols]
                )
            ).group_by(
                *association_cols
            ).having(
                sa.func.max(association_table_alias.c[tx_column]) ==
                self.association_version_table.c[tx_column]
            ).correlate(self.association_version_table)
        )
        return sa.exists(
            sa.select(1).where(
                sa.and_(
                    reflector(self.property.primaryjoin),
                    association_exists,
                    self.association_version_table.c.operation_type !=
                    Operation.DELETE.value,
                    adapt_columns(self.property.secondaryjoin),
                )
            ).correlate(self.local_cls, self.remote_cls)
        )

    # TODO: Get many-to-many relationships working.
    # def build_association_version_tables(self):
    #     """
    #     Builds many-to-many association version table for given property.
    #     Association version tables are used for tracking change history of
    #     many-to-many associations.
    #     """
    #     column = list(self.property.remote_side)[0]

    #     self.manager.association_tables.add(column.table)
    #     builder = TableBuilder(
    #         self.manager,
    #         column.table
    #     )
    #     metadata = column.table.metadata
    #     if builder.parent_table.schema:
    #         table_name = builder.parent_table.schema + '.' + builder.table_name
    #     elif metadata.schema:
    #         table_name = metadata.schema + '.' + builder.table_name
    #     else:
    #         table_name = builder.table_name

    #     if table_name not in metadata.tables:
    #         self.association_version_table = table = builder()
    #         self.manager.association_version_tables.add(table)
    #     else:
    #         # may have already been created if we visiting the 'other' side of
    #         # a self-referential many-to-many relationship
    #         self.association_version_table = metadata.tables[table_name]

    def __call__(self):
        """
        Builds reflected relationship between version classes based on given
        parent object's RelationshipProperty.
        """
        self.local_cls = version_class(self.model)
        self.versioned = False
        
        if version_class(self.property.mapper.class_):
            self.remote_cls = version_class(self.property.mapper.class_)
            self.versioned = True
        else:
            self.remote_cls = self.property.mapper.class_

        # TODO: Get many-to-many relationships working.
        # if (self.property.secondary is not None and
        #         not self.property.viewonly and
        #         not self.manager.is_excluded_property(
        #             self.model, self.property.key)):
        #     self.build_association_version_tables()

        #     # store remote cls to association table column pairs
        #     self.remote_to_association_column_pairs = []
        #     for column_pair in self.property.local_remote_pairs:
        #         if column_pair[0] in self.property.target.c.values():
        #             self.remote_to_association_column_pairs.append(column_pair)

        setattr(
            self.local_cls,
            self.property.key,
            self.reflected_relationship
        )
