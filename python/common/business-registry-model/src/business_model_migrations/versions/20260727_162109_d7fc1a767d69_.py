"""Add court order metadata

Revision ID: d7fc1a767d69
Revises: 1cdc6fdbf4cf
Create Date: 2026-07-27 16:21:09.583470

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = 'd7fc1a767d69'
down_revision = '1cdc6fdbf4cf'
branch_labels = None
depends_on = None


def upgrade():
    # Add court order data to metadata of filings
    op.execute(
        """
        UPDATE filings f
        SET meta_data = JSONB_SET(meta_data, '{courtOrder}',
                            jsonb_strip_nulls(jsonb_build_object(
                                'fileNumber', co.file_number,
                                'orderDetails', CASE WHEN co.order_details IS NOT NULL AND co.order_details <> '' THEN co.order_details ELSE NULL END,
                                'effectOfOrder', CASE WHEN co.effect_of_order IS NOT NULL AND co.effect_of_order <> '' THEN co.effect_of_order ELSE NULL END
                            ))
                        )
        FROM court_orders co
        WHERE 
            co.filing_id = f.id
        """
    )
    # Add court order filing document to metadata
    op.execute(
        """
        UPDATE filings f
        SET meta_data = JSONB_SET(meta_data, '{courtOrder,files}',
                            jsonb_build_array(
                                jsonb_build_object(
                                    'fileName', concat('Court Order ', co.file_number, '.pdf'),
                                    'fileKey', d.file_key
                                )
                            )
                        )
        FROM court_orders co
            JOIN documents d ON co.filing_id = d.filing_id
        WHERE 
            co.filing_id = f.id AND 
            f.filing_type = 'courtOrder' AND 
            d.type = 'court_order'
        """
    )


def downgrade():
    # Remove court order data from metadata of filings
    op.execute(
        """
        UPDATE filings f
        SET meta_data = JSONB_SET(meta_data, '{courtOrder}', 'jsonb_build_object()')
        FROM court_orders co
        WHERE 
            co.filing_id = f.id
        """
    )
