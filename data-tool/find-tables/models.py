from dataclasses import dataclass, field
from pprint import pformat
from textwrap import indent

from config import Config


@dataclass
class EventTable:
    filing_type_code: str
    event_ids: list
    child_tables: list = None

    def print(self):
        """Prints the mapping"""
        print("EVENT_IDs used to build mapping:")
        print(self.event_ids, end="\n\n")
        print(f"MAPPING (depth {Config.MAX_MAPPING_DEPTH}):")
        print(f"EVENT ({len(self.event_ids)} entries)")
        for child_table in self.child_tables:
            child_table.print()

    def build_mapping(self, cursor):
        """Get all child tables that reference the event table via foreign keys"""
        self.child_tables = []

        cursor.execute(
            """
            SELECT table_name, column_name
            FROM all_cons_columns
            WHERE constraint_name IN (
                SELECT constraint_name
                FROM all_constraints
                WHERE r_constraint_name IN (
                    SELECT constraint_name
                    FROM all_constraints
                    WHERE table_name=:table_name
                )
            )
            """,
            table_name="EVENT",
        )

        # Only get tables that have fk values in filing_ids_with_typ_cd
        for table_name, column_name in cursor.fetchall():
            stmt = (
                f"SELECT * FROM {table_name} WHERE {column_name} IN ("
                + ",".join(str(eid) for eid in self.event_ids)
                + ")"
            )
            cursor.execute(stmt)
            columns = [col[0] for col in cursor.description]
            cursor.rowfactory = lambda *args: dict(zip(columns, args))
            results = cursor.fetchall()
            if len(results) > 0:
                child_table = ChildTable(
                    table_name=table_name,
                    fk_column_to_parent=column_name,
                    rows=results,
                )
                child_table.recursive_set_child_tables(cursor)
                self.child_tables.append(child_table)


@dataclass
class ChildTable:
    table_name: str
    fk_column_to_parent: str
    rows: list
    num_rows: int = field(init=False)
    depth: int = 1
    child_tables: list = field(init=False)

    def __post_init__(self):
        self.num_rows = len(self.rows)
        self.child_tables = []

    def print(self):
        """Prints the mapping"""
        pad = "\t" * self.depth
        print(
            f"{pad}{self.table_name} ({self.num_rows} entries) on {self.fk_column_to_parent}"
        )
        if Config.VERBOSE and self.table_name != "EVENT":
            print(indent(pformat(self.rows, compact=True), pad))
        for child_table in self.child_tables:
            child_table.print()

    def recursive_set_child_tables(self, cursor):
        """Get all tables that this table references via foreign keys"""
        if self.depth >= Config.MAX_MAPPING_DEPTH:
            return

        cursor.execute(
            """
            SELECT table_name, column_name
            FROM all_cons_columns
            WHERE constraint_name IN (
                SELECT c_pk.constraint_name
                FROM all_cons_columns a
                JOIN all_constraints c ON a.owner=c.owner AND a.constraint_name=c.constraint_name
                JOIN all_constraints c_pk ON c.r_owner=c_pk.owner AND c.r_constraint_name=c_pk.constraint_name
                WHERE c.constraint_type='R' AND a.table_name=:table_name
            )
            """,
            table_name=self.table_name,
        )

        # Get only foreign keys with ids in fk_ids array
        for table_name, column_name in cursor.fetchall():
            if column_name not in self.rows[0]:
                print(
                    f"Could not find column {column_name} in table {self.table_name}."
                )
                continue

            column_vals = set(r[column_name] for r in self.rows)
            in_stmt = ",".join(f"'{cv}'" for cv in column_vals if cv is not None)
            if not in_stmt:
                print(f"Only NULL values for {column_name} in table {self.table_name}.")
                continue

            stmt = (
                f"SELECT * FROM {table_name} WHERE {column_name} IN (" + in_stmt + ")"
            )
            cursor.execute(stmt)
            columns = [col[0] for col in cursor.description]
            cursor.rowfactory = lambda *args: dict(zip(columns, args))
            results = cursor.fetchall()
            if len(results) > 0:
                child_table = ChildTable(
                    table_name=table_name,
                    fk_column_to_parent=column_name,
                    rows=results,
                    depth=self.depth + 1,
                )
                child_table.recursive_set_child_tables(cursor)
                self.child_tables.append(child_table)
