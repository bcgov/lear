-- Version 2 of the backfill database functions: these functions replace all the ones in the first version 
-- contained in file colin_lear_create_functions.sql.
-- This version significantly improves the performance of the backfill load for a single company.


--
-- During migration script development rollback historical data changes for an indiividual filing.
-- Restore filing to the tombstone data load state.
--
create or replace function public.colin_hist_filing_rollback(p_trans_id integer) returns integer
  language plpgsql
as $$
declare
begin
  delete
    from addresses
   where id in (select id from addresses_version where transaction_id = p_trans_id and office_id is not null);
  delete
    from offices
   where id in (select office_id from addresses_version where transaction_id = p_trans_id and office_id is not null);
  delete
    from addresses_version
   where transaction_id = p_trans_id
     and office_id is not null;
  delete
    from offices
   where id in (select id from offices_version where transaction_id = p_trans_id);
  delete
    from offices_version
   where transaction_id = p_trans_id;
  update offices_version
     set end_transaction_id = null
   where end_transaction_id = p_trans_id;
  delete 
    from party_roles 
   where id in (select id from party_roles_version where transaction_id = p_trans_id);   
  delete 
    from party_roles_version 
   where  transaction_id = p_trans_id;
  delete 
    from parties 
   where id in (select id 
                 from parties_version 
                where transaction_id = p_trans_id
                  and not exists (select p.id 
                                   from parties_version p
                                   where p.id = id
                                     and p.transaction_id != p_trans_id));   
  delete 
    from parties_version 
   where  transaction_id = p_trans_id;
  delete
    from addresses
   where id in (select a.id 
                  from addresses_version a
                 where a.transaction_id = p_trans_id 
                  and a.office_id is null
                  and not exists (select p.id 
                                   from parties_version p
                                   where (p.mailing_address_id = a.id or p.delivery_address_id = a.id)
                                     and p.transaction_id != p_trans_id));   
  delete
    from addresses_version
   where transaction_id = p_trans_id;

  update addresses_version
     set end_transaction_id = null
   where end_transaction_id = p_trans_id;
  update parties_version
     set end_transaction_id = null
   where end_transaction_id = p_trans_id;
  update party_roles_version
     set end_transaction_id = null
   where end_transaction_id = p_trans_id;

  delete
    from share_series
   where id in (select id from share_series_version where transaction_id = p_trans_id);
  delete
    from share_series_version
   where transaction_id = p_trans_id;
  update share_series_version
     set end_transaction_id = null
   where end_transaction_id = p_trans_id;
  delete
    from share_classes
   where id in (select id from share_classes_version where transaction_id = p_trans_id);
  delete
    from share_classes_version
   where transaction_id = p_trans_id;
  update share_classes_version
     set end_transaction_id = null
   where end_transaction_id = p_trans_id;
   
  delete
    from resolutions
   where id in (select id from resolutions_version where transaction_id = p_trans_id);
  delete
    from resolutions_version
   where transaction_id = p_trans_id;
  update resolutions_version
     set end_transaction_id = null
   where end_transaction_id = p_trans_id;
   
  delete
    from aliases
   where id in (select id from aliases_version where transaction_id = p_trans_id);
  delete
    from aliases_version
   where transaction_id = p_trans_id;
  update aliases_version
     set end_transaction_id = null
   where end_transaction_id = p_trans_id;

  delete
    from businesses_version
   where transaction_id = p_trans_id;
  update businesses_version
     set end_transaction_id = null
   where end_transaction_id = p_trans_id;
  
  delete
    from amalgamating_businesses
   where id in (select id from amalgamating_businesses_version where transaction_id = p_trans_id);
  delete
    from amalgamating_businesses_version
   where transaction_id = p_trans_id;
  update amalgamating_businesses_version
     set end_transaction_id = null
   where end_transaction_id = p_trans_id;
   
  delete
    from amalgamations
   where id in (select id from amalgamations_version where transaction_id = p_trans_id);
  delete
    from amalgamations_version
   where transaction_id = p_trans_id;
  update amalgamations_version
     set end_transaction_id = null
   where end_transaction_id = p_trans_id;
   
  delete
    from jurisdictions
   where id in (select id from jurisdictions_version where transaction_id = p_trans_id);
  delete
    from jurisdictions_version
   where transaction_id = p_trans_id;
  update jurisdictions_version
     set end_transaction_id = null
   where end_transaction_id = p_trans_id;

  return p_trans_id;
end;
$$;

--
-- During migration script development rollback historical data changes for an individual BC corp.
-- Restore corp to the tombstone data load state.
--
create or replace function public.colin_hist_corp_rollback(p_corp_num character varying) returns integer
  language plpgsql
as $$
declare
  bus_id integer := 0;
  tombstone_id integer := 0;
begin
  select b.id, f.transaction_id
    into bus_id, tombstone_id
    from businesses b, filings f
   where b.identifier = p_corp_num
     and b.id = f.business_id
     and f.filing_type = 'lear_tombstone'
     and status = 'TOMBSTONE';
  if tombstone_id is not null and tombstone_id > 0 and bus_id is not null and bus_id > 0 then
    delete
      from addresses
     where id in (select a.id 
                    from addresses_version a, filings f 
                   where f.business_id = bus_id
                     and f.transaction_id = a.transaction_id
                     and a.office_id is not null
                     and f.transaction_id != tombstone_id);
    delete
      from addresses_version
     where id in (select a.id 
                    from addresses_version a, filings f 
                   where f.business_id = bus_id
                     and f.transaction_id = a.transaction_id
                     and a.office_id is not null
                     and f.transaction_id != tombstone_id);
    delete
      from offices
     where id in (select o.id 
                    from offices_version o, filings f 
                   where f.business_id = bus_id
                     and f.transaction_id = o.transaction_id
                     and f.transaction_id != tombstone_id);
    delete
      from offices_version
     where id in (select o.id 
                    from offices_version o, filings f 
                   where f.business_id = bus_id
                     and f.transaction_id = o.transaction_id
                     and f.transaction_id != tombstone_id);
    delete 
      from party_roles 
     where id in (select p.id 
                    from party_roles_version p, filings f 
                   where f.business_id = bus_id
                     and f.transaction_id = p.transaction_id
                     and f.transaction_id != tombstone_id);
    delete 
      from party_roles_version 
     where id in (select p.id 
                   from party_roles_version p, filings f 
                  where f.business_id = bus_id
                    and f.transaction_id = p.transaction_id
                    and f.transaction_id != tombstone_id);
    delete 
      from parties 
     where id in (select p.id 
                    from parties_version p, filings f 
                   where f.business_id = bus_id
                     and f.transaction_id = p.transaction_id
                     and f.transaction_id != tombstone_id);
    delete 
      from parties_version 
     where id in (select p.id 
                    from parties_version p, filings f 
                   where f.business_id = bus_id
                     and f.transaction_id = p.transaction_id
                     and f.transaction_id != tombstone_id);
    delete
      from addresses
     where id in (select a.id 
                    from addresses_version a, filings f 
                   where f.business_id = bus_id
                     and f.transaction_id = a.transaction_id
                     and f.transaction_id != tombstone_id);
    delete
      from addresses_version
     where id in (select a.id 
                    from addresses_version a, filings f 
                   where f.business_id = bus_id
                     and f.transaction_id = a.transaction_id
                     and f.transaction_id != tombstone_id);

    delete
      from share_series
     where id in (select s.id 
                    from share_series_version s, filings f 
                   where f.business_id = bus_id
                     and f.transaction_id = s.transaction_id
                     and f.transaction_id != tombstone_id);
    delete
      from share_series_version
     where id in (select s.id 
                    from share_series_version s, filings f 
                   where f.business_id = bus_id
                     and f.transaction_id = s.transaction_id
                     and f.transaction_id != tombstone_id);

    delete
      from share_classes
     where id in (select s.id 
                    from share_classes_version s, filings f 
                   where f.business_id = bus_id
                     and f.transaction_id = s.transaction_id
                     and f.transaction_id != tombstone_id);
    delete
      from share_classes_version
     where id in (select s.id 
                    from share_classes_version s, filings f 
                   where f.business_id = bus_id
                     and f.transaction_id = s.transaction_id
                     and f.transaction_id != tombstone_id);
   
    delete
      from resolutions
     where id in (select r.id 
                    from resolutions_version r, filings f 
                   where f.business_id = bus_id
                     and f.transaction_id = r.transaction_id
                     and f.transaction_id != tombstone_id);
    delete
      from resolutions_version
     where id in (select r.id 
                    from resolutions_version r, filings f 
                   where f.business_id = bus_id
                     and f.transaction_id = r.transaction_id
                     and f.transaction_id != tombstone_id);
   
    delete
      from aliases
     where id in (select a.id 
                    from aliases_version a, filings f 
                   where f.business_id = bus_id
                     and f.transaction_id = a.transaction_id
                     and f.transaction_id != tombstone_id);
    delete
      from aliases_version
     where id in (select a.id 
                    from aliases_version a, filings f 
                   where f.business_id = bus_id
                     and f.transaction_id = a.transaction_id
                     and f.transaction_id != tombstone_id);

    delete
      from businesses_version
     where id = bus_id
       and transaction_id != tombstone_id;
  
    delete
      from amalgamating_businesses
     where id in (select a.id 
                    from amalgamating_businesses_version a, filings f 
                   where f.business_id = bus_id
                     and f.transaction_id = a.transaction_id
                     and f.transaction_id != tombstone_id);
    delete
      from amalgamating_businesses_version
     where id in (select a.id 
                    from amalgamating_businesses_version a, filings f 
                   where f.business_id = bus_id
                     and f.transaction_id = a.transaction_id
                     and f.transaction_id != tombstone_id);
   
    delete
      from amalgamations
     where id in (select a.id 
                    from amalgamations_version a, filings f 
                   where f.business_id = bus_id
                     and f.transaction_id = a.transaction_id
                     and f.transaction_id != tombstone_id);
    delete
      from amalgamations_version
     where id in (select a.id 
                    from amalgamations_version a, filings f 
                   where f.business_id = bus_id
                     and f.transaction_id = a.transaction_id
                     and f.transaction_id != tombstone_id);
   
    delete
      from jurisdictions
     where id in (select j.id 
                    from jurisdictions_version j, filings f 
                   where f.business_id = bus_id
                     and f.transaction_id = j.transaction_id
                     and f.transaction_id != tombstone_id);
    delete
      from jurisdictions_version
     where id in (select j.id 
                    from jurisdictions_version j, filings f 
                   where f.business_id = bus_id
                     and f.transaction_id = j.transaction_id
                     and f.transaction_id != tombstone_id);
  end if;
  return bus_id;
end;
$$;

-- Map colin officer_typ_cd to business officer role.
create or replace function public.to_officer_role(p_officer_typ_cd character varying) returns character varying
  language plpgsql
as $$
declare
begin
  return case when p_officer_typ_cd = 'PRE' then 'president'
              when p_officer_typ_cd = 'CFO' then 'cfo'
              when p_officer_typ_cd = 'CEO' then 'ceo'
              when p_officer_typ_cd = 'SEC' then 'secretary'
              when p_officer_typ_cd = 'VIP' then 'vice_president'
              when p_officer_typ_cd = 'TRE' then 'treasurer'
              when p_officer_typ_cd = 'CHR' then 'chair'
              when p_officer_typ_cd = 'ASC' then 'assistant_secretary'
              else 'other' end;
end;
$$;

-- Assign new backfill businesses database record ID's for a single company. Also map legacy to modern types on common tables. 
-- Include check to assign ID's only once per company.
create or replace function public.colin_hist_corp_setup(p_corp_num character varying,
                                                        p_business_id integer) returns integer
  language plpgsql
as $$
declare
  cur_officer cursor(v_corp_num character varying)
    for select oh.officer_typ_cd, oh.party_role_id, cp.corp_party_id, cp.prev_party_id,
               (select oh2.corp_party_id
                  from colin_extract.offices_held oh2
                 where oh2.corp_party_id = coalesce((select max(cp2.corp_party_id)
                                                       from colin_extract.corp_party cp2
                                                      where cp2.corp_num = cp.corp_num
                                                        and cp2.prev_party_id = cp.prev_party_id
                                                        and cp2.corp_party_id < cp.corp_party_id),
                                                    cp.prev_party_id)
                   and oh2.officer_typ_cd = oh.officer_typ_cd) as exists_party_id
         from colin_extract.corp_party cp, colin_extract.offices_held oh
         where cp.corp_num = v_corp_num
           and cp.party_typ_cd = 'OFF'
           and cp.prev_party_id is not null and cp.prev_party_id > 0
           and cp.corp_party_id = oh.corp_party_id
        order by cp.corp_party_id;
  rec_officer record;
  update_officer_count integer := 0;
  null_officer_count integer := 0;
  update_party_count integer := 0;
  null_party_count integer := 0;
  exists_counter integer := 0;
  rec_office_count record;
  rec_rg colin_extract.office%ROWTYPE;
  rec_rc colin_extract.office%ROWTYPE;
  rec_ds colin_extract.office%ROWTYPE;
  rec_lq colin_extract.office%ROWTYPE;
begin
  select count(event_id)
    into exists_counter
    from colin_extract.event
   where corp_num = p_corp_num
     and transaction_id is not null;

  if exists_counter = 0 then
    select count(cp.id)
      into exists_counter
      from businesses b, filings f, colin_event_ids ce, colin_extract.corp_processing cp, mig_corp_processing_history mcph
     where b.identifier = cp.corp_num
       and b.id = f.business_id
       and cp.processed_status = 'COMPLETED'
       and f.source = 'COLIN'
       and f.status = 'COMPLETED'
       and f.id = ce.filing_id
       and mcph.corp_processing_id = cp.id
       and mcph.history_migrated = true
       and b.identifier = p_corp_num;
  end if;

  if exists_counter = 0 then
/*
    update colin_extract.corporation
       set business_id = b.id
      from businesses b, filings f, colin_event_ids ce
     where b.id = f.business_id
       and f.source = 'COLIN'
       and f.status = 'COMPLETED'
       and f.id = ce.filing_id
       and f.filing_type != 'conversionLedger'
       and b.identifier = colin_extract.corporation.corp_num
       and b.identifier = p_corp_num;
*/
    update colin_extract.event
       set transaction_id = f.transaction_id
      from businesses b, filings f, colin_event_ids ce
     where b.id = f.business_id
       and f.source = 'COLIN'
       and f.status = 'COMPLETED'
       and f.id = ce.filing_id
       and f.filing_type not in ('conversionLedger')
       and ce.colin_event_id = colin_extract.event.event_id
       and f.filing_type != 'conversionLedger'
       and b.identifier = p_corp_num;
/*
    update colin_extract.filing
       set filing_id = f.id
      from businesses b, filings f, colin_event_ids ce
     where b.id = f.business_id
       and f.source = 'COLIN'
       and f.status = 'COMPLETED'
       and f.id = ce.filing_id
       and f.filing_type != 'conversionLedger'
       and ce.colin_event_id = colin_extract.filing.event_id
       and b.identifier = p_corp_num;
*/
    update colin_extract.office
       set office_type = case when office_typ_cd = 'RG' then 'registeredOffice'
                              when office_typ_cd = 'RC' then 'recordsOffice'  
                              when office_typ_cd = 'DS' then 'custodialOffice' 
                              when office_typ_cd = 'LQ' then 'liquidationRecordsOffice' else office_typ_cd end
     where corp_num = p_corp_num;

    update colin_extract.corp_party
       set role = case when party_typ_cd = 'DIR' then 'director'
                       when party_typ_cd = 'INC' then 'incorporator'
                       when party_typ_cd = 'RCC' then 'custodian'
                       when party_typ_cd = 'LIQ' then 'liquidator'
                       when party_typ_cd = 'RCM' then 'receiver'
                       when party_typ_cd = 'APP' then 'applicant'
                       else null end
     where corp_num = p_corp_num;

    update colin_extract.offices_held
       set role = to_officer_role(officer_typ_cd)
      from colin_extract.corp_party cp
     where cp.corp_num = p_corp_num
       and cp.party_typ_cd = 'OFF'
       and cp.corp_party_id = colin_extract.offices_held.corp_party_id;

    update colin_extract.share_struct_cls
       set new_id = nextval('share_classes_id_seq')
     where corp_num = p_corp_num;

    update colin_extract.share_series
       set new_id = nextval('share_series_id_seq')
     where corp_num = p_corp_num;

    select count(o.start_event_id) as rg_count,
           (select count(o2.start_event_id) from colin_extract.office o2 where o2.corp_num = p_corp_num and o2.office_typ_cd = 'RC') as rc_count,
           (select count(o2.start_event_id) from colin_extract.office o2 where o2.corp_num = p_corp_num and o2.office_typ_cd = 'DS') as ds_count,
           (select count(o2.start_event_id) from colin_extract.office o2 where o2.corp_num = p_corp_num and o2.office_typ_cd = 'LQ') as lq_count
      into rec_office_count
      from colin_extract.office o
      where o.corp_num = p_corp_num
        and o.office_typ_cd = 'RG';
    rec_rg.office_id := nextval('offices_id_seq');
    rec_rg.mailing_id := nextval('addresses_id_seq');
    rec_rg.delivery_id := nextval('addresses_id_seq');
    rec_rc.office_id := nextval('offices_id_seq');
    rec_rc.mailing_id := nextval('addresses_id_seq');
    rec_rc.delivery_id := nextval('addresses_id_seq');
    if rec_office_count.ds_count > 0 then
      rec_ds.office_id := nextval('offices_id_seq');
      rec_ds.mailing_id := nextval('addresses_id_seq');
      rec_ds.delivery_id := nextval('addresses_id_seq');
    end if;
    if rec_office_count.lq_count > 0 then
      rec_lq.office_id := nextval('offices_id_seq');
      rec_lq.mailing_id := nextval('addresses_id_seq');
      rec_lq.delivery_id := nextval('addresses_id_seq');
    end if;
    update colin_extract.office
       set office_type = case when office_typ_cd = 'RG' then 'registeredOffice'
                              when office_typ_cd = 'RC' then 'recordsOffice'  
                              when office_typ_cd = 'DS' then 'custodialOffice' 
                              when office_typ_cd = 'LQ' then 'liquidationRecordsOffice' else office_typ_cd end,
           office_id = case when office_typ_cd = 'RG' then rec_rg.office_id
                            when office_typ_cd = 'RC' then rec_rc.office_id 
                            when office_typ_cd = 'DS' then rec_ds.office_id 
                            when office_typ_cd = 'LQ' then rec_lq.office_id end,
           mailing_id = case when office_typ_cd = 'RG' then rec_rg.mailing_id
                             when office_typ_cd = 'RC' then rec_rc.mailing_id 
                             when office_typ_cd = 'DS' then rec_ds.mailing_id 
                             when office_typ_cd = 'LQ' then rec_lq.mailing_id end,
           delivery_id = case when office_typ_cd = 'RG' then rec_rg.delivery_id
                              when office_typ_cd = 'RC' then rec_rc.delivery_id 
                              when office_typ_cd = 'DS' then rec_ds.delivery_id 
                              when office_typ_cd = 'LQ' then rec_lq.delivery_id end
     where corp_num = p_corp_num;

    update colin_extract.corp_party
       set prev_party_id = null
     where colin_extract.corp_party.corp_num = p_corp_num
       and colin_extract.corp_party.prev_party_id is not null
       and colin_extract.corp_party.prev_party_id > 0
       and not exists (select cp2.corp_party_id 
                         from colin_extract.corp_party cp2 
                        where cp2.corp_num = colin_extract.corp_party.corp_num 
                          and cp2.corp_party_id = colin_extract.corp_party.prev_party_id);
    update colin_extract.corp_party
       set party_id = nextval('parties_id_seq'),
           mailing_id = nextval('offices_id_seq'),
           delivery_id = nextval('offices_id_seq'),
           party_role_id = case when role is not null then nextval('party_roles_id_seq') else null end
     where corp_num = p_corp_num
       and (prev_party_id is null or prev_party_id = 0);

    update colin_extract.offices_held
       set party_role_id = nextval('party_roles_id_seq')
      from colin_extract.corp_party cp
     where cp.corp_num = p_corp_num
       and cp.party_typ_cd = 'OFF'
       and (cp.prev_party_id is null or cp.prev_party_id = 0)
       and cp.corp_party_id = colin_extract.offices_held.corp_party_id;

    update_party_count := 0;
    select count(cp.corp_party_id)
      into null_party_count
      from colin_extract.corp_party cp
     where cp.corp_num = p_corp_num
       and cp.party_typ_cd != 'OFF'
       and cp.prev_party_id is not null
       and cp.prev_party_id > 0
       and cp.party_id is null;
    while update_party_count < 20 and null_party_count > 0 loop
      update_party_count := update_party_count + 1;
      update colin_extract.corp_party
         set party_id = cp.party_id,
             mailing_id = cp.mailing_id,
             delivery_id = cp.delivery_id,
             party_role_id = cp.party_role_id
        from colin_extract.corp_party cp
       where colin_extract.corp_party.corp_num = p_corp_num
         and colin_extract.corp_party.prev_party_id is not null
         and colin_extract.corp_party.prev_party_id > 0
         and colin_extract.corp_party.corp_num = cp.corp_num
         and colin_extract.corp_party.prev_party_id = cp.corp_party_id;

      select count(cp.corp_party_id)
        into null_party_count
        from colin_extract.corp_party cp
       where cp.corp_num = p_corp_num
         and cp.party_typ_cd != 'OFF'
         and cp.prev_party_id is not null
         and cp.prev_party_id > 0
         and cp.party_id is null;
    end loop;

    open cur_officer(p_corp_num);
    loop
      fetch cur_officer into rec_officer;
      exit when not found;      
      if rec_officer.exists_party_id is null then
        update colin_extract.offices_held
           set party_role_id =  nextval('party_roles_id_seq')
         where corp_party_id = rec_officer.corp_party_id
           and officer_typ_cd = rec_officer.officer_typ_cd;
      end if;
      update_officer_count := update_officer_count + 1;
    end loop;
    close cur_officer;

    if update_officer_count > 0 then
      update colin_extract.offices_held
         set party_role_id = oh.party_role_id        
        from colin_extract.corp_party cp, colin_extract.offices_held oh
       where cp.corp_num = p_corp_num
         and cp.party_typ_cd = 'OFF'
         and cp.prev_party_id is not null
         and cp.prev_party_id > 0
         and cp.corp_party_id = colin_extract.offices_held.corp_party_id
         and colin_extract.offices_held.party_role_id is null
         and oh.corp_party_id = coalesce((select max(cp2.corp_party_id)
                                            from colin_extract.corp_party cp2
                                           where cp2.corp_num = cp.corp_num
                                             and cp2.prev_party_id = cp.prev_party_id
                                             and cp2.corp_party_id < cp.corp_party_id),
                                          cp.prev_party_id)
         and colin_extract.offices_held.officer_typ_cd = oh.officer_typ_cd;
      select count(cp.corp_party_id)
        into null_officer_count
        from colin_extract.corp_party cp, colin_extract.offices_held oh
       where cp.corp_num = p_corp_num
         and cp.party_typ_cd = 'OFF'
         and cp.prev_party_id is not null
         and cp.prev_party_id > 0
         and cp.corp_party_id = oh.corp_party_id
         and oh.party_role_id is null;
      update_officer_count := 0;
      while update_officer_count < 20 and null_officer_count > 0 loop
        update_officer_count := update_officer_count + 1;
        update colin_extract.offices_held
           set party_role_id = oh.party_role_id        
          from colin_extract.corp_party cp, colin_extract.offices_held oh
         where cp.corp_num = p_corp_num
           and cp.party_typ_cd = 'OFF'
           and cp.prev_party_id is not null
           and cp.prev_party_id > 0
           and cp.corp_party_id = colin_extract.offices_held.corp_party_id
           and colin_extract.offices_held.party_role_id is null
           and oh.corp_party_id = coalesce((select max(cp2.corp_party_id)
                                              from colin_extract.corp_party cp2
                                             where cp2.corp_num = cp.corp_num
                                               and cp2.prev_party_id = cp.prev_party_id
                                               and cp2.corp_party_id < cp.corp_party_id),
                                            cp.prev_party_id)
           and colin_extract.offices_held.officer_typ_cd = oh.officer_typ_cd;
        select count(cp.corp_party_id)
          into null_officer_count
          from colin_extract.corp_party cp, colin_extract.offices_held oh
         where cp.corp_num = p_corp_num
           and cp.party_typ_cd = 'OFF'
           and cp.prev_party_id is not null
           and cp.prev_party_id > 0
           and cp.corp_party_id = oh.corp_party_id
           and oh.party_role_id is null;
      end loop;
    end if;

  end if;
  return exists_counter;
end;
$$;

-- Load the businesses_version history for a single company. 
create or replace function public.colin_hist_corp_businesses(p_corp_num character varying,
                                                             p_business_id integer) returns integer
  language plpgsql
as $$
declare
  cur_hist_filings cursor(v_corp_num character varying)
    for select e.event_id, e.event_type_cd, e.event_timerstamp, f.transaction_id, f.filing_type,
               (select f2.filing_type_cd
                  from colin_extract.filing f2
                 where ce.colin_event_id = f2.event_id) as colin_filing_type,
               case when f.filing_type in ('alteration','incorporationApplication','amalgamationApplication','conversion') then
                         (select cr.restriction_ind 
                            from colin_extract.corp_restriction cr 
                           where cr.corp_num = e.corp_num and cr.start_event_id = e.event_id)
                    else null end as restriction_ind,
               c.recognition_dts as founding_date,
               case when left(c.corp_type_cd, 1) = 'Q' then 'BC' else c.corp_type_cd end as legal_type,
               case when c.bn_15 is not null then bn_15 else bn_9 end as tax_id,
               c.send_ar_ind, c.last_ar_reminder_year,
               case when f.filing_type in ('alteration','incorporationApplication','amalgamationApplication',
                                           'transition','noticeOfWithdrawal','restoration','correction',
                                           'restorationApplication','changeOfName','conversion') then
                         (select cn.corp_name 
                            from colin_extract.corp_name cn 
                           where cn.corp_num = e.corp_num and cn.start_event_id = e.event_id and cn.corp_name_typ_cd in ('CO', 'NB'))
                    else null end as legal_name,
               (select min(f2.transaction_id)
                 from filings f2
                where f2.business_id = b.id
                  and f2.transaction_id > f.transaction_id) as end_transaction_id
          from businesses b, filings f, colin_event_ids ce, colin_extract.event e, colin_extract.corporation c
         where b.identifier = v_corp_num
           and b.identifier = c.corp_num
           and b.identifier = e.corp_num
           and b.id = f.business_id
           and f.source = 'COLIN'
           and f.status = 'COMPLETED'
           and f.filing_type != 'conversionLedger'
           and f.id = ce.filing_id
           and ce.colin_event_id = e.event_id
        order by f.id;
  rec_filing record;
  counter integer := 0;
  colin_filing_type varchar(20);
  rec_business record;
  rec_change record;
begin

  open cur_hist_filings(p_corp_num);
  loop
    fetch cur_hist_filings into rec_filing;
    exit when not found;
    if rec_filing.colin_filing_type is not null then
      colin_filing_type := rec_filing.colin_filing_type;
    else
      colin_filing_type := rec_filing.event_type_cd;
    end if;
    
    if counter = 0 then
      insert into businesses_version(id, last_modified, legal_name, founding_date, identifier, fiscal_year_end_date,
                                     last_ledger_timestamp, legal_type, restriction_ind, last_coa_date, last_cod_date, state,
                                     admin_freeze, send_ar_ind, no_dissolution, in_liquidation, tax_id,
                                     last_ar_reminder_year, transaction_id, end_transaction_id, operation_type)
        values(p_business_id, rec_filing.founding_date, rec_filing.legal_name, rec_filing.founding_date, p_corp_num,
               rec_filing.founding_date, rec_filing.founding_date, rec_filing.legal_type,
               case when rec_filing.restriction_ind is not null then rec_filing.restriction_ind else false end,
               rec_filing.founding_date, rec_filing.founding_date, 'ACTIVE', false, rec_filing.send_ar_ind, false,
               false, rec_filing.tax_id, rec_filing.last_ar_reminder_year::integer, rec_filing.transaction_id, rec_filing.end_transaction_id, 0);
      select *
        into rec_business
        from businesses_version
       where id = p_business_id
         and transaction_id = rec_filing.transaction_id
      fetch first 1 rows only;
    else
      rec_business.transaction_id := rec_filing.transaction_id;
      rec_business.end_transaction_id := rec_filing.end_transaction_id;
      rec_business.last_modified := rec_filing.event_timerstamp;
      if rec_filing.restriction_ind is not null then
        rec_business.restriction_ind := rec_filing.restriction_ind;
      end if;
      if rec_filing.legal_name is not null then
        rec_business.legal_name := rec_filing.legal_name;
      end if;
      if rec_filing.filing_type in ('annualReport','alteration','changeOfAddress','changeOfOfficers','legacyOther') then
        rec_business.last_coa_date := rec_business.last_modified; 
      end if;
      if rec_filing.filing_type = 'annualReport' then
        if rec_business.last_ar_date is not null then
          rec_business.last_ar_date := rec_business.last_ar_date + interval '1 years';
          rec_business.last_ar_year := rec_business.last_ar_year + 1;
        else
         rec_business.last_ar_date := to_timestamp(to_char(rec_filing.founding_date, 'YYYY-MM-DD') || ' 00:00:00', 'YYYY-MM-DD HH24:MI:SS') at time zone 'utc' + interval '1 years';
         rec_business.last_ar_year := cast(extract(year from rec_filing.founding_date) as int) + 1;
        end if;
      elsif rec_filing.filing_type = 'changeOfDirectors' then
        if rec_business.last_cod_date is null or rec_business.last_cod_date <= rec_business.founding_date then
          rec_business.last_cod_date := to_timestamp(to_char(rec_business.founding_date, 'YYYY-MM-DD') || ' 00:00:00', 'YYYY-MM-DD HH24:MI:SS') at time zone 'utc';
        else
          rec_business.last_cod_date := rec_business.last_modified;
        end if;
      elsif rec_filing.filing_type = 'alteration' then
        if rec_filing.colin_filing_type = 'NOALB' then
          rec_business.legal_type := 'BC';
        elsif rec_filing.colin_filing_type = 'NOALC' then
          rec_business.legal_type := 'CC';
        elsif rec_filing.colin_filing_type = 'NOALU' and left(p_corp_num, 1) = 'C' then
          rec_business.legal_type := 'CUL';
        elsif rec_filing.colin_filing_type = 'NOALU' then
          rec_business.legal_type := 'ULC';
        end if;
      elsif rec_filing.colin_filing_type is not null and 
         rec_filing.colin_filing_type in ('SYSDS','SYSDA','SYSDT','SYSDF','SYSDL','CONVDS', 'CONVDSF', 'CONVDSL', 'CONVDSO',
                                          'ADVD2','ADVDS','DISLC','DISLV','CO_PF', 'AM_PF') then
        rec_business.state := 'HISTORICAL';
        rec_business.dissolution_date := rec_filing.event_timerstamp;
      elsif rec_filing.colin_filing_type is not null and 
            rec_filing.colin_filing_type in ('SYSD1', 'SYSD2', 'SYST1', 'SYST2', 'CONVRSTR', 'CONVLRSTR', 'CO_PO', 'AM_PO') then
        rec_business.state := 'ACTIVE';
        rec_business.dissolution_date := null;
      elsif rec_filing.filing_type = 'transition' then
        rec_business.state := 'ACTIVE';
        if rec_business.last_cod_date is null or rec_business.last_cod_date <= rec_business.founding_date then
          rec_business.last_cod_date := to_timestamp(to_char(rec_business.founding_date, 'YYYY-MM-DD') || ' 00:00:00', 'YYYY-MM-DD HH24:MI:SS') at time zone 'utc';
        else
          rec_business.last_cod_date := rec_business.last_modified;
        end if;
      elsif rec_filing.filing_type = 'restoration' then
        rec_business.state := 'ACTIVE';
      elsif rec_filing.filing_type in ('ADMIN', 'ADCORP') then
        select *
          into rec_change
          from colin_extract.corp_state
        where corp_num = p_corp_num and start_event_id = rec_filing.event_id;
        if FOUND then
          if rec_change.op_state_type_cd = 'ACT' then
            rec_business.state := 'ACTIVE';
            rec_business.dissolution_date := null;
          else
            rec_business.state := 'HISTORICAL';
            rec_business.dissolution_date := rec_filing.event_timerstamp;
          end if;
        end if;
      elsif rec_filing.filing_type = 'continuedOut' or 
            (rec_filing.colin_filing_type is not null and rec_filing.colin_filing_type in ('COUTI', 'CONTO', 'AMALO', 'CONVCOUT')) then
        if rec_filing.colin_filing_type is not null and rec_filing.colin_filing_type in ('COUTI', 'AMALO', 'CONVCOUT') then
          rec_business.state := 'HISTORICAL';
        end if;
        select *
          into rec_change
          from colin_extract.cont_out
        where corp_num = p_corp_num and start_event_id = rec_filing.event_id;
        if FOUND then
          rec_business.continuation_out_date := rec_change.cont_out_dt;
          rec_business.foreign_jurisdiction := rec_change.can_jur_typ_cd;
          rec_business.foreign_legal_name := rec_change.home_company_nme;
          rec_business.foreign_jurisdiction_region := case when rec_change.othr_juri_desc is not null then left(rec_change.othr_juri_desc, 10) else null end;
        end if;
      elsif rec_filing.filing_type = 'noticeOfWithdrawal' then
        select f.event_id, f.filing_type_cd
          into rec_change
          from colin_extract.filing f
         where f.withdrawn_event_id = rec_filing.event_id;
        if rec_change.filing_type_cd in ('ICORP', 'CONTI', 'TRANS') then
          rec_business.state := 'HISTORICAL';
        elsif rec_change.filing_type_cd = 'ADVD2' then
          rec_business.state := 'ACTIVE';
        elsif rec_change.filing_type_cd in ('AMALH', 'AMLVU', 'AMALV', 'AMLRU', 'AMALR') then
          rec_business.state := 'HISTORICAL';
        end if;
      end if;
      
      insert into businesses_version
        values (rec_business.id,rec_business.last_modified,rec_business.last_ledger_id,rec_business.last_remote_ledger_id,
                rec_business.last_ar_date,rec_business.legal_name,rec_business.founding_date,rec_business.dissolution_date,
                rec_business.identifier,rec_business.tax_id,rec_business.fiscal_year_end_date,rec_business.submitter_userid,
                rec_business.transaction_id,rec_business.end_transaction_id,1,rec_business.last_agm_date,
                rec_business.last_ledger_timestamp,rec_business.legal_type,rec_business.restriction_ind,rec_business.last_ar_year,
                rec_business.association_type,rec_business.last_coa_date,rec_business.last_cod_date,rec_business.state,
                rec_business.admin_freeze,rec_business.state_filing_id,rec_business.naics_key,rec_business.naics_code,
                rec_business.naics_description,rec_business.start_date,rec_business.foreign_jurisdiction,
                rec_business.foreign_legal_name,rec_business.send_ar_ind,rec_business.restoration_expiry_date,
                rec_business.last_ar_reminder_year,rec_business.continuation_out_date,rec_business.foreign_jurisdiction_region,
                rec_business.no_dissolution,rec_business.last_tr_year,rec_business.amalgamation_out_date,
                rec_business.in_liquidation,rec_business.accession_number);  
    end if;

    counter := counter + 1;
  end loop;
  close cur_hist_filings;
  return counter;
end;
$$;

-- Load the share structure history for a single company.
-- Insert into the share_classes, share_series, share_classes_version, and share_series_version tables.
create or replace function public.colin_hist_corp_shares(p_corp_num character varying,
                                                         p_business_id integer) returns integer
  language plpgsql
as $$
declare
  cur_share_class cursor(v_corp_num character varying)
    for select e.transaction_id,
               (select e2.transaction_id 
                  from colin_extract.event e2
                 where s.end_event_id is not null and s.end_event_id > 0
                   and e2.event_id = s.end_event_id) as end_transaction_id,
               (select count(ss.series_id) 
                  from colin_extract.share_series ss 
                 where ss.corp_num = sc.corp_num 
                   and ss.start_event_id = sc.start_event_id
                   and ss.share_class_id = sc.share_class_id) as series_count,
               sc.share_class_id,
               case when sc.currency_typ_cd = 'OTH' then 'OTHER' else sc.currency_typ_cd end as currency_typ_cd,
               case when position('SHARES' in TRIM(UPPER(sc.class_nme))) < 1 then sc.class_nme || ' Shares'
                    else sc.class_nme end as class_nme,
               sc.max_share_ind, sc.share_quantity, sc.spec_rights_ind, sc.par_value_ind, sc.par_value_amt, sc.other_currency,
               sc.start_event_id, sc.new_id
          from colin_extract.share_struct s, colin_extract.share_struct_cls sc, colin_extract.event e
         where e.event_id = s.start_event_id
           and e.corp_num = s.corp_num
           and e.event_id = sc.start_event_id
           and e.corp_num = sc.corp_num
           and e.corp_num = v_corp_num
        order by sc.start_event_id;
  cur_share_series cursor(v_colin_event_id integer, v_corp_num character varying, v_share_class_id integer)
    for select ss.series_id, ss.max_share_ind, ss.share_quantity, ss.spec_right_ind, ss.series_nme
          from colin_extract.share_series ss
         where ss.corp_num = v_corp_num
           and ss.start_event_id = v_colin_event_id
           and ss.share_class_id = v_share_class_id
      order by ss.series_id;
  counter integer := 0;
  rec_share_class record;
  rec_share_series record;
begin
  open cur_share_class(p_corp_num);
  loop
    fetch cur_share_class into rec_share_class;
    exit when not found;
    counter := counter + 1;
    if rec_share_class.end_transaction_id is null then
      insert into share_classes
        values(rec_share_class.new_id,
               rec_share_class.class_nme,
               rec_share_class.share_class_id,
               rec_share_class.max_share_ind,
               rec_share_class.share_quantity,
               rec_share_class.par_value_ind,
               rec_share_class.par_value_amt,
               rec_share_class.currency_typ_cd,
               rec_share_class.spec_rights_ind,
               p_business_id,
               rec_share_class.other_currency); 
    end if;
    insert into share_classes_version
      values(rec_share_class.new_id,
             rec_share_class.class_nme,
             rec_share_class.share_class_id,
             rec_share_class.max_share_ind,
             rec_share_class.share_quantity,
             rec_share_class.par_value_ind,
             rec_share_class.par_value_amt,
             rec_share_class.currency_typ_cd,
             rec_share_class.spec_rights_ind,
             p_business_id,
             rec_share_class.transaction_id,
             rec_share_class.end_transaction_id,
             0,
             rec_share_class.other_currency);     
    if rec_share_class.end_transaction_id is not null then
      insert into share_classes_version
        values(rec_share_class.new_id,
               rec_share_class.class_nme,
               rec_share_class.share_class_id,
               rec_share_class.max_share_ind,
               rec_share_class.share_quantity,
               rec_share_class.par_value_ind,
               rec_share_class.par_value_amt,
               rec_share_class.currency_typ_cd,
               rec_share_class.spec_rights_ind,
               p_business_id,
               rec_share_class.end_transaction_id,
               null,
               2,
               rec_share_class.other_currency);     
    end if;

    if rec_share_class.series_count > 0 then
      open cur_share_series(rec_share_class.start_event_id, p_corp_num, rec_share_class.share_class_id);
      loop
        fetch cur_share_series into rec_share_series;
        exit when not found;
        if rec_share_class.end_transaction_id is null then
          insert into share_series
            values(rec_share_series.new_id,
                   rec_share_series.series_nme,
                   rec_share_series.series_id,
                   rec_share_series.max_share_ind,
                   rec_share_series.share_quantity,
                   rec_share_series.spec_right_ind,
                   rec_share_class.new_id); 
        end if;
        insert into share_series_version
          values(rec_share_series.new_id,
                 rec_share_series.series_nme,
                 rec_share_series.series_id,
                 rec_share_series.max_share_ind,
                 rec_share_series.share_quantity,
                 rec_share_series.spec_right_ind,
                 rec_share_class.new_id,
                 rec_share_class.transaction_id,
                 rec_share_class.end_transaction_id,
                 0);
        if rec_share_class.end_transaction_id is not null then
          insert into share_series_version
            values(rec_share_series.new_id,
                   rec_share_series.series_nme,
                   rec_share_series.series_id,
                   rec_share_series.max_share_ind,
                   rec_share_series.share_quantity,
                   rec_share_series.spec_right_ind,
                   rec_share_class.new_id,
                   rec_share_class.end_transaction_id,
                   null,
                   2);
        end if;
      end loop;
      close cur_share_series;
    end if;
  end loop;
  close cur_share_class;
  return counter;
end;
$$;

-- Load the offices history for a single company.
-- Insert into the offices, offices_version, addresses, and addresses_version tables.
create or replace function public.colin_hist_corp_offices(p_corp_num character varying,
                                                          p_business_id integer) returns integer
  language plpgsql
as $$
declare
  cur_office cursor(v_corp_num character varying)
    for select e.transaction_id,
               (select e2.transaction_id 
                  from colin_extract.event e2
                 where o.end_event_id is not null and o.end_event_id > 0
                   and e2.event_id = o.end_event_id) as end_transaction_id,
               o.start_event_id, o.office_typ_cd, o.mailing_addr_id, o.delivery_addr_id, o.office_type, o.office_id,
               o.mailing_id, o.delivery_id
          from colin_extract.office o, colin_extract.event e
         where e.corp_num = v_corp_num
           and e.event_id = o.start_event_id
           and e.corp_num = o.corp_num
        order by o.start_event_id;
  counter integer := 0;
  rec_office record;
  rec_mailing record;
  rec_delivery record;
  update_type integer := 0;
  rg_counter integer := 0; 
  rc_counter integer := 0; 
  ds_counter integer := 0; 
  lq_counter integer := 0; 
begin
  open cur_office(p_corp_num);
  loop
    fetch cur_office into rec_office;
    exit when not found;
    counter := counter + 1;
    if rec_office.office_typ_cd = 'RG' and rg_counter = 0 then
      rg_counter := 1;
      update_type := 0;
    elsif rec_office.office_typ_cd = 'RC' and rc_counter = 0 then
      rc_counter := 1;
      update_type := 0;
    elsif rec_office.office_typ_cd = 'DS' and ds_counter = 0 then
      ds_counter := 1;
      update_type := 0;
    elsif rec_office.office_typ_cd = 'LQ' and lq_counter = 0 then
      lq_counter := 1;
      update_type := 0;
    else
      update_type := 1;
    end if;
    if rec_office.mailing_addr_id is not null then
      select addr_line_1, city, province, country_typ_cd, postal_cd, delivery_instructions,
             case when addr_line_2 is not null and addr_line_3 is not null then addr_line_2 || ' ' || addr_line_3
                  else addr_line_2 end as addr_line_2              
        into rec_mailing
        from colin_extract.address 
       where addr_id = rec_office.mailing_addr_id;
    end if;
    if rec_office.delivery_addr_id is not null then
      select addr_line_1, city, province, country_typ_cd, postal_cd, delivery_instructions,
             case when addr_line_2 is not null and addr_line_3 is not null then addr_line_2 || ' ' || addr_line_3
                  else addr_line_2 end as addr_line_2              
        into rec_delivery
        from colin_extract.address 
       where addr_id = rec_office.delivery_addr_id;
    end if;
    if rec_office.end_transaction_id is null then
      insert into offices values(rec_office.office_id, rec_office.office_type, null, p_business_id);
      if rec_office.mailing_addr_id is not null then
        insert into addresses 
          values(rec_office.mailing_id, 'mailing', rec_mailing.addr_line_1, rec_mailing.addr_line_2,
                 rec_mailing.city, rec_mailing.province, rec_mailing.country_typ_cd, rec_mailing.postal_cd,
                 rec_mailing.delivery_instructions, p_business_id, rec_office.office_id, null);
      end if;
      if rec_office.delivery_addr_id is not null then
        insert into addresses 
          values(rec_office.delivery_id, 'delivery', rec_delivery.addr_line_1, rec_delivery.addr_line_2,
                 rec_delivery.city, rec_delivery.province, rec_delivery.country_typ_cd, rec_delivery.postal_cd,
                 rec_delivery.delivery_instructions, p_business_id, rec_office.office_id, null);
      end if;
    end if;
    if update_type = '0' then
      insert into offices_version values(rec_office.office_id,
                                         rec_office.office_type,
                                         null,
                                         p_business_id,
                                         rec_office.transaction_id,
                                         rec_office.end_transaction_id,
                                         update_type);
    end if;
    if rec_office.mailing_addr_id is not null then
      insert into addresses_version
        values(rec_office.mailing_id, 'mailing', rec_mailing.addr_line_1, rec_mailing.addr_line_2,
               rec_mailing.city, rec_mailing.province, rec_mailing.country_typ_cd, rec_mailing.postal_cd,
               rec_mailing.delivery_instructions, p_business_id, rec_office.transaction_id, rec_office.end_transaction_id,
               update_type, rec_office.office_id, null);
    end if;
    if rec_office.delivery_addr_id is not null then
      insert into addresses_version
        values(rec_office.delivery_id, 'delivery', rec_delivery.addr_line_1, rec_delivery.addr_line_2,
               rec_delivery.city, rec_delivery.province, rec_delivery.country_typ_cd, rec_delivery.postal_cd,
               rec_delivery.delivery_instructions, p_business_id, rec_office.transaction_id, rec_office.end_transaction_id,
               update_type, rec_office.office_id, null);
    end if;
  end loop;
  close cur_office;
  return counter;
end;
$$;

-- Load the parties history excluding officers for a single company.
-- Insert into the party_roles, party_roles_version, parties, parties_version, addresses, and addresses_version tables.
create or replace function public.colin_hist_corp_parties(p_corp_num character varying,
                                                          p_business_id integer) returns integer
  language plpgsql
as $$
declare
  cur_party cursor(v_corp_num character varying)
    for select e.transaction_id,
               (select e2.transaction_id 
                  from colin_extract.event e2
                 where cp.end_event_id is not null and cp.end_event_id > 0
                   and e2.event_id = cp.end_event_id) as end_transaction_id,
               cp.mailing_addr_id, cp.delivery_addr_id, cp.party_typ_cd,
               case when cp.appointment_dt is not null then
                         cast((to_timestamp(to_char(cp.appointment_dt, 'YYYY-MM-DD') || ' 00:00:00', 'YYYY-MM-DD HH24:MI:SS') at time zone 'utc') as timestamp with time zone)
                    when cp.appointment_dt is null and cp.prev_party_id is not null and cp.prev_party_id > 0 then
                         (select cast((to_timestamp(to_char(e2.event_timerstamp, 'YYYY-MM-DD') || ' 00:00:00', 'YYYY-MM-DD HH24:MI:SS') at time zone 'utc') as timestamp with time zone)
                            from colin_extract.event e2, colin_extract.corp_party cp2
                           where cp2.corp_num = cp.corp_num
                             and cp2.corp_party_id = cp.prev_party_id
                             and e2.corp_num = cp.corp_num
                             and e2.event_id = cp2.start_event_id)
                    else cp.appointment_dt end as appointment_dt,
               case when cp.cessation_dt is not null then
                         cast((to_timestamp(to_char(cp.cessation_dt, 'YYYY-MM-DD') || ' 00:00:00', 'YYYY-MM-DD HH24:MI:SS') at time zone 'utc') as timestamp with time zone)
                    else cp.cessation_dt end as cessation_dt,
               case when cp.last_name is not null and trim(cp.last_name) != '' then upper(cp.last_name) else null end as last_name,
               case when cp.middle_name is not null and trim(cp.middle_name) != '' then upper(cp.middle_name) else null end as middle_name,
               case when cp.first_name is not null and  trim(cp.first_name) != '' then upper(cp.first_name) else null end as first_name,
               case when cp.business_name is not null and  trim(cp.business_name) != '' then upper(cp.business_name) else null end as business_name,
               cp.email_address, cp.prev_party_id, cp.start_event_id, cp.end_event_id,
               cp.role as party_role, cp.party_id, cp.party_role_id, cp.mailing_id, cp.delivery_id,
               cast((to_timestamp(to_char(e.event_timerstamp, 'YYYY-MM-DD') || ' 00:00:00', 'YYYY-MM-DD HH24:MI:SS') at time zone 'utc') as timestamp with time zone) as party_date,
               case when cp.last_name is not null and trim(cp.last_name) != '' then 'person' else 'organization' end as party_type,
               (select count(cp2.corp_party_id)
                  from colin_extract.corp_party cp2
                 where cp2.corp_num = cp.corp_num
                   and cp2.prev_party_id = cp.corp_party_id) as edit_count
         from colin_extract.corp_party cp, colin_extract.event e
         where e.corp_num = v_corp_num
           and e.event_id = cp.start_event_id
           and e.corp_num = cp.corp_num
           and cp.party_typ_cd != 'OFF'
        order by corp_party_id;
  counter integer := 0;
  rec_party record;
  rec_mailing record;
  rec_delivery record;
begin
  open cur_party(p_corp_num);
  loop
    fetch cur_party into rec_party;
    exit when not found;
    counter := counter + 1;
    if rec_party.mailing_addr_id is not null then
      select addr_line_1, city, province, country_typ_cd, postal_cd, delivery_instructions,
             case when addr_line_2 is not null and addr_line_3 is not null then addr_line_2 || ' ' || addr_line_3
                  else addr_line_2 end as addr_line_2              
        into rec_mailing
        from colin_extract.address 
       where addr_id = rec_party.mailing_addr_id;
    else
      rec_party.mailing_id := null;
    end if;
    if rec_party.delivery_addr_id is not null then
      select addr_line_1, city, province, country_typ_cd, postal_cd, delivery_instructions,
             case when addr_line_2 is not null and addr_line_3 is not null then addr_line_2 || ' ' || addr_line_3
                  else addr_line_2 end as addr_line_2              
        into rec_delivery
        from colin_extract.address 
       where addr_id = rec_party.delivery_addr_id;
    else
      rec_party.delivery_id := null;
    end if;
    if rec_party.end_event_id is not null and --rec_party.party_typ_cd = 'DIR' and 
       (rec_party.prev_party_id is null or rec_party.prev_party_id < 1) and rec_party.cessation_dt is null then
      rec_party.cessation_dt := rec_party.party_date;
    end if;
    if rec_party.appointment_dt is null and (rec_party.prev_party_id is null or rec_party.prev_party_id < 1) then --rec_party.party_typ_cd = 'DIR' and 
      rec_party.appointment_dt := rec_party.party_date;
    end if;
    
    if rec_party.prev_party_id is null or rec_party.prev_party_id < 1 then
      if rec_party.mailing_addr_id is not null then
        insert into addresses_version
          values(rec_party.mailing_id, 'mailing', rec_mailing.addr_line_1, rec_mailing.addr_line_2,
                 rec_mailing.city, rec_mailing.province, rec_mailing.country_typ_cd, rec_mailing.postal_cd,
                 rec_mailing.delivery_instructions, p_business_id, rec_party.transaction_id, rec_party.end_transaction_id,
                 0, null, null);
      end if;
      if rec_party.delivery_addr_id is not null then
        insert into addresses_version 
          values(rec_party.delivery_id, 'delivery', rec_delivery.addr_line_1, rec_delivery.addr_line_2,
                 rec_delivery.city, rec_delivery.province, rec_delivery.country_typ_cd, rec_delivery.postal_cd,
                 rec_delivery.delivery_instructions, p_business_id, rec_party.transaction_id, rec_party.end_transaction_id,
                 0, null, null);
      end if;

      insert into parties_version 
        values(rec_party.party_id, rec_party.party_type, rec_party.first_name, rec_party.middle_name, rec_party.last_name, null,
               rec_party.business_name, rec_party.delivery_id, rec_party.mailing_id, rec_party.transaction_id, 
               rec_party.end_transaction_id, 0, null, rec_party.email_address, null);      
      insert into party_roles_version 
        values(rec_party.party_role_id, rec_party.party_role, rec_party.appointment_dt, null, p_business_id,
               rec_party.party_id, rec_party.transaction_id, rec_party.end_transaction_id, 0, null, null);
    elsif (rec_party.prev_party_id is not null and rec_party.prev_party_id > 0) or 
          (rec_party.end_event_id is not null and rec_party.edit_count > 0) then -- editing
      insert into parties_version 
        values(rec_party.party_id, rec_party.party_type, rec_party.first_name, rec_party.middle_name, rec_party.last_name, null,
               rec_party.business_name, rec_party.delivery_id, rec_party.mailing_id, rec_party.transaction_id, 
               rec_party.end_transaction_id, 1, null, rec_party.email_address, null);
      insert into party_roles_version 
        values(rec_party.party_role_id, rec_party.party_role, rec_party.appointment_dt, null, p_business_id,
               rec_party.party_id, rec_party.transaction_id, rec_party.end_transaction_id, 1, null, null);
      if rec_party.delivery_addr_id is not null then
        insert into addresses_version 
          values(rec_party.delivery_id, 'delivery', rec_delivery.addr_line_1, rec_delivery.addr_line_2,
                 rec_delivery.city, rec_delivery.province, rec_delivery.country_typ_cd, rec_delivery.postal_cd,
                 rec_delivery.delivery_instructions, p_business_id, rec_party.transaction_id, rec_party.end_transaction_id,
                 1, null, null);
      end if;
      if rec_party.mailing_addr_id is not null then
        insert into addresses_version
          values(rec_party.mailing_id, 'mailing', rec_mailing.addr_line_1, rec_mailing.addr_line_2,
                 rec_mailing.city, rec_mailing.province, rec_mailing.country_typ_cd, rec_mailing.postal_cd,
                 rec_mailing.delivery_instructions, p_business_id, rec_party.transaction_id, rec_party.end_transaction_id,
                 1, null, null);
      end if;
    end if;
    if rec_party.end_event_id is not null and rec_party.edit_count = 0 and rec_party.start_event_id != rec_party.end_event_id then -- removing
      insert into parties_version 
        values(rec_party.party_id, rec_party.party_type, rec_party.first_name, rec_party.middle_name, rec_party.last_name, null,
               rec_party.business_name, rec_party.delivery_id, rec_party.mailing_id, rec_party.end_transaction_id, 
               null, 1, null, rec_party.email_address, null);      
      insert into party_roles_version 
        values(rec_party.party_role_id, rec_party.party_role, rec_party.appointment_dt, rec_party.cessation_dt, p_business_id,
               rec_party.party_id, rec_party.end_transaction_id, null, 1, null, null);    
    end if;

    -- Active if no end event id or if cessation date. Need to verify cessation date rule for all party roles.
    if rec_party.end_event_id is null or (rec_party.end_event_id is not null and rec_party.edit_count = 0) then
      if rec_party.mailing_addr_id is not null then
        insert into addresses 
          values(rec_party.mailing_id, 'mailing', rec_mailing.addr_line_1, rec_mailing.addr_line_2,
                 rec_mailing.city, rec_mailing.province, rec_mailing.country_typ_cd, rec_mailing.postal_cd,
                 rec_mailing.delivery_instructions, p_business_id, null, null);
      end if;
      if rec_party.delivery_addr_id is not null then
        insert into addresses 
          values(rec_party.delivery_id, 'delivery', rec_delivery.addr_line_1, rec_delivery.addr_line_2,
                 rec_delivery.city, rec_delivery.province, rec_delivery.country_typ_cd, rec_delivery.postal_cd,
                 rec_delivery.delivery_instructions, p_business_id, null, null);
      end if;
      insert into parties
        values(rec_party.party_id, rec_party.party_type, rec_party.first_name, rec_party.middle_name, rec_party.last_name, null,
               rec_party.business_name, rec_party.delivery_id, rec_party.mailing_id, null, rec_party.email_address, null);      
      insert into party_roles 
        values(rec_party.party_role_id, rec_party.party_role, rec_party.appointment_dt, rec_party.cessation_dt, p_business_id,
               rec_party.party_id, null, null);
    end if;
  end loop;
  close cur_party;
  return counter;
end;
$$;

-- Load the officers history for a single company.
-- Insert into the party_roles, party_roles_version, parties, parties_version, addresses, and addresses_version tables.
create or replace function public.colin_hist_corp_officers(p_corp_num character varying,
                                                           p_business_id integer) returns integer
  language plpgsql
as $$
declare
  cur_party cursor(v_corp_num character varying)
    for select e.transaction_id,
               (select e2.transaction_id 
                  from colin_extract.event e2
                 where cp.end_event_id is not null and cp.end_event_id > 0
                   and e2.event_id = cp.end_event_id) as end_transaction_id,
               cp.mailing_addr_id, cp.delivery_addr_id, oh.officer_typ_cd,
               case when cp.appointment_dt is not null then
                         cast((to_timestamp(to_char(cp.appointment_dt, 'YYYY-MM-DD') || ' 00:00:00', 'YYYY-MM-DD HH24:MI:SS') at time zone 'utc') as timestamp with time zone)
                    when cp.appointment_dt is null and cp.prev_party_id is not null and cp.prev_party_id > 0 then
                         (select cast((to_timestamp(to_char(e2.event_timerstamp, 'YYYY-MM-DD') || ' 00:00:00', 'YYYY-MM-DD HH24:MI:SS') at time zone 'utc') as timestamp with time zone)
                            from colin_extract.event e2, colin_extract.corp_party cp2
                           where cp2.corp_num = cp.corp_num
                             and cp2.corp_party_id = cp.prev_party_id
                             and e2.corp_num = cp.corp_num
                             and e2.event_id = cp2.start_event_id)
                    else cp.appointment_dt end as appointment_dt,
               case when cp.cessation_dt is not null then
                         cast((to_timestamp(to_char(cp.cessation_dt, 'YYYY-MM-DD') || ' 00:00:00', 'YYYY-MM-DD HH24:MI:SS') at time zone 'utc') as timestamp with time zone)
                    else cp.cessation_dt end as cessation_dt,
               case when cp.last_name is not null and trim(cp.last_name) != '' then upper(cp.last_name) else null end as last_name,
               case when cp.middle_name is not null and trim(cp.middle_name) != '' then upper(cp.middle_name) else null end as middle_name,
               case when cp.first_name is not null and  trim(cp.first_name) != '' then upper(cp.first_name) else null end as first_name,
               case when cp.business_name is not null and  trim(cp.business_name) != '' then upper(cp.business_name) else null end as business_name,
               cp.email_address, cp.prev_party_id, cp.start_event_id, cp.end_event_id,
               oh.role as party_role, cp.party_id, oh.party_role_id, cp.mailing_id, cp.delivery_id,
               cast((to_timestamp(to_char(e.event_timerstamp, 'YYYY-MM-DD') || ' 00:00:00', 'YYYY-MM-DD HH24:MI:SS') at time zone 'utc') as timestamp with time zone) as party_date,
               case when cp.last_name is not null and trim(cp.last_name) != '' then 'person' else 'organization' end as party_type,
               (select count(cp2.corp_party_id)
                  from colin_extract.corp_party cp2
                 where cp2.corp_num = cp.corp_num
                   and (cp2.prev_party_id = cp.corp_party_id or
                        (cp.prev_party_id is not null and cp.prev_party_id > 0 and cp2.prev_party_id = cp.prev_party_id and
                         cp2.corp_party_id > cp.corp_party_id))) as edit_count,
               case when cp.prev_party_id is not null and cp.prev_party_id > 0 then
                         (select count(oh2.corp_party_id)
                           from colin_extract.offices_held oh2
                          where oh2.corp_party_id = coalesce((select max(cp2.corp_party_id)
                                                                from colin_extract.corp_party cp2
                                                               where cp2.corp_num = cp.corp_num
                                                                 and cp2.prev_party_id = cp.prev_party_id
                                                                 and cp2.corp_party_id < cp.corp_party_id),
                                                              cp.prev_party_id)
                            and oh2.role = oh.role)
                    else 0 end as exists_count,
                 case when cp.end_event_id is not null then                 
                         (select count(oh2.corp_party_id)
                           from colin_extract.offices_held oh2, colin_extract.corp_party cp2
                          where cp2.corp_num = cp.corp_num
                            and cp2.start_event_id = cp.end_event_id
                            and cp2.prev_party_id is not null
                            and cp2.prev_party_id > 0
                            and cp.prev_party_id in (cp.corp_party_id, cp.prev_party_id)
                            and cp2.corp_party_id = oh2.corp_party_id
                            and oh2.role = oh.role)
                    else 1 end as keep_count,
                 case when cp.end_event_id is not null then
                           (select cast((to_timestamp(to_char(e.event_timerstamp, 'YYYY-MM-DD') || ' 00:00:00', 'YYYY-MM-DD HH24:MI:SS') at time zone 'utc') as timestamp with time zone)
                              from colin_extract.event e
                             where e.corp_num = cp.corp_num and e.event_id = cp.end_event_id)
                      else null end as party_end_date,
                 (select count(cp2.corp_party_id)
                    from colin_extract.corp_party cp2
                   where cp2.corp_num = cp.corp_num
                     and cp2.party_id = cp.party_id
                     and cp2.corp_party_id < cp.corp_party_id) as party_exists_count
         from colin_extract.corp_party cp, colin_extract.event e, colin_extract.offices_held oh
         where e.corp_num = v_corp_num
           and e.event_id = cp.start_event_id
           and e.corp_num = cp.corp_num
           and cp.party_typ_cd = 'OFF'
           and cp.corp_party_id = oh.corp_party_id
        order by cp.corp_party_id;
  counter integer := 0;
  rec_party record;
  rec_mailing record;
  rec_delivery record;
  last_party_id integer := 0;
begin
  open cur_party(p_corp_num);
  loop
    fetch cur_party into rec_party;
    exit when not found;
    counter := counter + 1;
    if rec_party.party_id != last_party_id then
      last_party_id := rec_party.party_id;
      if rec_party.mailing_addr_id is not null then
        select addr_line_1, city, province, country_typ_cd, postal_cd, delivery_instructions,
               case when addr_line_2 is not null and addr_line_3 is not null then addr_line_2 || ' ' || addr_line_3
                    else addr_line_2 end as addr_line_2              
          into rec_mailing
          from colin_extract.address 
         where addr_id = rec_party.mailing_addr_id;
      else
        rec_party.mailing_id := null;
      end if;
      if rec_party.delivery_addr_id is not null then
        select addr_line_1, city, province, country_typ_cd, postal_cd, delivery_instructions,
               case when addr_line_2 is not null and addr_line_3 is not null then addr_line_2 || ' ' || addr_line_3
                    else addr_line_2 end as addr_line_2              
          into rec_delivery
          from colin_extract.address 
         where addr_id = rec_party.delivery_addr_id;
      else
        rec_party.delivery_id := null;
      end if;
      if rec_party.end_event_id is not null and --rec_party.party_typ_cd = 'DIR' and 
         (rec_party.prev_party_id is null or rec_party.prev_party_id < 1) and rec_party.cessation_dt is null then
        rec_party.cessation_dt := rec_party.party_end_date;
      end if;
      if rec_party.appointment_dt is null and (rec_party.prev_party_id is null or rec_party.prev_party_id < 1) then --rec_party.party_typ_cd = 'DIR' and 
        rec_party.appointment_dt := rec_party.party_date;
      end if;
    
      if rec_party.prev_party_id is null or rec_party.prev_party_id < 1 then
        if rec_party.mailing_addr_id is not null then
          insert into addresses_version
            values(rec_party.mailing_id, 'mailing', rec_mailing.addr_line_1, rec_mailing.addr_line_2,
                   rec_mailing.city, rec_mailing.province, rec_mailing.country_typ_cd, rec_mailing.postal_cd,
                   rec_mailing.delivery_instructions, p_business_id, rec_party.transaction_id, rec_party.end_transaction_id,
                   0, null, null);
        end if;
        if rec_party.delivery_addr_id is not null then
          insert into addresses_version 
            values(rec_party.delivery_id, 'delivery', rec_delivery.addr_line_1, rec_delivery.addr_line_2,
                   rec_delivery.city, rec_delivery.province, rec_delivery.country_typ_cd, rec_delivery.postal_cd,
                   rec_delivery.delivery_instructions, p_business_id, rec_party.transaction_id, rec_party.end_transaction_id,
                   0, null, null);
        end if;

        insert into parties_version 
          values(rec_party.party_id, rec_party.party_type, rec_party.first_name, rec_party.middle_name, rec_party.last_name, null,
                 rec_party.business_name, rec_party.delivery_id, rec_party.mailing_id, rec_party.transaction_id, 
                 rec_party.end_transaction_id, 0, null, rec_party.email_address, null);      
        insert into party_roles_version 
          values(rec_party.party_role_id, rec_party.party_role, rec_party.appointment_dt, null, p_business_id,
                 rec_party.party_id, rec_party.transaction_id, rec_party.end_transaction_id, 0, null, 'OFFICER');
      elsif (rec_party.prev_party_id is not null and rec_party.prev_party_id > 0) or 
            (rec_party.end_event_id is not null and rec_party.edit_count > 0) then -- editing
        insert into parties_version 
          values(rec_party.party_id, rec_party.party_type, rec_party.first_name, rec_party.middle_name, rec_party.last_name, null,
                 rec_party.business_name, rec_party.delivery_id, rec_party.mailing_id, rec_party.transaction_id, 
                 rec_party.end_transaction_id, 1, null, rec_party.email_address, null);
        if rec_party.delivery_addr_id is not null then
          insert into addresses_version 
            values(rec_party.delivery_id, 'delivery', rec_delivery.addr_line_1, rec_delivery.addr_line_2,
                   rec_delivery.city, rec_delivery.province, rec_delivery.country_typ_cd, rec_delivery.postal_cd,
                   rec_delivery.delivery_instructions, p_business_id, rec_party.transaction_id, rec_party.end_transaction_id,
                   1, null, null);
        end if;
        if rec_party.mailing_addr_id is not null then
          insert into addresses_version
            values(rec_party.mailing_id, 'mailing', rec_mailing.addr_line_1, rec_mailing.addr_line_2,
                   rec_mailing.city, rec_mailing.province, rec_mailing.country_typ_cd, rec_mailing.postal_cd,
                   rec_mailing.delivery_instructions, p_business_id, rec_party.transaction_id, rec_party.end_transaction_id,
                   1, null, null);
        end if;
        if rec_party.prev_party_id is not null and rec_party.prev_party_id > 0 and rec_party.exists_count = 0 then -- adding role
          if rec_party.appointment_dt is null then
            rec_party.appointment_dt := rec_party.party_date;
          end if;
          insert into party_roles_version 
            values(rec_party.party_role_id, rec_party.party_role, rec_party.appointment_dt, null, p_business_id,
                   rec_party.party_id, rec_party.transaction_id, rec_party.end_transaction_id, 0, null, 'OFFICER');
        elsif rec_party.end_event_id is not null and rec_party.exists_count > 0 then
          insert into party_roles_version 
            values(rec_party.party_role_id, rec_party.party_role, rec_party.appointment_dt, null, p_business_id,
                   rec_party.party_id, rec_party.transaction_id, rec_party.end_transaction_id, 1, null, 'OFFICER');
        end if;
      end if;
      if rec_party.end_event_id is not null and rec_party.edit_count = 0 then -- removing
        insert into parties_version 
          values(rec_party.party_id, rec_party.party_type, rec_party.first_name, rec_party.middle_name, rec_party.last_name, null,
                 rec_party.business_name, rec_party.delivery_id, rec_party.mailing_id, rec_party.end_transaction_id, 
                 null, 1, null, rec_party.email_address, null);      
        insert into party_roles_version 
          values(rec_party.party_role_id, rec_party.party_role, rec_party.appointment_dt, rec_party.cessation_dt, p_business_id,
                 rec_party.party_id, rec_party.end_transaction_id, null, 1, null, 'OFFICER');    
      elsif rec_party.end_event_id is not null and rec_party.keep_count = 0 then -- removing role
        rec_party.cessation_dt := rec_party.party_end_date;
        insert into party_roles_version 
          values(rec_party.party_role_id, rec_party.party_role, rec_party.appointment_dt, rec_party.cessation_dt, p_business_id,
                 rec_party.party_id, rec_party.end_transaction_id, null, 1, null, 'OFFICER');
      elsif rec_party.end_event_id is null and rec_party.exists_count > 0 then -- editing
        insert into party_roles_version 
          values(rec_party.party_role_id, rec_party.party_role, rec_party.appointment_dt, null, p_business_id,
                 rec_party.party_id, rec_party.transaction_id, rec_party.end_transaction_id, 1, null, 'OFFICER');
      end if;

      -- Active if no end event id or if cessation date. Need to verify cessation date rule for all party roles.
      if rec_party.party_exists_count = 0 then
        if rec_party.mailing_addr_id is not null then
          insert into addresses 
            values(rec_party.mailing_id, 'mailing', rec_mailing.addr_line_1, rec_mailing.addr_line_2,
                   rec_mailing.city, rec_mailing.province, rec_mailing.country_typ_cd, rec_mailing.postal_cd,
                   rec_mailing.delivery_instructions, p_business_id, null, null);
        end if;
        if rec_party.delivery_addr_id is not null then
          insert into addresses 
            values(rec_party.delivery_id, 'delivery', rec_delivery.addr_line_1, rec_delivery.addr_line_2,
                   rec_delivery.city, rec_delivery.province, rec_delivery.country_typ_cd, rec_delivery.postal_cd,
                   rec_delivery.delivery_instructions, p_business_id, null, null);
        end if;
        insert into parties
          values(rec_party.party_id, rec_party.party_type, rec_party.first_name, rec_party.middle_name, rec_party.last_name, null,
                 rec_party.business_name, rec_party.delivery_id, rec_party.mailing_id, null, rec_party.email_address, null);      
      end if;
      if rec_party.end_event_id is null or (rec_party.end_event_id is not null and rec_party.edit_count = 0) or
         (rec_party.end_event_id is not null and rec_party.edit_count > 0 and rec_party.keep_count = 0) then
        insert into party_roles 
          values(rec_party.party_role_id, rec_party.party_role, rec_party.appointment_dt, rec_party.cessation_dt, p_business_id,
                 rec_party.party_id, null, 'OFFICER');
      end if;
    else -- only party role update
      if rec_party.prev_party_id is null or rec_party.prev_party_id < 1 then
        insert into party_roles_version 
          values(rec_party.party_role_id, rec_party.party_role, rec_party.appointment_dt, null, p_business_id,
                 rec_party.party_id, rec_party.transaction_id, rec_party.end_transaction_id, 0, null, 'OFFICER');
      elsif rec_party.prev_party_id is not null and rec_party.prev_party_id > 0 and rec_party.exists_count = 0 then -- editing
        if rec_party.appointment_dt is null then
          rec_party.appointment_dt := rec_party.party_date;
        end if;
        insert into party_roles_version 
             values(rec_party.party_role_id, rec_party.party_role, rec_party.appointment_dt, null, p_business_id,
                    rec_party.party_id, rec_party.transaction_id, rec_party.end_transaction_id, 0, null, 'OFFICER');
      elsif rec_party.end_event_id is not null and rec_party.edit_count > 0 then -- editing
        insert into party_roles_version 
          values(rec_party.party_role_id, rec_party.party_role, rec_party.appointment_dt, null, p_business_id,
                 rec_party.party_id, rec_party.transaction_id, rec_party.end_transaction_id, 1, null, 'OFFICER');
      elsif rec_party.end_event_id is null and rec_party.exists_count > 0 then -- editing
        insert into party_roles_version 
          values(rec_party.party_role_id, rec_party.party_role, rec_party.appointment_dt, null, p_business_id,
                 rec_party.party_id, rec_party.transaction_id, rec_party.end_transaction_id, 1, null, 'OFFICER');
      end if;
      if rec_party.end_event_id is not null and (rec_party.edit_count = 0 or rec_party.keep_count = 0) then -- removing
        if rec_party.appointment_dt is null then
          rec_party.appointment_dt := rec_party.party_date;
        end if;
        if rec_party.cessation_dt is null then
          rec_party.cessation_dt := rec_party.party_end_date;
        end if;
        insert into party_roles_version 
          values(rec_party.party_role_id, rec_party.party_role, rec_party.appointment_dt, rec_party.cessation_dt, p_business_id,
                 rec_party.party_id, rec_party.end_transaction_id, null, 1, null, 'OFFICER');    
      end if;
      -- role added or removed
      if rec_party.end_event_id is null or (rec_party.end_event_id is not null and rec_party.edit_count = 0) or
         (rec_party.end_event_id is not null and rec_party.edit_count > 0 and rec_party.keep_count = 0) then
        insert into party_roles 
          values(rec_party.party_role_id, rec_party.party_role, rec_party.appointment_dt, rec_party.cessation_dt, p_business_id,
                 rec_party.party_id, null, 'OFFICER');
      end if;
    end if;
  end loop;
  close cur_party;
  return counter;
end;
$$;

-- Load the corp resolutions history for a single company.
-- Insert into the resolutions and resolutions_version tables.
create or replace function public.colin_hist_corp_resolutions(p_corp_num character varying,
                                                              p_business_id integer) returns integer
  language plpgsql
as $$
declare
  cur_resolution cursor(v_corp_num character varying)
    for select e.transaction_id,
               case when r.resolution_dt is not null then
                         cast((to_timestamp(to_char(r.resolution_dt, 'YYYY-MM-DD') || ' 00:00:00', 'YYYY-MM-DD HH24:MI:SS') at time zone 'utc') as timestamp with time zone)
                    else r.resolution_dt end as resolution_dt,
               r.start_event_id, r.resolution_id
          from colin_extract.resolution r, colin_extract.event e
         where e.corp_num = v_corp_num
           and e.corp_num = r.corp_num
           and e.event_id = r.start_event_id
        order by r.start_event_id;
  counter integer := 0;
  rec_resolution record;
begin
  open cur_resolution(p_corp_num);
  loop
    fetch cur_resolution into rec_resolution;
    exit when not found;
    counter := counter + 1;
    insert into resolutions_version
      values(rec_resolution.resolution_id, rec_resolution.resolution_dt, 'SPECIAL', p_business_id,
             rec_resolution.transaction_id, rec_resolution.end_transaction_id, 0, null, null, null, null);
    if rec_resolution.end_event_id is not null then
      insert into resolutions_version
        values(rec_resolution.resolution_id, rec_resolution.resolution_dt, 'SPECIAL', p_business_id,
               rec_resolution.end_transaction_id, null, 1, null, null, null, null);
    else
      insert into resolutions
        values(rec_resolution.resolution_id, rec_resolution.resolution_dt, 'SPECIAL', p_business_id, null, null, null, null);
    end if;
  end loop;
  close cur_resolution;
  return counter;
end;
$$;

-- Load the corp name aliases history for a single company.
-- Insert into the aliases and aliases_version tables.
create or replace function public.colin_hist_corp_aliases(p_corp_num character varying,
                                                          p_business_id integer) returns integer
  language plpgsql
as $$
declare
  cur_alias cursor(v_corp_num character varying)
    for select e.transaction_id,
               (select e2.transaction_id 
                  from colin_extract.event e2
                 where cn.end_event_id is not null
                   and e2.event_id = cn.end_event_id) as end_transaction_id,
               upper(cn.corp_name) as corp_name, cn.corp_name_typ_cd, cn.start_event_id, cn.end_event_id, cn.alias_id, cn.alias_type,
               case when cn.end_event_id is not null then
                         (select count(cn2.start_event_id)
                            from colin_extract.corp_name cn2
                           where cn2.corp_num = cn.corp_num
                             and cn2.start_event_id = cn.end_event_id
                             and cn2.corp_name_typ_cd = cn.corp_name_typ_cd)
                    else 0 end as edit_count,
               case when cn.end_event_id is not null then
                         (select count(cn2.start_event_id)
                            from colin_extract.corp_name cn2
                           where cn2.corp_num = cn.corp_num
                             and cn2.end_event_id = cn.start_event_id
                             and cn2.corp_name_typ_cd = cn.corp_name_typ_cd)
                    else 0 end as exists_count
          from colin_extract.corp_name cn, colin_extract.event e
         where e.corp_num = v_corp_num
           and e.corp_num = cn.corp_num
           and e.event_id = cn.start_event_id
           and cn.corp_name_typ_cd not in ('CO', 'NB')
        order by cn.start_event_id;
  counter integer := 0;
  rec_alias record;
begin
  open cur_alias(p_corp_num);
  loop
    fetch cur_alias into rec_alias;
    exit when not found;
    counter := counter + 1;
    insert into aliases_version
      values(rec_alias.alias_id, rec_alias.corp_name, rec_alias.alias_type, p_business_id, rec_alias.transaction_id,
             rec_alias.end_transaction_id, 0);
    if rec_alias.end_event_id is not null then
      insert into aliases_version
        values(rec_alias.alias_id, rec_alias.corp_name, rec_alias.alias_type, p_business_id, rec_alias.end_transaction_id,
               null, 1);
    else
      insert into aliases values(rec_alias.alias_id, rec_alias.corp_name, rec_alias.alias_type, p_business_id);
    end if;
/*
    if rec_alias.end_event_id is null or (rec_alias.end_event_id is not null and rec_alias.exists_count = 0) then
      insert into aliases_version
        values(rec_alias.alias_id, rec_alias.corp_name, rec_alias.alias_type, p_business_id, rec_alias.transaction_id,
               rec_alias.end_transaction_id, 0);
    elsif rec_alias.end_event_id is not null and rec_alias.edit_count > 0 then
      insert into aliases_version
        values(rec_alias.alias_id, rec_alias.corp_name, rec_alias.alias_type, p_business_id, rec_alias.transaction_id,
               rec_alias.end_transaction_id, 1);
    elsif rec_alias.end_event_id is not null and rec_alias.edit_count = 0 then 
      insert into aliases_version
        values(rec_alias.alias_id, rec_alias.corp_name, rec_alias.alias_type, p_business_id, rec_alias.end_transaction_id,
               null, 1);
    end if;
    if rec_alias.end_event_id is null then
      insert into aliases values(rec_alias.alias_id, rec_alias.corp_name, rec_alias.alias_type, p_business_id);
    end if;
*/
  end loop;
  close cur_alias;
  return counter;
end;
$$;

-- Load the juridictions history for a single company.
-- Insert into the juridictions and juridictions_version tables.
create or replace function public.colin_hist_corp_jurisdictions(p_corp_num character varying,
                                                                p_business_id integer) returns integer
  language plpgsql
as $$
declare
  cur_juri cursor(v_corp_num character varying)
    for select e.transaction_id,
               case when j.home_recogn_dt is not null then
                         cast((to_timestamp(to_char(j.home_recogn_dt, 'YYYY-MM-DD') || ' 00:00:00', 'YYYY-MM-DD HH24:MI:SS') at time zone 'utc') as timestamp with time zone)
                    else j.home_recogn_dt end as home_recogn_dt,
               j.start_event_id, j.can_jur_typ_cd, j.othr_juris_desc, j.home_juris_num,
               j.bc_xpro_num, j.home_company_nme, j.filing_id, j.jurisdiction_id
          from colin_extract.jurisdiction j, colin_extract.event e
         where e.corp_num = v_corp_num
           and e.corp_num = j.corp_num
           and e.event_id = j.start_event_id
        order by j.start_event_id;
  counter integer := 0;
  prev_trans_id integer := 0;
  juri_id integer := 0;
  rec_juri record;
begin
  open cur_juri(p_corp_num);
  loop
    fetch cur_juri into rec_juri;
    exit when not found;
    counter := counter + 1;
    if counter = 1 then
      juri_id := rec_juri.jurisdiction_id;
      insert into jurisdictions_version
        values(juri_id, 'CA', rec_juri.can_jur_typ_cd, rec_juri.home_juris_num, rec_juri.home_company_nme,
               null, rec_juri.home_recogn_dt, rec_juri.bc_xpro_num, null, p_business_id, rec_juri.filing_id,
               rec_juri.transaction_id, null, 0);
    else
      update jurisdiction_versions
         set end_transaction_id = rec_juri.transaction_id
       where business_id = p_business_id
         and transaction_id = prev_trans_id
         and end_transaction_id is null;
      insert into jurisdictions_version
        values(juri_id, 'CA', rec_juri.can_jur_typ_cd, rec_juri.home_juris_num, rec_juri.home_company_nme,
               null, rec_juri.home_recogn_dt, rec_juri.bc_xpro_num, null, p_business_id, rec_juri.filing_id,
               rec_juri.transaction_id, null, 1);
    end if;
    prev_trans_id := juri_rec.transaction_id;
  end loop;
  close cur_juri;
  -- last record is active one
  insert into jurisdictions
    values(juri_id, 'CA', rec_juri.can_jur_typ_cd, rec_juri.home_juris_num, rec_juri.home_company_nme,
           null, rec_juri.home_recogn_dt, rec_juri.bc_xpro_num, null, p_business_id, rec_juri.filing_id);
  return counter;
end;
$$;

-- Load additional amalgamation specific changes for a single BC company. 
-- Insert into the amalgamations, amalgamations_version, amalgamating_businesses and amalgamating_businesses_version tables.
-- All changes for amalgamation filings: COLIN AMALH,AMALV,AMALR,AMLRU,AMLVU,AMLHU,AMLHC,AMLRC,AMLVC filing types.
-- For each ting, create a corresponding businesses_version record setting the state and dissolution date.
-- Ting businesses_version state=historical, dissolution_date=event_ts.
create or replace function public.colin_hist_corp_amalgamations(p_corp_num character varying,
                                                                p_business_id integer) returns integer
  language plpgsql
as $$
declare
  cur_ting cursor(v_corp_num character varying)
    for select e.transaction_id, b.id as business_id, ce.filing_id,
               cast((to_timestamp(to_char(e.event_timerstamp, 'YYYY-MM-DD HH24:MI:SS'), 'YYYY-MM-DD HH24:MI:SS') at time zone 'utc') as timestamp with time zone) as event_ts,
               cia.event_id, cia.ting_corp_num, cia.corp_involve_id, cia.can_jur_typ_cd, cia.adopted_corp_ind,
               cia.home_juri_num, cia.othr_juri_desc, cia.foreign_nme, cia.amalg_id, cia.amalg_bus_id,
               (select f.filing_type_cd from colin_extract.filing f where f.event_id = e.event_id) as filing_type_cd
          from businesses b, colin_extract.event e, colin_extract.corp_involved_amalgamating cia, colin_event_ids ce
         where e.corp_num = v_corp_num
           and e.corp_num = cia.ted_corp_num
           and e.event_id = cia.event_id
           and e.event_id = ce.colin_event_id
           and cia.ting_corp_num = b.identifier
        order by cia.ting_corp_num;
  cur_ting_bus cursor(v_corp_num character varying)
    for select e.transaction_id as amalg_trans_id,
               cast((to_timestamp(to_char(e.event_timerstamp, 'YYYY-MM-DD HH24:MI:SS'), 'YYYY-MM-DD HH24:MI:SS') at time zone 'utc') as timestamp with time zone) as event_ts,
               b.* 
          from businesses_version b, colin_extract.event e, colin_extract.corp_involved_amalgamating cia, filings f
         where e.corp_num = v_corp_num
           and e.corp_num = cia.ted_corp_num
           and e.event_id = cia.event_id
           and cia.ting_corp_num = b.identifier
           and b.end_transaction_id is null
           and b.transaction_id = f.transaction_id
           and f.status != 'TOMBSTONE';
  counter integer := 0;
  rec_ting record;
  rec_ting_bus record;
  amalg_type varchar(30);
  ting_role varchar(30);
  bus_trans_id integer := 0;
  amalg_id integer := 0;
begin
  open cur_ting(p_corp_num);
  loop
    fetch cur_ting into rec_ting;
    exit when not found;
    counter := counter + 1;
    if counter = 1 then
      amalg_id := rec_ting.amalg_id;
      if rec_ting.filing_type_cd in ('AMALH', 'AMLHU', 'AMLHC') then
        amalg_type := 'horizontal';
      elsif rec_ting.filing_type_cd in ('AMALV', 'AMLVU', 'AMLVC') then
        amalg_type := 'vertical';
      elsif rec_ting.filing_type_cd = 'CONVAMAL' then
        amalg_type := 'unknown';
      else
        amalg_type := 'regular';
      end if;
      insert into amalgamations 
        values(amalg_id, p_business_id, rec_ting.filing_id, rec_ting.event_ts, false,
               cast(amalg_type as amalgamation_type));
      insert into amalgamations_version 
        values(amalg_id, p_business_id, rec_ting.filing_id, rec_ting.event_ts, cast(amalg_type as amalgamation_type),
               false, rec_ting.transaction_id, null, 0);
    end if;
    if rec_ting.adopted_corp_ind = true then
      ting_role := 'primary';
    else
      ting_role := 'amalgamating';
    end if;
    insert into amalgamating_businesses
      values(rec_ting.amalg_bus_id, rec_ting.business_id, amalg_id, rec_ting.can_jur_typ_cd, rec_ting.foreign_nme,
             rec_ting.home_juri_num, cast(ting_role as amalgamating_business_role), rec_ting.can_jur_typ_cd);
    insert into amalgamating_businesses_version
      values(rec_ting.amalg_bus_id, rec_ting.business_id, amalg_id, cast(ting_role as amalgamating_business_role),
             rec_ting.can_jur_typ_cd, rec_ting.can_jur_typ_cd, rec_ting.foreign_nme, rec_ting.home_juri_num,
             rec_ting.transaction_id, null, 0);
  end loop;
  close cur_ting;
  
  open cur_ting_bus(p_corp_num);
  loop
    fetch cur_ting_bus into rec_ting_bus;
    exit when not found;
    bus_trans_id := rec_ting_bus.transaction_id;
    rec_ting_bus.operation_type := 1;
    rec_ting_bus.transaction_id := rec_ting_bus.amalg_trans_id;
    rec_ting_bus.last_modified := rec_ting_bus.event_ts;
    rec_ting_bus.dissolution_date := rec_ting_bus.event_ts;
    rec_ting_bus.state := 'HISTORICAL';
    update businesses_version
       set end_transaction_id = rec_ting_bus.amalg_trans_id
     where id = rec_ting_bus.id
       and end_transaction_id is null
       and transaction_id = bus_trans_id;     
    insert into businesses_version
      values (rec_ting_bus.id,rec_ting_bus.last_modified,rec_ting_bus.last_ledger_id,rec_ting_bus.last_remote_ledger_id,
              rec_ting_bus.last_ar_date,rec_ting_bus.legal_name,rec_ting_bus.founding_date,rec_ting_bus.dissolution_date,
              rec_ting_bus.identifier,rec_ting_bus.tax_id,rec_ting_bus.fiscal_year_end_date,rec_ting_bus.submitter_userid,
              rec_ting_bus.transaction_id,rec_ting_bus.end_transaction_id,rec_ting_bus.operation_type,rec_ting_bus.last_agm_date,
              rec_ting_bus.last_ledger_timestamp,rec_ting_bus.legal_type,rec_ting_bus.restriction_ind,rec_ting_bus.last_ar_year,
              rec_ting_bus.association_type,rec_ting_bus.last_coa_date,rec_ting_bus.last_cod_date,rec_ting_bus.state,
              rec_ting_bus.admin_freeze,rec_ting_bus.state_filing_id,rec_ting_bus.naics_key,rec_ting_bus.naics_code,
              rec_ting_bus.naics_description,rec_ting_bus.start_date,rec_ting_bus.foreign_jurisdiction,
              rec_ting_bus.foreign_legal_name,rec_ting_bus.send_ar_ind,rec_ting_bus.restoration_expiry_date,
              rec_ting_bus.last_ar_reminder_year,rec_ting_bus.continuation_out_date,rec_ting_bus.foreign_jurisdiction_region,
              rec_ting_bus.no_dissolution,rec_ting_bus.last_tr_year,rec_ting_bus.amalgamation_out_date,
              rec_ting_bus.in_liquidation,rec_ting_bus.accession_number,rec_ting_bus.backfill_cutoff_filing_id);
  end loop;
  close cur_ting_bus;
  
  return counter;
end;
$$;


-- Migrate colin filing data for a single BC company.
-- WARNING: this function does not check if the filing data has previously migrated.
-- Use colin_hist_backfill_corp instead to migrate safely.
create or replace function public.colin_hist_corp_v2(p_corp_num character varying, p_business_id integer) returns integer
  language plpgsql
as $$
declare
  rec_counts record;
  exists_count integer := 0;
begin

  select (select count(r.start_event_id)
          from colin_extract.resolution r
         where r.corp_num = c.corp_num) as resolution_count,
       (select count(j.start_event_id)
          from colin_extract.jurisdiction j
         where j.corp_num = c.corp_num) as jurisdiction_count,
       (select count(cia.event_id)
          from colin_extract.corp_involved_amalgamating cia
         where cia.ted_corp_num = c.corp_num) as ci_amalg_count,
       (select count(cn.start_event_id)
          from colin_extract.corp_name cn
         where cn.corp_num = c.corp_num
           and cn.corp_name_typ_cd not in ('CO', 'NB')) as alias_count
   into rec_counts
   from colin_extract.corporation c
  where c.corp_num = p_corp_num; 
  
  exists_count := colin_hist_corp_setup(p_corp_num, p_business_id);
  perform colin_hist_corp_businesses(p_corp_num, p_business_id);
  perform colin_hist_corp_shares(p_corp_num, p_business_id);
  perform colin_hist_corp_offices(p_corp_num, p_business_id);
  perform colin_hist_corp_parties(p_corp_num, p_business_id);
  perform colin_hist_corp_officers(p_corp_num, p_business_id);

  if rec_counts.resolution_count > 0 then
    if exists_count = 0 then
      update colin_extract.resolution
         set resolution_id = nextval('resolutions_id_seq')
       where corp_num = p_corp_num;      
    end if;
    perform colin_hist_corp_resolutions(p_corp_num, p_business_id);
  end if;
  if rec_counts.alias_count > 0 then
    if exists_count = 0 then
      update colin_extract.corp_name
         set alias_id = nextval('aliases_id_seq'),
             alias_type = case when corp_name_typ_cd = 'TR' then 'TRANSLATION'
                               when corp_name_typ_cd = 'AA' then 'AB_ASSUMED'
                               when corp_name_typ_cd = 'AN' then 'AB_COMPANY'
                               when corp_name_typ_cd = 'SA' then 'SK_ASSUMED'
                               when corp_name_typ_cd = 'SN' then 'SK_COMPANY'
                               when corp_name_typ_cd = 'NO' then 'CROSS_REFERENCE'
                               else 'ASSUMED' end
       where corp_num = p_corp_num
         and corp_name_typ_cd not in ('CO', 'NB');      
    end if;
    perform colin_hist_corp_aliases(p_corp_num, p_business_id);
  end if;
  if rec_counts.jurisdiction_count > 0 then
    if exists_count = 0 then
      update colin_extract.jurisdiction
         set jurisdiction_id = nextval('jurisdictions_id_seq'),
             filing_id = (select ce.filing_id 
                            from colin_event_ids ce
                           where ce.colin_event_id = start_event_id)
       where corp_num = p_corp_num;      
    end if;
    perform colin_hist_corp_jurisdictions(p_corp_num, p_business_id);
  end if;
  if rec_counts.ci_amalg_count > 0 then
    if exists_count = 0 then
      update colin_extract.corp_involved_amalgamating
         set amalg_id = nextval('amalgamation_id_seq'),
             amalg_bus_id = nextval('amalgamating_business_id_seq')
       where ted_corp_num = p_corp_num;      
    end if;
    perform colin_hist_corp_amalgamations(p_corp_num, p_business_id);
  end if;

  return p_business_id;
end;
$$;

--
-- The history data backfill replaces the tombstone records except for the businesses, filings, and comments tables. 
-- After the filing history data has migrated, this function removes tombstone records from the following tables:
-- addresses, addresses_version
-- offices, offices_version
-- party_roles, party_roles_version
-- parties, parties_version
-- share_series, share_series_version
-- share_classes, share_classes_version
-- resolutions, resolutions_version
-- aliases, aliases_version
-- amalgamating_businesses, amalgamating_businesses_version
-- amalgamations, amalgamations_version
-- jurisdictions, jurisdictions_version
-- businesses_version
create or replace function public.colin_hist_version_cleanup(p_business_id integer,
                                                             p_tombstone_trans_id integer) returns integer
  language plpgsql
as $$
declare
begin
  delete
    from addresses
   where id in (select id 
                  from addresses_version 
                 where transaction_id = p_tombstone_trans_id
                   and business_id = p_business_id
                   and office_id is not null);
  delete
    from offices
   where id in (select office_id 
                  from addresses_version 
                 where transaction_id = p_tombstone_trans_id 
                   and business_id = p_business_id
                   and office_id is not null);
  delete
    from addresses_version
   where transaction_id = p_tombstone_trans_id
     and business_id = p_business_id
     and office_id is not null;
  delete
    from offices
   where id in (select id 
                  from offices_version
                 where transaction_id = p_tombstone_trans_id
                   and business_id = p_business_id);
  delete
    from offices_version
   where transaction_id = p_tombstone_trans_id
     and business_id = p_business_id;
  delete 
    from party_roles 
   where id in (select id 
                  from party_roles_version
                 where transaction_id = p_tombstone_trans_id 
                   and business_id = p_business_id);   
  delete 
    from party_roles_version 
   where transaction_id = p_tombstone_trans_id
     and business_id = p_business_id;
  delete 
    from parties 
   where id in (select id 
                  from parties_version 
                 where transaction_id = p_tombstone_trans_id);   
  delete 
    from parties_version 
   where  transaction_id = p_tombstone_trans_id;
  delete
    from addresses_version
   where transaction_id = p_tombstone_trans_id
     and business_id = p_business_id;

  delete
    from share_series
   where id in (select id from share_series_version where transaction_id = p_tombstone_trans_id);
  delete
    from share_series_version
   where transaction_id = p_tombstone_trans_id;
  delete
    from share_classes
   where id in (select id 
                  from share_classes_version 
                 where transaction_id = p_tombstone_trans_id
                   and business_id = p_business_id);
  delete
    from share_classes_version
   where transaction_id = p_tombstone_trans_id
     and business_id = p_business_id;
   
  delete
    from resolutions
   where id in (select id 
                  from resolutions_version 
                 where transaction_id = p_tombstone_trans_id
                   and business_id = p_business_id);
  delete
    from resolutions_version
   where transaction_id = p_tombstone_trans_id
     and business_id = p_business_id;
   
  delete
    from aliases
   where id in (select id 
                  from aliases_version 
                 where transaction_id = p_tombstone_trans_id
                   and business_id = p_business_id);
  delete
    from aliases_version
   where transaction_id = p_tombstone_trans_id
     and business_id = p_business_id;

  delete
    from businesses_version
   where transaction_id = p_tombstone_trans_id;
  
  delete
    from amalgamating_businesses
   where id in (select id 
                 from amalgamating_businesses_version 
                where transaction_id = p_tombstone_trans_id
                  and business_id = p_business_id);
  delete
    from amalgamating_businesses_version
   where transaction_id = p_tombstone_trans_id
     and business_id = p_business_id;
   
  delete
    from amalgamations
   where id in (select id 
                  from amalgamations_version 
                 where transaction_id = p_tombstone_trans_id
                   and business_id = p_business_id);
  delete
    from amalgamations_version
   where transaction_id = p_tombstone_trans_id
     and business_id = p_business_id;
   
  delete
    from jurisdictions
   where id in (select id 
                 from jurisdictions_version 
                where transaction_id = p_tombstone_trans_id
                  and business_id = p_business_id);
  delete
    from jurisdictions_version
   where transaction_id = p_tombstone_trans_id
     and business_id = p_business_id;

  return p_tombstone_trans_id;
end;
$$;

-- INCOMPLETE
-- Backfill post-migration filing updates: final updates after migrating COLIN filing history.
-- If filings have been created after tombstone migration and before backfill migration: 
-- The migrated active transaction ID's need to be updated if they are no longer active. 
-- Active records may need to be updated.
-- The last backfill migrated businesses_version record is always updated.
-- Find any tombstone transaction id where the end_transaction_id is not null.
-- Find the corresponding backfill migrated record and set the end_transaction_id to the tombstone record end_transaction_id.
-- Manually inspect each table change and delete orphaned or duplicate records on a case by case basis.
-- This step should only need to be performed once backfilling previously loaded corps.
-- Afterward the backfill should occur immediately after the tombstone data is loaded.
create or replace function public.colin_hist_post_migration(p_business_id integer,
                                                            p_tombstone_trans_id integer) returns integer
  language plpgsql
as $$
declare
  cur_party_roles cursor(v_business_id integer, v_tombstone_trans_id integer)
    for select pr.*, p.first_name, p.middle_initial, p.last_name, p.organization_name,
               (select pr2.cessation_date 
                  from party_roles_version pr2
                 where pr2.id = pr.id
                   and pr2.transaction_id = pr.end_transaction_id) as role_cessation_date
          from party_roles_version pr, parties_version p
         where pr.business_id = v_business_id
           and pr.transaction_id = v_tombstone_trans_id
           and pr.end_transaction_id is not null
           and pr.party_id = p.id
           and p.transaction_id = v_tombstone_trans_id;
  cur_addresses cursor(v_tombstone_trans_id integer)
    for select a2.*
          from addresses_version a, addresses_version a2
         where a.transaction_id = v_tombstone_trans_id
           and a.end_transaction_id is not null
           and a.operation_type != 2
           and a.id = a2.id
           and a.end_transaction_id = a2.transaction_id;
  cur_share_classes cursor(v_business_id integer, v_tombstone_trans_id integer)
    for select s2.*
          from share_classes_version s, share_classes_version s2
         where s.business_id = v_business_id
           and s.transaction_id = v_tombstone_trans_id
           and s.end_transaction_id is not null
           and s.operation_type != 2
           and s.id = s2.id
           and s.end_transaction_id = s2.transaction_id;
  cur_aliases cursor(v_business_id integer, v_tombstone_trans_id integer)
    for select a2.*
          from aliases_version a, aliases_version a2
         where a.business_id = v_business_id
           and a.transaction_id = v_tombstone_trans_id
           and a.end_transaction_id is not null
           and a.operation_type != 2
           and a.id = a2.id
           and a.end_transaction_id = a2.transaction_id;
  rec_change record;
  rec_party_role record;
  rec_address record;
  rec_share_class record;
  rec_alias record;
  party_role_id integer := 0;
  address_id integer := 0;
  share_class_id integer := 0;
  alias_id integer := 0;
  counter integer := 0;
begin
  select max(f.transaction_id) as last_trans_id,
         (select end_transaction_id from businesses_version where transaction_id = p_tombstone_trans_id) as bus_end_trans_id,
         (select count(id) from parties_version where transaction_id = p_tombstone_trans_id and end_transaction_id is not null) as party_count,
         (select count(id) from party_roles_version where transaction_id = p_tombstone_trans_id and end_transaction_id is not null) as role_count,
         (select count(id) from offices_version where transaction_id = p_tombstone_trans_id and end_transaction_id is not null) as office_count,
         (select count(id) from addresses_version where transaction_id = p_tombstone_trans_id and end_transaction_id is not null) as address_count,
         (select count(id) from aliases_version where transaction_id = p_tombstone_trans_id and end_transaction_id is not null) as alias_count,
         (select count(id) from resolutions_version where transaction_id = p_tombstone_trans_id and end_transaction_id is not null) as resolution_count,
         (select count(id) from share_classes_version where transaction_id = p_tombstone_trans_id and end_transaction_id is not null) as share_class_count,
         (select count(id) from share_series_version where transaction_id = p_tombstone_trans_id and end_transaction_id is not null) as share_series_count,
         (select count(id) from party_class_version where transaction_id = p_tombstone_trans_id and end_transaction_id is not null) as party_class_count
    into rec_change
    from filings f
   where f.business_id = p_business_id
     and f.source = 'COLIN'
     and f.status = 'COMPLETED'
     and f.filing_type not in ('conversionLedger');

  if rec_change.bus_end_trans_id is not null then
    counter := counter + 1;
    update businesses_version
       set end_transaction_id = rec_change.bus_end_trans_id
     where id = p_business_id
       and transaction_id = rec_change.last_trans_id;
  end if;
  if rec_change.bus_end_trans_id is not null and rec_change.role_count > 0 then
    counter := counter + 1;
    open cur_party_roles(p_business_id, p_tombstone_trans_id);
    loop
      fetch cur_party_roles into rec_party_role;
      exit when not found;
      party_role_id := 0;
      select pr.id
         into party_role_id
         from party_roles_version pr, parties p
        where pr.role = rec_party_role.role
          and pr.business_id = p_business_id
          and pr.transaction_id < p_tombstone_trans_id
          and pr.end_transaction_id is null
          and pr.operation_type in (0, 1)
          and pr.party_id = p.id
          and ((p.party_type = 'person'
               and (p.first_name = rec_party_role.first_name
                    and p.last_name = rec_party_role.last_name
                    and (p.middle_initial = rec_party_role.middle_initial or p.middle_initial is null)))
                or p.organization_name = rec_party_role.organization_name)
         order by pr.id;
      if FOUND and party_role_id > 0 then
        update party_roles_version
           set end_transaction_id = rec_party_role.end_transaction_id
         where id = party_role_id;
         insert into party_roles_version
           values(party_role_id, rec_party_role.role, rec_party_role.appointment_dt,
                  rec_party_role.role_cessation_date, rec_party_role.business_id, rec_party_role.party_id,
                  rec_party_role.end_transaction_id, null, 1, rec_party_role.filing_id, rec_party_role.party_class_type);
         if rec_party_role.role = 'director' and rec_party_role.role_cessation_date is not null then
           update party_roles
              set cessation_date = rec_party_role.role_cessation_date
            where id = party_role_id;
         end if;
      end if;
    end loop;
    close cur_party_roles;
  end if;
  if rec_change.bus_end_trans_id is not null and rec_change.address_count > 0 then
    counter := counter + 1;
    open cur_addresses(p_tombstone_trans_id);
    loop
      fetch cur_addresses into rec_address;
      exit when not found;
      address_id := 0;
      select a.id
         into address_id
         from addresses_version a
        where (a.business_id = p_business_id
               or (a.office_id is not null and exists (select o.id from offices_version o where o.business_id = p_business_id)))
          and a.transaction_id < p_tombstone_trans_id
          and a.end_transaction_id is null
          and a.operation_type in (0, 1)
          and a.address_type = rec_address.address_type
          and a.street = rec_address.street
          and a.city = rec_address.city
          and a.region = rec_address.region
          and a.country = rec_address.country
          and a.postal_code = rec_address.postal_code
          fetch first 1 rows only;
      if FOUND and address_id > 0 then
        update addresses_version
           set end_transaction_id = rec_address.transaction_id
         where id = address_id;
        insert into addresses_version 
          values(address_id, rec_address.address_type, rec_address.street, rec_address.street_additional,
                 rec_address.city, rec_address.region, rec_address.country, rec_address.postal_code,
                 rec_address.delivery_instructions, rec_address.business_id, rec_address.transaction_id, null, 1, rec_address.office_id, null);
        update addresses
           set street = rec_address.street,
               street_additional = rec_address.street_additional, 
               city = rec_address.city,
               region = rec_address.region,
               country = rec_address.country,
               postal_code = rec_address.postal_code,
               delivery_instructions = rec_address.delivery_instructions
         where id = address_id;
      end if;
    end loop;
    close cur_addresses;
  end if;
  if rec_change.bus_end_trans_id is not null and rec_change.share_class_count > 0 then
    counter := counter + 1;
    open cur_share_classes(p_business_id, p_tombstone_trans_id);
    loop
      fetch cur_share_classes into rec_share_class;
      exit when not found;
      share_class_id := 0;
      select s.id
         into share_class_id
         from share_classes_version s
        where s.business_id = p_business_id
          and s.transaction_id < p_tombstone_trans_id
          and s.end_transaction_id is null
          and s.operation_type in (0, 1)
          and s.name = rec_share_class.name
          fetch first 1 rows only;
      if FOUND and share_class_id > 0 then
        update share_classes_version
           set end_transaction_id = rec_share_class.transaction_id
         where id = share_class_id;
        insert into share_classes_version
            values(share_class_id,
                   rec_share_class.name,
                   rec_share_class.priority,
                   rec_share_class.max_share_flag,
                   rec_share_class.max_shares,
                   rec_share_class.par_value_flag,
                   rec_share_class.par_value,
                   rec_share_class.currency,
                   rec_share_class.special_rights_flag,
                   rec_share_class.business_id,
                   rec_share_class.transaction_id,
                   null,
                   2,
                   rec_share_class.currency_additional); 
      end if;
    end loop;
    close cur_share_classes;
  end if;
  if rec_change.bus_end_trans_id is not null and rec_change.alias_count > 0 then
    counter := counter + 1;
    open cur_aliases(p_business_id, p_tombstone_trans_id);
    loop
      fetch cur_aliases into rec_alias;
      exit when not found;
      alias_id := 0;
      select a.id
         into alias_id
         from aliases_version s
        where a.business_id = p_business_id
          and a.transaction_id < p_tombstone_trans_id
          and a.end_transaction_id is null
          and a.operation_type in (0, 1)
          and a.alias = rec_alias.alias
          and a.type = rec_alias.type
          fetch first 1 rows only;
      if FOUND and alias_id > 0 then
        update aliases_version
           set end_transaction_id = rec_alias.transaction_id
         where id = alias_id;
        insert into aliases_version
            values(alias_id,rec_alias.alias,rec_alias.type,rec_alias.business_id,rec_alias.transaction_id,null,rec_alias.operation_type);
        if rec_alias.operation_type = 1 then
          update aliases
             set alias = rec_alias.alias, type = rec_alias.type
           where id = alias_id;
        end if;
      end if;
    end loop;
    close cur_aliases;
  end if;
  return counter;
end;
$$;

-- Backfill all outstanding colin corps matching on the colin_extract.corp_processing table where:
--   - The processed status is COMPLETED
--   - The business tombstone data exists
--   - The business historical data has not already migrated: no mig_corp_processing_history record for the corp_processing.id
--      exists where history_migrated = true. 
create or replace procedure public.colin_hist_backfill(p_env character varying)
  language plpgsql
as $$
declare
  cur_hist_corps cursor(v_env character varying)
    for select b.id as business_id, b.identifier, cp.id as corp_processing_id,
               (select f.transaction_id 
                  from filings f 
                 where f.business_id = b.id
                   and f.source = 'COLIN'
                   and f.status = 'TOMBSTONE'
                   and f.filing_type = 'lear_tombstone') as tombstone_trans_id,
               (select count(mcph.corp_processing_id) from mig_corp_processing_history mcph where mcph.corp_processing_id = cp.id) as mcph_exists_count,
               (select max(e.event_timerstamp) from colin_extract.event e where e.corp_num = b.identifier) as last_colin_ts,
               (select max(f2.filing_date) from filings f2 where f2.business_id = b.id and f2.status != 'TOMBSTONE') as last_business_ts
         from businesses b, colin_extract.corp_processing cp
        where b.identifier = cp.corp_num
          and cp.processed_status = 'COMPLETED'
          and cp.environment = v_env
          and exists (select f2.id from filings f2, colin_event_ids ce, colin_extract.event e
                        where e.corp_num = b.identifier
                          and e.event_id = ce.colin_event_id
                          and ce.filing_id = f2.id
                          and f2.business_id = b.id)
          and not exists (select mcph.corp_processing_id 
                            from mig_corp_processing_history mcph
                           where mcph.corp_processing_id = cp.id
                             and mcph.history_migrated = true)
        order by cp.id;
  rec_corp record;
  counter integer := 0;
  commit_counter integer := 0;
  mig_filing_exists boolean;
begin
  RAISE NOTICE 'COLIN filing history migration starting % ', now();
  open cur_hist_corps(p_env);
  loop
    fetch cur_hist_corps into rec_corp;
    exit when not found;
    counter := counter + 1;
    commit_counter := commit_counter + 1;
    perform colin_hist_corp_v2(p_corp_num, rec_corp.business_id);
    if rec_corp.last_business_ts > rec_corp.last_colin_ts then
      perform colin_hist_post_migration(rec_corp.business_id, cast(rec_corp.tombstone_trans_id as integer));
    end if;
    perform colin_hist_version_cleanup(rec_corp.business_id, cast(rec_corp.tombstone_trans_id as integer));

    if (rec_corp.last_business_ts - interval '5 seconds') > rec_corp.last_colin_ts then
        mig_filing_exists := true;
    else
        mig_filing_exists := false;
    end if;
    if rec_corp.mcph_exists_count = 0 then
      insert into mig_corp_processing_history
        values(rec_corp.corp_processing_id, rec_corp.tombstone_trans_id, mig_filing_exists, true, true, now(), now());
    else
      update mig_corp_processing_history
         set post_mig_filing_exists = mig_filing_exists,
             history_migrated = true,
             history_migrated_ts = now()
       where corp_processing_id = rec_corp.corp_processing_id;
    end if;

    update businesses
       set backfill_cutoff_filing_id = null
     where id = rec_corp.business_id;
    update filings
       set status = 'BACKFILLED'
     where filing_type = 'lear_tombstone'
       and status = 'TOMBSTONE'
       and transaction_id = rec_corp.tombstone_trans_id;
    if commit_counter = 200 then
      commit;
      commit_counter := 0;
    end if;
  end loop;
  close cur_hist_corps;
  commit;
  RAISE NOTICE 'COLIN filing history migration completed at %. Number of corporations updated: %.', now(), counter;
end;
$$;

-- Backfill colin BC corps matching on the colin_extract.corp_processing table within a start and end ID range where:
--   - The processed status is COMPLETED
--   - The business tombstone data exists
--   - The business historical data has not already migrated: no mig_corp_processing_history record for the corp_processing.id
--      exists where history_migrated = true. 
create or replace procedure public.colin_hist_backfill_range(p_env character varying,
                                                             p_processing_id_start integer,
                                                             p_processing_id_end integer)
  language plpgsql
as $$
declare
  cur_hist_corps cursor(v_env character varying, v_start_id integer, v_end_id integer)
    for select b.id as business_id, b.identifier, cp.id as corp_processing_id,
               (select f.transaction_id 
                  from filings f 
                 where f.business_id = b.id
                   and f.source = 'COLIN'
                   and f.status = 'TOMBSTONE'
                   and f.filing_type = 'lear_tombstone') as tombstone_trans_id,
               (select count(mcph.corp_processing_id) from mig_corp_processing_history mcph where mcph.corp_processing_id = cp.id) as mcph_exists_count,
               (select max(e.event_timerstamp) from colin_extract.event e where e.corp_num = b.identifier) as last_colin_ts,
               (select max(f2.filing_date) from filings f2 where f2.business_id = b.id and f2.status != 'TOMBSTONE') as last_business_ts
         from businesses b, colin_extract.corp_processing cp
        where b.identifier = cp.corp_num
          and cp.processed_status = 'COMPLETED'
          and cp.environment = v_env
          and cp.id between v_start_id and v_end_id
          and exists (select f2.id from filings f2, colin_event_ids ce, colin_extract.event e
                        where e.corp_num = b.identifier
                          and e.event_id = ce.colin_event_id
                          and ce.filing_id = f2.id
                          and f2.business_id = b.id)
          and not exists (select mcph.corp_processing_id 
                            from mig_corp_processing_history mcph
                           where mcph.corp_processing_id = cp.id
                             and mcph.history_migrated = true)
        order by cp.id;
  rec_corp record;
  counter integer := 0;
  commit_counter integer := 0;
  mig_filing_exists boolean;
begin
  RAISE NOTICE 'COLIN filing history migration starting % ', now();
  open cur_hist_corps(p_env, p_processing_id_start, p_processing_id_end);
  loop
    fetch cur_hist_corps into rec_corp;
    exit when not found;
    counter := counter + 1;
    commit_counter := commit_counter + 1;
    perform colin_hist_corp_v2(p_corp_num, rec_corp.business_id);
    if rec_corp.last_business_ts > rec_corp.last_colin_ts then
      perform colin_hist_post_migration(rec_corp.business_id, cast(rec_corp.tombstone_trans_id as integer));
    end if;
    perform colin_hist_version_cleanup(rec_corp.business_id, cast(rec_corp.tombstone_trans_id as integer));

    if (rec_corp.last_business_ts - interval '5 seconds') > rec_corp.last_colin_ts then
        mig_filing_exists := true;
    else
        mig_filing_exists := false;
    end if;
    if rec_corp.mcph_exists_count = 0 then
      insert into mig_corp_processing_history
        values(rec_corp.corp_processing_id, rec_corp.tombstone_trans_id, mig_filing_exists, true, true, now(), now());
    else
      update mig_corp_processing_history
         set post_mig_filing_exists = mig_filing_exists,
             history_migrated = true,
             history_migrated_ts = now()
       where corp_processing_id = rec_corp.corp_processing_id;
    end if;

    update businesses
       set backfill_cutoff_filing_id = null
     where id = rec_corp.business_id;
    update filings
       set status = 'BACKFILLED'
     where filing_type = 'lear_tombstone'
       and status = 'TOMBSTONE'
       and transaction_id = rec_corp.tombstone_trans_id;
    if commit_counter = 200 then
      commit;
      commit_counter := 0;
    end if;
  end loop;
  close cur_hist_corps;
  commit;
  RAISE NOTICE 'COLIN filing history migration completed at %. Number of corporations updated: %.', now(), counter;
end;
$$;

-- Backfill a single BC corp matching on the colin_extract.corp_processing table where:
--   - The processed status is COMPLETED
--   - The business tombstone data exists
--   - The business historical data has not already migrated: no mig_corp_processing_history record for the corp_processing.id
--      exists where history_migrated = true. 
create or replace function public.colin_hist_backfill_corp(p_env character varying,
                                                           p_corp_num character varying) returns integer
  language plpgsql
as $$
declare
  cur_hist_corp cursor(v_env character varying, v_corp_num character varying)
    for select b.id as business_id, b.identifier, cp.id as corp_processing_id,
               (select f.transaction_id 
                  from filings f 
                 where f.business_id = b.id
                   and f.source = 'COLIN'
                   and f.status = 'TOMBSTONE'
                   and f.filing_type = 'lear_tombstone') as tombstone_trans_id,
               (select count(mcph.corp_processing_id) from mig_corp_processing_history mcph where mcph.corp_processing_id = cp.id) as mcph_exists_count,
               (select max(e.event_timerstamp) from colin_extract.event e where e.corp_num = b.identifier) as last_colin_ts,
               (select max(f2.filing_date) from filings f2 where f2.business_id = b.id and f2.status != 'TOMBSTONE') as last_business_ts
         from businesses b, colin_extract.corp_processing cp
        where cp.corp_num = v_corp_num
          and b.identifier = cp.corp_num
          and cp.processed_status = 'COMPLETED'
          and cp.environment = v_env
          and exists (select f2.id from filings f2, colin_event_ids ce, colin_extract.event e
                        where e.corp_num = b.identifier
                          and e.event_id = ce.colin_event_id
                          and ce.filing_id = f2.id
                          and f2.business_id = b.id)
          and not exists (select mcph.corp_processing_id 
                            from mig_corp_processing_history mcph
                           where mcph.corp_processing_id = cp.id
                             and mcph.history_migrated = true)
        order by cp.id;
  rec_corp record;
  counter integer := 0;
  mig_filing_exists boolean;
begin
  open cur_hist_corp(p_env, p_corp_num);
  loop
    fetch cur_hist_corp into rec_corp;
    exit when not found;
    counter := counter + 1;
    perform colin_hist_corp_v2(p_corp_num, rec_corp.business_id);
    if rec_corp.last_business_ts > rec_corp.last_colin_ts then
      perform colin_hist_post_migration(rec_corp.business_id, cast(rec_corp.tombstone_trans_id as integer));
    end if;
    perform colin_hist_version_cleanup(rec_corp.business_id, cast(rec_corp.tombstone_trans_id as integer));

    if (rec_corp.last_business_ts - interval '5 seconds') > rec_corp.last_colin_ts then
        mig_filing_exists := true;
    else
        mig_filing_exists := false;
    end if;
    if rec_corp.mcph_exists_count = 0 then
      insert into mig_corp_processing_history
        values(rec_corp.corp_processing_id, rec_corp.tombstone_trans_id, mig_filing_exists, true, true, now(), now());
    else
      update mig_corp_processing_history
         set post_mig_filing_exists = mig_filing_exists,
             history_migrated = true,
             history_migrated_ts = now()
       where corp_processing_id = rec_corp.corp_processing_id;
    end if;
    update businesses
       set backfill_cutoff_filing_id = null
     where id = rec_corp.business_id;
    update filings
       set status = 'BACKFILLED'
     where filing_type = 'lear_tombstone'
       and status = 'TOMBSTONE'
       and transaction_id = rec_corp.tombstone_trans_id;
  end loop;
  close cur_hist_corp;
  return counter;
end;
$$;

