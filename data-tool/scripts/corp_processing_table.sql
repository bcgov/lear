CREATE SEQUENCE IF NOT EXISTS corp_processing_id_seq START WITH 1 INCREMENT BY 1;

CREATE TABLE IF NOT EXISTS corp_processing (
    id                   integer DEFAULT nextval('corp_processing_id_seq'::regclass) NOT NULL  ,
    corp_num             varchar(10)  NOT NULL  ,
    corp_name            varchar(150)    ,
    flow_name            varchar(100)  NOT NULL  ,
    processed_status     varchar(25)  NOT NULL  ,
    failed_event_file_type varchar(25)    ,
    last_processed_event_id integer    ,
    failed_event_id      integer    ,
    environment          varchar(25)    ,
    create_date          timestamptz    ,
    last_modified        timestamptz    ,
    last_error           varchar(1000)    ,
    CONSTRAINT pk_corp_processing PRIMARY KEY ( id ),
    CONSTRAINT unq_corp_processing UNIQUE ( corp_num, flow_name, environment )
    );

CREATE INDEX IF NOT EXISTS idx_corp_processing_processed_status ON corp_processing  ( processed_status );

ALTER TABLE corp_processing ADD CONSTRAINT fk_corp_processing_corporation FOREIGN KEY ( corp_num ) REFERENCES corporation( corp_num );

ALTER TABLE corp_processing ADD CONSTRAINT fk_corp_processing_event FOREIGN KEY ( failed_event_id ) REFERENCES event( event_id );

ALTER TABLE corp_processing ADD CONSTRAINT fk_corp_processing_event_0 FOREIGN KEY ( last_processed_event_id ) REFERENCES event( event_id );
