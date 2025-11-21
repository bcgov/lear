# Copyright © 2024 Province of British Columbia
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
"""PostgresDB data type utilities."""
from sqlalchemy.types import UserDefinedType


class PostgreSQLXML(UserDefinedType):
    """
    A custom SQLAlchemy type to handle PostgreSQL's XML data type.

    This class allows SQLAlchemy to store and retrieve XML data in PostgreSQL databases.
    It provides methods to bind and process data when inserting into or querying from the database.

    Example usage:
        class MyModel(Base):
            __tablename__ = 'my_model'
            id = Column(Integer, primary_key=True)
            payload = Column(PostgreSQLXML(), nullable=False)
    """

    def get_col_spec(self):
        """
        Return the column type specification.

        This method returns the string 'XML' to indicate that the column should store XML data.
        """
        return "XML"

    def bind_processor(self, dialect):
        """
        Return a processor for binding values to the database.

        Args:
            dialect: The database dialect being used.
        Returns:
            A function that processes the value to be stored in the database. In this case, the function
            returns the value unchanged, as no special processing is needed.
        """
        def process(value):
            return value
        return process

    def result_processor(self, dialect, coltype):
        """
        Return a processor for retrieving values from the database.

        Args:
            dialect: The database dialect being used.
            coltype: The column type.
        Returns:
            A function that processes the value retrieved from the database. In this case, the function
            returns the value unchanged, as no special processing is needed.
        """
        def process(value):
            return value
        return process
