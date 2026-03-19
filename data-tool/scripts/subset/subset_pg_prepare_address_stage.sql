-- Prepare the shared address staging table used by subset_transfer_chunk.sql.
-- This is a regular table (not TEMP) because DbSchemaCLI transfer work may use separate sessions.

DROP TABLE IF EXISTS public.subset_address_stage;

CREATE TABLE public.subset_address_stage (
    addr_id         numeric(10),
    province        varchar(2),
    country_typ_cd  varchar(2),
    postal_cd       varchar(15),
    addr_line_1     varchar(50),
    addr_line_2     varchar(50),
    addr_line_3     varchar(50),
    city            varchar(40)
);

