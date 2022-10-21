CREATE SEQUENCE IF NOT EXISTS affiliation_processing_id_seq START WITH 1 INCREMENT BY 1;

CREATE TABLE IF NOT EXISTS affiliation_processing (
    id                   integer DEFAULT nextval('affiliation_processing_id_seq'::regclass) NOT NULL  ,
    account_id           integer  NOT NULL  ,
    contact_name         varchar(150)    ,
    contact_email        varchar(150)    ,
    corp_num             varchar(10)  NOT NULL  ,
    corp_name            varchar(150)    ,
    notes                varchar(600)    ,
    environment          varchar(25)  NOT NULL  ,
    processed_status     varchar(25) DEFAULT 'NOT_PROCESSED' NOT NULL  ,
    create_date          timestamptz DEFAULT CURRENT_TIMESTAMP NOT NULL  ,
    last_modified        timestamptz    ,
    last_error           varchar(1000)    ,
    CONSTRAINT pk_affiliation_processing PRIMARY KEY ( id ),
    CONSTRAINT unq_affiliation_processing UNIQUE ( account_id, corp_num, environment )
    );

ALTER TABLE affiliation_processing ADD CONSTRAINT fk_affiliation_processing_corporation FOREIGN KEY ( corp_num ) REFERENCES corporation( corp_num );
