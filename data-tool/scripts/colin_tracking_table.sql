create sequence IF not exists colin_tracking_id_seq start with 1 INCREMENT by 1;

create table if not exists colin_tracking
(
    id                      integer default nextval('colin_tracking_id_seq'::regclass) not null
        constraint pk_colin_tracking primary key,
    corp_num                varchar(10)                                                 not null
        constraint fk_colin_tracking_corporation references corporation (corp_num),
    corp_type_cd            varchar(3),
    frozen                  boolean default False,
	in_early_adopter        boolean default False,
    environment             varchar(25),
    create_date             timestamp with time zone default CURRENT_TIMESTAMP,
    last_modified           timestamp with time zone default CURRENT_TIMESTAMP,
    claimed_at              timestamp with time zone default CURRENT_TIMESTAMP,
    flow_name               varchar(100)                                                not null,
    flow_run_id             uuid,
    processed_status        varchar(25)                                                 not null,
    last_error                   varchar(1000),
    batch_id                integer,                                                    -- placeholder FK

    constraint unq_colin_tracking unique (corp_num, flow_name, environment)
);
