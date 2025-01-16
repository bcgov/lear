def get_unprocessed_corps_query(data_load_env: str):
    query = f"""
            select tbl_fe.*, cp.flow_name, cp.processed_status, cp.last_processed_event_id
            from (select e.corp_num,
                         c.corp_type_cd,
                         count(e.corp_num)                         as cnt,
                         string_agg(e.event_type_cd || '_' || COALESCE(f.filing_type_cd, 'NULL'), ','
                                    order by e.event_id)           as event_file_types,
                         array_agg(e.event_id order by e.event_id) as event_ids,
                         array_agg(e.event_id order by e.event_id) FILTER (WHERE e.event_type_cd = 'FILE' and f.filing_type_cd in ('CORGP', 'CORSP', 'FRCCH', 'FRCRG') ) as correction_event_ids,
                         min(e.event_id)                           as first_event_id,
                         max(e.event_id)                           as last_event_id
                  from event e
                           join corporation c on c.corp_num = e.corp_num
                           left outer join filing f on e.event_id = f.event_id
                  where 1 = 1
                        -- corp with multiple share classes and series
--                         and e.corp_num = 'BC1393945'
                        -- corp with annual reports
--                          and e.corp_num = 'BC1208648'
                  group by e.corp_num, c.corp_type_cd) as tbl_fe
                     left outer join corp_processing cp on 
                        cp.corp_num = tbl_fe.corp_num 
                        and cp.flow_name = 'corps-flow'
                        and cp.environment = '{data_load_env}'
            where 1 = 1    
--                    and tbl_fe.event_file_types like 'FILE_ICORP%'             
--                    and tbl_fe.event_file_types like 'FILE_ICORU%'             
--                    and tbl_fe.event_file_types like 'FILE_ICORC%'             
--                 and ((cp.processed_status is null or cp.processed_status <> 'COMPLETED')
                   and ((cp.processed_status is null or cp.processed_status not in ('PROCESSING', 'COMPLETED', 'FAILED', 'PARTIAL'))
                   or (cp.processed_status = 'COMPLETED' and cp.last_processed_event_id <> tbl_fe.last_event_id))
            order by tbl_fe.first_event_id
            limit 5
            ;
        """
    return query


def get_corp_event_filing_data_query(corp_num: str, event_id: int):
    query = f"""
        select
            -- current corp_name at point in time
            (select corp_name as curr_corp_name
             from corp_name
             where corp_num = '{corp_num}'
               and start_event_id <= {event_id}
               and end_event_id is null
               and corp_name_typ_cd in ('CO', 'NB')),                       
            -- event
            e.event_id             as e_event_id,
            e.corp_num             as e_corp_num,
            e.event_type_cd        as e_event_type_cd,
            to_char(e.event_timerstamp, 'YYYY-MM-DD') as e_event_dt_str,
            to_char(e.event_timerstamp, 'YYYY-MM-DD HH24:MI:SS')::timestamp AT time zone 'America/Los_Angeles' as e_event_dts_pacific,
            to_char(e.trigger_dts, 'YYYY-MM-DD') as e_trigger_dt_str,
            to_char(e.trigger_dts, 'YYYY-MM-DD HH24:MI:SS')::timestamp AT time zone 'America/Los_Angeles' as e_trigger_dts_pacific,
            -- filing
            f.event_id             as f_event_id,
            f.filing_type_cd       as f_filing_type_cd,
            to_char(f.effective_dt, 'YYYY-MM-DD') as f_effective_dt_str,
            to_char(f.effective_dt, 'YYYY-MM-DD HH24:MI:SS')::timestamp AT time zone 'America/Los_Angeles' as f_effective_dts_pacific,
            f.withdrawn_event_id   as f_withdrawn_event_id,
            case
                when e.event_type_cd = 'CONVFMRCP' and f.ods_type_cd is null THEN 'P'
                -- registration related filings marked as paper only but should be available as electronic filings
                when (f.effective_dt >= '2004-03-15' and f.effective_dt <= '2011-04-08')
                      and f.filing_type_cd in ('FRREG', 'FRARG', 'FRCRG')
                      and not (f.filing_type_cd = 'FRARG' and e.event_type_cd ~ '^CONV.*$')
                    THEN 'F'
                else f.ods_type_cd
            end f_ods_type,            
            f.nr_num               as f_nr_num,
            to_char(f.period_end_dt, 'YYYY-MM-DD') as f_period_end_dt_str,
            -- corporation
            c.corp_num             as c_corp_num,
            c.corp_frozen_type_cd  as c_corp_frozen_type_cd,
            c.corp_type_cd         as c_corp_type_cd,
            c.send_ar_ind          as c_send_ar_ind,
            to_char(c.recognition_dts, 'YYYY-MM-DD HH24:MI:SS')::timestamp AT time zone 'America/Los_Angeles' as c_recognition_dts_pacific,
            c.bn_9                 as c_bn_9,
            c.bn_15                as c_bn_15,
            case 
                when (c.bn_15 is null or c.bn_15 = '')
                    THEN c.bn_9
                else c.bn_15
            end c_bn,
            c.admin_email          as c_admin_email,
            -- corp_name
            cn.corp_num            as cn_corp_num,
            cn.corp_name_typ_cd    as cn_corp_name_typ_cd,
            cn.start_event_id      as cn_start_event_id,
            cn.end_event_id        as cn_end_event_id,
            cn.corp_name           as cn_corp_name,
            -- corp_state
            cs.corp_num            as cs_corp_num,
            cs.start_event_id      as cs_start_event_id,
            cs.end_event_id        as cs_end_event_id,
            cs.state_type_cd       as cs_corp_state_typ_cd,
            -- business_description
            bd.corp_num            as bd_corp_num,
            bd.start_event_id      as bd_start_event_id,
            bd.end_event_id        as bd_end_event_id,
            to_char(bd.business_start_date, 'YYYY-MM-DD') as bd_business_start_date_dt_str,
            to_char(bd.business_start_date, 'YYYY-MM-DD HH24:MI:SS')::timestamp AT time zone 'America/Los_Angeles' as bd_business_start_date_dts_pacific,
            bd.naics_code          as bd_naics_code,
            bd.description         as bd_description,
            -- ledger_text
            lt.event_id            as lt_event_id,
            lt.notation            as lt_notation,
            -- filing user
            u.event_id             as u_event_id,
            u.user_id              as u_user_id,
            u.last_name            as u_last_name,
            u.first_name           as u_first_name,
            u.middle_name          as u_middle_name,
            u.email_addr           as u_email_addr,
            to_char(u.event_timestmp, 'YYYY-MM-DD HH24:MI:SS')::timestamp AT time zone 'America/Los_Angeles' as u_event_timestmp_dts_pacific            
        from event e
                 left outer join filing f on e.event_id = f.event_id
                 left outer join corporation c on c.corp_num = e.corp_num
                 left outer join corp_name cn on cn.start_event_id = e.event_id and cn.corp_name_typ_cd in ('CO', 'NB')
                 left outer join corp_state cs on cs.start_event_id = e.event_id
                 left outer join business_description bd on bd.start_event_id = e.event_id
                 left outer join ledger_text lt on lt.event_id = e.event_id
                 left outer join filing_user u on u.event_id = e.event_id
        where 1 = 1
          and e.corp_num = '{corp_num}'
          and e.event_id = {event_id}
        order by e.event_id
        ;
        """
    return query


def get_corp_event_filing_corp_party_data_query(corp_num: str,
                                                event_id: int,
                                                prev_event_ids: list,
                                                event_filing_data_dict: dict):
    f_effective_dt_str = event_filing_data_dict['f_effective_dt_str']
    event_dt_str = event_filing_data_dict['e_event_dt_str']
    appoint_dt_str = f_effective_dt_str if f_effective_dt_str else event_dt_str

    sub_condition = ''

    if prev_event_ids:
        prev_event_ids_str =  ",".join([str(i) for i in prev_event_ids])
        sub_condition = \
            f"""
                or (cp.start_event_id != {event_id} and 
                    cp.start_event_id in ({prev_event_ids_str}) and 
                    cp.end_event_id is null and
                    cp.party_typ_cd not in ('FCP', 'INC')) 
                or (cp.start_event_id != {event_id} and
                    cp.start_event_id in ({prev_event_ids_str}) and
                    cp.end_event_id != {event_id} and
                    cp.end_event_id not in ({prev_event_ids_str}) and
                    cp.party_typ_cd  not in ('FCP', 'INC'))
            """

    query = f"""
        select cp.corp_party_id                                                     as cp_corp_party_id,
               cp.mailing_addr_id                                                   as cp_mailing_addr_id,
               cp.delivery_addr_id                                                  as cp_delivery_addr_id,
               cp.corp_num                                                          as cp_corp_num,
               cp.party_typ_cd                                                      as cp_party_typ_cd,
               cp.start_event_id                                                    as cp_start_event_id,
               cp.end_event_id                                                      as cp_end_event_id,
               case 
                    when cp.party_typ_cd in ('FCP', 'INC') 
                        THEN NULL
                    else cp.prev_party_id 
               end cp_prev_party_id,
               case
                    when cp.appointment_dt is not null 
                         and cp.start_event_id = {event_id} 
                         and cp.party_typ_cd  not in ('FCP', 'INC') 
                         and cp.prev_party_id is null
                         THEN to_char(cp.appointment_dt, 'YYYY-MM-DD')
                    when cp.appointment_dt is null 
                         and cp.start_event_id = {event_id} 
                         and cp.party_typ_cd  not in ('FCP', 'INC') 
                         and cp.prev_party_id is null
                         THEN '{appoint_dt_str}' 
                    else NULL
               end cp_appointment_dt,
               cp.last_name              as cp_last_name,
               cp.middle_name            as cp_middle_name,
               cp.first_name             as cp_first_name,
               trim(cp.business_name)    as cp_business_name,
               case 
                    when cp.bus_company_num = '' then NULL
                    when cp.bus_company_num ~ '^[0-9]+$' and length(cp.bus_company_num) <= 7  
                        then concat('BC', cp.bus_company_num)
                    else cp.bus_company_num
               end cp_bus_company_num,
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
               'BAS'                     as ma_address_format_type,
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
               'BAS'                     as da_address_format_type,
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
                 join corp_party cp on cp.start_event_id = e.event_id
                 left outer join address ma on cp.mailing_addr_id = ma.addr_id
                 left outer join address da on cp.delivery_addr_id = da.addr_id
        where 1 = 1
          and e.corp_num = '{corp_num}'
          and (e.event_id = {event_id} {sub_condition})
        order by e.event_id
        ;
        """
    return query


def get_corp_event_filing_office_data_query(corp_num: str, event_id: int, include_prev_active_offices: bool = False):
    sub_condition = ''

    if include_prev_active_offices:
        sub_condition = \
            f"""
                or (o.start_event_id < {event_id} and o.end_event_id is null)
                or (o.start_event_id < {event_id} and o.end_event_id > {event_id}) 
            """

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
               'BAS'                     as ma_address_format_type,
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
               'BAS'                     as da_address_format_type,
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
          and e.corp_num = '{corp_num}'
          and (e.event_id = {event_id} {sub_condition})
        ;
        """
    return query


def get_corp_comments_data_query(corp_num: str):
    query = f"""
        select to_char(cc.comment_dts, 'YYYY-MM-DD HH24:MI:SS')::timestamp AT time zone 'America/Los_Angeles' as cc_comment_dts_pacific,
               cc.corp_num as cc_corp_num,
               cc.comments as cc_comments
        from corp_comments cc
        where cc.corp_num = '{corp_num}'
        order by cc.comment_dts
        ;
        """
    return query


# for retrieval of names that maps to LEAR aliases table
def get_corp_event_names_data_query(corp_num: str, event_id: int):
    query = f"""
        select cn.corp_num         as cn_corp_num,
               cn.corp_name_typ_cd as cn_corp_name_typ_cd,
               cn.start_event_id   as cn_start_event_id,
               cn.end_event_id     as cn_end_event_id,
               cn.corp_name        as cn_corp_name
        from corp_name cn
        where corp_num = '{corp_num}'
          and start_event_id = {event_id}
          and end_event_id is null
          and corp_name_typ_cd not in ('CO', 'NB')
        ;
        """
    return query


def get_share_structure_data_query(corp_num: str, event_id: int):
    query = f"""
        SELECT ss.corp_num        as ss_corp_num,
               ss.start_event_id  as ss_start_event_id,
               ssc.share_class_id as ssc_share_class_id,
               ssc.class_nme      as ssc_class_nme,
               ssc.currency_typ_cd as ssc_currency_typ_cd,
               ssc.max_share_ind as ssc_max_share_ind,
               ssc.share_quantity as ssc_share_quantity,
               ssc.spec_rights_ind as ssc_spec_rights_ind,
               ssc.par_value_ind as ssc_par_value_ind,
               ssc.par_value_amt as ssc_par_value_amt,
               ssc.other_currency as ssc_other_currency,
               srs.share_class_id as srs_share_class_id,
               srs.series_nme as srs_series_nme,
               srs.max_share_ind as srs_max_share_ind,
               srs.share_quantity as srs_share_quantity,
               srs.spec_right_ind as srs_spec_right_ind
        FROM share_struct ss
                 left outer join SHARE_STRUCT_CLS ssc on ssc.START_EVENT_ID = ss.START_EVENT_ID and ssc.CORP_NUM = ss.CORP_NUM
                 left outer join SHARE_SERIES srs
                                 on srs.START_EVENT_ID = ssc.START_EVENT_ID and srs.CORP_NUM = ssc.CORP_NUM and
                                    srs.SHARE_CLASS_ID = ssc.SHARE_CLASS_ID
        WHERE ss.corp_num = '{corp_num}'
          and ss.start_event_id = {event_id}
          and ss.end_event_id is null
        ;
        """
    return query


def get_corp_event_jurisdiction_data_query(corp_num: str, event_id: int):
    query = f"""
        select
            j.corp_num 			as j_corp_num,
            j.start_event_id 	as j_start_event_id,
            j.can_jur_typ_cd 	as j_can_jur_typ_cd,
            j.xpro_typ_cd 		as j_xpro_typ_cd,
            j.home_company_nme 	as j_home_company_nme,
            j.home_juris_num 	as j_home_juris_num,
            to_char(j.home_recogn_dt, 'YYYY-MM-DD') as j_home_recogn_dt,
            j.othr_juris_desc 	as j_othr_juris_desc,
            j.bc_xpro_num 		as j_bc_xpro_num
        from jurisdiction j
        where corp_num = '{corp_num}'
        and start_event_id = {event_id}
        ;
        """
    return query