def get_unprocessed_firms_query(data_load_env: str):
    query = f"""
            select tbl_fe.*, cp.flow_name, cp.processed_status, cp.last_processed_event_id
            from (select e.corp_num,
                         count(e.corp_num)                         as cnt,
                         string_agg(e.event_type_cd || '_' || COALESCE(f.filing_type_cd, 'NULL'), ','
                                    order by e.event_id)           as event_file_types,
                         array_agg(e.event_id order by e.event_id) as event_ids,
                         min(e.event_id)                           as first_event_id,
                         max(e.event_id)                           as last_event_id
                  from event e
                           left outer join filing f on e.event_id = f.event_id
                  where 1 = 1
                        -- complex change registration examples
--                         and e.corp_num in ('FM0632494', 'FM0554197', 'FM0429973', 'FM0433647', 'FM0433664', 'FM0434289', 
--                                            'FM0436872') 
--                     and e.corp_num = 'FM0399872' -- can be used to test incremental processing
--                     and e.corp_num = 'FM0554955' -- can be used to test incremental processing
                       -- incremental load testing 
--                        and e.corp_num in 'FM0775109', 'FM0558927', 'FM0706557', 'FM0799312','FM0675146', 'FM0772925'
                        -- firms that need backslash added to corp name
--                        and e.corp_num in ('FM0151616', 'FM0236781', 'FM0185321', 'FM0259938', 'FM0249302', 'FM0446106',
--                                           'FM0270319', 'FM0344562', 'FM0344563', 'FM0285081', 'FM0303834', 'FM0789778', 
--                                           'FM0535825', 'FM0749012')
--                     -- firms with missing req'd business info 
--                     and e.corp_num in ('FM0614946', 'FM0614924', 'FM0613627', 'FM0613561', 'FM0272480', 'FM0272488')
                       -- naics length greater than 150
--                        and e.corp_num in ('FM0779644', 'FM0779657', 'FM0779771', 'FM0780109', 'FM0780298', 'FM0780352')
                       -- firms that had address issues
--                     and e.corp_num in ('FM0281021', 'FM0472059', 'FM0279239')
                       -- firms with basic address format
--                        and e.corp_num = 'FM0585484'  
                       -- firms with advanced address format
--                        and e.corp_num = 'FM0367712'
                        -- utc testing
--                         and e.corp_num in ('FM0554193', 'FM0554211', 'FM0554212')
                       -- firms that had address issues 
                       -- firms with conversion filings
--                         and e.corp_num in ('FM0272508', 'FM0272576', 'FM0308447')
                       -- firms with put back on filings
--                         and e.corp_num in ('FM0278254', 'FM0349992', 'FM0418992') 
                  group by e.corp_num) as tbl_fe
                     left outer join corp_processing cp on 
                        cp.corp_num = tbl_fe.corp_num 
                        and cp.flow_name = 'sp-gp-flow'
                        and cp.environment = '{data_load_env}'
            where 1 = 1
                   and tbl_fe.event_file_types = 'FILE_FRREG'
--                 and tbl_fe.event_file_types like 'FILE_FRREG%'
--                 and tbl_fe.event_file_types like '%FILE_FRREG,%FRCHG%'
--                 and tbl_fe.event_file_types = 'CONVFMREGI_FRREG,CONVFMACP_FRMEM'
--                 and tbl_fe.event_file_types = 'CONVFMREGI_FRREG'
--                 and tbl_fe.event_file_types like '%CONVFMACP_FRMEM%'
--                 and tbl_fe.event_file_types like '%CONVFMMISS_FRCHG%'
--                 and tbl_fe.event_file_types like '%CONVFMNC_FRCHG%'
--                 and tbl_fe.event_file_types like '%CONVFMREGI_FRCHG%'
--                 and tbl_fe.event_file_types like '%FILE_ADDGP%'
--                 and tbl_fe.event_file_types like '%FILE_ADDSP%'
--                 and tbl_fe.event_file_types like '%FILE_CHGGP%'
--                 and tbl_fe.event_file_types like '%FILE_CHGSP%'
--                 and tbl_fe.event_file_types like 'FILE_FRREG,FILE_CHGSP%'
--                 and tbl_fe.event_file_types like '%FILE_FRNAM%'
--                 and tbl_fe.event_file_types like '%FILE_FRNAT%'
--                 and tbl_fe.event_file_types like '%FILE_MEMGP%'
--                 and tbl_fe.event_file_types like '%FILE_NAMGP%'
--                 and tbl_fe.event_file_types like '%FILE_NAMSP%'
--                 and tbl_fe.event_file_types like '%FILE_NATGP%'
--                 and tbl_fe.event_file_types like '%FILE_NATSP%'
--                 and tbl_fe.event_file_types like '%CONVFMDISS_FRDIS%'
--                 and tbl_fe.event_file_types like '%FILE_DISGP%'
--                 and tbl_fe.event_file_types like 'CONVFMREGI_FRREG,FILE_DISGP'
--                 and tbl_fe.event_file_types like '%FILE_DISSP%'
--                 and tbl_fe.event_file_types like 'CONVFMREGI_FRREG,FILE_DISSP'
--                 and tbl_fe.event_file_types like '%FILE_FRDIS%'
--                 and tbl_fe.event_file_types like 'CONVFMREGI_FRREG,FILE_FRDIS'
--                 and tbl_fe.event_file_types like '%ADMIN_ADMCF%'
--                 and tbl_fe.event_file_types like '%FILE_FRPBO%'
                   and ((cp.processed_status is null or cp.processed_status <> 'COMPLETED')
                   or (cp.processed_status = 'COMPLETED' and cp.last_processed_event_id <> tbl_fe.last_event_id))
            order by tbl_fe.first_event_id
            limit 50
            ;
        """
    return query


def get_firm_event_filing_data_query(corp_num: str, event_id: int):
    query = f"""
        select
            -- current corp_name at point in time
            (select corp_name as curr_corp_name
             from corp_name
             where corp_num = '{corp_num}'
               and start_event_id <= {event_id}
               and end_event_id is null),        
            -- event
            e.event_id             as e_event_id,
            e.corp_num             as e_corp_num,
            e.event_type_cd        as e_event_type_cd,
            to_char(e.event_timerstamp, 'YYYY-MM-DD') as e_event_dt_str,
            to_char(e.event_timerstamp, 'YYYY-MM-DD HH:MI:SS')::timestamp AT time zone 'pdt' as e_event_dts_utc,
            e.trigger_dts          as e_trigger_dts,
            -- filing
            f.event_id             as f_event_id,
            f.filing_type_cd       as f_filing_type_cd,
            to_char(f.effective_dt, 'YYYY-MM-DD') as f_effective_dt_str,
            to_char(f.effective_dt, 'YYYY-MM-DD HH:MI:SS')::timestamp AT time zone 'pdt' as f_effective_dts_utc,
            f.withdrawn_event_id   as f_withdrawn_event_id,
            f.ods_type_cd          as f_ods_type,
            f.nr_num               as f_nr_num,
            -- corporation
            c.corp_num             as c_corp_num,
            c.corp_frozen_type_cd  as c_corp_frozen_type_cd,
            c.corp_type_cd         as c_corp_type_cd,
            to_char(c.recognition_dts, 'YYYY-MM-DD HH:MI:SS')::timestamp AT time zone 'pdt' as c_recognition_dts_utc,
            c.bn_9                 as c_bn_9,
            c.bn_15                as c_bn_15,
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
            to_char(bd.business_start_date, 'YYYY-MM-DD HH:MI:SS')::timestamp AT time zone 'pdt' as bd_business_start_date_dts_utc,
            bd.naics_code          as bd_naics_code,
            bd.description         as bd_description,
            -- ledger_text
            lt.event_id            as lt_event_id,
            lt.notation            as lt_notation,
            -- payment
            p.event_id             as p_event_id,
            p.payment_typ_cd       as payment_typ_cd,
            p.fee_cd               as p_fee_cd,
            p.gst_num              as p_gst_num,
            p.bcol_account_num     as p_bcol_account_num,
            p.payment_total        as p_payment_total,
            p.folio_num            as p_folio_num,
            p.dat_num              as p_dat_num,
            p.routing_slip         as p_routing_slip,
            p.fas_balance          as p_fas_balance,
            -- filing user
            u.event_id             as u_event_id,
            u.user_id              as u_user_id,
            u.last_name            as u_last_name,
            u.first_name           as u_first_name,
            u.middle_name          as u_middle_name,
            u.email_addr           as u_email_addr
        from event e
                 left outer join filing f on e.event_id = f.event_id
                 left outer join corporation c on c.corp_num = e.corp_num
                 left outer join corp_name cn on cn.start_event_id = e.event_id
                 left outer join corp_state cs on cs.start_event_id = e.event_id
                 left outer join business_description bd on bd.start_event_id = e.event_id
                 left outer join ledger_text lt on lt.event_id = e.event_id
                 left outer join unused_payment p on p.event_id = e.event_id
                 left outer join filing_user u on u.event_id = e.event_id
        where 1 = 1
          and e.corp_num = '{corp_num}'
          and e.event_id = {event_id}
        order by e.event_id
        ;
        """
    return query


def get_firm_event_filing_corp_party_data_query(corp_num: str,
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
                    cp.party_typ_cd != 'FCP') 
                or (cp.start_event_id != {event_id} and
                    cp.start_event_id in ({prev_event_ids_str}) and
                    cp.end_event_id != {event_id} and
                    cp.end_event_id not in ({prev_event_ids_str}) and
                    cp.party_typ_cd != 'FCP')
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
                    when cp.party_typ_cd = 'FCP' 
                        THEN NULL
                    else cp.prev_party_id 
               end cp_prev_party_id,
               case
                    when cp.appointment_dt is not null 
                         and cp.start_event_id = {event_id} 
                         and cp.party_typ_cd != 'FCP' 
                         and cp.prev_party_id is null
                         THEN to_char(cp.appointment_dt, 'YYYY-MM-DD')
                    when cp.appointment_dt is null 
                         and cp.start_event_id = {event_id} 
                         and cp.party_typ_cd != 'FCP' 
                         and cp.prev_party_id is null
                         THEN '{appoint_dt_str}' 
                    else NULL
               end cp_appointment_dt,
               cp.last_name              as cp_last_name,
               cp.middle_name            as cp_middle_name,
               cp.first_name             as cp_first_name,
               cp.business_name          as cp_business_name,
               NULLIF(cp.bus_company_num, '')                                       as cp_bus_company_num,
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
               ma.address_format_type    as ma_address_format_type,
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
               da.address_format_type    as da_address_format_type,
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


def get_firm_event_filing_office_data_query(corp_num: str, event_id: int):
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
               ma.address_format_type    as ma_address_format_type,
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
               da.address_format_type    as da_address_format_type,
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
          and e.event_id = {event_id}
        ;
        """
    return query
