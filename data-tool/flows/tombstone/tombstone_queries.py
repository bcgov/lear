def get_unprocessed_corps_query(flow_name, environment, batch_size):
    query = f"""
    select c.corp_num, c.corp_type_cd, cs.state_type_cd, cp.flow_name, cp.processed_status, cp.last_processed_event_id, cp.failed_event_id, cp.failed_event_file_type
    from corporation c
    left outer join corp_state cs
        on cs.corp_num = c.corp_num
    left outer join corp_processing cp
        on cp.corp_num = c.corp_num 
        and cp.flow_name = '{flow_name}'
        and cp.environment = '{environment}'
    where 1 = 1
--    and c.corp_type_cd like 'BC%' -- some are 'Q%'
--    and c.corp_num = 'BC0000621' -- state changes a lot
--    and c.corp_num = 'BC0883637' -- one pary with multiple roles, but werid address_ids, same filing submitter but diff email
--    and c.corp_num = 'BC0046540' -- one share class with multiple series
--    and c.corp_num = 'BC0673578' -- lots of translations
--    and c.corp_num = 'BC0566856' -- single quotes in share structure (format issue - solved)
--    and c.corp_num = 'BC0326163' -- double quotes in corp name, no share structure, city in street additional of party's address
--    and c.corp_num = 'BC0395512' -- long RG, RC addresses
--    and c.corp_num = 'BC0043406' -- lots of directors
--    and c.corp_num in ('BC0326163', 'BC0395512', 'BC0883637') -- TODO: re-migrate issue (can be solved by adding tracking)
--    and c.corp_num = 'BC0870626' -- lots of filings - IA, CoDs, ARs
--      and c.corp_num = 'BC0004969' -- lots of filings - IA, ARs, transition, alteration, COD, COA
--    and c.corp_num = 'BC0002567' -- lots of filings - IA, ARs, transition, COD
--    and c.corp_num in ('BC0068889', 'BC0441359') -- test users mapping
--    and c.corp_num in ('BC0326163', 'BC0046540', 'BC0883637', 'BC0043406', 'BC0068889', 'BC0441359')

--    and c.corp_num in (
--        'BC0472301', 'BC0649417', 'BC0808085', 'BC0803411', 'BC0511226', 'BC0833000', 'BC0343855', 'BC0149266', -- dissolution
--        'BC0548839', 'BC0541207', 'BC0462424', 'BC0021973', -- restoration
--        'BC0034290', -- legacy other
--        'BC0207097', 'BC0693625', 'BC0754041', 'BC0072008', 'BC0355241', 'BC0642237', 'BC0555891', 'BC0308683', -- correction
--        'BC0688906', 'BC0870100', 'BC0267106', 'BC0873461', -- alteration
--        'BC0536998', 'BC0574096', 'BC0663523' -- new mappings of CoA, CoD
        -- TED
--          'BC0812196',                -- amalg - r (with xpro)
--          'BC0870100',                -- amalg - v
--          'BC0747392'                 -- amalg - h
        -- TING
--          'BC0593394',                -- amalg - r (with xpro)
--         'BC0805986', 'BC0561086',   -- amalg - v
--          'BC0543231', 'BC0358476'    -- amalg - h
--    )
    and c.corp_type_cd in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE') -- TODO: update transfer script
    and cs.end_event_id is null
--    and ((cp.processed_status is null or cp.processed_status != 'COMPLETED'))
      and cp.processed_status is null
      and cp.flow_run_id is null
--    and cs.state_type_cd = 'ACT'
--    order by random()
    limit {batch_size}
    """
    return query


def get_total_unprocessed_count_query(flow_name, environment):
    query = f"""
    select count(*)
    from corporation c
    left outer join corp_state cs
        on cs.corp_num = c.corp_num
    left outer join corp_processing cp
        on cp.corp_num = c.corp_num 
        and cp.flow_name = '{flow_name}'
        and cp.environment = '{environment}'
    where 1 = 1
    and cs.end_event_id is null
    and ((cp.processed_status is null or cp.processed_status != 'COMPLETED'))
    """
    return query


def get_corp_users_query(corp_nums: list):
    corp_nums_str = ', '.join([f"'{x}'" for x in corp_nums])
    query = f"""
    select
        u_user_id,
        u_full_name,
        string_agg(event_type_cd || '_' || coalesce(filing_type_cd, 'NULL'), ',') as event_file_types,
        u_first_name,
        u_middle_name,
        u_last_name,
        to_char(
            min(event_timerstamp::timestamp at time zone 'UTC'),
            'YYYY-MM-DD HH24:MI:SSTZH:TZM'
        ) as earliest_event_dt_str,
        min(u_email_addr) as u_email_addr,
        u_role_typ_cd
    from (
    select
        upper(u.user_id) as u_user_id,
        u.last_name as u_last_name,
        u.first_name as u_first_name,
        u.middle_name as u_middle_name,
        e.event_type_cd,
        f.filing_type_cd,
        e.event_timerstamp,
        case
            when u.first_name is null and u.middle_name is null and u.last_name is null then null
            else upper(concat_ws('_', nullif(trim(u.first_name),''), nullif(trim(u.middle_name),''), nullif(trim(u.last_name),'')))
        end as u_full_name,
        u.email_addr as u_email_addr,
        u.role_typ_cd as u_role_typ_cd
    from event e
            left outer join filing f on e.event_id = f.event_id
            left outer join filing_user u on u.event_id = e.event_id
    where 1 = 1
--        and e.corp_num in ('BC0326163', 'BC0046540', 'BC0883637', 'BC0043406', 'BC0068889', 'BC0441359')
        and e.corp_num in ({corp_nums_str})
    ) sub
    group by sub.u_user_id, sub.u_full_name, sub.u_first_name, sub.u_middle_name, sub.u_last_name, sub.u_role_typ_cd
    order by sub.u_user_id;
    """
    return query


def get_business_query(corp_num, suffix):
    query = f"""
    select
        c.corp_num as identifier,
        -- legal_name: current corp_name (latest)
        coalesce(
            (
                select corp_name
                from corp_name
                where 1 = 1
        --		  and corp_num = 'BC0684912' 
        --        and corp_num = 'BC0000621' 
        --        and corp_num = 'BC0088913' 
        --        and corp_num = 'BC0008045'
        --        and corp_num = 'BC0006574'
        --        and corp_num = 'BC0049194'
                and corp_num = '{corp_num}'
                and end_event_id is null
                and corp_name_typ_cd in ('CO', 'NB')
            ), ''
        )  || '{suffix if suffix else ''}' as legal_name,
        corp_type_cd as legal_type,
    -- founding_date
        to_char(
        (case
            when (c.recognition_dts is null and e.event_timerstamp is not null) then e.event_timerstamp
            else c.recognition_dts
        end)::timestamp at time zone 'UTC', 'YYYY-MM-DD HH24:MI:SSTZH:TZM') as founding_date,
    -- state
        (
            select op_state_type_cd
            from corp_state
            where 1 = 1
    --        and corp_num = 'BC0684912' 
    --        and corp_num = 'BC0000621'
    --        and corp_num = 'BC0088913'
    --        and corp_num = 'BC0008045'
    --        and corp_num = 'BC0006574'
    --        and corp_num = 'BC0049194'
            and corp_num = '{corp_num}'
            and end_event_id is null
        ) as state,
    -- tax_id
        case 
            when (c.bn_15 is null or c.bn_15 = '')
                THEN c.bn_9
            else c.bn_15
        end tax_id,
    -- TODO: submitter_userid
    --
        c.send_ar_ind,
        to_char(c.last_ar_filed_dt::timestamp at time zone 'UTC', 'YYYY-MM-DD HH24:MI:SSTZH:TZM') as last_ar_date,
    -- admin_freeze
        case
            when c.corp_frozen_type_cd = 'C'
            then true
            else false
        end admin_freeze
    from corporation c
    left outer join event e on e.corp_num = c.corp_num and e.event_type_cd = 'CONVICORP' -- need to add other event like CONVAMAL, CONVCIN...
    where 1 = 1
    --and c.corp_num = 'BC0684912' -- state - ACT
    --and c.corp_num = 'BC0000621' -- state - HLD
    --and c.corp_num = 'BC0088913' -- frozen - S
    --and c.corp_num = 'BC0008045' -- name - AN
    --and c.corp_num = 'BC0006574' -- no recognition_dts but has CONVICORP, no last_ar_filed_at
    --and c.corp_num = 'BC0049194' -- CONVAML
    and c.corp_num = '{corp_num}'
    --and e.event_timerstamp is null -- use it to check other CONV
    ;
    """
    return query


def get_offices_and_addresses_query(corp_num):
    query = f"""
    select o.corp_num                as o_corp_num,
        o.office_typ_cd           as o_office_typ_cd,
        o.start_event_id          as o_start_event_id,
        o.end_event_id            as o_end_event_id,
        o.mailing_addr_id         as o_mailing_addr_id,
        o.delivery_addr_id        as o_delivery_addr_id,
        -- mailing address
        ma.addr_id                as ma_addr_id,
        ma.province               as ma_province,
        ma.country_typ_cd         as ma_country_typ_cd,
        ma.postal_cd              as ma_postal_cd,
        ma.addr_line_1            as ma_addr_line_1,
        ma.addr_line_2            as ma_addr_line_2,
        ma.addr_line_3            as ma_addr_line_3,
        ma.city                   as ma_city,
--        'BAS'                     as ma_address_format_type,
        ma.delivery_instructions  as ma_delivery_instructions,
        ma.unit_no                as ma_unit_no,
        ma.unit_type              as ma_unit_type,
        ma.civic_no               as ma_civic_no,
        ma.civic_no_suffix        as ma_civic_no_suffix,
        ma.street_name            as ma_street_name,
        ma.street_type            as ma_street_type,
        ma.street_direction       as ma_street_direction,
        ma.lock_box_no            as ma_lock_box_no,
        ma.installation_type      as ma_installation_type,
        ma.installation_name      as ma_installation_name,
        ma.installation_qualifier as ma_installation_qualifier,
        ma.route_service_type     as ma_route_service_type,
        ma.route_service_no       as ma_route_service_no,
        -- delivery address
        da.addr_id                as da_addr_id,
        da.province               as da_province,
        da.country_typ_cd         as da_country_typ_cd,
        da.postal_cd              as da_postal_cd,
        da.addr_line_1            as da_addr_line_1,
        da.addr_line_2            as da_addr_line_2,
        da.addr_line_3            as da_addr_line_3,
        da.city                   as da_city,
--        'BAS'                     as da_address_format_type,
        da.delivery_instructions  as da_delivery_instructions,
        da.unit_no                as da_unit_no,
        da.unit_type              as da_unit_type,
        da.civic_no               as da_civic_no,
        da.civic_no_suffix        as da_civic_no_suffix,
        da.street_name            as da_street_name,
        da.street_type            as da_street_type,
        da.street_direction       as da_street_direction,
        da.lock_box_no            as da_lock_box_no,
        da.installation_type      as da_installation_type,
        da.installation_name      as da_installation_name,
        da.installation_qualifier as da_installation_qualifier,
        da.route_service_type     as da_route_service_type,
        da.route_service_no       as da_route_service_no
    from event e
            join office o on o.start_event_id = e.event_id
            left outer join address ma on o.mailing_addr_id = ma.addr_id
            left outer join address da on o.delivery_addr_id = da.addr_id
    where 1 = 1
--        and e.corp_num = 'BC0043406' -- office_typ_cd: RG, RC, TH, SH
        and e.corp_num = '{corp_num}'
        and o.end_event_id is null
        and o.office_typ_cd in ('RG', 'RC')
    ;
    """
    return query


def get_parties_and_addresses_query(corp_num):
    query = f"""
        select cp.corp_party_id                                              as cp_corp_party_id,
        cp.mailing_addr_id                                                   as cp_mailing_addr_id,
        cp.delivery_addr_id                                                  as cp_delivery_addr_id,
        cp.corp_num                                                          as cp_corp_num,
        cp.party_typ_cd                                                      as cp_party_typ_cd,
        cp.start_event_id                                                    as cp_start_event_id,
        cp.end_event_id                                                      as cp_end_event_id,
        cp.prev_party_id                                                     as cp_prev_party_id,
        to_char(
        (case
            when cp.appointment_dt is not null then date_trunc('day', cp.appointment_dt)
            when cp.appointment_dt is null and f.effective_dt is not null then date_trunc('day', f.effective_dt)
            when cp.appointment_dt is null and f.effective_dt is null then date_trunc('day', e.event_timerstamp)
            else null
        end)::timestamp at time zone 'UTC', 'YYYY-MM-DD HH24:MI:SSTZH:TZM') as cp_appointment_dt_str,
        to_char(cp.cessation_dt::timestamp at time zone 'UTC', 'YYYY-MM-DD HH24:MI:SSTZH:TZM')     as cp_cessation_dt_str,
        cp.last_name              as cp_last_name,
        cp.middle_name            as cp_middle_name,
        cp.first_name             as cp_first_name,
        concat_ws(' ', nullif(trim(cp.first_name),''), nullif(trim(cp.middle_name),''), nullif(trim(cp.last_name),'')) as cp_full_name,
        trim(cp.business_name)    as cp_business_name,
        -- TODO: need to figure it out, thougth according to the spreadsheet, it converts to identifier
--        case 
--                when cp.bus_company_num = '' then NULL
--               when cp.bus_company_num ~ '^[0-9]+$' and length(cp.bus_company_num) <= 7  
--                    then concat('BC', cp.bus_company_num)
--                else cp.bus_company_num
--        end cp_bus_company_num,
--        cp.bus_company_num as cp_bus_company_num,
        cp.email_address          as cp_email_address,
        cp.phone                  as cp_phone,
        -- mailing address
        ma.addr_id                as ma_addr_id,
        ma.province               as ma_province,
        ma.country_typ_cd         as ma_country_typ_cd,
        ma.postal_cd              as ma_postal_cd,
        ma.addr_line_1            as ma_addr_line_1,
        ma.addr_line_2            as ma_addr_line_2,
        ma.addr_line_3            as ma_addr_line_3,
        ma.city                   as ma_city,
--        'BAS'                     as ma_address_format_type,
        ma.delivery_instructions  as ma_delivery_instructions,
        ma.unit_no                as ma_unit_no,
        ma.unit_type              as ma_unit_type,
        ma.civic_no               as ma_civic_no,
        ma.civic_no_suffix        as ma_civic_no_suffix,
        ma.street_name            as ma_street_name,
        ma.street_type            as ma_street_type,
        ma.street_direction       as ma_street_direction,
        ma.lock_box_no            as ma_lock_box_no,
        ma.installation_type      as ma_installation_type,
        ma.installation_name      as ma_installation_name,
        ma.installation_qualifier as ma_installation_qualifier,
        ma.route_service_type     as ma_route_service_type,
        ma.route_service_no       as ma_route_service_no,           
        -- delivery address
        da.addr_id                as da_addr_id,
        da.province               as da_province,
        da.country_typ_cd         as da_country_typ_cd,
        da.postal_cd              as da_postal_cd,
        da.addr_line_1            as da_addr_line_1,
        da.addr_line_2            as da_addr_line_2,
        da.addr_line_3            as da_addr_line_3,
        da.city                   as da_city,
--        'BAS'                     as da_address_format_type,
        da.delivery_instructions  as da_delivery_instructions,
        da.unit_no                as da_unit_no,
        da.unit_type              as da_unit_type,
        da.civic_no               as da_civic_no,
        da.civic_no_suffix        as da_civic_no_suffix,
        da.street_name            as da_street_name,
        da.street_type            as da_street_type,
        da.street_direction       as da_street_direction,
        da.lock_box_no            as da_lock_box_no,
        da.installation_type      as da_installation_type,
        da.installation_name      as da_installation_name,
        da.installation_qualifier as da_installation_qualifier,
        da.route_service_type     as da_route_service_type,
        da.route_service_no       as da_route_service_no
    from
    event e
            join corp_party cp on cp.start_event_id = e.event_id
            left outer join filing f on f.event_id = e.event_id
    --        corp_party cp
            left outer join address ma on cp.mailing_addr_id = ma.addr_id
            left outer join address da on cp.delivery_addr_id = da.addr_id
    where 1 = 1
    --    and e.corp_num = 'BC0043406' -- lots of DIR
    --    and e.corp_num = 'BC0006247' -- OFF, DIR, RCC
    --    and e.corp_num = 'BC0883637' -- INC, DIR
        and e.corp_num = '{corp_num}'
        and cp.end_event_id is null
        and cp.party_typ_cd in ('INC', 'DIR')
    --order by e.event_id
    order by cp_full_name, e.event_id
    ;
    """
    return query


def get_share_classes_share_series_query(corp_num):
    query = f"""
    select
    -- share_struct
        ss.corp_num        as ss_corp_num,
        ss.start_event_id  as ss_start_event_id,
    -- share_struct_cls
        ssc.share_class_id as ssc_share_class_id,
        ssc.class_nme      as ssc_class_nme,
        ssc.currency_typ_cd as ssc_currency_typ_cd,
        ssc.max_share_ind as ssc_max_share_ind,
        ssc.share_quantity as ssc_share_quantity,
        ssc.spec_rights_ind as ssc_spec_rights_ind,
        ssc.par_value_ind as ssc_par_value_ind,
        ssc.par_value_amt as ssc_par_value_amt,
        ssc.other_currency as ssc_other_currency,
    -- share_series
        srs.share_class_id as srs_share_class_id,
        srs.series_id as srs_series_id,
        srs.series_nme as srs_series_nme,
        srs.max_share_ind as srs_max_share_ind,
        srs.share_quantity as srs_share_quantity,
        srs.spec_right_ind as srs_spec_right_ind
    from share_struct ss
            left outer join share_struct_cls ssc on ssc.START_EVENT_ID = ss.START_EVENT_ID and ssc.CORP_NUM = ss.CORP_NUM
            left outer join share_series srs
                            on srs.START_EVENT_ID = ssc.START_EVENT_ID and srs.CORP_NUM = ssc.CORP_NUM and
                                srs.SHARE_CLASS_ID = ssc.SHARE_CLASS_ID
    where 1 = 1
    -- and ss.corp_num = 'BC0684934'  -- no share series
    -- and ss.corp_num = 'BC0009056' -- have share series
    -- and ss.corp_num = 'BC0022717' -- one share structure has multiple series
    -- and ss.corp_num = 'BC0046540' -- one share structure has multiple series
    and ss.corp_num = '{corp_num}'
    and ss.end_event_id is null
    order by ssc_share_class_id
    ;
    """
    return query


def get_aliases_query(corp_num):
    query = f"""
    select cn.corp_num         as cn_corp_num,
        cn.corp_name_typ_cd as cn_corp_name_typ_cd,
        cn.corp_name        as cn_corp_name
    from corp_name cn
    where 1 = 1 
    --		  and corp_num = 'BC0684912' -- name - CO
    --        and corp_num = 'BC0008045' -- name - CO, AN
    --    and corp_num = 'BC0043406' -- name - NB, SN, AN
        and corp_num = '{corp_num}'
        and end_event_id is null
        and corp_name_typ_cd = 'TR'
    --    and corp_name_typ_cd not in ('CO', 'NB')
    """
    return query


def get_resolutions_query(corp_num):
    query = f"""
    select
        r.corp_num as r_corp_num,
        to_char(r.resolution_dt, 'YYYY-MM-DD') as r_resolution_dt_str,
        r.resolution_type_code as r_resolution_type_code,
        r.end_event_id
    from resolution r
    where 1 = 1
    and r.corp_num = '{corp_num}'
--    and r.corp_num = 'BC0018784' -- has entry with end_event_id (NOALA + AM_SS -> alteration in lear)
    -- and r.end_event_id is null -- I don't know
    ;
    """
    return query


def get_filings_query(corp_num):
    query = f"""
    select                    
            -- event
            e.event_id             as e_event_id,
            e.corp_num             as e_corp_num,
            e.event_type_cd        as e_event_type_cd,
            to_char(e.event_timerstamp::timestamp at time zone 'UTC', 'YYYY-MM-DD HH24:MI:SSTZH:TZM') as e_event_dt_str,
            to_char(e.trigger_dts::timestamp at time zone 'UTC', 'YYYY-MM-DD HH24:MI:SSTZH:TZM') as e_trigger_dt_str,
            e.event_type_cd || '_' || COALESCE(f.filing_type_cd, 'NULL') as event_file_type,
            -- filing
            f.event_id             as f_event_id,
            f.filing_type_cd       as f_filing_type_cd,
            to_char(f.effective_dt::timestamp at time zone 'UTC', 'YYYY-MM-DD HH24:MI:SSTZH:TZM') as f_effective_dt_str,
            f.withdrawn_event_id   as f_withdrawn_event_id,
--          paper only now -> f_ods_type
            f.nr_num               as f_nr_num,
            to_char(f.period_end_dt::timestamp at time zone 'UTC', 'YYYY-MM-DD HH24:MI:SSTZH:TZM') as f_period_end_dt_str,
            -- state filing info
            (
                select start_event_id
                from corp_state
                where 1 = 1
                and corp_num = '{corp_num}'
                and end_event_id is null
            ) as cs_state_event_id,
            --- filing user
            upper(u.user_id)              as u_user_id,
            u.last_name            as u_last_name,
            u.first_name           as u_first_name,
            u.middle_name          as u_middle_name,
            case
                when u.first_name is null and u.middle_name is null and u.last_name is null then null
                else upper(concat_ws('_', nullif(trim(u.first_name),''), nullif(trim(u.middle_name),''), nullif(trim(u.last_name),'')))
            end as u_full_name,
            u.email_addr           as u_email_addr,
            u.role_typ_cd          as u_role_typ_cd
        from event e
                 left outer join filing f on e.event_id = f.event_id
                 left outer join filing_user u on u.event_id = e.event_id
        where 1 = 1
            and e.corp_num = '{corp_num}'
--          and e.corp_num = 'BC0068889'
--          and e.corp_num = 'BC0449924'  -- AR, ADCORP
--        and e.trigger_dts is not null
        order by e.event_timerstamp
        ;
    """
    return query


def get_amalgamation_query(corp_num):
    query = f"""
    select
        e.event_id            as e_event_id,
        ted_corp_num,
        ting_corp_num,
        cs.state_type_cd      as ting_state_type_cd,
        cs.end_event_id       as ting_state_end_event_id,
        corp_involve_id,
        can_jur_typ_cd,
        adopted_corp_ind,
        home_juri_num,
        othr_juri_desc,
        foreign_nme,
        -- event
        e.event_type_cd        as e_event_type_cd,
        to_char(e.event_timerstamp::timestamp at time zone 'UTC', 'YYYY-MM-DD HH24:MI:SSTZH:TZM') as e_event_dt_str,
        -- filing
        f.filing_type_cd       as f_filing_type_cd,
        to_char(f.effective_dt::timestamp at time zone 'UTC', 'YYYY-MM-DD HH24:MI:SSTZH:TZM') as f_effective_dt_str,
        f.court_appr_ind       as f_court_approval,
        -- event_file
        e.event_type_cd || '_' || COALESCE(f.filing_type_cd, 'NULL') as event_file_type
    from corp_involved_amalgamating cig
        left outer join event e on e.event_id = cig.event_id
        left outer join filing f on e.event_id = f.event_id
        left outer join corp_state cs on cig.ting_corp_num = cs.corp_num and cs.start_event_id = e.event_id
    where 1 = 1
    and cs.end_event_id is null
    and cig.ted_corp_num = '{corp_num}'
    order by cig.corp_involve_id;
    """
    return query


def get_corp_snapshot_filings_queries(config, corp_num):
    queries = {
        'businesses': get_business_query(corp_num, config.CORP_NAME_SUFFIX),
        'offices': get_offices_and_addresses_query(corp_num),
        'parties': get_parties_and_addresses_query(corp_num),
        'share_classes': get_share_classes_share_series_query(corp_num),
        'aliases': get_aliases_query(corp_num),
        'resolutions': get_resolutions_query(corp_num),
        'filings': get_filings_query(corp_num),
        'amalgamations': get_amalgamation_query(corp_num)
    }

    return queries
