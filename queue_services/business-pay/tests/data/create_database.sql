
CREATE TABLE IF NOT EXISTS public.filings (
    id integer NOT NULL,
    filing_date timestamp with time zone,
    filing_type character varying(30),
    filing_sub_type character varying(30),
    filing_json jsonb,
    payment_id character varying(4096),
    transaction_id bigint,
    business_id integer,
    submitter_id integer,
    status character varying(20),
    payment_completion_date timestamp with time zone,
    paper_only boolean,
    completion_date timestamp with time zone,
    effective_date timestamp with time zone,
    source character varying(15),
    parent_filing_id integer,
    payment_status_code character varying(50),
    temp_reg character varying(10),
    payment_account character varying(30),
    court_order_file_number character varying(20),
    court_order_date timestamp with time zone,
    court_order_effect_of_order character varying(500),
    tech_correction_json jsonb,
    colin_only boolean,
    deletion_locked boolean,
    order_details character varying(2000),
    submitter_roles character varying(200),
    meta_data jsonb
);

CREATE SEQUENCE IF NOT EXISTS public.filings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.filings_id_seq OWNED BY public.filings.id;
