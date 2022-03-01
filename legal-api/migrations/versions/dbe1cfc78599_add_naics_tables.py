"""add_naics_tables

Revision ID: dbe1cfc78599
Revises: 33501a263f32
Create Date: 2022-03-01 06:13:11.004608

"""
from flask import current_app
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql.schema import MetaData, Table
import uuid

from migrations.bulk_data.naics_structures_2017_v3 import naics_structures
from migrations.bulk_data.naics_elements_2017_v3 import naics_elements
from migrations.bulk_data.naics_structures_2017_v3_subset_testing_only import naics_structures_test_only
from migrations.bulk_data.naics_elements_2017_v3_subset_testing_only import naics_elements_test_only

# revision identifiers, used by Alembic.
revision = 'dbe1cfc78599'
down_revision = '33501a263f32'
branch_labels = None
depends_on = None


def upgrade():

    # Notes: bulk dictionary data for naics_structure and naics_element data used for the bulk inserts below were
    # generated via a Jupyter notebook(/lear/tests/data/naics/create_alembic_import_data_from_naics_csvs.ipynb).
    # The dictionary data are imported from migrations.bulk_data to make this migration file more readable and
    # also easier to work with.
    #
    # Different data sets are used to overcome the slow performance of using the actual NAICS dataset for testing
    # purposes.  As such when migrations are performed during test runs, only a small subset of data is used to load
    # the test database for tests.

    is_test_mode = current_app.config.get('TESTING', False)
    print(f'is_test_mode: {is_test_mode}')

    # naics_structures table
    op.create_table('naics_structures',
                    sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
                    sa.Column('naics_key', UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
                    sa.Column('level', sa.Integer(), nullable=False),
                    sa.Column('hierarchical_structure', sa.String(length=25), nullable=False),
                    sa.Column('code', sa.String(length=10), nullable=False),
                    sa.Column('year', sa.Integer(), nullable=False),
                    sa.Column('version', sa.Integer(), nullable=False),
                    sa.Column('class_title', sa.String(length=150), nullable=False),
                    sa.Column('superscript', sa.String(length=5), nullable=True),
                    sa.Column('class_definition', sa.String(length=5100), nullable=False),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_index(op.f('ix_naics_structure_level'), 'naics_structures', ['level'], unique=False)
    op.create_index(op.f('ix_naics_structure_code'), 'naics_structures', ['code'], unique=False)
    op.create_index(op.f('ix_naics_structure_year'), 'naics_structures', ['year'], unique=False)
    op.create_index(op.f('ix_naics_structure_version'), 'naics_structures', ['version'], unique=False)
    op.create_index(op.f('ix_naics_structure_class_title'), 'naics_structures', ['class_title'], unique=False)
    op.create_index(op.f('ix_naics_structure_class_defn'), 'naics_structures', ['class_definition'], unique=False)

    meta = MetaData(bind=op.get_bind())
    meta.reflect(only=('naics_structures',))
    naics_structures_table = Table('naics_structures', meta)

    naics_structures_to_insert = naics_structures_test_only if is_test_mode else naics_structures
    op.bulk_insert(
        naics_structures_table,
        naics_structures_to_insert
    )

    # naics_elements table
    op.create_table('naics_elements',
                    sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
                    sa.Column('level', sa.Integer(), nullable=False),
                    sa.Column('code', sa.String(length=10), nullable=False),
                    sa.Column('year', sa.Integer(), nullable=False),
                    sa.Column('version', sa.Integer(), nullable=False),
                    sa.Column('class_title', sa.String(length=150), nullable=False),
                    sa.Column('element_type',
                              sa.Enum('ALL_EXAMPLES',
                                      'ILLUSTRATIVE_EXAMPLES',
                                      'INCLUSIONS',
                                      'EXCLUSIONS',
                                      name='element_type'),
                              nullable=False),
                    sa.Column('element_description', sa.String(length=500), nullable=False),
                    sa.Column('naics_structure_id', sa.Integer(), nullable=False),
                    sa.ForeignKeyConstraint(['naics_structure_id'], ['naics_structures.id'], ),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_index(op.f('ix_naics_element_level'), 'naics_elements', ['level'], unique=False)
    op.create_index(op.f('ix_naics_element_code'), 'naics_elements', ['code'], unique=False)
    op.create_index(op.f('ix_naics_element_year'), 'naics_elements', ['year'], unique=False)
    op.create_index(op.f('ix_naics_element_version'), 'naics_elements', ['version'], unique=False)
    op.create_index(op.f('ix_naics_element_class_title'), 'naics_elements', ['class_title'], unique=False)
    op.create_index(op.f('ix_naics_element_element_type'), 'naics_elements', ['element_type'], unique=False)
    op.create_index(op.f('ix_naics_element_element_desc'), 'naics_elements', ['element_description'], unique=False)

    meta = MetaData(bind=op.get_bind())
    meta.reflect(only=('naics_elements',))
    naics_elements_table = Table('naics_elements', meta)

    conn = op.get_bind()

    naics_elements_to_insert = naics_elements_test_only if is_test_mode else naics_elements

    # update naics elements data with naics_structure_id by retrieving corresponding naics structure row
    for naics_element in naics_elements_to_insert:
        naics_code = naics_element.get('code')
        select_query = f"select * from naics_structures where code = '{naics_code}'"
        query = conn.execute(select_query)
        naics_structure_result = query.fetchall()[0]
        naics_element['naics_structure_id'] = naics_structure_result.id

    op.bulk_insert(
        naics_elements_table,
        naics_elements_to_insert
    )


def downgrade():
    op.drop_table('naics_elements')
    op.execute("DROP TYPE element_type;")
    op.drop_table('naics_structures')
