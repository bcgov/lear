CREATE TABLE public.mig_corp_processing_history (
  corp_processing_id INTEGER PRIMARY KEY,
  tombstone_trans_id INTEGER NOT NULL,
  post_mig_filing_exists BOOLEAN DEFAULT FALSE,
  history_migrated BOOLEAN DEFAULT FALSE,
  tombstone_officer_migrated BOOLEAN DEFAULT FALSE,
  history_migrated_ts TIMESTAMP NULL,
  officer_migrated_ts TIMESTAMP NULL
);
drop table mig_corp_processing_history;

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
   where id in (select id from parties_version where transaction_id = p_trans_id and operation_type = 0);   
  delete 
    from parties_version 
   where  transaction_id = p_trans_id;
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
/*
select colin_hist_filing_rollback(1815266);
*/

--
-- During migration script development rollback historical data changes for an individual BC corp.
-- Restore corp to the tombstone data load state.
--
create or replace function public.colin_hist_corp_rollback(p_corp_num character varying) returns integer
  language plpgsql
as $$
declare
  cur_hist_trans cursor(v_corp_num character varying)
    for select f.transaction_id
          from businesses b, filings f, colin_event_ids ce, colin_extract.event e
         where b.identifier = v_corp_num
           and b.id = f.business_id
           and f.source = 'COLIN'
           and f.status = 'COMPLETED'
           and f.id = ce.filing_id
           and ce.colin_event_id = e.event_id
           and f.filing_type not in ('conversionLedger')
        order by f.id desc;
  rec_trans record;
  counter integer := 0;
begin
  open cur_hist_trans(p_corp_num);
  loop
    fetch cur_hist_trans into rec_trans;
    exit when not found;
    perform colin_hist_filing_rollback(cast(rec_trans.transaction_id as integer));
    counter := counter + 1;
  end loop;
  close cur_hist_trans;
  return counter;
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


-- All address change scenarios by update type:
-- 0 insert into addresses, addresses_version
-- 1 update same addresses id. Update, insert in addresses_version. Update addresses.
-- 2 delete: update, insert in addresses_version delete from addresses. 
create or replace function public.colin_hist_address_change(p_colin_address_id integer,
                                                            p_business_id integer,
                                                            p_trans_id integer,
                                                            p_address_id integer,
                                                            p_address_type character varying,
                                                            p_update_type integer default 1,
                                                            p_office_id integer default null) returns integer
  language plpgsql
as $$
declare
  rec_new_address record;
  rec_existing_address record;
begin
  if p_update_type in (0, 1) then
    select addr_line_1, city, province, country_typ_cd, postal_cd, delivery_instructions,
           case when addr_line_2 is not null and addr_line_3 is not null then addr_line_2 || ' ' || addr_line_3
                else addr_line_2 end as addr_line_2              
      into rec_new_address 
      from colin_extract.address 
     where addr_id = p_colin_address_id;
  end if;

  if p_update_type in (1, 2) then
    select *
      into rec_existing_address
      from addresses_version
     where id = p_address_id
       and end_transaction_id is null
       and address_type = p_address_type
       and operation_type in (0, 1);

    update addresses_version
       set end_transaction_id = p_trans_id
     where id = p_address_id
       and end_transaction_id is null
       and address_type = p_address_type
       and operation_type in (0, 1);
  end if;

  if p_update_type in (0, 1) then
    if p_update_type = 0 then
      insert into addresses 
        values(p_address_id, p_address_type, rec_new_address.addr_line_1, rec_new_address.addr_line_2,
               rec_new_address.city, rec_new_address.province, rec_new_address.country_typ_cd, rec_new_address.postal_cd,
               rec_new_address.delivery_instructions, p_business_id, p_office_id, null);
    else
      update addresses
         set street = rec_new_address.addr_line_1,
             street_additional = rec_new_address.addr_line_2, 
             city = rec_new_address.city,
             region = rec_new_address.province,
             country = rec_new_address.country_typ_cd,
             postal_code = rec_new_address.postal_cd,
             delivery_instructions = rec_new_address.delivery_instructions
        where id = p_address_id;
    end if;
    insert into addresses_version 
      values(p_address_id, p_address_type, rec_new_address.addr_line_1, rec_new_address.addr_line_2,
             rec_new_address.city, rec_new_address.province, rec_new_address.country_typ_cd, rec_new_address.postal_cd,
             rec_new_address.delivery_instructions, p_business_id, p_trans_id, null, p_update_type, p_office_id, null);

  elsif p_update_type = 2 then
    insert into addresses_version 
      values(rec_existing_address.id, rec_existing_address.address_type, rec_existing_address.street,
             rec_existing_address.street_additional, rec_existing_address.city, rec_existing_address.region,
             rec_existing_address.country, rec_existing_address.postal_code, rec_existing_address.delivery_instructions,
             rec_existing_address.business_id, p_trans_id, null, p_update_type, rec_existing_address.office_id,
             rec_existing_address.furnishings_id);
    delete from addresses where id = p_address_id;
  end if;

  return p_trans_id;
end;
$$;

-- For filings that only change existing party addresses.
-- Return 0 if the edit is actually a party change because an address is added or removed.
-- Same party id. Update addresses, update end_transaction_id, insert in addresses_version.
create or replace function public.colin_hist_party_address_edit(p_existing_trans_id integer,
                                                                p_trans_id integer,
                                                                p_business_id integer,
                                                                p_party_id integer,
                                                                p_rec_party record) returns integer
  language plpgsql
as $$
declare
  rec_existing_party record;
  party_update boolean := false;
  counter integer := 0;
begin
  select *
    into rec_existing_party
    from parties_version
   where id = p_party_id
     and transaction_id = p_existing_trans_id
     and operation_type in (0, 1)
     and end_transaction_id is null
     and party_type = p_rec_party.party_type;

  if p_rec_party.delivery_addr_id is null and rec_existing_party.delivery_address_id is not null then
    party_update := true;
  elsif p_rec_party.delivery_addr_id is not null and rec_existing_party.delivery_address_id is null then
    party_update := true;
  elsif p_rec_party.mailing_addr_id is null and rec_existing_party.mailing_address_id is not null then
    party_update := true;
  elsif p_rec_party.mailing_addr_id is not null and rec_existing_party.mailing_address_id is null then
    party_update := true;
  end if;

  if party_update = false then  
    if p_rec_party.delivery_addr_id is not null and rec_existing_party.delivery_address_id is not null then
      perform colin_hist_address_change(p_rec_party.delivery_addr_id::integer, p_business_id, p_trans_id,
                                        rec_existing_party.delivery_address_id,
                                        cast('delivery' as character varying), 1, rec_existing_party.office_id);
      counter := counter + 1;
    end if;
    if p_rec_party.mailing_addr_id is not null and rec_existing_party.mailing_address_id then
      perform colin_hist_address_change(p_rec_party.mailing_addr_id::integer, p_business_id, p_trans_id,
                                        rec_existing_party.mailing_address_id,
                                        cast('mailing' as character varying), 1, rec_existing_party.office_id);
      counter := counter + 1;
    end if;
  end if;
  return counter;
end;
$$;

-- All office change scenarios by update type:
-- 0 insert into offices, offices_version
-- 1 update same offices id. Update end transaction id, insert in offices_version. Update offices.
-- 2 delete: update, insert in offices_version delete from offices. 
create or replace function public.colin_hist_office_change(p_business_id integer,
                                                           p_trans_id integer,
                                                           p_office_id integer,
                                                           p_update_type integer,
                                                           p_office_type character varying,
                                                           p_mailing_id integer,
                                                           p_delivery_id integer) returns integer
  language plpgsql
as $$
declare
  rec_existing_office record;
  mailing_id integer := 0;
  delivery_id integer := 0;
begin
  if p_update_type in (1, 2) then
    select ov.*,
           (select id 
              from addresses
             where business_id = p_business_id and office_id = ov.id and address_type = 'delivery') as delivery_address_id,
           (select id
              from addresses
             where business_id = p_business_id and office_id = ov.id and address_type = 'mailing') as mailing_address_id
      into rec_existing_office
      from offices_version ov
     where ov.id = p_office_id
       and ov.end_transaction_id is null
       and ov.operation_type in (0, 1);
  end if;
  if p_update_type = 0 then
    insert into offices values(p_office_id, p_office_type, null, p_business_id);
    insert into offices_version values(p_office_id, p_office_type, null, p_business_id, p_trans_id, null, p_update_type);

    if p_mailing_id is not null then
      mailing_id := nextval('addresses_id_seq');
      perform colin_hist_address_change(p_mailing_id::integer, p_business_id, p_trans_id, mailing_id,
                                        cast('mailing' as character varying), p_update_type, p_office_id);
    end if;
    if p_delivery_id is not null then
      delivery_id := nextval('addresses_id_seq');
      perform colin_hist_address_change(p_delivery_id::integer, p_business_id, p_trans_id, delivery_id,
                                        cast('delivery' as character varying), p_update_type, p_office_id);
    end if;
  elsif p_update_type = 1 then
      if p_delivery_id is not null and rec_existing_office.delivery_address_id is null then -- adding
        delivery_id := nextval('addresses_id_seq');
        perform colin_hist_address_change(p_delivery_id::integer, p_business_id, p_trans_id, delivery_id,
                                          cast('delivery' as character varying), 0, rec_existing_office.id);
      elsif p_delivery_id is null and rec_existing_office.delivery_address_id is not null then -- deleting
        perform colin_hist_address_change(0, p_business_id, p_trans_id, rec_existing_office.delivery_address_id,
                                          cast('delivery' as character varying), 2, rec_existing_office.id);
      elsif p_delivery_id is not null and rec_existing_office.delivery_address_id is not null then -- updating
        delivery_id := rec_existing_office.delivery_address_id;
        perform colin_hist_address_change(p_delivery_id::integer, p_business_id, p_trans_id, delivery_id,
                                          cast('delivery' as character varying), p_update_type, rec_existing_office.id);
      end if;
      if p_mailing_id is not null and rec_existing_office.mailing_address_id is null then -- adding
        mailing_id := nextval('addresses_id_seq');
        perform colin_hist_address_change(p_mailing_id::integer, p_business_id, p_trans_id, mailing_id,
                                          cast('mailing' as character varying), 0, rec_existing_office.id);
      elsif p_mailing_id is null and rec_existing_office.mailing_address_id is not null then -- deleting
        perform colin_hist_address_change(0, p_business_id, p_trans_id, rec_existing_office.mailing_address_id,
                                          cast('mailing' as character varying), 2, rec_existing_office.id);
      elsif p_mailing_id is not null and rec_existing_office.mailing_address_id is not null then -- updating
        mailing_id := rec_existing_office.mailing_address_id;
        perform colin_hist_address_change(p_mailing_id::integer, p_business_id, p_trans_id, mailing_id,
                                          cast('mailing' as character varying), p_update_type, rec_existing_office.id);
      end if;
  elsif p_update_type = 2 then
    if rec_existing_office.delivery_address_id is not null then
      perform colin_hist_address_change(0, p_business_id, p_trans_id, rec_existing_office.delivery_address_id,
                                        cast('delivery' as character varying), p_update_type, rec_existing_office.id);
    end if;
    if rec_existing_office.mailing_address_id is not null then
      perform colin_hist_address_change(0, p_business_id, p_trans_id, rec_existing_office.mailing_address_id,
                                        cast('mailing' as character varying), p_update_type, rec_existing_office.id);
    end if;    
    update offices_version
       set end_transaction_id = p_trans_id
     where id = p_office_id
       and end_transaction_id is null
       and operation_type in (0, 1);
   insert into offices_version
     values(rec_existing_office.id,
            rec_existing_office.office_type,
            rec_existing_office.deactivated_date,
            rec_existing_office.business_id,
            p_trans_id,
            null,
            p_update_type);            
    delete from offices where id = rec_existing_office.id;
  end if;

  return p_trans_id;
end;
$$;


-- All party change scenarios by update type:
-- 0 insert into parties, parties_version
-- 1 update same parties id. Update end transaction id, insert in parties_version. Update parties.
-- 2 delete: update, insert in parties_version delete from parties. 
create or replace function public.colin_hist_party_change(p_business_id integer,
                                                          p_trans_id integer,
                                                          p_party_id integer,
                                                          p_update_type integer,
                                                          p_rec_party record,
                                                          p_colin_filing_type character varying) returns integer
  language plpgsql
as $$
declare
  rec_existing_party record;
  counter integer := 0;
  mailing_id integer := 0;
  delivery_id integer := 0;
  v_party_type varchar(30);
begin
  if p_update_type in (1, 2) then
    select *
      into rec_existing_party
      from parties_version
     where id = p_party_id
       and end_transaction_id is null
       and operation_type in (0, 1);
  end if;
  if p_update_type in (0, 1) then
    if p_rec_party.last_name is not null and trim(p_rec_party.last_name) != '' then
      v_party_type := 'person';
    else
      v_party_type := 'organization';
    end if;
  end if;

  if p_update_type = 0 then
    if p_rec_party.mailing_addr_id is not null then
      mailing_id := nextval('addresses_id_seq');
      perform colin_hist_address_change(cast(p_rec_party.mailing_addr_id as integer), p_business_id, p_trans_id, mailing_id,
                                        cast('mailing' as character varying), p_update_type, null);
    else
      mailing_id := null;
    end if;
    if p_rec_party.delivery_addr_id is not null then
      delivery_id := nextval('addresses_id_seq');
      perform colin_hist_address_change(cast(p_rec_party.delivery_addr_id as integer), p_business_id, p_trans_id, delivery_id,
                                        cast('delivery' as character varying), p_update_type, null);
    else
      delivery_id := null;
    end if;
    insert into parties_version 
      values(p_party_id, v_party_type, p_rec_party.first_name, p_rec_party.middle_name, p_rec_party.last_name, null,
             p_rec_party.business_name, delivery_id, mailing_id, p_trans_id, null, 0, null, p_rec_party.email_address, null);      
    insert into parties
      values(p_party_id, v_party_type, p_rec_party.first_name, p_rec_party.middle_name, p_rec_party.last_name, null,
             p_rec_party.business_name, delivery_id, mailing_id, null, p_rec_party.email_address, null);      
  elsif p_update_type = 1 then
    if p_colin_filing_type is not null and p_colin_filing_type in ('xx') then
      counter := colin_hist_party_address_edit(rec_existing_party.transaction_id, p_trans_id, p_business_id,
                                               rec_existing_party.id, p_rec_party); 
    end if;
    if counter = 0 then
      if p_rec_party.delivery_addr_id is not null and rec_existing_party.delivery_address_id is null then -- adding
        delivery_id := nextval('addresses_id_seq');
        perform colin_hist_address_change(p_rec_party.delivery_addr_id::integer, p_business_id, p_trans_id, delivery_id,
                                          cast('delivery' as character varying), 0, null);
      elsif p_rec_party.delivery_addr_id is null and rec_existing_party.delivery_address_id is not null then -- deleting
        perform colin_hist_address_change(0, p_business_id, p_trans_id, rec_existing_party.delivery_address_id,
                                          cast('delivery' as character varying), 2, null);
        delivery_id := null;
      elsif p_rec_party.delivery_addr_id is not null and rec_existing_party.delivery_address_id is not null then -- updating
        delivery_id := rec_existing_party.delivery_address_id;
        perform colin_hist_address_change(p_rec_party.delivery_addr_id::integer, p_business_id, p_trans_id, delivery_id,
                                          cast('delivery' as character varying), p_update_type, null);
      end if;
      if p_rec_party.mailing_addr_id is not null and rec_existing_party.mailing_address_id is null then -- adding
        mailing_id := nextval('addresses_id_seq');
        perform colin_hist_address_change(p_rec_party.mailing_addr_id::integer, p_business_id, p_trans_id, mailing_id,
                                          cast('mailing' as character varying), 0, null);
      elsif p_rec_party.mailing_addr_id is null and rec_existing_party.mailing_address_id is not null then -- deleting
        perform colin_hist_address_change(0, p_business_id, p_trans_id, rec_existing_party.mailing_address_id,
                                          cast('mailing' as character varying), 2, null);
        mailing_id := null;
      elsif p_rec_party.mailing_addr_id is not null and rec_existing_party.mailing_address_id is not null then -- updating
        mailing_id := rec_existing_party.mailing_address_id;
        perform colin_hist_address_change(p_rec_party.mailing_addr_id::integer, p_business_id, p_trans_id, mailing_id,
                                          cast('mailing' as character varying), p_update_type, null);
      end if;
      if mailing_id = 0 then
        mailing_id := null;
      end if;
      if delivery_id = 0 then
        delivery_id := null;
      end if;
      
      update parties_version
         set end_transaction_id = p_trans_id
       where id = rec_existing_party.id
         and operation_type in (0, 1)
         and end_transaction_id is null;
     insert into parties_version
       values(rec_existing_party.id,
              v_party_type,
              p_rec_party.first_name,
              p_rec_party.middle_name,
              p_rec_party.last_name,
              rec_existing_party.title,
              p_rec_party.business_name,
              delivery_id,
              mailing_id,
              p_trans_id,
              null,
              p_update_type,
              rec_existing_party.identifier,
              p_rec_party.email_address,
              rec_existing_party.alternate_name);            
      update parties
         set first_name = p_rec_party.first_name,
             middle_initial = p_rec_party.middle_name,
             last_name = p_rec_party.last_name,
             organization_name = p_rec_party.business_name,
             email = p_rec_party.email_address,
             mailing_address_id = mailing_id,
             delivery_address_id = delivery_id,
             party_type = v_party_type
      where id = rec_existing_party.id;
    end if;
  elsif p_update_type = 2 then
    update parties_version
       set end_transaction_id = p_trans_id
     where id = p_party_id
       and end_transaction_id is null
       and operation_type in (0, 1);
   insert into parties_version
     values(rec_existing_party.id,
            rec_existing_party.party_type,
            rec_existing_party.first_name,
            rec_existing_party.middle_initial,
            rec_existing_party.last_name,
            rec_existing_party.title,
            rec_existing_party.organization_name,
            rec_existing_party.delivery_address_id,
            rec_existing_party.mailing_address_id,
            p_trans_id,
            null,
            p_update_type,
            rec_existing_party.identifier,
            rec_existing_party.email,
            rec_existing_party.alternate_name);            
    delete from parties where id = rec_existing_party.id;
    if rec_existing_party.delivery_address_id is not null then
      perform colin_hist_address_change(0, p_business_id, p_trans_id, rec_existing_party.delivery_address_id,
                                        cast('delivery' as character varying), p_update_type, null);
    end if;
    if rec_existing_party.mailing_address_id is not null then
      perform colin_hist_address_change(0, p_business_id, p_trans_id, rec_existing_party.mailing_address_id,
                                        cast('mailing' as character varying), p_update_type, null);
    end if;    
  end if;

  return p_trans_id;
end;
$$;


-- All party change scenarios by update type:
-- 0 insert into party_roles, party_roles_version
-- 1 update same party_roles id. Update end transaction id, insert in party_roles_version. Update party_roles.
-- 2 delete: update, insert in party_roles_version, delete from party_roles. 
create or replace function public.colin_hist_party_role_change(p_business_id integer,
                                                               p_trans_id integer,
                                                               p_party_role_id integer,
                                                               p_update_type integer,
                                                               p_rec_party record,
                                                               p_colin_filing_type character varying) returns integer
  language plpgsql
as $$
declare
  rec_existing_role record;
  counter integer := 0;
  party_id integer := 0;
  v_business_id integer := 0;
  filing_id integer := 0;
  class_type partyclasstype;
begin
  if p_update_type in (1, 2) then
    select *
      into rec_existing_role
      from party_roles_version
     where id = p_party_role_id
       and end_transaction_id is null
       and operation_type in (0, 1);
  end if;

  if p_rec_party.party_role in ('applicant', 'incorporator') then
    v_business_id := null;
    select id
      into filing_id
      from filings
     where business_id = p_business_id
       and transaction_id = p_trans_id;
  else
    v_business_id := p_business_id;
    filing_id := null;
  end if;
  if p_update_type = 0 then
    if p_rec_party.party_typ_cd = 'OFF' then
      class_type := cast('OFFICER' as partyclasstype);
    else
      class_type := null;
    end if;
    party_id := nextval('parties_id_seq');
    perform colin_hist_party_change(v_business_id, p_trans_id, party_id, p_update_type, p_rec_party, p_colin_filing_type);
    insert into party_roles_version 
      values(p_party_role_id, p_rec_party.party_role, p_rec_party.appointment_dt,
             null, v_business_id, party_id, p_trans_id, null, p_update_type, filing_id, class_type);
    insert into party_roles 
      values(p_party_role_id, p_rec_party.party_role, p_rec_party.appointment_dt,
            p_rec_party.cessation_dt, v_business_id, party_id, filing_id, class_type);
  elsif p_update_type = 1 then
    -- party role edit is a party edit not a role change
    perform colin_hist_party_change(v_business_id, p_trans_id, rec_existing_role.party_id, p_update_type, p_rec_party, p_colin_filing_type);
  elsif p_update_type = 2 and (p_rec_party.party_role = 'director' or p_rec_party.party_typ_cd = 'OFF') then
    update party_roles_version
       set end_transaction_id = p_trans_id
     where id = p_party_role_id
       and end_transaction_id is null
       and operation_type in (0, 1);
   insert into party_roles_version
     values(rec_existing_role.id,
            rec_existing_role.role,
            rec_existing_role.appointment_date,
            p_rec_party.cessation_dt,
            rec_existing_role.business_id,
            rec_existing_role.party_id,
            p_trans_id,
            null,
            1,
            rec_existing_role.filing_id,
            rec_existing_role.party_class_type);
    update party_roles
       set cessation_date = p_rec_party.cessation_dt
     where id = p_party_role_id;
  elsif p_update_type = 2 then
    update party_roles_version
       set end_transaction_id = p_trans_id
     where id = p_party_role_id
       and end_transaction_id is null
       and operation_type in (0, 1);
   insert into party_roles_version
     values(rec_existing_role.id,
            rec_existing_role.role,
            rec_existing_role.appointment_date,
            rec_existing_role.cessation_date,
            rec_existing_role.business_id,
            rec_existing_role.party_id,
            p_trans_id,
            null,
            p_update_type,
            rec_existing_role.filing_id,
            rec_existing_role.party_class_type);            
    delete from party_roles where id = rec_existing_role.id;
    perform colin_hist_party_change(v_business_id, p_trans_id, rec_existing_role.party_id, p_update_type, p_rec_party, p_colin_filing_type);
  end if;

  return p_trans_id;
end;
$$;

-- Use for filings that add or delete an office, or change a an office address.
-- Specify colin office type as some filings change more than 1 office. 
create or replace function public.colin_hist_offices(p_colin_event_id integer,
                                                     p_business_id integer,
                                                     p_trans_id integer,
                                                     p_corp_num character varying,
                                                     p_update_type integer,
                                                     p_colin_office_type character varying) returns integer
  language plpgsql
as $$
declare
  rec_hist_off record;
  office_id integer := 0;
begin
  if p_update_type = 0 then
    select office_typ_cd,
           case when office_typ_cd = 'RG' then 'registeredOffice'
                when office_typ_cd = 'RC' then 'recordsOffice'  
                when office_typ_cd = 'DS' then 'custodialOffice' 
                when office_typ_cd = 'LQ' then 'liquidationRecordsOffice' else office_typ_cd end as office_type,
           mailing_addr_id, delivery_addr_id, start_event_id, end_event_id
      into rec_hist_off
      from colin_extract.office
     where corp_num = p_corp_num
       and start_event_id = p_colin_event_id
       and office_typ_cd = p_colin_office_type;
  elsif p_update_type = 1 then
    select o.office_typ_cd,
           case when o.office_typ_cd = 'RG' then 'registeredOffice'
                when o.office_typ_cd = 'RC' then 'recordsOffice'  
                when o.office_typ_cd = 'DS' then 'custodialOffice' 
                when o.office_typ_cd = 'LQ' then 'liquidationRecordsOffice' else o.office_typ_cd end as office_type,
           o.mailing_addr_id, o.delivery_addr_id, o.start_event_id, o.end_event_id,
           (select ov.id 
              from filings f, colin_event_ids ce, colin_extract.office o2, offices_version ov, addresses_version a
             where o2.corp_num = o.corp_num
               and o2.end_event_id = o.start_event_id
               and o2.office_typ_cd = o.office_typ_cd
               and ce.colin_event_id = o2.start_event_id
               and ce.filing_id = f.id
               and ov.business_id = p_business_id
               and a.business_id = ov.business_id
               and ov.id = a.office_id
               and a.transaction_id = f.transaction_id
               and a.end_transaction_id is null
               and a.operation_type in (0, 1)
            fetch first 1 rows only) as office_id
      into rec_hist_off
      from colin_extract.office o
     where o.corp_num = p_corp_num
       and o.start_event_id = p_colin_event_id
       and o.office_typ_cd = p_colin_office_type;
  elsif p_update_type = 2 then
    select o.office_typ_cd,
           case when o.office_typ_cd = 'RG' then 'registeredOffice'
                when o.office_typ_cd = 'RC' then 'recordsOffice'  
                when o.office_typ_cd = 'DS' then 'custodialOffice' 
                when o.office_typ_cd = 'LQ' then 'liquidationRecordsOffice' else o.office_typ_cd end as office_type,
           o.mailing_addr_id, o.delivery_addr_id, o.start_event_id, o.end_event_id,
           (select ov.id 
              from filings f, colin_event_ids ce, offices_version ov, addresses_version a
             where ce.colin_event_id = o.start_event_id
               and ce.filing_id = f.id
               and ov.business_id = p_business_id
               and a.business_id = ov.business_id
               and ov.id = a.office_id
               and a.transaction_id = f.transaction_id
               and a.end_transaction_id is null
               and a.operation_type in (0, 1)
            fetch first 1 rows only) as office_id
      into rec_hist_off
      from colin_extract.office o
     where o.corp_num = p_corp_num
       and o.end_event_id = p_colin_event_id
       and o.office_typ_cd = p_colin_office_type;
  end if;

  if FOUND then
    if p_update_type = 0 then
      office_id := nextval('offices_id_seq');
    else
      office_id := rec_hist_off.office_id;
    end if;
    perform colin_hist_office_change(p_business_id, p_trans_id, office_id, p_update_type,
                                     cast(rec_hist_off.office_type as character varying),
                                     cast(rec_hist_off.mailing_addr_id as integer),
                                     cast(rec_hist_off.delivery_addr_id as integer));  
  end if;
  
  return p_trans_id;
end;
$$;

-- Use for filings that add, delete or update a party.
-- Specify colin party type. 
create or replace function public.colin_hist_parties(p_colin_event_id integer,
                                                     p_business_id integer,
                                                     p_trans_id integer,
                                                     p_corp_num character varying,
                                                     p_update_type integer,
                                                     p_colin_party_type character varying,
                                                     p_colin_filing_type character varying) returns integer
  language plpgsql
as $$
declare
  rec_hist_party record;
  party_role_id integer := 0;
begin
  if p_update_type = 0 then
    select cp.mailing_addr_id, cp.delivery_addr_id, cp.party_typ_cd,
           case when cp.party_typ_cd = 'DIR' then 'director'
                when cp.party_typ_cd = 'RCC' then 'custodian'
                when cp.party_typ_cd = 'LIQ' then 'liquidator'
                when cp.party_typ_cd = 'RCM' then 'receiver'
                when cp.party_typ_cd = 'APP' then 'applicant'
                else cp.party_typ_cd end as party_role,
           cp.appointment_dt, cp.cessation_dt,
           case when cp.last_name is not null and trim(cp.last_name) != '' then upper(cp.last_name) else null end as last_name,
           case when cp.middle_name is not null and trim(cp.middle_name) != '' then upper(cp.middle_name) else null end as middle_name,
           case when cp.first_name is not null and  trim(cp.first_name) != '' then upper(cp.first_name) else null end as first_name,
           case when cp.business_name is not null and  trim(cp.business_name) != '' then upper(cp.business_name) else null end as business_name,
           cp.email_address, cp.prev_party_id, cp.start_event_id, cp.end_event_id, null as party_role_id
     into rec_hist_party
     from colin_extract.corp_party cp 
    where cp.corp_num = p_corp_num
      and cp.start_event_id = p_colin_event_id
      and cp.party_typ_cd = p_colin_party_type;
  elsif p_update_type = 1 then
    select cp.mailing_addr_id, cp.delivery_addr_id, cp.party_typ_cd,
           case when cp.party_typ_cd = 'DIR' then 'director'
                when cp.party_typ_cd = 'RCC' then 'custodian'
                when cp.party_typ_cd = 'LIQ' then 'liquidator'
                when cp.party_typ_cd = 'RCM' then 'receiver'
                when cp.party_typ_cd = 'APP' then 'applicant'
                else cp.party_typ_cd end as party_role,
           cp.appointment_dt, cp.cessation_dt,
           case when cp.last_name is not null and trim(cp.last_name) != '' then upper(cp.last_name) else null end as last_name,
           case when cp.middle_name is not null and trim(cp.middle_name) != '' then upper(cp.middle_name) else null end as middle_name,
           case when cp.first_name is not null and  trim(cp.first_name) != '' then upper(cp.first_name) else null end as first_name,
           case when cp.business_name is not null and  trim(cp.business_name) != '' then upper(cp.business_name) else null end as business_name,
           cp.email_address, cp.prev_party_id, cp.start_event_id, cp.end_event_id,
           (select pr.id
              from party_roles_version pr, filings f, colin_event_ids ce, colin_extract.corp_party cp2, parties_version p
             where cp2.corp_num = cp.corp_num
               and cp2.end_event_id = cp.start_event_id
               and cp2.party_typ_cd = cp.party_typ_cd
               and ce.colin_event_id = cp2.start_event_id
               and ce.filing_id = f.id
               and pr.business_id = p_business_id
               and pr.party_id = p.id
               and ((p.transaction_id = f.transaction_id and p.end_transaction_id is null and p.operation_type in (0, 1)) or 
                    exists (select a.id 
                              from addresses_version a 
                             where a.business_id = pr.business_id
                               and (p.mailing_address_id = a.id or p.delivery_address_id = a.id)
                               and a.transaction_id = f.transaction_id
                               and a.end_transaction_id is null
                               and a.operation_type in (0, 1)))
               fetch first 1 rows only) as party_role_id
     into rec_hist_party
     from colin_extract.corp_party cp 
    where cp.corp_num = p_corp_num
      and cp.start_event_id = p_colin_event_id
      and cp.party_typ_cd = p_colin_party_type;
  elsif p_update_type = 2 then
    select cp.mailing_addr_id, cp.delivery_addr_id, cp.party_typ_cd,
           case when cp.party_typ_cd = 'DIR' then 'director'
                when cp.party_typ_cd = 'RCC' then 'custodian'
                when cp.party_typ_cd = 'LIQ' then 'liquidator'
                when cp.party_typ_cd = 'RCM' then 'receiver'
                when cp.party_typ_cd = 'APP' then 'applicant'
                else cp.party_typ_cd end as party_role,
           cp.appointment_dt, cp.cessation_dt,
           case when cp.last_name is not null and trim(cp.last_name) != '' then upper(cp.last_name) else null end as last_name,
           case when cp.middle_name is not null and trim(cp.middle_name) != '' then upper(cp.middle_name) else null end as middle_name,
           case when cp.first_name is not null and  trim(cp.first_name) != '' then upper(cp.first_name) else null end as first_name,
           case when cp.business_name is not null and  trim(cp.business_name) != '' then upper(cp.business_name) else null end as business_name,
           cp.email_address, cp.prev_party_id, cp.start_event_id, cp.end_event_id,
           (select pr.id
              from party_roles_version pr, filings f, colin_event_ids ce, parties_version p
             where ce.colin_event_id = cp.start_event_id
               and ce.filing_id = f.id
               and pr.business_id = p_business_id
               and pr.party_id = p.id
               and ((p.transaction_id = f.transaction_id and p.end_transaction_id is null and p.operation_type in (0, 1)) or 
                    exists (select a.id 
                              from addresses_version a 
                             where a.business_id = pr.business_id
                               and (p.mailing_address_id = a.id or p.delivery_address_id = a.id)
                               and a.transaction_id = f.transaction_id
                               and a.end_transaction_id is null
                               and a.operation_type in (0, 1)))
               fetch first 1 rows only) as party_role_id
     into rec_hist_party
     from colin_extract.corp_party cp 
    where cp.corp_num = p_corp_num
      and cp.end_event_id = p_colin_event_id
      and cp.party_typ_cd = p_colin_party_type;
  end if;

  if FOUND then
    if p_update_type = 0 then
      party_role_id := nextval('party_roles_id_seq');
    else
      party_role_id := rec_hist_party.party_role_id;
    end if;
    perform colin_hist_party_role_change(p_business_id, p_trans_id, party_role_id, p_update_type, rec_hist_party, p_colin_filing_type);  
  end if;
  
  return p_trans_id;
end;
$$;

-- Create new share_classes, share_classes_version records. Return new share_class_id.
create or replace function public.colin_hist_shareclass_add(p_trans_id integer,
                                                            p_business_id integer,
                                                            p_update_type integer,
                                                            p_class_rec record) returns integer
  language plpgsql
as $$
declare
  class_id integer := 0;
  currency_type varchar(60);
  share_name varchar(1000);
begin
  class_id := nextval('share_classes_id_seq');
  currency_type := case when p_class_rec.currency_typ_cd = 'OTH' then 'OTHER'
                        else p_class_rec.currency_typ_cd end;
  if position('SHARES' in TRIM(UPPER(p_class_rec.class_nme))) < 1 then
    share_name := p_class_rec.class_nme || ' Shares';
  else
    share_name := p_class_rec.class_nme;
  end if;
  insert into share_classes
    values(class_id,
           share_name,
           p_class_rec.share_class_id,
           p_class_rec.max_share_ind,
           p_class_rec.share_quantity,
           p_class_rec.par_value_ind,
           p_class_rec.par_value_amt,
           currency_type,
           p_class_rec.spec_rights_ind,
           p_business_id,
           p_class_rec.other_currency); 
  insert into share_classes_version
    values(class_id,
           share_name,
           p_class_rec.share_class_id,
           p_class_rec.max_share_ind,
           p_class_rec.share_quantity,
           p_class_rec.par_value_ind,
           p_class_rec.par_value_amt,
           currency_type,
           p_class_rec.spec_rights_ind,
           p_business_id,
           p_trans_id,
           null,
           p_update_type,
           p_class_rec.other_currency); 
  return class_id;
end;
$$;

-- Create the share series for an individual share class.
-- Insert into the share_series and share_series_version tables.
create or replace function public.colin_hist_shareseries_add(p_corp_num character varying,
                                                             p_colin_event_id integer,
                                                             p_trans_id integer,
                                                             p_colin_class_id integer,
                                                             p_share_class_id integer,
                                                             p_update_type integer) returns integer
  language plpgsql
as $$
declare
  cur_hist_share_series cursor(v_colin_event_id integer, v_corp_num character varying, v_share_class_id integer)
    for select ss.series_id, ss.max_share_ind, ss.share_quantity, ss.spec_right_ind, ss.series_nme
          from colin_extract.share_series ss
         where ss.corp_num = v_corp_num
           and ss.start_event_id = v_colin_event_id
           and ss.share_class_id = v_share_class_id
      order by ss.series_id;
  counter integer := 0;
  rec_hist_share_series record;
  series_id integer := 0;
begin  
  open cur_hist_share_series(p_colin_event_id, p_corp_num, p_colin_class_id);
  loop
    fetch cur_hist_share_series into rec_hist_share_series;
    exit when not found;
    counter := counter + 1;
    series_id := nextval('share_series_id_seq');
    insert into share_series
      values(series_id,
             rec_hist_share_series.series_nme,
             rec_hist_share_series.series_id,
             rec_hist_share_series.max_share_ind,
             rec_hist_share_series.share_quantity,
             rec_hist_share_series.spec_right_ind,
             p_share_class_id); 
    insert into share_series_version
      values(series_id,
             rec_hist_share_series.series_nme,
             rec_hist_share_series.series_id,
             rec_hist_share_series.max_share_ind,
             rec_hist_share_series.share_quantity,
             rec_hist_share_series.spec_right_ind,
             p_share_class_id,
             p_trans_id,
             null,
             p_update_type); 
  end loop;
  close cur_hist_share_series;
  return counter;
end;
$$;

-- Create historical resolution for an individual filing.
-- Insert into the resolutions and resolutions_version tables.
create or replace function public.colin_hist_resolution_add(p_business_id integer,
                                                            p_trans_id integer,
                                                            p_resolution_dt timestamp with time zone) returns integer
  language plpgsql
as $$
declare
  res_id integer := 0;
begin
  res_id := nextval('resolutions_id_seq');
  insert into resolutions_version
    values(res_id, p_resolution_dt, 'SPECIAL', p_business_id, p_trans_id, null, 0, null, null, null, null);
  insert into resolutions
    values(res_id, p_resolution_dt, 'SPECIAL', p_business_id, null, null, null, null);
  return p_trans_id;
end;
$$;

-- Create historical alias (name that is not NR corp name or numbered) for an individual filing.
-- Insert into the aliases and aliases_version tables.
create or replace function public.colin_hist_alias_add(p_corp_num character varying,
                                                       p_colin_event_id integer,
                                                       p_business_id integer,
                                                       p_trans_id integer,
                                                       p_alias_rec record) returns integer
  language plpgsql
as $$
declare
  cur_hist_alias cursor(v_colin_event_id integer, v_corp_num character varying)
    for select upper(cn.corp_name) as corp_name, 
               case when cn.corp_name_typ_cd = 'TR' then 'TRANSLATION'
                    when cn.corp_name_typ_cd = 'AA' then 'AB_ASSUMED'
                    when cn.corp_name_typ_cd = 'AN' then 'AB_COMPANY'
                    when cn.corp_name_typ_cd = 'SA' then 'SK_ASSUMED'
                    when cn.corp_name_typ_cd = 'SN' then 'SK_COMPANY'
                    when cn.corp_name_typ_cd = 'NO' then 'CROSS_REFERENCE'
                    else 'ASSUMED' end as name_type,
               cn.start_event_id,
               cn.end_event_id
          from colin_extract.corp_name cn
         where cn.corp_num = v_corp_num
           and cn.corp_name_typ_cd not in ('CO', 'NB')
           and cn.start_event_id = v_colin_event_id
      order by cn.start_event_id;
  alias_id integer := 0;
  rec_alias record;
begin
  if p_alias_rec is not null then
    alias_id := nextval('aliases_id_seq');
    insert into aliases_version
      values(alias_id, p_alias_rec.corp_name, p_alias_rec.name_type, p_business_id, p_trans_id, null, 0);
    insert into aliases
      values(alias_id, p_alias_rec.corp_name, p_alias_rec.name_type, p_business_id);
  else
    open cur_hist_alias(p_colin_event_id, p_corp_num);
    loop
      fetch cur_hist_alias into rec_alias;
      exit when not found;
      alias_id := nextval('aliases_id_seq');
      insert into aliases_version
        values(alias_id, rec_alias.corp_name, rec_alias.name_type, p_business_id, p_trans_id, null, 0);
      insert into aliases
        values(alias_id, rec_alias.corp_name, rec_alias.name_type, p_business_id);
    end loop;
    close cur_hist_alias;
  end if;
  return p_trans_id;
end;
$$;

--
-- Create registered and records office offices_version, addresses_version records for a business's initial filing.
--
create or replace function public.colin_hist_first_office(p_corp_num character varying,
                                                          p_colin_event_id integer,
                                                          p_trans_id integer,
                                                          p_business_id integer) returns integer
  language plpgsql
as $$
declare
  cur_hist_office cursor(v_colin_event_id integer, v_corp_num character varying)
    for select o.office_typ_cd,
               case when o.office_typ_cd = 'RG' then 'registeredOffice' else 'recordsOffice' end as office_type,  
               o.mailing_addr_id, o.delivery_addr_id
          from colin_extract.office o
         where o.corp_num = v_corp_num
           and o.start_event_id = v_colin_event_id
           and o.office_typ_cd in ('RG', 'RC');
  rec_hist_office record;
  office_id integer := 0;
begin  
  open cur_hist_office(p_colin_event_id, p_corp_num);
  loop
    fetch cur_hist_office into rec_hist_office;
    exit when not found;
    office_id := nextval('offices_id_seq');
    perform colin_hist_office_change(p_business_id, p_trans_id, office_id, 0,
                                     cast(rec_hist_office.office_type as character varying),
                                     cast(rec_hist_office.mailing_addr_id as integer),
                                     cast(rec_hist_office.delivery_addr_id as integer));  
  end loop;
  close cur_hist_office;
  return p_trans_id;
end;
$$;
/*
select public.colin_hist_first_office('BC0754828', 7056737, 1579980, 78283);
delete
  from addresses
 where id in (select id from addresses_version where transaction_id = 1579980 and office_id is not null);
delete
  from offices
 where id in (select id from offices_version where transaction_id = 1579980);
delete
  from addresses_version
 where transaction_id = 1579980;
delete
  from offices_version
 where transaction_id = 1579980;
*/

--
-- Create parties for a BC business's initial filing: directors, incorporator, completing party if applicable. 
-- Create pary_roles, party_roles_version, parties, parties_version, addresses, and addresses_version records.
--
create or replace function public.colin_hist_first_party(p_corp_num character varying,
                                                         p_colin_event_id integer,
                                                         p_trans_id integer,
                                                         p_business_id integer) returns integer
  language plpgsql
as $$
declare
  cur_hist_party cursor(v_colin_event_id integer, v_corp_num character varying)
    for select cp.mailing_addr_id, cp.delivery_addr_id, cp.party_typ_cd,
               case when cp.party_typ_cd = 'INC' then 'incorporator'
                    when cp.party_typ_cd = 'DIR' then 'director'
                    else cp.party_typ_cd end as party_role,
               case when cp.party_typ_cd = 'DIR' and cp.appointment_dt is null then
                         cast((to_timestamp(to_char(e.event_timerstamp, 'YYYY-MM-DD') || ' 00:00:00', 'YYYY-MM-DD HH24:MI:SS') at time zone 'utc') as timestamp with time zone)
                    else cast((to_timestamp(to_char(cp.appointment_dt, 'YYYY-MM-DD') || ' 00:00:00', 'YYYY-MM-DD HH24:MI:SS') at time zone 'utc') as timestamp with time zone)
                    end as appointment_dt,
               cp.cessation_dt,
               case when cp.last_name is not null and trim(cp.last_name) != '' then upper(cp.last_name) else null end as last_name,
               case when cp.middle_name is not null and trim(cp.middle_name) != '' then upper(cp.middle_name) else null end as middle_name,
               case when cp.first_name is not null and  trim(cp.first_name) != '' then upper(cp.first_name) else null end as first_name,
               case when cp.business_name is not null and  trim(cp.business_name) != '' then upper(cp.business_name) else null end as business_name,
               cp.email_address, cp.prev_party_id, cp.start_event_id, cp.end_event_id,
               (select count(c.event_id) from colin_extract.completing_party c where c.event_id = p_colin_event_id) as completing_count 
          from colin_extract.corp_party cp, colin_extract.event e
         where cp.corp_num = v_corp_num
           and cp.start_event_id = v_colin_event_id
           and cp.start_event_id = e.event_id
           and (cp.end_event_id is null or cp.end_event_id > cp.start_event_id)
           and cp.party_typ_cd in ('DIR', 'INC')
         order by cp.corp_party_id;
  rec_hist_party record;
  completing_party_count integer := -1;
  cp_rec record;
  mailing_id integer := 0;
  party_id integer := 0;
  filing_id integer := 0;
  party_role_id integer := 0;
begin
  open cur_hist_party(p_colin_event_id, p_corp_num);
  loop
    fetch cur_hist_party into rec_hist_party;
    exit when not found;
    party_role_id := nextval('party_roles_id_seq');
    perform colin_hist_party_role_change(p_business_id, p_trans_id, party_role_id, 0, rec_hist_party, null); 
    if completing_party_count = -1 then
      completing_party_count := rec_hist_party.completing_count;
    end if;
  end loop;
  close cur_hist_party;
  -- Completing party conditional.
  if completing_party_count > 0 then
    select mailing_addr_id, upper(first_nme) as first_name, upper(last_nme) as last_name, email_req_address,
      case when middle_nme is not null and trim(middle_nme) != '' then upper(middle_nme) else null end as middle_name 
      into cp_rec
      from colin_extract.completing_party
     where event_id = p_colin_event_id;
    select id
      into filing_id
      from filings
     where business_id = p_business_id
       and transaction_id = p_trans_id;

    mailing_id := nextval('addresses_id_seq');
    party_id := nextval('parties_id_seq');
    party_role_id := nextval('party_roles_id_seq');
    perform colin_hist_address_change(cast(cp_rec.mailing_addr_id as integer), p_business_id, p_trans_id, mailing_id,
                                      cast('mailing' as character varying), 0, null);
    insert into parties_version 
      values(party_id,'person', cp_rec.first_name, cp_rec.middle_name, cp_rec.last_name, null,
             null, null, mailing_id, p_trans_id, null, 0, null, cp_rec.email_req_address, null);      
    insert into parties 
      values(party_id,'person', cp_rec.first_name, cp_rec.middle_name, cp_rec.last_name, null,
             null, null, mailing_id, null, cp_rec.email_req_address, null);      
    insert into party_roles_version 
       values(party_role_id, 'completing_party', null, null, null, party_id, p_trans_id, null, 0, filing_id, null);
    insert into party_roles 
       values(party_role_id, 'completing_party', null, null, null, party_id, filing_id, null);
  end if;
  return p_trans_id;
end;
$$;
/*
select colin_hist_first_party('BC0701238', 5829454, 1815255, 88058);
delete 
  from addresses_version 
 where  transaction_id = 1815255;
delete 
  from parties_version 
 where  transaction_id = 1815255;
delete 
  from party_roles_version 
 where  transaction_id = 1815255;
*/

-- Create share classes, share series records for the BC business initial filing.
-- Insert into the share_classes, share_series, share_classes_version, and share_series_version tables.
create or replace function public.colin_hist_first_shares(p_corp_num character varying,
                                                          p_colin_event_id integer,
                                                          p_trans_id integer,
                                                          p_business_id integer) returns integer
  language plpgsql
as $$
declare
  cur_hist_share_class cursor(v_colin_event_id integer, v_corp_num character varying)
    for select sc.share_class_id, sc.currency_typ_cd, sc.max_share_ind, sc.class_nme, sc.share_quantity, sc.spec_rights_ind,
               sc.par_value_ind, sc.par_value_amt, sc.other_currency,
               (select count(ss.series_id) 
                  from colin_extract.share_series ss 
                 where ss.corp_num = sc.corp_num 
                   and ss.start_event_id = sc.start_event_id
                   and ss.share_class_id = sc.share_class_id) as series_count
          from colin_extract.share_struct_cls sc
         where sc.corp_num = v_corp_num
           and sc.start_event_id = v_colin_event_id
        order by sc.share_class_id;
  counter integer := 0;
  rec_hist_share_class record;
  class_id integer := 0;
begin
  
  open cur_hist_share_class(p_colin_event_id, p_corp_num);
  loop
    fetch cur_hist_share_class into rec_hist_share_class;
    exit when not found;
    counter := counter + 1;
    class_id := colin_hist_shareclass_add(p_trans_id, p_business_id, 0, rec_hist_share_class);
    if rec_hist_share_class.series_count > 0 then
       perform colin_hist_shareseries_add(p_corp_num, p_colin_event_id, p_trans_id,
                                          rec_hist_share_class.share_class_id::integer, class_id, 0);
    end if;
  end loop;
  close cur_hist_share_class;
  return p_trans_id;
end;
$$;
/*
select colin_hist_first_shares('BC0721627', 6229064, 1659857, 80616); -- 1 class, no series
select colin_hist_first_shares('BC1416273', 18126453, 1585014, 78533); -- 1 class, 2 series
delete 
  from share_series 
 where id in (select id from share_series_version where transaction_id = 1659857);   
delete 
  from share_series_version 
 where  transaction_id = 1659857;
delete 
  from share_classes 
 where id in (select id from share_classes_version where transaction_id = 1659857);   
delete 
  from share_classes_version 
 where  transaction_id = 1659857;
*/


-- Create a business record for the BC business initial filing.
-- Insert into the businesses_version table. From tombstone the businesses table data is current and will not be modified.
-- Set initial last_modified,legal_name,founding_date,identifier,fiscal_year_end_date,last_ledger_timestamp,legal_type,
-- restriction_ind,last_coa_date,last_cod_date,state,admin_freeze,send_ar_ind,no_dissolution,in_liquidation,tax_id.
create or replace function public.colin_hist_first_business(p_corp_num character varying,
                                                            p_colin_event_id integer,
                                                            p_trans_id integer,
                                                            p_business_id integer) returns integer
  language plpgsql
as $$
declare
  rec_business record;
begin
  select c.corp_num as identifier, c.recognition_dts as founding_date,
         case when left(c.corp_type_cd, 1) = 'Q' then 'BC' else c.corp_type_cd end as legal_type,
         case when c.bn_15 is not null then bn_15 else bn_9 end as tax_id,
         c.send_ar_ind,
         cn.corp_name as legal_name,
         (select cr.restriction_ind
            from colin_extract.corp_restriction cr
           where cr.corp_num = c.corp_num
             and cr.start_event_id = p_colin_event_id) as restriction_ind
    into rec_business
    from colin_extract.corporation c, colin_extract.corp_name cn
   where c.corp_num = p_corp_num
     and cn.corp_num = c.corp_num
     and cn.start_event_id = p_colin_event_id
     and cn.corp_name_typ_cd in ('CO', 'NB');
  insert into businesses_version(id, last_modified, legal_name, founding_date, identifier, fiscal_year_end_date,
                                 last_ledger_timestamp, legal_type, restriction_ind, last_coa_date, last_cod_date, state,
                                 admin_freeze, send_ar_ind, no_dissolution, in_liquidation, tax_id, transaction_id, operation_type)
    values(p_business_id, rec_business.founding_date, rec_business.legal_name, rec_business.founding_date, p_corp_num,
           rec_business.founding_date, rec_business.founding_date, rec_business.legal_type,
           case when rec_business.restriction_ind is not null then rec_business.restriction_ind else false end,
           rec_business.founding_date, rec_business.founding_date, 'ACTIVE', false, rec_business.send_ar_ind, false,
           false, rec_business.tax_id, p_trans_id, 0);
  return p_trans_id;
end;
$$;
/*
select colin_hist_first_business('BC0754828', 7056737, 1579980, 78283);
*/

-- Additional amalgamation specific changes. Insert into amalgamations, amalgamation_buisinesses tables.
-- All changes for amalgamation filings: COLIN AMALH,AMALV,AMALR,AMLRU,AMLVU,AMLHU,AMLHC,AMLRC,AMLVC filing types.
-- For each ting, create a corresponding businesses_version record setting the state and dissolution date.
-- Ting businesses_version state=historical, dissolution_date=event_ts.
create or replace function public.colin_hist_amalgamation(p_colin_event_id integer,
                                                          p_trans_id integer,
                                                          p_business_id integer,
                                                          p_colin_filing_type character varying) returns integer
  language plpgsql
as $$
declare
  cur_hist_ting cursor(v_colin_event_id integer)
    for select b.id as business_id, e.event_timerstamp, ce.filing_id, cia.* 
          from businesses b, colin_extract.event e, colin_extract.corp_involved_amalgamating cia, colin_event_ids ce
         where e.event_id = v_colin_event_id
           and e.event_id = cia.event_id
           and e.event_id = ce.colin_event_id
           and cia.ting_corp_num = b.identifier;
  cur_hist_business cursor(v_colin_event_id integer)
    for select b.* 
          from businesses_version b, colin_extract.corp_involved_amalgamating cia, filings f
         where cia.event_id = v_colin_event_id 
           and cia.ting_corp_num = b.identifier
           and b.end_transaction_id is null
           and b.transaction_id = f.transaction_id
           and f.status != 'TOMBSTONE';
  rec_business record;
  rec_ting record;
  amalg_id integer := 0;
  amalg_type varchar(30);
  ting_bus_id integer := 0;
  event_ts timestamp;
  bus_trans_id integer;
  ting_role varchar(30);
begin
  if p_colin_filing_type in ('AMALH', 'AMLHU', 'AMLHC') then
    amalg_type := 'horizontal';
  elsif p_colin_filing_type in ('AMALV', 'AMLVU', 'AMLVC') then
    amalg_type := 'vertical';
  elsif p_colin_filing_type = 'CONVAMAL' then
    amalg_type := 'unknown';
  else
    amalg_type := 'regular';
  end if;
  open cur_hist_ting(p_colin_event_id);
  loop
    fetch cur_hist_ting into rec_ting;
    exit when not found;
    if amalg_id = 0 then
      amalg_id := nextval('amalgamation_id_seq');
      event_ts := rec_ting.event_timerstamp;
      insert into amalgamations 
        values(amalg_id, p_business_id, rec_ting.filing_id, event_ts, false, cast(amalg_type as amalgamation_type));
      insert into amalgamations_version 
        values(amalg_id, p_business_id, rec_ting.filing_id, event_ts, cast(amalg_type as amalgamation_type), false,
               p_trans_id, null, 0);
    end if;
    ting_bus_id := nextval('amalgamating_business_id_seq');
    if rec_ting.adopted_corp_ind = true then
      ting_role := 'primary';
    else
      ting_role := 'amalgamating';
    end if;
    insert into amalgamating_businesses
      values(ting_bus_id, rec_ting.business_id, amalg_id, null, rec_ting.foreign_nme, rec_ting.home_juri_num,
             cast(ting_role as amalgamating_business_role), rec_ting.can_jur_typ_cd);
    insert into amalgamating_businesses_version
      values(ting_bus_id, rec_ting.business_id, amalg_id, cast(ting_role as amalgamating_business_role),
             null, rec_ting.can_jur_typ_cd, rec_ting.foreign_nme, rec_ting.home_juri_num, p_trans_id, null, 0);
  end loop;
  close cur_hist_ting;

  open cur_hist_business(p_colin_event_id);
  loop
    fetch cur_hist_business into rec_business;
    exit when not found;
    bus_trans_id := rec_business.transaction_id;
    rec_business.operation_type := 1;
    rec_business.transaction_id := p_trans_id;
    rec_business.last_modified := event_ts;
    rec_business.dissolution_date := event_ts;
    rec_business.state := 'HISTORICAL';
    update businesses_version
       set end_transaction_id = p_trans_id
     where id = rec_business.id
       and end_transaction_id is null
       and transaction_id = bus_trans_id;     
    insert into businesses_version
      values (rec_business.id,rec_business.last_modified,rec_business.last_ledger_id,rec_business.last_remote_ledger_id,
              rec_business.last_ar_date,rec_business.legal_name,rec_business.founding_date,rec_business.dissolution_date,
              rec_business.identifier,rec_business.tax_id,rec_business.fiscal_year_end_date,rec_business.submitter_userid,
              rec_business.transaction_id,rec_business.end_transaction_id,rec_business.operation_type,rec_business.last_agm_date,
              rec_business.last_ledger_timestamp,rec_business.legal_type,rec_business.restriction_ind,rec_business.last_ar_year,
              rec_business.association_type,rec_business.last_coa_date,rec_business.last_cod_date,rec_business.state,
              rec_business.admin_freeze,rec_business.state_filing_id,rec_business.naics_key,rec_business.naics_code,
              rec_business.naics_description,rec_business.start_date,rec_business.foreign_jurisdiction,
              rec_business.foreign_legal_name,rec_business.send_ar_ind,rec_business.restoration_expiry_date,
              rec_business.last_ar_reminder_year,rec_business.continuation_out_date,rec_business.foreign_jurisdiction_region,
              rec_business.no_dissolution,rec_business.last_tr_year,rec_business.amalgamation_out_date,
              rec_business.in_liquidation,rec_business.accession_number);
  end loop;
  close cur_hist_business;
  return p_trans_id;
end;
$$;
/*
select public.colin_hist_first_filing('BC0101502'); -- Ting 1 78465
select public.colin_hist_first_filing('BC0303909'); -- Ting 2 78467
select public.colin_hist_first_filing('BC1276757'); -- AMALH 78471
select colin_hist_filing_rollback(1583682); -- AMALH
select colin_hist_filing_rollback(1583603); -- Ting 2
select colin_hist_filing_rollback(1583626); -- Ting 1

select public.colin_hist_first_filing('BC0435126'); -- Ting 1 78246
select public.colin_hist_first_filing('BC0292517'); -- Ting 2 78243
select public.colin_hist_first_filing('BC0690750'); -- AMALR 78248
select colin_hist_filing_rollback(1579375); -- AMALR
select colin_hist_filing_rollback(1579213); -- Ting 2
select colin_hist_filing_rollback(1579206); -- Ting 1

*/


-- COLIN only adds, no history.
-- Insert into the jurisdictions and jurisdictions_version tables.
CREATE OR REPLACE FUNCTION public.colin_hist_jurisdiction(p_colin_event_id integer,
                                                          p_trans_id integer,
                                                          p_business_id integer,
                                                          p_corp_num character varying)
 RETURNS integer
 LANGUAGE plpgsql
AS $$
declare
  rec_jur record;
  jur_id integer := 0;
begin
  select j.*,
         (select f.id from filings f where f.transaction_id = p_trans_id) as filing_id 
    into rec_jur
    from colin_extract.jurisdiction j
   where j.corp_num = p_corp_num
     and j.start_event_id = p_colin_event_id;
  if FOUND then
    jur_id := nextval('jurisdictions_id_seq');
    insert into jurisdictions
      values(jur_id, 'CA', rec_jur.can_jur_typ_cd, rec_jur.home_juris_num, rec_jur.home_company_nme, null, rec_jur.home_recogn_dt,
             rec_jur.bc_xpro_num, null, p_business_id, rec_jur.filing_id);
    insert into jurisdictions_version
      values(jur_id, 'CA', rec_jur.can_jur_typ_cd, rec_jur.home_juris_num, rec_jur.home_company_nme, null, rec_jur.home_recogn_dt,
             rec_jur.bc_xpro_num, null, p_business_id, rec_jur.filing_id, p_trans_id, null, 0);
  end if;

  return p_trans_id;
end;
$$

--
-- Create all records for the business's initial filing.
--
create or replace function public.colin_hist_first_filing(p_corp_num character varying) returns integer
  language plpgsql
as $$
declare
  colin_event_id integer := 0;
  trans_id integer := 0;
  bus_id integer := 0;
  resolution_dt timestamp with time zone;
  alias_count integer := 0;
  event_type varchar(20);
  filing_type varchar(20);
begin
  select min(ce.colin_event_id), min(f.transaction_id), min(f.business_id)
    into colin_event_id, trans_id, bus_id
    from businesses b, filings f, colin_event_ids ce
   where b.identifier = p_corp_num
     and b.id = f.business_id
     and f.source = 'COLIN'
     and f.status = 'COMPLETED'
     and f.id = ce.filing_id
     and f.filing_type not in ('conversionLedger');

  perform colin_hist_first_office(p_corp_num, colin_event_id, trans_id, bus_id);
  perform colin_hist_first_party(p_corp_num, colin_event_id, trans_id, bus_id);
  perform colin_hist_first_shares(p_corp_num, colin_event_id, trans_id, bus_id);
  perform colin_hist_first_business(p_corp_num, colin_event_id, trans_id, bus_id);
  select count(cn.start_event_id),
         (select r.resolution_dt 
           from colin_extract.resolution r
           where r.corp_num = p_corp_num
             and r.start_event_id = colin_event_id),
         (select e.event_type_cd from colin_extract.event e where e.event_id = colin_event_id) as event_type_cd,
         (select f.filing_type_cd from colin_extract.filing f where f.event_id = colin_event_id) as filing_type_cd
    into alias_count, resolution_dt, event_type, filing_type
    from colin_extract.corp_name cn
   where cn.corp_num = p_corp_num
     and cn.start_event_id = colin_event_id
     and cn.corp_name_typ_cd not in ('CO', 'NB');

  if resolution_dt is not null then
    perform colin_hist_resolution_add(bus_id, trans_id, resolution_dt);  
  end if;
  if alias_count > 0 then
    perform colin_hist_alias_add(p_corp_num, colin_event_id, bus_id, trans_id, null);  
  end if;
  if event_type in ('CONVICORP', 'CONVAMAL') then
    perform colin_hist_officer(colin_event_id, bus_id, trans_id, p_corp_num);
    if event_type in ('CONVAMAL') then
      perform colin_hist_amalgamation(colin_event_id, trans_id, bus_id, event_type);
      perform colin_hist_jurisdiction(colin_event_id, trans_id, bus_id, p_corp_num);
    end if;
  elsif event_type = 'CONVCIN' then
    perform colin_hist_jurisdiction(colin_event_id, trans_id, bus_id, p_corp_num);
  end if;
  if filing_type is not null and filing_type in ('AMALH','AMALV','AMALR','AMLRU','AMLVU','AMLHU','AMLHC','AMLRC','AMLVC') then
    perform colin_hist_amalgamation(colin_event_id, trans_id, bus_id, filing_type);
  elsif filing_type is not null and filing_type in ('CONTI','CONTU','CONTC') then
    perform colin_hist_jurisdiction(colin_event_id, trans_id, bus_id, p_corp_num);
  end if;

  return trans_id;
end;
$$;
/*
select public.colin_hist_first_filing('C1225717'); -- CONTI 78553
select colin_hist_filing_rollback(1585244);

select public.colin_hist_first_filing('C1170744'); -- CONTU 78552
select colin_hist_filing_rollback(1585095);

*/

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

-- Historical update to edit a single officer for a single filing.
-- And officer edit may update the offices held - the party roles.
-- If the existing offices match the new offices the party roles are unchanged.
-- Otherwise, if the existing offices count matches the new count, update the roles.
-- Otherwise if the existing count > new count, remove offices using the event timestamp as the cessation date.
-- Otherwise if the existing count < new count, add offices using the event timestamp as the appointment date.
-- And edit may also modify the party name or addresses.
-- Update party_roles, parties, party_roles_version, parties_version, addresses, addresses_version
-- Update end_transaction_id on addresses_version, parties_version, party_roles_version
create or replace function public.colin_hist_officer_edit(p_trans_id integer,
                                                          p_business_id integer,
                                                          p_rec_party record) returns integer
  language plpgsql
as $$
declare
  cur_party_role cursor(v_business_id integer, v_party_id integer)
    for select pr.*
          from party_roles_version pr
         where pr.business_id = v_business_id
           and pr.party_class_type = 'OFFICER'
           and pr.party_id = v_party_id
           and pr.end_transaction_id is null
           and pr.cessation_date is null
           and pr.operation_type in (0, 1);
  cur_office_edit cursor(v_corp_party_id integer, v_prev_party_id integer)
    for select oh.officer_typ_cd, to_officer_role(oh.officer_typ_cd) as officer_role, cp.corp_party_id, cp.prev_party_id,
               cp.start_event_id
      from colin_extract.corp_party cp, colin_extract.offices_held oh
     where cp.corp_party_id in (v_prev_party_id, v_corp_party_id)
       and cp.corp_party_id = oh.corp_party_id
    order by cp.corp_party_id desc, oh.officer_typ_cd;

  rec_party_role record;
  rec_colin_change record;
  officer_role varchar(30);
  party_role_id integer := 0;
  new_count integer := 0;
  existing_count integer := 0;
  new_offices varchar(100);
  existing_offices varchar(100);
  remove_offices varchar(100);
  add_offices varchar(100);
  previous_party_id integer;
begin
  new_offices := '';
  existing_offices := '';
  remove_offices := '';
  add_offices := '';
  new_count := 0;
  existing_count := 0;
  
  select max(corp_party_id)
    into previous_party_id
    from colin_extract.corp_party
   where corp_num = p_rec_party.corp_num
     and party_typ_cd = 'OFF'
     and prev_party_id = p_rec_party.prev_party_id
     and corp_party_id < p_rec_party.corp_party_id;
  if previous_party_id is null then
    previous_party_id := p_rec_party.prev_party_id;
  end if;
   
  open cur_office_edit(p_rec_party.corp_party_id, previous_party_id);
  loop
    fetch cur_office_edit into rec_colin_change;
    exit when not found;
    if rec_colin_change.start_event_id = p_rec_party.start_event_id then
      if new_offices = '' then
        new_offices := rec_colin_change.officer_role;
      else
        new_offices := new_offices || ',' || rec_colin_change.officer_role;
      end if;
      new_count := new_count + 1;
    else
      if existing_offices = '' then
        existing_offices := rec_colin_change.officer_role;
      else
        existing_offices := existing_offices || ',' || rec_colin_change.officer_role;
      end if;
      existing_count := existing_count + 1;
      if position(rec_colin_change.officer_role in new_offices) < 1 then
        if remove_offices = '' then
          remove_offices := rec_colin_change.officer_role;
        else
          remove_offices := remove_offices || ',' || rec_colin_change.officer_role;
        end if;
      end if;
    end if;
  end loop;
  close cur_office_edit;
  for i in 1 .. array_length(string_to_array(new_offices, ','), 1)
  loop
    officer_role := SPLIT_PART(new_offices, ',', i);
    if position(officer_role in existing_offices) < 1 then
      if add_offices = '' then
        add_offices := officer_role;
      else
        add_offices := add_offices || ',' || officer_role;
      end if;
    end if;
  end loop;

  perform colin_hist_party_change(p_business_id, p_trans_id, p_rec_party.party_id, 1, p_rec_party, null);

  if new_offices = existing_offices then -- no change
    officer_role := null;
  elsif new_count = existing_count then -- replacing
    open cur_party_role(p_business_id, p_rec_party.party_id);
    loop
      fetch cur_party_role into rec_party_role;
      exit when not found;
      if position(rec_party_role.role in remove_offices) > 0 then
        officer_role := SPLIT_PART(add_offices, ',', 1);
        if officer_role is not null and length(officer_role) >= 3 then
          add_offices := replace(add_offices, officer_role, '');
          if left(add_offices, 1) = ',' and length(add_offices) > 1 then
            add_offices := substr(add_offices, 2);
          end if;
          update party_roles
             set role = officer_role
           where business_id = p_business_id
             and id = rec_party_role.id;
          update party_roles_version
             set end_transaction_id = p_trans_id
           where id = rec_party_role.id
             and end_transaction_id is null
             and cessation_date is null;
          insert into party_roles_version
            values(rec_party_role.id,
                   officer_role,
                   rec_party_role.appointment_date,
                   rec_party_role.cessation_date,
                   rec_party_role.business_id,
                   rec_party_role.party_id,
                   p_trans_id,
                   null,
                   1,
                   rec_party_role.filing_id,
                   rec_party_role.party_class_type);
        end if;
      end if;
    end loop;
    close cur_party_role;
  else
    if add_offices != '' then
      for i in 1 .. array_length(string_to_array(add_offices, ','), 1)
      loop
        officer_role := SPLIT_PART(add_offices, ',', i);
        party_role_id := nextval('party_roles_id_seq');
        insert into party_roles_version 
          values(party_role_id, officer_role, p_rec_party.party_date, null,
                 p_business_id, p_rec_party.party_id, p_trans_id, null, 0, null, cast('OFFICER' as partyclasstype));
        insert into party_roles 
          values(party_role_id, officer_role, p_rec_party.party_date, null, 
                 p_business_id, p_rec_party.party_id, null, cast('OFFICER' as partyclasstype));
      end loop;
    end if;

    if remove_offices != '' then
      for i in 1 .. array_length(string_to_array(remove_offices, ','), 1)
      loop
        officer_role := SPLIT_PART(remove_offices, ',', i);
        select pr.*
          from party_roles_version pr
          into rec_party_role
         where pr.business_id = p_business_id
           and pr.party_class_type = 'OFFICER'
           and pr.party_id = p_rec_party.party_id
           and pr.role = officer_role
           and pr.end_transaction_id is null
           and pr.transaction_id != p_trans_id
           and pr.operation_type in (0, 1);
        if found then
          update party_roles
             set cessation_date = p_rec_party.party_date
           where business_id = p_business_id
             and id = rec_party_role.id;
          rec_party_role.end_transaction_id := p_trans_id;
          insert into party_roles_version
            values(rec_party_role.id,
                   rec_party_role.role,
                   rec_party_role.appointment_date,
                   p_rec_party.party_date,
                   rec_party_role.business_id,
                   rec_party_role.party_id,
                   p_trans_id,
                   null,
                   1,
                   rec_party_role.filing_id,
                   rec_party_role.party_class_type);
        end if;
      end loop;
    end if;
  end if;
  return p_trans_id;
end;
$$;

-- Historical update to remove a single officer for a single filing.
-- Set the active party_roles record cessation date. Do not modify the parties record.
-- Set the party_roles_version end transaction id and cessation date.
-- Set the parties_version end transaction id.
-- Update party_roles, parties, party_roles_version, parties_version, addresses, addresses_version
-- Update end_transaction_id on addresses_version, parties_version, party_roles_version
create or replace function public.colin_hist_officer_remove(p_existing_trans_id integer,
                                                            p_trans_id integer,
                                                            p_business_id integer,
                                                            p_rec_party record) returns integer
  language plpgsql
as $$
declare
  cur_party_role cursor(v_trans_id integer, v_business_id integer, v_first character varying, v_last character varying)
    for select pr.*
          from party_roles_version pr, parties_version p
         where pr.business_id = v_business_id
           and pr.transaction_id = v_trans_id
           and pr.party_class_type = 'OFFICER'
           and pr.transaction_id = p.transaction_id
           and pr.party_id = p.id
           and p.first_name = v_first
           and p.last_name = v_last
           and pr.operation_type in (0, 1)
           and pr.end_transaction_id is null;
  rec_party_role record;
  party_id integer := 0;
begin
  open cur_party_role(p_existing_trans_id, p_business_id, p_rec_party.first_name, p_rec_party.last_name);
  loop
    fetch cur_party_role into rec_party_role;
    exit when not found;
    if p_rec_party.cessation_dt is null and p_rec_party.party_date is not null then
      p_rec_party.cessation_dt := p_rec_party.party_date;
    end if;
    p_rec_party.party_role := rec_party_role.role; 
    perform colin_hist_party_role_change(p_business_id, p_trans_id, rec_party_role.id, 2, p_rec_party, null);  
  end loop;
  close cur_party_role;
  return p_trans_id;
end;
$$;

-- Resolution removed or updated matching on transaction id.
-- Set end_transaction_id on removed resolutions_version record.
-- If deleting (p_update_type = 2):
--   1. Insert delete record in the resolutions_version table.
--   2. Delete the corresponding record from the resolutions table.
create or replace function public.colin_hist_resolution_update(p_existing_trans_id integer,
                                                               p_trans_id integer,
                                                               p_business_id integer,
                                                               p_resolution_dt  timestamp with time zone, 
                                                               p_update_type integer) returns integer
  language plpgsql
as $$
declare
  rec_resolution record;
begin
  if p_update_type = 2 then
    select *
      into rec_resolution
      from resolutions_version
     where business_id = p_business_id
       and transaction_id = p_existing_trans_id
       and operation_type in (0, 1)
       and (end_transaction_id is null or end_transaction_id = p_trans_id)
     fetch first 1 rows only;
    insert into resolutions_version
      values(rec_resolution.id,
            rec_resolution.resolution_date,
            rec_resolution.type,
            rec_resolution.business_id,
            p_trans_id,
            null,
            p_update_type,
            rec_resolution.resolution,
            null,
            null,
            null);
  elsif p_update_type = 3 then 
    insert into resolutions_version
      values(nextval('resolutions_id_seq'),
             p_resolution_dt,
             'SPECIAL',
             p_business_id,
             p_trans_id,
             null,
             1,
             null,
             null,
             null,
             null);
  end if;
  if p_update_type in (1, 2) then
    update resolutions_version
       set end_transaction_id = p_trans_id
     where business_id = p_business_id
       and transaction_id = p_existing_trans_id
       and operation_type in (0, 1)
       and end_transaction_id is null;
  end if;
  if p_update_type = 2 then
    delete
      from resolutions
     where id in (select distinct id 
                    from resolutions_version 
                   where transaction_id = p_existing_trans_id 
                     and business_id = p_business_id
                     and operation_type in (0, 1)
                     and (end_transaction_id is null or end_transaction_id = p_trans_id));
  elsif p_update_type = 3 then
    update resolutions
       set resolution_date = p_resolution_dt
     where id in (select distinct id 
                    from resolutions_version 
                   where transaction_id = p_existing_trans_id 
                     and business_id = p_business_id
                     and operation_type in (0, 1)
                     and (end_transaction_id is null or end_transaction_id = p_trans_id));
  end if;
  return p_trans_id;
end;
$$;

-- Name alias removed or updated matching on transaction id.
-- Set end_transaction_id on removed aliases_version record.
-- If deleting (p_update_type = 2):
--   1. Insert delete record in the aliases_version table.
--   2. Delete the corresponding record from the aliases table.
create or replace function public.colin_hist_alias_update(p_existing_trans_id integer,
                                                          p_trans_id integer,
                                                          p_business_id integer,
                                                          p_alias character varying,
                                                          p_name_type character varying,
                                                          p_update_type integer) returns integer
  language plpgsql
as $$
declare
  rec_alias record;
begin
  if p_update_type = 2 then
    select *
      into rec_alias
      from aliases_version
     where business_id = p_business_id
       and transaction_id = p_existing_trans_id
       and operation_type in (0, 1)
       and (end_transaction_id is null or end_transaction_id = p_trans_id)
     fetch first 1 rows only;
    insert into aliases_version
      values(rec_alias.id,
            rec_alias.alias,
            rec_alias.type,
            rec_alias.business_id,
            p_trans_id,
            null,
            p_update_type);
  elsif p_update_type = 3 then 
    insert into aliases_version
      values(nextval('aliases_id_seq'),
             p_alias,
             p_name_type,
             p_business_id,
             p_trans_id,
             null,
             1);
  end if;
  if p_update_type in (1, 2) then
    update aliases_version
       set end_transaction_id = p_trans_id
     where business_id = p_business_id
       and transaction_id = p_existing_trans_id
       and operation_type in (0, 1)
       and end_transaction_id is null;
  end if;
  if p_update_type = 2 then
    delete
      from aliases
     where id in (select distinct id 
                    from aliases_version 
                   where transaction_id = p_existing_trans_id 
                     and business_id = p_business_id
                     and operation_type in (0, 1)
                     and (end_transaction_id is null or end_transaction_id = p_trans_id));
  elsif p_update_type = 3 then
    update aliases
       set alias = p_alias, type = p_name_type
     where id in (select distinct id 
                    from aliases_version 
                   where transaction_id = p_existing_trans_id 
                     and business_id = p_business_id
                     and operation_type in (0, 1)
                     and (end_transaction_id is null or end_transaction_id = p_trans_id));
  end if;
  return p_trans_id;
end;
$$;

--
-- Historical director updates for a single filing.
-- 1. Address changes.
-- 2. Remove director. 
-- 3. Add director.
-- 4. Change director appointment, cessation dates.
create or replace function public.colin_hist_director(p_colin_event_id integer,
                                                      p_business_id integer,
                                                      p_trans_id integer,
                                                      p_corp_num character varying) returns integer
  language plpgsql
as $$
declare
  cur_hist_party cursor(v_colin_event_id integer, v_corp_num character varying)
    for select cp.mailing_addr_id, cp.delivery_addr_id, cp.party_typ_cd, cast('director' as character varying) as party_role,
               case when cp.appointment_dt is not null then
                         cast((to_timestamp(to_char(cp.appointment_dt, 'YYYY-MM-DD') || ' 00:00:00', 'YYYY-MM-DD HH24:MI:SS') at time zone 'utc') as timestamp with time zone)
                    else cp.appointment_dt end as appointment_dt,
               case when cp.cessation_dt is not null then
                         cast((to_timestamp(to_char(cp.cessation_dt, 'YYYY-MM-DD') || ' 00:00:00', 'YYYY-MM-DD HH24:MI:SS') at time zone 'utc') as timestamp with time zone)
                    else cp.cessation_dt end as cessation_dt,
               case when cp.last_name is not null and trim(cp.last_name) != '' then upper(cp.last_name) else null end as last_name,
               case when cp.middle_name is not null and trim(cp.middle_name) != '' then upper(cp.middle_name) else null end as middle_name,
               case when cp.first_name is not null and  trim(cp.first_name) != '' then upper(cp.first_name) else null end as first_name,
               case when cp.business_name is not null and  trim(cp.business_name) != '' then upper(cp.business_name) else null end as business_name,
               cp.email_address, cp.prev_party_id, cp.start_event_id, cp.end_event_id,
               case when cp.start_event_id = v_colin_event_id and cp.prev_party_id is not null then
                         (select pr.id 
                            from filings f, colin_event_ids ce, colin_extract.corp_party cp2, party_roles_version pr, parties_version p
                           where cp2.corp_party_id = cp.prev_party_id
                             and ce.colin_event_id = cp2.start_event_id
                             and ce.filing_id = f.id
                             and pr.business_id = f.business_id
                             and pr.role = 'director'
                             and pr.party_id = p.id
                             and p.transaction_id = f.transaction_id
                             and p.first_name = upper(cp2.first_name)
                             and p.last_name = upper(cp2.last_name)
                             and pr.operation_type in (0, 1)
                             and pr.end_transaction_id is null)
                    when cp.start_event_id != v_colin_event_id and cp.end_event_id is not null and cp.end_event_id = v_colin_event_id then
                         (select pr.id 
                            from filings f, colin_event_ids ce, party_roles_version pr, parties_version p
                           where ce.colin_event_id = cp.start_event_id
                             and ce.filing_id = f.id
                             and pr.business_id = f.business_id
                             and pr.role = 'director'
                             and pr.party_id = p.id
                             and p.transaction_id = f.transaction_id
                             and p.first_name = upper(cp.first_name)
                             and p.last_name = upper(cp.last_name)
                             and pr.operation_type in (0, 1)
                             and pr.end_transaction_id is null
                             fetch first 1 rows only)
                   else null end as party_role_id,
               case when cp.start_event_id != v_colin_event_id and cp.end_event_id is not null and cp.end_event_id = v_colin_event_id then
                         (select count(cp2.corp_party_id) 
                            from colin_extract.corp_party cp2
                           where cp2.corp_num = cp.corp_num
                             and cp2.start_event_id = cp.end_event_id
                             and cp2.prev_party_id is not null
                             and cp2.prev_party_id = cp.corp_party_id)
                   else 0 end as link_count,
               (select cast((to_timestamp(to_char(e.event_timerstamp, 'YYYY-MM-DD') || ' 00:00:00', 'YYYY-MM-DD HH24:MI:SS') at time zone 'utc') as timestamp with time zone)
                  from colin_extract.event e
                 where e.event_id = v_colin_event_id) as party_date
          from colin_extract.corp_party cp
        where cp.corp_num = v_corp_num
          and (cp.start_event_id = v_colin_event_id or cp.end_event_id = v_colin_event_id)
          and cp.party_typ_cd = 'DIR'
        order by corp_party_id;
  rec_hist_dir record;
  counter integer := 0;
  update_type integer := 3;
  party_role_id integer := 0;
begin
  open cur_hist_party(p_colin_event_id, p_corp_num);
  loop
    fetch cur_hist_party into rec_hist_dir;
    exit when not found;
    update_type := 3; -- Do nothing
    -- Removing if not linked, otherwise set up for update.
    if rec_hist_dir.start_event_id != p_colin_event_id and rec_hist_dir.end_event_id is not null and 
       rec_hist_dir.end_event_id = p_colin_event_id and rec_hist_dir.link_count = 0 then
      update_type := 2;
    elsif rec_hist_dir.start_event_id = p_colin_event_id and rec_hist_dir.prev_party_id is not null then
      update_type := 1;
    elsif rec_hist_dir.start_event_id = p_colin_event_id then
      update_type := 0;
    end if;
    if update_type in (1, 2) then
      party_role_id := rec_hist_dir.party_role_id;
    elsif update_type = 0 then
      party_role_id := nextval('party_roles_id_seq');
    end if;
    if update_type in (0, 1) and rec_hist_dir.appointment_dt is null and rec_hist_dir.party_date is not null then
      rec_hist_dir.appointment_dt := rec_hist_dir.party_date;
    end if;
    if update_type = 2 and rec_hist_dir.cessation_dt is null and rec_hist_dir.party_date is not null then
      rec_hist_dir.cessation_dt := rec_hist_dir.party_date;
    end if;
    if party_role_id is not null and party_role_id > 0 and update_type != 3 then
      counter := counter + 1;
      perform colin_hist_party_role_change(p_business_id, p_trans_id, party_role_id, update_type, rec_hist_dir, null);  
    end if;
  end loop;
  close cur_hist_party;
  return counter;
end;
$$;
/*
select public.colin_hist_first_filing('BC0701238');
select colin_hist_filing(7656446, 88058, 1815266, 'BC0701238', 'changeOfDirectors', 'NOCDR');
select colin_hist_filing(7667797, 88058, 1815268, 'BC0701238', 'changeOfDirectors', 'NOCDR');
select colin_hist_filing_rollback(1815268);
select colin_hist_filing_rollback(1815266);
select colin_hist_filing_rollback(1815255);
*/

--
-- Historical officer updates for a single filing. And officer may hold 1 or more offices.
-- 1. Remove officer. 
-- 2. Add officer.
-- 3. Change officer offices held.
-- Inserts into addresses, addresses_version, parties, parties_version, party_roles, party_roles_version.
create or replace function public.colin_hist_officer(p_colin_event_id integer,
                                                     p_business_id integer,
                                                     p_trans_id integer,
                                                     p_corp_num character varying) returns integer
  language plpgsql
as $$
declare
  cur_hist_party cursor(v_colin_event_id integer, v_corp_num character varying)
     for select cp.mailing_addr_id, cp.delivery_addr_id, cp.party_typ_cd, cast('officer' as character varying) as party_role,
                case when cp.appointment_dt is not null then
                          cast((to_timestamp(to_char(cp.appointment_dt, 'YYYY-MM-DD') || ' 00:00:00', 'YYYY-MM-DD HH24:MI:SS') at time zone 'utc') as timestamp with time zone)
                     else cp.appointment_dt end as appointment_dt,
                case when cp.cessation_dt is not null then
                          cast((to_timestamp(to_char(cp.cessation_dt, 'YYYY-MM-DD') || ' 00:00:00', 'YYYY-MM-DD HH24:MI:SS') at time zone 'utc') as timestamp with time zone)
                     else cp.cessation_dt end as cessation_dt,
                case when cp.last_name is not null and trim(cp.last_name) != '' then upper(cp.last_name) else null end as last_name,
                case when cp.middle_name is not null and trim(cp.middle_name) != '' then upper(cp.middle_name) else null end as middle_name,
                case when cp.first_name is not null and  trim(cp.first_name) != '' then upper(cp.first_name) else null end as first_name,
                case when cp.business_name is not null and  trim(cp.business_name) != '' then upper(cp.business_name) else null end as business_name,
                cp.email_address, cp.corp_party_id, cp.prev_party_id, cp.start_event_id, cp.end_event_id,
                case when cp.start_event_id != v_colin_event_id and cp.end_event_id is not null and cp.end_event_id = v_colin_event_id
                          and cp.prev_party_id > 0 and cp.cessation_dt is not null then
                          (select f.transaction_id 
                             from filings f, colin_event_ids ce, colin_extract.corp_party cp2
                            where cp2.corp_party_id = cp.prev_party_id
                              and cp2.corp_num = cp.corp_num
                              and ce.colin_event_id = cp2.start_event_id
                              and ce.filing_id = f.id)
                     when cp.start_event_id != v_colin_event_id and cp.end_event_id is not null and cp.end_event_id = v_colin_event_id then
                          (select f.transaction_id 
                             from filings f, colin_event_ids ce
                            where ce.colin_event_id = cp.start_event_id
                              and ce.filing_id = f.id)
                    else null end as end_trans_id,
                case when cp.start_event_id != v_colin_event_id and cp.end_event_id is not null and cp.end_event_id = v_colin_event_id then
                          (select count(cp2.corp_party_id) 
                             from colin_extract.corp_party cp2
                            where cp2.corp_num = cp.corp_num
                              and cp2.start_event_id = cp.end_event_id
                              and cp2.prev_party_id is not null
                              and (cp2.prev_party_id = cp.corp_party_id or cp2.prev_party_id = cp.prev_party_id))
                    else 0 end as link_count,
                (select cast((to_timestamp(to_char(e.event_timerstamp, 'YYYY-MM-DD') || ' 00:00:00', 'YYYY-MM-DD HH24:MI:SS') at time zone 'utc') as timestamp with time zone)
                   from colin_extract.event e
                  where e.event_id = v_colin_event_id) as party_date,
               case when cp.start_event_id = v_colin_event_id and cp.prev_party_id is not null then
                         (select pr.party_id 
                            from filings f, colin_event_ids ce, colin_extract.corp_party cp2, party_roles_version pr, parties_version p
                           where cp2.corp_party_id = cp.prev_party_id
                             and ce.colin_event_id = cp2.start_event_id
                             and ce.filing_id = f.id
                             and pr.business_id = f.business_id
                             and pr.party_class_type is not null
                             and pr.party_class_type = 'OFFICER'
                             and pr.party_id = p.id
                             and p.transaction_id = f.transaction_id
                             and p.first_name = upper(cp2.first_name)
                             and p.last_name = upper(cp2.last_name)
                             and pr.operation_type in (0, 1)
                             and pr.cessation_date is null
                             and pr.end_transaction_id is null
                             fetch first 1 rows only)
                   else null end as party_id,
                   cp.corp_num
          from colin_extract.corp_party cp 
        where cp.corp_num = v_corp_num
          and (cp.start_event_id = v_colin_event_id or cp.end_event_id = v_colin_event_id)
          and cp.party_typ_cd = 'OFF'
        order by corp_party_id;
  cur_hist_officer_offices cursor(v_party_id integer)
    for select to_officer_role(officer_typ_cd) as party_role
      from colin_extract.offices_held
     where corp_party_id = v_party_id;
  rec_hist_party record;
  rec_hist_officer_office record;
  counter integer := 0;
  update_type integer := 3;
  party_id integer := 0;
  party_role_id integer := 0;
begin
  open cur_hist_party(p_colin_event_id, p_corp_num);
  loop
    fetch cur_hist_party into rec_hist_party;
    exit when not found;
    update_type := 3; -- Do nothing
    -- Removing if not linked, otherwise set up for update.
    if rec_hist_party.start_event_id != p_colin_event_id and rec_hist_party.end_event_id is not null and 
       rec_hist_party.end_event_id = p_colin_event_id and rec_hist_party.link_count = 0 then
      update_type := 2;
    elsif rec_hist_party.start_event_id != p_colin_event_id and rec_hist_party.end_event_id is not null and 
       rec_hist_party.end_event_id = p_colin_event_id and rec_hist_party.cessation_dt is not null then
      update_type := 2;
    elsif rec_hist_party.start_event_id = p_colin_event_id and rec_hist_party.prev_party_id is not null and rec_hist_party.prev_party_id > 0 then
      update_type := 1;
    elsif rec_hist_party.start_event_id = p_colin_event_id then
      update_type := 0;
    end if;
    -- Removing
    if update_type = 2 then
      counter := counter + 1;
      perform colin_hist_officer_remove(rec_hist_party.end_trans_id::integer, p_trans_id, p_business_id, rec_hist_party);
    -- Editing: appointment date does not change.
    elsif update_type = 1 and rec_hist_party.party_id is not null then
      rec_hist_party.appointment_dt := null;
      rec_hist_party.cessation_dt := null;
      counter := counter + 1;
      perform colin_hist_officer_edit(p_trans_id, p_business_id, rec_hist_party);
    -- Adding
    elsif update_type = 0 then
      counter := counter + 1;
      party_id := nextval('parties_id_seq');
      perform colin_hist_party_change(p_business_id, p_trans_id, party_id, 0, rec_hist_party, null);
      if rec_hist_party.appointment_dt is null and rec_hist_party.party_date is not null then
        rec_hist_party.appointment_dt := rec_hist_party.party_date;
      end if;
      rec_hist_party.cessation_dt := null;
      open cur_hist_officer_offices(rec_hist_party.corp_party_id);
      loop
        fetch cur_hist_officer_offices into rec_hist_officer_office;          
        exit when not found;
        party_role_id := nextval('party_roles_id_seq');
        insert into party_roles_version 
          values(party_role_id, rec_hist_officer_office.party_role, rec_hist_party.appointment_dt, rec_hist_party.cessation_dt,
                 p_business_id, party_id, p_trans_id, null, 0, null, cast('OFFICER' as partyclasstype));
        insert into party_roles 
          values(party_role_id, rec_hist_officer_office.party_role, rec_hist_party.appointment_dt, rec_hist_party.cessation_dt, 
                 p_business_id, party_id, null, cast('OFFICER' as partyclasstype));
      end loop;
      close cur_hist_officer_offices;
    end if;
  end loop;
  close cur_hist_party;
  return counter;
end;
$$;

/*
select colin_hist_officer(7656192, 88058, 1815262, 'BC0701238'); -- add officer
select colin_hist_officer(7656197, 88058, 1815264, 'BC0701238'); -- remove officer, add officer
select colin_hist_filing_rollback(1815264);
select colin_hist_filing_rollback(1815262);
*/

-- Remove all active share classes and series:
-- 1. Delete from share_series.
-- 2. Set end_event_id in share_series_version.
-- 3. Create share_series_version with op type = 2.
-- 4. Delete from share_classes.
-- 5. Set end_event_id in share_classes_version.
-- 6. Create share_classes_version with op type = 2.
create or replace function public.colin_hist_shares_remove(p_existing_trans_id integer,
                                                           p_trans_id integer,
                                                           p_business_id integer) returns integer
  language plpgsql
as $$
declare
  cur_hist_series cursor(v_trans_id integer)
    for select *
          from share_series_version 
         where transaction_id = v_trans_id
      order by id;
  cur_hist_class cursor(v_business_id integer, v_trans_id integer)
    for select *
          from share_classes_version 
         where business_id = v_business_id
           and transaction_id = v_trans_id
      order by id;
  rec_hist_series record;
  rec_hist_class record;
begin
  open cur_hist_series(p_existing_trans_id);
  loop
    fetch cur_hist_series into rec_hist_series;
    exit when not found;
      insert into share_series_version
        values(rec_hist_series.id,
               rec_hist_series.name,
               rec_hist_series.priority,
               rec_hist_series.max_share_flag,
               rec_hist_series.max_shares,
               rec_hist_series.special_rights_flag,
               rec_hist_series.share_class_id,
               p_trans_id,
               null,
               2);
  end loop;
  close cur_hist_series;
  update share_series_version
     set end_transaction_id = p_trans_id
   where transaction_id = p_existing_trans_id
     and operation_type = 0;
  delete
    from share_series
   where id in (select id from share_series_version where transaction_id = p_existing_trans_id);

  open cur_hist_class(p_business_id, p_existing_trans_id);
  loop
    fetch cur_hist_class into rec_hist_class;
    exit when not found;
      insert into share_classes_version
        values(rec_hist_class.id,
               rec_hist_class.name,
               rec_hist_class.priority,
               rec_hist_class.max_share_flag,
               rec_hist_class.max_shares,
               rec_hist_class.par_value_flag,
               rec_hist_class.par_value,
               rec_hist_class.currency,
               rec_hist_class.special_rights_flag,
               p_business_id,
               p_trans_id,
               null,
               2,
               rec_hist_class.currency_additional);
  end loop;
  close cur_hist_class;
  update share_classes_version
     set end_transaction_id = p_trans_id
   where business_id = p_business_id
     and transaction_id = p_existing_trans_id
     and operation_type = 0;
  delete
    from share_classes
   where id in (select id from share_classes_version where business_id = p_business_id and transaction_id = p_existing_trans_id);

  return p_trans_id;
end;
$$;

-- Remove existing, active share structure. Create new share classes, share series records.
-- Insert into the share_classes, share_series, share_classes_version, and share_series_version tables.
create or replace function public.colin_hist_shares(p_corp_num character varying,
                                                    p_colin_event_id integer,
                                                    p_trans_id integer,
                                                    p_business_id integer) returns integer
  language plpgsql
as $$
declare
  cur_hist_share_class cursor(v_colin_event_id integer, v_corp_num character varying)
    for select sc.share_class_id, sc.currency_typ_cd, sc.max_share_ind, sc.class_nme, sc.share_quantity, sc.spec_rights_ind,
               sc.par_value_ind, sc.par_value_amt, sc.other_currency,
               (select count(ss.series_id) 
                  from colin_extract.share_series ss 
                 where ss.corp_num = sc.corp_num 
                   and ss.start_event_id = sc.start_event_id
                   and ss.share_class_id = sc.share_class_id) as series_count,
               (select f.transaction_id 
                  from colin_extract.share_struct ss, filings f, colin_event_ids ce
                 where ss.corp_num = sc.corp_num
                   and ss.end_event_id = sc.start_event_id
                   and ss.start_event_id = ce.colin_event_id
                   and f.id = ce.filing_id) as end_trans_id
          from colin_extract.share_struct_cls sc
         where sc.corp_num = v_corp_num
           and sc.start_event_id = v_colin_event_id
        order by sc.share_class_id;
  rec_hist_share_class record;
  class_id integer := 0;
  end_trans_id integer := 0;
begin  
  open cur_hist_share_class(p_colin_event_id, p_corp_num);
  loop
    fetch cur_hist_share_class into rec_hist_share_class;
    exit when not found;
    class_id := colin_hist_shareclass_add(p_trans_id, p_business_id, 0, rec_hist_share_class);
    if rec_hist_share_class.series_count > 0 then
       perform colin_hist_shareseries_add(p_corp_num, p_colin_event_id, p_trans_id,
                                          rec_hist_share_class.share_class_id::integer, class_id, 0);
    end if;
    if rec_hist_share_class.end_trans_id is not null then
      end_trans_id := rec_hist_share_class.end_trans_id;
    end if;
  end loop;
  close cur_hist_share_class;
  if end_trans_id > 0 then
    perform colin_hist_shares_remove(end_trans_id, p_trans_id, p_business_id);
  end if;
  return p_trans_id;
end;
$$;
/*
select colin_hist_first_shares('BC0653983', 6330854, 1584645, 78497); 
select colin_hist_shares('BC0653983', 9137930, 1584659, 78497);
select colin_hist_shares('BC0653983', 12374429, 1584669, 78497);
select colin_hist_filing_rollback(1584669);
select colin_hist_filing_rollback(1584659);
delete 
  from share_series 
 where id in (select id from share_series_version where transaction_id = 1584645);   
delete 
  from share_series_version 
 where  transaction_id = 1584645;
delete 
  from share_classes 
 where id in (select id from share_classes_version where transaction_id = 1584645);   
delete 
  from share_classes_version 
 where  transaction_id = 1584645;
*/


--
-- Historical resolution updates for a single filing.
-- 1. Add resolution.
-- 2. Remove/edit resolution (corrections only).
-- Create/edit resolutions and resolutions_version records.
create or replace function public.colin_hist_resolution(p_colin_event_id integer,
                                                        p_business_id integer,
                                                        p_trans_id integer,
                                                        p_corp_num character varying) returns integer
  language plpgsql
as $$
declare
  cur_hist_resolution cursor(v_colin_event_id integer, v_corp_num character varying)
    for select r.resolution_dt, r.start_event_id, r.end_event_id,
               case when r.start_event_id = v_colin_event_id then
                         (select f.transaction_id 
                            from filings f, colin_event_ids ce, colin_extract.resolution r2
                           where r2.corp_num = r.corp_num
                             and r2.end_event_id is not null
                             and ce.colin_event_id = r2.end_event_id
                             and ce.filing_id = f.id)
                    when r.start_event_id != v_colin_event_id and r.end_event_id is not null and r.end_event_id = v_colin_event_id then
                         (select f.transaction_id 
                            from filings f, colin_event_ids ce
                           where ce.colin_event_id = r.start_event_id
                             and ce.filing_id = f.id)
                   else null end as end_trans_id,
               case when r.start_event_id != v_colin_event_id and r.end_event_id is not null and r.end_event_id = v_colin_event_id then
                         (select count(r2.start_event_id) 
                            from colin_extract.resolution r2
                           where r2.corp_num = r.corp_num
                             and r2.start_event_id = r.end_event_id)
                    when r.start_event_id = v_colin_event_id then
                         (select count(r2.start_event_id) 
                            from colin_extract.resolution r2
                           where r2.corp_num = r.corp_num
                             and r2.end_event_id = r.start_event_id)
                    else 0 end as link_count
          from colin_extract.resolution r 
        where r.corp_num = v_corp_num
          and (r.start_event_id = v_colin_event_id or r.end_event_id = v_colin_event_id)
        order by r.start_event_id;
  rec_hist_resolution record;
  counter integer := 0;
  update_type integer := 1;
begin
  open cur_hist_resolution(p_colin_event_id, p_corp_num);
  loop
    fetch cur_hist_resolution into rec_hist_resolution;
    exit when not found;
    -- Removing if not linked, otherwise set up for update.
    if rec_hist_resolution.start_event_id != p_colin_event_id and rec_hist_resolution.end_event_id is not null and rec_hist_resolution.end_event_id = p_colin_event_id then
      counter := counter + 1;
      if rec_hist_resolution.link_count > 0 then
        update_type := 1;
      else
        update_type := 2;
      end if;
      perform colin_hist_resolution_update(rec_hist_resolution.end_trans_id::integer, p_trans_id, p_business_id, null, update_type);
    -- Adding or updating
    elsif rec_hist_resolution.start_event_id = p_colin_event_id then
      counter := counter + 1;
      if rec_hist_resolution.link_count > 0 and rec_hist_resolution.end_trans_id is not null then
        perform colin_hist_resolution_update(rec_hist_resolution.end_trans_id::integer,
                                             p_trans_id,
                                             p_business_id,
                                             rec_hist_resolution.resolution_dt,
                                             3);
      else
        perform colin_hist_resolution_add(p_business_id, p_trans_id, rec_hist_resolution.resolution_dt);  
      end if;
    end if;
  end loop;
  close cur_hist_resolution;
  return counter;
end;
$$;
/*
select colin_hist_resolution(9137930, 78497, 1584659, 'BC0653983'); -- add
select colin_hist_resolution(12374429, 78497, 1584669, 'BC0653983'); -- add
select colin_hist_filing_rollback(1584669);
select colin_hist_filing_rollback(1584659);
*/

--
-- Historical name alias updates for a single filing.
-- 1. Add alias.
-- 2. Remove/edit alias.
-- Create/edit aliases and aliases_version records.
create or replace function public.colin_hist_alias(p_colin_event_id integer,
                                                   p_business_id integer,
                                                   p_trans_id integer,
                                                   p_corp_num character varying) returns integer
  language plpgsql
as $$
declare
  cur_hist_alias cursor(v_colin_event_id integer, v_corp_num character varying)
    for select upper(cn.corp_name) as corp_name, 
               case when cn.corp_name_typ_cd = 'TR' then 'TRANSLATION'
                    when cn.corp_name_typ_cd = 'AA' then 'AB_ASSUMED'
                    when cn.corp_name_typ_cd = 'AN' then 'AB_COMPANY'
                    when cn.corp_name_typ_cd = 'SA' then 'SK_ASSUMED'
                    when cn.corp_name_typ_cd = 'SN' then 'SK_COMPANY'
                    when cn.corp_name_typ_cd = 'NO' then 'CROSS_REFERENCE'
                    else 'ASSUMED' end as name_type,
               cn.start_event_id,
               cn.end_event_id,
               case when cn.start_event_id = v_colin_event_id then
                         (select f.transaction_id 
                            from filings f, colin_event_ids ce, colin_extract.corp_name cn2
                           where cn2.corp_num = cn.corp_num
                             and cn2.end_event_id is not null
                             and cn2.corp_name_typ_cd = cn.corp_name_typ_cd
                             and ce.colin_event_id = cn2.end_event_id
                             and ce.filing_id = f.id)
                    when cn.start_event_id != v_colin_event_id and cn.end_event_id is not null and cn.end_event_id = v_colin_event_id then
                         (select f.transaction_id 
                            from filings f, colin_event_ids ce
                           where ce.colin_event_id = cn.start_event_id
                             and ce.filing_id = f.id)
                   else null end as end_trans_id,
               case when cn.start_event_id != v_colin_event_id and cn.end_event_id is not null and cn.end_event_id = v_colin_event_id then
                         (select count(cn2.start_event_id) 
                            from colin_extract.corp_name cn2
                           where cn2.corp_num = cn.corp_num
                             and cn2.start_event_id = cn.end_event_id
                             and cn2.corp_name_typ_cd = cn.corp_name_typ_cd)
                    when cn.start_event_id = v_colin_event_id then
                         (select count(cn2.start_event_id) 
                            from colin_extract.corp_name cn2
                           where cn2.corp_num = cn.corp_num
                             and cn2.end_event_id = cn.start_event_id
                             and cn2.corp_name_typ_cd = cn.corp_name_typ_cd)
                    else 0 end as link_count
          from colin_extract.corp_name cn
         where cn.corp_num = v_corp_num
           and cn.corp_name_typ_cd not in ('CO', 'NB')
           and (cn.start_event_id = v_colin_event_id or cn.end_event_id = v_colin_event_id)
      order by cn.start_event_id;
  rec_hist_alias record;
  counter integer := 0;
  update_type integer := 1;
begin
  open cur_hist_alias(p_colin_event_id, p_corp_num);
  loop
    fetch cur_hist_alias into rec_hist_alias;
    exit when not found;
    -- Removing if not linked, otherwise set up for update.
    if rec_hist_alias.start_event_id != p_colin_event_id and rec_hist_alias.end_event_id is not null and rec_hist_alias.end_event_id = p_colin_event_id then
      counter := counter + 1;
      if rec_hist_alias.link_count > 0 then
        update_type := 1;
      else
        update_type := 2;
      end if;
      perform colin_hist_alias_update(rec_hist_alias.end_trans_id::integer, p_trans_id, p_business_id, null, null, update_type);
    -- Adding or updating
    elsif rec_hist_alias.start_event_id = p_colin_event_id then
      counter := counter + 1;
      if rec_hist_alias.link_count > 0 and rec_hist_alias.end_trans_id is not null then
        perform colin_hist_alias_update(rec_hist_alias.end_trans_id::integer,
                                        p_trans_id,
                                        p_business_id,
                                        rec_hist_alias.corp_name,
                                        rec_hist_alias.name_type,
                                        3);
      else
        perform colin_hist_alias_add(p_corp_num, p_colin_event_id, p_business_id, p_trans_id, rec_hist_alias);  
      end if;
    end if;
  end loop;
  close cur_hist_alias;
  return counter;
end;
$$;


-- Historical correction or amendment colin filing changes.
-- Corrections: CO_* filings: CO_AR,CO_BC,CO_DI,CO_DO,CO_LI,,CO_PO,CO_PF,CO_SS,CO_RR,CO_LQ,CO_RM,CO_TR,CO_LR
-- Amendments: AM_* filings: AM_PO,AM_PF,AM_AR,AM_BC,AM_DI,AM_DO,AM_SS,AM_RR,AM_LQ,AM_LI,AM_TR,AM_RM,AM_LR
-- AM_AR, CO_AR: change officers
-- AM_LI, CO_LI: nothing to do (update ledger information).
-- AM_SS, CO_SS: change share structure
-- AM_RR, CO_RR: change office address
-- AM_BC, CO_BC: change corp_name
-- AM_DI, CO_DI: change directors
-- AM_DO, CO_DO: change dissolution custodian, office
-- AM_PO, CO_PO: corp state, remove dissolution/liquidation party, party_role, office
-- AM_LQ, CO_LQ: change liquidator party, liquidation office.
-- AM_PF, CO_PF: nothing to do: only a corp state change.
-- AM_TR, CO_TR: only 1, changes share structure.
-- AM_RM, CO_RM: change receiver party.
-- AM_LR, CO_LR: no records in extract.
create or replace function public.colin_hist_correct_amend(p_colin_event_id integer,
                                                           p_business_id integer,
                                                           p_trans_id integer,
                                                           p_corp_num character varying,
                                                           p_colin_filing_type character varying) returns integer
  language plpgsql
as $$
declare
  party_type varchar(30);
begin
  if p_colin_filing_type in ('CO_AR', 'AM_AR') then
    perform colin_hist_officer(p_colin_event_id, p_business_id, p_trans_id, p_corp_num);
  elsif p_colin_filing_type in ('CO_SS', 'AM_SS', 'AM_TR', 'CO_TR') then
    perform colin_hist_shares(p_corp_num, p_colin_event_id, p_trans_id, p_business_id);
  elsif p_colin_filing_type in ('CO_RR', 'AM_RR') then
    perform colin_hist_offices(p_colin_event_id, p_business_id, p_trans_id, p_corp_num, 1, 'RG');
    perform colin_hist_offices(p_colin_event_id, p_business_id, p_trans_id, p_corp_num, 1, 'RC');
  elsif p_colin_filing_type in ('CO_DI', 'AM_DI') then
    perform colin_hist_director(p_colin_event_id, p_business_id, p_trans_id, p_corp_num);
  elsif p_colin_filing_type in ('CO_DO', 'AM_DO') then
    perform colin_hist_parties(p_colin_event_id, p_business_id, p_trans_id, p_corp_num, 1, 'RCC', p_colin_filing_type);
    perform colin_hist_offices(p_colin_event_id, p_business_id, p_trans_id, p_corp_num, 1, 'DS');
  elsif p_colin_filing_type in ('CO_RM', 'AM_RM') then
    perform colin_hist_parties(p_colin_event_id, p_business_id, p_trans_id, p_corp_num, 1, 'RCM', p_colin_filing_type);
  elsif p_colin_filing_type in ('AM_LQ', 'CO_LQ') then
    perform colin_hist_parties(p_colin_event_id, p_business_id, p_trans_id, p_corp_num, 1, 'LIQ', p_colin_filing_type);
    perform colin_hist_offices(p_colin_event_id, p_business_id, p_trans_id, p_corp_num, 1, 'LQ');
  elsif p_colin_filing_type in ('CO_PO', 'AM_PO') then
    perform colin_hist_parties(p_colin_event_id, p_business_id, p_trans_id, p_corp_num, 2, 'RCC', p_colin_filing_type);
    perform colin_hist_offices(p_colin_event_id, p_business_id, p_trans_id, p_corp_num, 2, 'DS');
    perform colin_hist_parties(p_colin_event_id, p_business_id, p_trans_id, p_corp_num, 2, 'LIQ', p_colin_filing_type);
    perform colin_hist_offices(p_colin_event_id, p_business_id, p_trans_id, p_corp_num, 2, 'LQ');
  end if;
  return p_trans_id;
end;
$$;

-- All changes for alteration filings: COLIN NOALA, NOALB, NOALC, NOALU filing types.
create or replace function public.colin_hist_alteration(p_colin_event_id integer,
                                                        p_business_id integer,
                                                        p_trans_id integer,
                                                        p_corp_num character varying,
                                                        p_colin_filing_type character varying,
                                                        p_rec_business record) returns record
  language plpgsql
as $$
declare
  rec_change record;
  party_type varchar(30);
begin
    select count(ss.start_event_id) as ss_count,
           (select cn.corp_name 
              from colin_extract.corp_name cn 
             where cn.corp_num = p_corp_num and cn.start_event_id = p_colin_event_id
               and cn.corp_name_typ_cd in ('CO', 'NB')) as legal_name,
           (select count(cn.start_event_id) 
              from colin_extract.corp_name cn 
             where cn.corp_num = p_corp_num and cn.start_event_id = p_colin_event_id
               and cn.corp_name_typ_cd not in ('CO', 'NB')) as alias_count,
           (select count(r.start_event_id) 
              from colin_extract.resolution r 
             where r.corp_num = p_corp_num and r.start_event_id = p_colin_event_id) as resolution_count,
           (select cr.restriction_ind 
              from colin_extract.corp_restriction cr 
             where cr.corp_num = p_corp_num and cr.start_event_id = p_colin_event_id) as restriction_ind         
      into rec_change
      from colin_extract.share_struct ss
     where ss.corp_num = p_corp_num
       and ss.start_event_id = p_colin_event_id;
    if rec_change.legal_name is not null then
      p_rec_business.legal_name := rec_change.legal_name;
    end if;
    if rec_change.ss_count > 0 then
      perform colin_hist_shares(p_corp_num, p_colin_event_id, p_trans_id, p_business_id);
    end if;
    if rec_change.alias_count > 0 then
      perform colin_hist_alias(p_colin_event_id, p_business_id, p_trans_id, p_corp_num);
    end if;
    if rec_change.resolution_count > 0 then
      perform colin_hist_resolution(p_colin_event_id, p_business_id, p_trans_id, p_corp_num);
    end if;
    if rec_change.restriction_ind is not null then
      p_rec_business.restriction_ind := rec_change.restriction_ind;
    end if;
    if p_colin_filing_type = 'NOALB' then
      p_rec_business.legal_type := 'BC';
    elsif p_colin_filing_type = 'NOALC' then
      p_rec_business.legal_type := 'CC';
    elsif p_colin_filing_type = 'NOALU' and left(p_corp_num, 1) = 'C' then
      p_rec_business.legal_type := 'CUL';
    elsif p_colin_filing_type = 'NOALU' then
      p_rec_business.legal_type := 'ULC';
    end if;
  return p_rec_business;
end;
$$;

-- All changes for restoration filings: COLIN RESTL,RESTF,RESXL,RESXF,RUSTF,RUSTL,RUSXF,RUSXL filing types.
-- Change corp state from HIS to ACT.
-- RESTL, RESXL: APP (applicant) party type 
-- RESTF, RESXF: APP party type, RG, RC office, corp_name
-- RUSTF, RUSTL,RUSXF,RUSXL: 0 filings in the extract.
CREATE OR REPLACE FUNCTION public.colin_hist_restoration(p_colin_event_id integer, p_business_id integer, p_trans_id integer, p_corp_num character varying, p_colin_filing_type character varying, p_rec_business record)
 RETURNS record
 LANGUAGE plpgsql
AS $function$
declare
  rec_change record;
  party_type varchar(30);
begin
  p_rec_business.state := 'ACTIVE';
  if p_colin_filing_type in ('RESTL', 'RESTF', 'RESXL') then
    perform colin_hist_parties(p_colin_event_id, p_business_id, p_trans_id, p_corp_num, 0, 'APP', p_colin_filing_type);
  end if;
  if p_colin_filing_type in ('RESTF', 'RESXF') then
    perform colin_hist_offices(p_colin_event_id, p_business_id, p_trans_id, p_corp_num, 1, 'RG');
    perform colin_hist_offices(p_colin_event_id, p_business_id, p_trans_id, p_corp_num, 1, 'RC');
    select cn.corp_name 
      into p_rec_business.legal_name
      from colin_extract.corp_name cn 
     where cn.corp_num = p_corp_num and cn.start_event_id = p_colin_event_id
       and cn.corp_name_typ_cd in ('CO', 'NB');    
  end if;
  return p_rec_business;
end;
$function$

-- NWITH NOCAD has a different query.
-- 1. End currently active RG and RC offices addresses.
-- 2. Restore previouly active RG and RC office addresses.
create or replace function public.colin_hist_withdraw_offices(p_colin_event_id integer,
                                                              p_business_id integer,
                                                              p_trans_id integer,
                                                              p_colin_office_type character varying) returns integer
  language plpgsql
as $$
declare
  cur_hist_withdrawn cursor(v_colin_event_id integer, v_business_id character varying, v_office_type character varying)
    for select distinct a.* 
          from filings f, colin_event_ids ce, offices_version ov, addresses_version a
         where ce.colin_event_id = v_colin_event_id
           and ce.filing_id = f.id
           and ov.business_id = v_business_id
           and a.business_id = ov.business_id
           and ov.id = a.office_id
           and ov.office_type = v_office_type
           and ov.end_transaction_id is null
           and a.end_transaction_id = f.transaction_id
           and a.operation_type in (0, 1);
  office_type varchar(20);
  rec_hist_address record;
  withdrawn_trans_id integer := 0;
  v_office_id integer := 0;
begin
  if p_colin_office_type = 'RG' then
    office_type := 'registeredOffice';
  else
    office_type := 'recordsOffice';
  end if;
  open cur_hist_withdrawn(p_colin_event_id, p_business_id, office_type);
  loop
    fetch cur_hist_withdrawn into rec_hist_address;
    exit when not found;
    if withdrawn_trans_id = 0 then
      withdrawn_trans_id := rec_hist_address.end_transaction_id;
      v_office_id := rec_hist_address.office_id;
    end if;
    rec_hist_address.end_transaction_id := null;
    update addresses
       set street = rec_hist_address.addr_line_1,
           street_additional = rec_hist_address.addr_line_2, 
           city = rec_hist_address.city,
           region = rec_hist_address.province,
           country = rec_hist_address.country_typ_cd,
           postal_code = rec_hist_address.postal_cd,
           delivery_instructions = rec_hist_address.delivery_instructions
    where id = rec_hist_address.id;
  end loop;
  close cur_hist_withdrawn;
  update addresses_version
     set end_transaction_id = p_trans_id
   where business_id = p_business_id
     and transaction_id = withdrawn_trans_id
     and office_id = v_office_id
     and end_transaction_id is null
     and operation_type = 1;
  return p_trans_id;
end;
$$;


-- NWITH amalgamations 
-- TED businesses_version state becomes historical.
-- Ting businesses_version state=active
create or replace function public.colin_hist_withdraw_amalg(p_colin_event_id integer,
                                                            p_trans_id integer) returns integer
  language plpgsql
as $$
declare
  cur_hist_business cursor(v_colin_event_id integer)
    for select b.* 
          from businesses_version b, colin_extract.corp_involved_amalgamating cia, filings f
         where cia.event_id = v_colin_event_id 
           and cia.ting_corp_num = b.identifier
           and b.end_transaction_id is null
           and b.transaction_id = f.transaction_id
           and f.status != 'TOMBSTONE';
  rec_business record;
  rec_ting record;
  amalg_id integer := 0;
  amalg_type varchar(30);
  ting_bus_id integer := 0;
  event_ts timestamp;
  bus_trans_id integer;
  ting_role varchar(30);
begin
  open cur_hist_business(p_colin_event_id);
  loop
    fetch cur_hist_business into rec_business;
    exit when not found;
    bus_trans_id := rec_business.transaction_id;
    rec_business.operation_type := 1;
    rec_business.transaction_id := p_trans_id;
    rec_business.last_modified := event_ts;
    rec_business.dissolution_date := null;
    rec_business.state := 'ACTIVE';
    update businesses_version
       set end_transaction_id = p_trans_id
     where id = rec_business.id
       and end_transaction_id is null
       and transaction_id = bus_trans_id;     
    insert into businesses_version
      values (rec_business.id,rec_business.last_modified,rec_business.last_ledger_id,rec_business.last_remote_ledger_id,
              rec_business.last_ar_date,rec_business.legal_name,rec_business.founding_date,rec_business.dissolution_date,
              rec_business.identifier,rec_business.tax_id,rec_business.fiscal_year_end_date,rec_business.submitter_userid,
              rec_business.transaction_id,rec_business.end_transaction_id,rec_business.operation_type,rec_business.last_agm_date,
              rec_business.last_ledger_timestamp,rec_business.legal_type,rec_business.restriction_ind,rec_business.last_ar_year,
              rec_business.association_type,rec_business.last_coa_date,rec_business.last_cod_date,rec_business.state,
              rec_business.admin_freeze,rec_business.state_filing_id,rec_business.naics_key,rec_business.naics_code,
              rec_business.naics_description,rec_business.start_date,rec_business.foreign_jurisdiction,
              rec_business.foreign_legal_name,rec_business.send_ar_ind,rec_business.restoration_expiry_date,
              rec_business.last_ar_reminder_year,rec_business.continuation_out_date,rec_business.foreign_jurisdiction_region,
              rec_business.no_dissolution,rec_business.last_tr_year,rec_business.amalgamation_out_date,
              rec_business.in_liquidation,rec_business.accession_number);
  end loop;
  close cur_hist_business;
  return p_trans_id;
end;
$$;


--
-- Historical collective changes for a single filing.
-- Create businesses_version record, set end transaction id on previous businesses_version record.
-- Set new businesses_version record values based on the filing/event changes.
create or replace function public.colin_hist_filing(p_colin_event_id integer,
                                                    p_business_id integer,
                                                    p_trans_id integer,
                                                    p_corp_num character varying,
                                                    p_filing_type character varying,
                                                    p_colin_filing_type character varying) returns integer
  language plpgsql
as $$
declare
  rec_event record;
  rec_business record;
  rec_change record;
begin
  select *
    into rec_business
    from businesses_version
   where id = p_business_id
     and end_transaction_id is null
   fetch first 1 rows only;
 select e.*, 
       (select cr.restriction_ind from colin_extract.corp_restriction cr where cr.start_event_id = e.event_id) as restriction_ind
   into rec_event
   from colin_extract.event e
  where e.corp_num = p_corp_num
    and e.event_id = p_colin_event_id;

  rec_business.operation_type := 1;
  rec_business.transaction_id := p_trans_id;
  rec_business.last_modified := rec_event.event_timerstamp;
  if rec_event.restriction_ind is not null then
    rec_business.restriction_ind := rec_event.restriction_ind;
  end if;
  if p_colin_filing_type is not null and 
     p_colin_filing_type in ('SYSDS','SYSDA','SYSDT','SYSDF','SYSDL','CONVDS', 'CONVDSF', 'CONVDSL', 'CONVDSO') then
    rec_business.state := 'HISTORICAL';
    rec_business.dissolution_date := rec_event.event_timerstamp;
  elsif p_colin_filing_type is not null and  p_colin_filing_type in ('ADVD2','ADVDS','DISLC','DISLV') then
    rec_business.state := 'HISTORICAL';
    rec_business.dissolution_date := rec_event.event_timerstamp;
    perform colin_hist_parties(p_colin_event_id, p_business_id, p_trans_id, p_corp_num, 0, 'RCC', p_colin_filing_type);
    perform colin_hist_offices(p_colin_event_id, p_business_id, p_trans_id, p_corp_num, 0, 'DS');
  elsif p_colin_filing_type is not null and p_colin_filing_type in ('NOLDS', 'NOCDS') then
    perform colin_hist_parties(p_colin_event_id, p_business_id, p_trans_id, p_corp_num, 0, 'RCC', p_colin_filing_type);
    perform colin_hist_offices(p_colin_event_id, p_business_id, p_trans_id, p_corp_num, 0, 'DS');
  elsif p_colin_filing_type in ('CO_PF', 'AM_PF') then
    rec_business.state := 'HISTORICAL';
    rec_business.dissolution_date := rec_event.event_timerstamp;
  elsif p_colin_filing_type in ('SYSD1', 'SYSD2', 'SYST1', 'SYST2', 'CONVRSTR', 'CONVLRSTR') then
    rec_business.state := 'ACTIVE';
    rec_business.dissolution_date := null;
  elsif left(p_colin_filing_type, 3) in ('CO_', 'AM_') then
    if p_colin_filing_type in ('CO_BC', 'AM_BC') then
      select cn.corp_name 
        into rec_business.legal_name
        from colin_extract.corp_name cn 
       where cn.corp_num = p_corp_num and cn.start_event_id = p_colin_event_id
         and cn.corp_name_typ_cd in ('CO', 'NB');    
    else
      perform colin_hist_correct_amend(p_colin_event_id, p_business_id, p_trans_id, p_corp_num, p_colin_filing_type);
    end if;
    if p_colin_filing_type in ('CO_PO', 'AM_PO') then
      rec_business.state := 'ACTIVE';
      rec_business.dissolution_date := null;
    end if;
  elsif p_filing_type is not null and p_filing_type in ('transition') then
    rec_business.state := 'ACTIVE';
    if rec_business.last_cod_date is null or rec_business.last_cod_date <= rec_business.founding_date then
      rec_business.last_cod_date := to_timestamp(to_char(rec_business.founding_date, 'YYYY-MM-DD') || ' 00:00:00', 'YYYY-MM-DD HH24:MI:SS') at time zone 'utc';
    else
      rec_business.last_cod_date := rec_business.last_modified;
    end if;
    perform colin_hist_director(p_colin_event_id, p_business_id, p_trans_id, p_corp_num);
    perform colin_hist_offices(p_colin_event_id, p_business_id, p_trans_id, p_corp_num, 1, 'RG');
    perform colin_hist_offices(p_colin_event_id, p_business_id, p_trans_id, p_corp_num, 1, 'RC');
    perform colin_hist_shares(p_corp_num, p_colin_event_id, p_trans_id, p_business_id);
    perform colin_hist_alias(p_colin_event_id, p_business_id, p_trans_id, p_corp_num);
  elsif p_filing_type is not null and p_filing_type in ('alteration') then
    rec_business := colin_hist_alteration(p_colin_event_id, p_business_id, p_trans_id, p_corp_num, p_colin_filing_type, rec_business);
  elsif p_filing_type is not null and p_filing_type in ('restoration') then
    rec_business := colin_hist_restoration(p_colin_event_id, p_business_id, p_trans_id, p_corp_num, p_colin_filing_type, rec_business);
  elsif p_filing_type is not null and p_filing_type in ('annualReport') then
    perform colin_hist_officer(p_colin_event_id, p_business_id, p_trans_id, p_corp_num);
    if rec_business.last_ar_reminder_year is not null and rec_business.last_ar_reminder_year > 0 then
      rec_business.last_ar_reminder_year := rec_business.last_ar_reminder_year + 1;
    end if;
    if rec_business.last_ar_date is not null then
      rec_business.last_ar_date := rec_business.last_ar_date + interval '1 years';
      rec_business.last_ar_year := rec_business.last_ar_year + 1;
    else
     select to_timestamp(to_char(c.recognition_dts, 'YYYY-MM-DD') || ' 00:00:00', 'YYYY-MM-DD HH24:MI:SS') at time zone 'utc' + interval '1 years',
            cast(extract(year from c.recognition_dts) as int) + 1
       into rec_business.last_ar_date, rec_business.last_ar_year
       from colin_extract.corporation c
      where c.corp_num = p_corp_num;
    end if;
  elsif p_filing_type is not null and p_filing_type in ('changeOfAddress') then
    perform colin_hist_offices(p_colin_event_id, p_business_id, p_trans_id, p_corp_num, 1, 'RG');
    perform colin_hist_offices(p_colin_event_id, p_business_id, p_trans_id, p_corp_num, 1, 'RC');
  elsif (p_filing_type is not null and p_filing_type = 'transferRecordsOffice') or (p_colin_filing_type is not null and p_colin_filing_type = 'NOTRA') then
    perform colin_hist_offices(p_colin_event_id, p_business_id, p_trans_id, p_corp_num, 1, 'RC');
  elsif p_filing_type is not null and p_filing_type in ('changeOfDirectors') then
    if rec_business.last_cod_date is null or rec_business.last_cod_date <= rec_business.founding_date then
      rec_business.last_cod_date := to_timestamp(to_char(rec_business.founding_date, 'YYYY-MM-DD') || ' 00:00:00', 'YYYY-MM-DD HH24:MI:SS') at time zone 'utc';
    else
      rec_business.last_cod_date := rec_business.last_modified;
    end if;
    perform colin_hist_director(p_colin_event_id, p_business_id, p_trans_id, p_corp_num);
  elsif (p_filing_type is not null and p_filing_type = 'appointLiquidator') or (p_colin_filing_type is not null and p_colin_filing_type = 'LQSIN') then
    perform colin_hist_parties(p_colin_event_id, p_business_id, p_trans_id, p_corp_num, 0, 'LIQ', p_colin_filing_type);
    perform colin_hist_offices(p_colin_event_id, p_business_id, p_trans_id, p_corp_num, 0, 'LQ');
  elsif p_filing_type is not null and p_filing_type = 'appointReceiver' then
    perform colin_hist_parties(p_colin_event_id, p_business_id, p_trans_id, p_corp_num, 0, 'RCM', p_colin_filing_type);
    perform colin_hist_offices(p_colin_event_id, p_business_id, p_trans_id, p_corp_num, 0, 'LQ');
  elsif p_colin_filing_type is not null and p_colin_filing_type = 'LQWOS' then
    perform colin_hist_offices(p_colin_event_id, p_business_id, p_trans_id, p_corp_num, 2, 'LQ');
  elsif p_filing_type is not null and p_filing_type = 'ceaseLiquidator' then
    perform colin_hist_parties(p_colin_event_id, p_business_id, p_trans_id, p_corp_num, 2, 'LIQ', p_colin_filing_type);
  elsif (p_filing_type is not null and p_filing_type = 'changeLiquidatorAddress') or (p_colin_filing_type is not null and p_colin_filing_type = 'NOCAL') then
    perform colin_hist_parties(p_colin_event_id, p_business_id, p_trans_id, p_corp_num, 1, 'LIQ', p_colin_filing_type);
    perform colin_hist_offices(p_colin_event_id, p_business_id, p_trans_id, p_corp_num, 1, 'LQ');
  elsif p_colin_filing_type is not null and p_colin_filing_type = 'NOCER' then
    perform colin_hist_parties(p_colin_event_id, p_business_id, p_trans_id, p_corp_num, 2, 'RCM', p_colin_filing_type);
  elsif p_colin_filing_type is not null and p_colin_filing_type = 'NOCRM' then
    perform colin_hist_parties(p_colin_event_id, p_business_id, p_trans_id, p_corp_num, 1, 'RCM', p_colin_filing_type);
  elsif p_colin_filing_type is not null and p_colin_filing_type = 'NOERA' then
    perform colin_hist_offices(p_colin_event_id, p_business_id, p_trans_id, p_corp_num, 1, 'RG');
  elsif p_colin_filing_type is not null and p_colin_filing_type in ('ADMIN', 'ADCORP') then
    select *
      into rec_change
      from colin_extract.corp_state
    where start_event_id = p_colin_event_id;
    if FOUND then
      if rec_change.op_state_type_cd = 'ACT' then
        rec_business.state := 'ACTIVE';
        rec_business.dissolution_date := null;
      else
        rec_business.state := 'HISTORICAL';
        rec_business.dissolution_date := rec_event.event_timerstamp;
      end if;
    end if;
  elsif p_colin_filing_type is not null and p_colin_filing_type = 'CONVNC' then
    select cn.corp_name 
      into rec_business.legal_name
      from colin_extract.corp_name cn 
      where cn.corp_num = p_corp_num and cn.start_event_id = p_colin_event_id
        and cn.corp_name_typ_cd in ('CO', 'NB');    
  elsif (p_filing_type is not null and p_filing_type = 'continuedOut') or 
        (p_colin_filing_type is not null and p_colin_filing_type in ('COUTI', 'CONTO', 'AMALO', 'CONVCOUT')) then
    if p_colin_filing_type is not null and p_colin_filing_type in ('COUTI', 'AMALO', 'CONVCOUT') then
      rec_business.state := 'HISTORICAL';
    end if;
    select *
      into rec_change
      from colin_extract.cont_out
    where start_event_id = p_colin_event_id;
    if FOUND then
      rec_business.continuation_out_date := rec_change.cont_out_dt;
      rec_business.foreign_jurisdiction := rec_change.can_jur_typ_cd;
      rec_business.foreign_legal_name := rec_change.home_company_nme;
      rec_business.foreign_legal_name := case when rec_change.othr_juri_desc is not null then left(rec_change.othr_juri_desc, 10) else null end;
    end if;
  elsif p_filing_type is not null and p_filing_type in ('noticeOfWithdrawal') then
    select f.event_id, f.filing_type_cd
      into rec_change
      from colin_extract.filing f
     where f.withdrawn_event_id = p_colin_event_id;
    if rec_change.filing_type_cd in ('ICORP', 'CONTI', 'TRANS') then
      rec_business.state := 'HISTORICAL';
    elsif rec_change.filing_type_cd = 'ADVD2' then
      rec_business.state := 'ACTIVE';
    elsif rec_change.filing_type_cd = 'NOCAD' then
      perform colin_hist_withdraw_offices(rec_change.event_id, p_business_id, p_trans_id, 'RG');
      perform colin_hist_withdraw_offices(rec_change.event_id, p_business_id, p_trans_id, 'RC');
    elsif rec_change.filing_type_cd in ('NOALA', 'NOALU') then
      rec_business := colin_hist_alteration(p_colin_event_id, p_business_id, p_trans_id, p_corp_num, rec_change.filing_type_cd, rec_business);
    elsif rec_change.filing_type_cd in ('AMALH', 'AMLVU', 'AMALV', 'AMLRU', 'AMALR') then
      rec_business.state := 'HISTORICAL';
      perform colin_hist_withdraw_amalg(rec_change.event_id, p_trans_id);
    end if;
  end if;
  
  insert into businesses_version
    values (rec_business.id,rec_business.last_modified,rec_business.last_ledger_id,rec_business.last_remote_ledger_id,
            rec_business.last_ar_date,rec_business.legal_name,rec_business.founding_date,rec_business.dissolution_date,
            rec_business.identifier,rec_business.tax_id,rec_business.fiscal_year_end_date,rec_business.submitter_userid,
            rec_business.transaction_id,rec_business.end_transaction_id,rec_business.operation_type,rec_business.last_agm_date,
            rec_business.last_ledger_timestamp,rec_business.legal_type,rec_business.restriction_ind,rec_business.last_ar_year,
            rec_business.association_type,rec_business.last_coa_date,rec_business.last_cod_date,rec_business.state,
            rec_business.admin_freeze,rec_business.state_filing_id,rec_business.naics_key,rec_business.naics_code,
            rec_business.naics_description,rec_business.start_date,rec_business.foreign_jurisdiction,
            rec_business.foreign_legal_name,rec_business.send_ar_ind,rec_business.restoration_expiry_date,
            rec_business.last_ar_reminder_year,rec_business.continuation_out_date,rec_business.foreign_jurisdiction_region,
            rec_business.no_dissolution,rec_business.last_tr_year,rec_business.amalgamation_out_date,
            rec_business.in_liquidation,rec_business.accession_number);  
  update businesses_version
     set end_transaction_id = p_trans_id
   where id = p_business_id
     and end_transaction_id is null
     and transaction_id != p_trans_id;     
  return p_trans_id;
end;
$$;
/*
-- Verify business and trans ids before running: replaced with each load.
-- NOALA
select public.colin_hist_first_filing('BC1246637');
select colin_hist_filing(16346325, 78293, 1580096, 'BC1246637', 'alteration', 'NOALA'); -- Name
select colin_hist_filing(16566408, 78293, 1580105, 'BC1246637', 'alteration', 'NOALA'); -- Name
select colin_hist_filing(16640592, 78293, 1580108, 'BC1246637', 'alteration', 'NOALA');  -- Class
select colin_hist_filing_rollback(1580108);
select colin_hist_filing_rollback(1580105);
select colin_hist_filing_rollback(1580096);
select colin_hist_filing_rollback(1580088);
-- AR
select public.colin_hist_first_filing('BC0873464');
select colin_hist_filing(10400281, 83444, 1756938, 'BC0873464', 'annualReport', 'ANNBC');
select colin_hist_filing(16092209, 83444, 1756964, 'BC0873464', 'annualReport', 'ANNBC');
select colin_hist_filing(16502044, 83444, 1756966, 'BC0873464', 'annualReport', 'ANNBC');
select colin_hist_filing(18082774, 83444, 1756970, 'BC0873464', 'annualReport', 'ANNBC');
select colin_hist_filing_rollback(1756970);
select colin_hist_filing_rollback(1756966);
select colin_hist_filing_rollback(1756964);
select colin_hist_filing_rollback(1756938);
select colin_hist_filing_rollback(1756936);
-- Office change
select public.colin_hist_first_filing('BC1395304');
select colin_hist_filing(18373435, 78299, 1580156, 'BC1395304', 'changeOfAddress', 'NOCAD');
select colin_hist_filing(18416563, 78299, 1580157, 'BC1395304', 'changeOfAddress', 'NOCAD');
select colin_hist_filing(18837500, 78299, 1580158, 'BC1395304', 'annualReport', 'ANNBC');
select colin_hist_filing(18837553, 78299, 1580159, 'BC1395304', 'changeOfAddress', 'NOCAD');
select colin_hist_filing(19805340, 78299, 1580160, 'BC1395304', 'annualReport', 'ANNBC');
select colin_hist_filing_rollback(1580160);
select colin_hist_filing_rollback(1580159);
select colin_hist_filing_rollback(1580158);
select colin_hist_filing_rollback(1580157);
select colin_hist_filing_rollback(1580156);
select colin_hist_filing_rollback(1580155);
-- NOCDR
select public.colin_hist_first_filing('BC1249698');
select colin_hist_filing(18040390, 81261, 1682420, 'BC1249698', 'changeOfDirectors', 'NOCDR');
select colin_hist_filing(18407763, 81261, 1682430, 'BC1249698', 'changeOfDirectors', 'NOCDR');
select colin_hist_filing(19946434, 81261, 1682438, 'BC1249698', 'changeOfDirectors', 'NOCDR');
select colin_hist_filing(19946440, 81261, 1682442, 'BC1249698', 'changeOfDirectors', 'NOCDR');
select colin_hist_filing_rollback(1682442);
select colin_hist_filing_rollback(1682438);
select colin_hist_filing_rollback(1682430);
select colin_hist_filing_rollback(1682420);
select colin_hist_filing_rollback(1682392);
-- ADVD2
select public.colin_hist_first_filing('BC1197417');
select colin_hist_filing(18647079, 78510, 1584916, 'BC1197417', 'dissolution', 'ADVD2');
select colin_hist_filing_rollback(1584916);
select colin_hist_filing_rollback(1584882);
-- AM_SS
select public.colin_hist_first_filing('BC1519380');
select colin_hist_filing(19722696, 78541, 1585049, 'BC1519380', 'alteration', 'AM_SS');
select colin_hist_filing_rollback(1585049);
select colin_hist_filing_rollback(1585043);
-- AM_RR
select public.colin_hist_first_filing('BC1519380');
select colin_hist_filing(19722731, 78541, 1585052, 'BC1519380', 'changeOfAddress', 'AM_RR');
select colin_hist_filing_rollback(1585052);
select colin_hist_filing_rollback(1585043);
-- CO_BC
select public.colin_hist_first_filing('BC0998813');
select colin_hist_filing(11629040, 78504, 1584748, 'BC0998813', 'correction', 'CO_BC');
select colin_hist_filing_rollback(1584748);
select colin_hist_filing_rollback(1584731);
-- AM_DI
select public.colin_hist_first_filing('C1225717');
select colin_hist_filing(15574459, 78553, 1585250, 'C1225717', 'changeOfDirectors', 'AM_DI');
select colin_hist_filing_rollback(1585250);
select colin_hist_filing_rollback(1585244);
-- AM_DO
select public.colin_hist_first_filing('BC1197417');
select colin_hist_filing(18647079, 78510, 1584916, 'BC1197417', 'dissolution', 'ADVD2');
select colin_hist_filing(18918067, 78510, 1584924, 'BC1197417', 'changeOfAddress', 'AM_DO');
select colin_hist_filing_rollback(1584924);
select colin_hist_filing_rollback(1584916);
select colin_hist_filing_rollback(1584882);
-- NOAPL, AM_LQ, DISLC event, CO_PO
select public.colin_hist_first_filing('BC0721627');
--select colin_hist_filing(13818624, 80616, 1659901, 'BC0721627', 'appointLiquidator', 'NOAPL');
--select colin_hist_filing(14536505, 80616, 1659904, 'BC0721627', 'alteration', 'AM_LQ');
select colin_hist_filing(16214736, 80616, 1659909, 'BC0721627', 'dissolution', 'DISLC');
select colin_hist_filing(16214887, 80616, 1659911, 'BC0721627', 'putBackOn', 'CO_PO');
select colin_hist_filing_rollback(1659911);
select colin_hist_filing_rollback(1659909);
--select colin_hist_filing_rollback(1659904);
--select colin_hist_filing_rollback(1659901);
select colin_hist_filing_rollback(1659857);
-- NOARM, NOCER, AM_RM, CO_RM
select public.colin_hist_first_filing('BC1172545');
select colin_hist_filing(19646716, 77450, 1548660, 'BC1172545', 'appointReceiver', 'NOARM');
select colin_hist_filing(19828489, 77450, 1548663, 'BC1172545', 'ceaseReceiver', 'NOCER');
select colin_hist_filing(19828614, 77450, 1548665, 'BC1172545', 'correction', 'CO_RM');
select colin_hist_filing_rollback(1548665);
select colin_hist_filing_rollback(1548663);
select colin_hist_filing_rollback(1548660);
select colin_hist_filing_rollback(1548633);
-- NOAPL, AM_LQ, NOCEL
select public.colin_hist_first_filing('BC0752755');
select colin_hist_filing(10267512, 81260, 1682408, 'BC0752755', 'appointLiquidator', 'NOAPL');
select colin_hist_filing(16537850, 81260, 1682443, 'BC0752755', 'alteration', 'AM_LQ');
select colin_hist_filing(16537858, 81260, 1682449, 'BC0752755', 'ceaseLiquidator', 'NOCEL');
select colin_hist_filing_rollback(1682449);
select colin_hist_filing_rollback(1682443);
select colin_hist_filing_rollback(1682408);
select colin_hist_filing_rollback(1682370);
-- CONVICORP, TRANS
select public.colin_hist_first_filing('BC0011262');
select colin_hist_filing(6901982, 73073, 1402920, 'BC0011262', 'transition', 'TRANS');
select colin_hist_filing_rollback(1402920);
select colin_hist_filing_rollback(1402915);
*/


-- Migrate colin filing data for a single BC corp in filing and event chronological order.
-- WARNING: this function does not check if the filing data has previously migrated.
-- Use colin_hist_backfill_corp instead to migrate safely.
create or replace function public.colin_hist_corp(p_corp_num character varying, p_business_id integer) returns integer
  language plpgsql
as $$
declare
  cur_hist_filings cursor(v_corp_num character varying)
    for select ce.colin_event_id, e.event_type_cd,
               (select f2.filing_type_cd
                  from colin_extract.filing f2
                 where ce.colin_event_id = f2.event_id) as colin_filing_type,
               f.filing_type, f.id as filing_id, f.transaction_id
          from businesses b, filings f, colin_event_ids ce, colin_extract.event e
         where b.identifier = v_corp_num
           and b.id = f.business_id
           and f.source = 'COLIN'
           and f.status = 'COMPLETED'
           and f.id = ce.filing_id
           and ce.colin_event_id = e.event_id
           and f.filing_type not in ('conversionLedger')
        order by f.id;
  rec_filing record;
  counter integer := 0;
  colin_filing_type varchar(20);
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
      perform colin_hist_first_filing(p_corp_num);
    else
      perform colin_hist_filing(rec_filing.colin_event_id,
                                p_business_id,
                                cast(rec_filing.transaction_id as integer),
                                p_corp_num,
                                rec_filing.filing_type,
                                colin_filing_type);
    end if;
    counter := counter + 1;
  end loop;
  close cur_hist_filings;
  return counter;
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
    perform colin_hist_corp(p_corp_num, rec_corp.business_id);
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
    perform colin_hist_corp(p_corp_num, rec_corp.business_id);
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
    perform colin_hist_corp(p_corp_num, rec_corp.business_id);
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
