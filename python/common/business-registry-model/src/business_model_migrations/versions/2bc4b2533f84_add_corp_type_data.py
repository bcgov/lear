"""add corp type table

Revision ID: b7c4b2533f84
Revises: 1fcdb213657d
Create Date: 2021-06-19 04:49:53.498323

"""
from alembic import op
from sqlalchemy.sql.schema import MetaData, Table

# revision identifiers, used by Alembic.
revision = '2bc4b2533f84'
down_revision = '1a45bff11567'
branch_labels = None
depends_on = None


def upgrade():
    # meta = MetaData(bind=op.get_bind())
    # meta.reflect(only=('corp_types',))
    # corp_types_table = Table('corp_types', meta)

    bind = op.get_bind()
    meta = MetaData()
    corp_types_table = Table('corp_types', meta, autoload_with=bind)

    op.bulk_insert(
        corp_types_table,
        [
            {'corp_type_cd': 'A', 'colin_ind': 'Y', 'corp_class': 'XPRO', 'short_desc': 'EXTRA PRO', 'full_desc': 'Extraprovincial Company', 'legislation': 'BC Business Corporations Act'},
            {'corp_type_cd': 'B', 'colin_ind': 'Y', 'corp_class': 'XPRO', 'short_desc': 'EXTRA PRO', 'full_desc': 'Extraprovincial Company', 'legislation': 'BC Business Corporations Act'},
            {'corp_type_cd': 'BC', 'colin_ind': 'Y', 'corp_class': 'BC', 'short_desc': 'BC COMPANY', 'full_desc': 'BC Limited Company', 'legislation': 'BC Business Corporations Act'},
            {'corp_type_cd': 'C', 'colin_ind': 'Y', 'corp_class': 'BC', 'short_desc': 'CONTINUE IN', 'full_desc': 'BC Limited Company', 'legislation': 'BC Business Corporations Act'},
            {'corp_type_cd': 'CBEN', 'colin_ind': 'Y', 'corp_class': 'BC', 'short_desc': 'CONTINUE IN', 'full_desc': 'CONTINUE IN BEN', 'legislation': 'BC Business Corporations Act'},
            {'corp_type_cd': 'CEM', 'colin_ind': 'N', 'corp_class': 'OT', 'short_desc': 'CEMETARY', 'full_desc': 'Cemetary', 'legislation': ''},
            {'corp_type_cd': 'CP', 'colin_ind': 'N', 'corp_class': 'OT', 'short_desc': 'COOP', 'full_desc': 'BC Cooperative Association', 'legislation': 'BC Cooperative Association Act'},
            {'corp_type_cd': 'EPR', 'colin_ind': 'Y', 'corp_class': 'XPRO', 'short_desc': 'EXTRA PRO REG', 'full_desc': 'Extraprovincial Registration', 'legislation': ''},
            {'corp_type_cd': 'FOR', 'colin_ind': 'Y', 'corp_class': 'XPRO', 'short_desc': 'FOREIGN', 'full_desc': 'Foreign Registration', 'legislation': ''},
            {'corp_type_cd': 'LIC', 'colin_ind': 'Y', 'corp_class': 'XPRO', 'short_desc': 'LICENSED', 'full_desc': 'Licensed (Extra-Pro)', 'legislation': ''},
            {'corp_type_cd': 'LIB', 'colin_ind': 'N', 'corp_class': 'OT', 'short_desc': 'LIBRARY', 'full_desc': 'Public Library Association', 'legislation': ''},
            {'corp_type_cd': 'LLC', 'colin_ind': 'Y', 'corp_class': 'XPRO', 'short_desc': 'LIMITED CO', 'full_desc': 'Limited Liability Company', 'legislation': 'BC Business Corporations Act'},
            {'corp_type_cd': 'PA', 'colin_ind': 'N', 'corp_class': 'OT', 'short_desc': 'PRIVATE ACT', 'full_desc': 'Private Act', 'legislation': 'Private Act'},
            {'corp_type_cd': 'PAR', 'colin_ind': 'N', 'corp_class': 'OT', 'short_desc': 'PARISHES', 'full_desc': 'Parishes', 'legislation': 'BC Partnership Act'},
            {'corp_type_cd': 'PFS', 'colin_ind': 'N', 'corp_class': 'OT', 'short_desc': 'PENS FUND SOC', 'full_desc': 'Pension Funded Society', 'legislation': ''},
            {'corp_type_cd': 'QA', 'colin_ind': 'Y', 'corp_class': 'BC', 'short_desc': 'CO 1860', 'full_desc': 'CO 1860', 'legislation': ''},
            {'corp_type_cd': 'QB', 'colin_ind': 'Y', 'corp_class': 'BC', 'short_desc': 'CO 1862', 'full_desc': 'CO 1862', 'legislation': ''},
            {'corp_type_cd': 'QC', 'colin_ind': 'Y', 'corp_class': 'BC', 'short_desc': 'CO 1878', 'full_desc': 'CO 1878', 'legislation': ''},
            {'corp_type_cd': 'QD', 'colin_ind': 'Y', 'corp_class': 'BC', 'short_desc': 'CO 1890', 'full_desc': 'CO 1890', 'legislation': ''},
            {'corp_type_cd': 'QE', 'colin_ind': 'Y', 'corp_class': 'BC', 'short_desc': 'CO 1897', 'full_desc': 'CO 1897', 'legislation': ''},
            {'corp_type_cd': 'REG', 'colin_ind': 'Y', 'corp_class': 'XPRO', 'short_desc': 'REGISTRATION', 'full_desc': 'Registraton (Extra-pro)', 'legislation': 'BC Business Corporations Act'},
            {'corp_type_cd': 'RLY', 'colin_ind': 'N', 'corp_class': 'OT', 'short_desc': 'RAILWAYS', 'full_desc': 'Railways', 'legislation': ''},
            {'corp_type_cd': 'SB', 'colin_ind': 'N', 'corp_class': 'OT', 'short_desc': 'SOCIETY BRANCH', 'full_desc': 'Society Branch', 'legislation': ''},
            {'corp_type_cd': 'T', 'colin_ind': 'N', 'corp_class': 'OT', 'short_desc': 'TRUST', 'full_desc': 'Trust', 'legislation': 'BC Partnership Act'},
            {'corp_type_cd': 'TMY', 'colin_ind': 'N', 'corp_class': 'OT', 'short_desc': 'TRAMWAYS', 'full_desc': 'Tramways', 'legislation': ''},
            {'corp_type_cd': 'XCP', 'colin_ind': 'N', 'corp_class': 'OT', 'short_desc': 'XPRO COOP', 'full_desc': 'Extraprovincial Cooperative Association', 'legislation': 'BC Cooperative Association Act'},
            {'corp_type_cd': 'ULC', 'colin_ind': 'Y', 'corp_class': 'BC', 'short_desc': 'BC ULC COMPANY', 'full_desc': 'BC Unlimited Liability Company', 'legislation': 'BC Business Corporations Act'},
            {'corp_type_cd': 'CUL', 'colin_ind': 'Y', 'corp_class': 'BC', 'short_desc': 'ULC CONTINUE IN', 'full_desc': 'Continuation In as a BC ULC', 'legislation': 'BC Business Corporations Act'},
            {'corp_type_cd': 'UQA', 'colin_ind': 'Y', 'corp_class': 'BC', 'short_desc': 'ULC CO 1860', 'full_desc': 'ULC CO 1860', 'legislation': ''},
            {'corp_type_cd': 'UQB', 'colin_ind': 'Y', 'corp_class': 'BC', 'short_desc': 'ULC CO 1862', 'full_desc': 'ULC CO 1862', 'legislation': ''},
            {'corp_type_cd': 'UQC', 'colin_ind': 'Y', 'corp_class': 'BC', 'short_desc': 'ULC CO 1878', 'full_desc': 'ULC CO 1878', 'legislation': ''},
            {'corp_type_cd': 'UQD', 'colin_ind': 'Y', 'corp_class': 'BC', 'short_desc': 'ULC CO 1890', 'full_desc': 'ULC CO 1890', 'legislation': ''},
            {'corp_type_cd': 'UQE', 'colin_ind': 'Y', 'corp_class': 'BC', 'short_desc': 'ULC CO 1897', 'full_desc': 'ULC CO 1897', 'legislation': ''},
            {'corp_type_cd': 'CC', 'colin_ind': 'Y', 'corp_class': 'BC', 'short_desc': 'BC CCC', 'full_desc': 'BC Community Contribution Company', 'legislation': 'BC Business Corporations Act'},
            {'corp_type_cd': 'CCC', 'colin_ind': 'Y', 'corp_class': 'BC', 'short_desc': 'CCC CONTINUE IN', 'full_desc': 'BC Community Contribution Company', 'legislation': 'BC Business Corporations Act'},
            {'corp_type_cd': 'S', 'colin_ind': 'Y', 'corp_class': 'SOC', 'short_desc': 'SOCIETY', 'full_desc': 'Society', 'legislation': 'BC Societies Act'},
            {'corp_type_cd': 'XS', 'colin_ind': 'Y', 'corp_class': 'SOC', 'short_desc': 'XPRO SOCIETY', 'full_desc': 'Extraprovincial Society', 'legislation': 'BC Societies Act'},
            {'corp_type_cd': 'SP', 'colin_ind': 'Y', 'corp_class': 'FIRM', 'short_desc': 'SOLE PROP', 'full_desc': 'Sole Proprietorship', 'legislation': 'BC Partnership Act'},
            {'corp_type_cd': 'GP', 'colin_ind': 'Y', 'corp_class': 'FIRM', 'short_desc': 'PARTNERSHIP', 'full_desc': 'General Partnership', 'legislation': 'BC Partnership Act'},
            {'corp_type_cd': 'LP', 'colin_ind': 'Y', 'corp_class': 'FIRM', 'short_desc': 'LIM PARTNERSHIP', 'full_desc': 'Limited Partnership', 'legislation': 'BC Partnership Act'},
            {'corp_type_cd': 'XP', 'colin_ind': 'Y', 'corp_class': 'FIRM', 'short_desc': 'XPRO LIM PARTNR', 'full_desc': 'Extraprovincial Limited Partnership', 'legislation': 'BC Partnership Act'},
            {'corp_type_cd': 'LL', 'colin_ind': 'Y', 'corp_class': 'FIRM', 'short_desc': 'LL PARTNERSHIP', 'full_desc': 'Limited Liability Partnership', 'legislation': 'BC Partnership Act'},
            {'corp_type_cd': 'XL', 'colin_ind': 'Y', 'corp_class': 'FIRM', 'short_desc': 'XPRO LL PARTNR', 'full_desc': 'Extrapro Limited Liability Partnership', 'legislation': 'BC Partnership Act'},
            {'corp_type_cd': 'MF', 'colin_ind': 'Y', 'corp_class': 'FIRM', 'short_desc': 'MISC FIRM', 'full_desc': 'Miscellaneous Firm', 'legislation': 'BC Partnership Act'},
            {'corp_type_cd': 'FI', 'colin_ind': 'N', 'corp_class': 'OT', 'short_desc': 'FINANCIAL', 'full_desc': 'Financial Institutions', 'legislation': 'Credit Union Incorporation Act'},
            {'corp_type_cd': 'CS', 'colin_ind': 'Y', 'corp_class': 'SOC', 'short_desc': 'CONT IN SOCIETY', 'full_desc': 'Society', 'legislation': 'BC Societies Act'},
            {'corp_type_cd': 'BEN', 'colin_ind': 'Y', 'corp_class': 'BC', 'short_desc': 'BENEFIT COMPANY', 'full_desc': 'BC Benefit Company', 'legislation': 'BC Business Corporations Act'}
        ]
    )


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    # ### end Alembic commands ###
    pass
