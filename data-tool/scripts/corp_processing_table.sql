CREATE SEQUENCE IF NOT EXISTS corp_processing_id_seq START WITH 1 INCREMENT BY 1;

create table if not exists corp_processing
(
    id                      integer default nextval('corp_processing_id_seq'::regclass) not null
    constraint pk_corp_processing
    primary key,
    corp_num                varchar(10)                                                 not null
    constraint fk_corp_processing_corporation
    references corporation (corp_num),
    corp_name               varchar(150),
    flow_name               varchar(100)                                                not null,
    processed_status        varchar(25)                                                 not null,
    failed_event_file_type  varchar(25),
    last_processed_event_id integer
    constraint fk_corp_processing_event_0
    references event (event_id),
    failed_event_id         integer
    constraint fk_corp_processing_event
    references event (event_id),
    environment             varchar(25),
    create_date             timestamp with time zone,
    last_modified           timestamp with time zone,
    last_error              varchar(1000),
    claimed_at              timestamp with time zone,
    flow_run_id             uuid,
    corp_type_cd            varchar(3),
    filings_count           integer,
    constraint unq_corp_processing
    unique (corp_num, flow_name, environment)
    );

create index if not exists idx_corp_processing_flow_name
    on corp_processing (flow_name);

create index if not exists idx_corp_processing_last_processed_event_id
    on corp_processing (last_processed_event_id);

create index if not exists idx_corp_processing_processed_status
    on corp_processing (processed_status);

