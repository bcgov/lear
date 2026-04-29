/*
This file contains all functions and stored procedures for approved address record transpose updates. The changes
only apply to active parties and offices belonging to active businesses. See the comment for the procedure
"colin_address_transpose" for a summary of the specific changes. 

The transpose changes are intended to be run as part of a colin data migration before the extract is loaed into
the target, modernized business database.

Usage:
1. Compile all the functions and stored procedures in this file.
2. Run the procedure to transpose the addresses (takes approximately 7 minutes):
   call colin_address_transpose();

Example address ID's and these instructions are in this spreadsheet:
https://docs.google.com/spreadsheets/d/1-BLTklhdiW0401sN6I68inF1-retATANyTZDswBwGcQ/edit?gid=642728421#gid=642728421


-- Uncomment and executed to drop all address transpose functions and procedures.
drop procedure colin_address_transpose;
drop procedure colin_address_transpose_cleanup;
drop procedure colin_address_transpose_city;
drop procedure colin_address_duplicate_region;
drop procedure colin_address_transpose_region;
drop procedure colin_address_duplicate_pcode;
drop procedure colin_address_transpose_pcode;
drop procedure colin_address_duplicate_country;
drop procedure colin_address_transpose_country;
drop function colin_update_address_us_state;
drop function colin_update_address_ca_province;
drop function colin_update_address_pcode;
drop function colin_update_address_country;
*/


--
-- Try and extract a Canada or US postal code from address text: city, then address_line_3, then address_line_2  
--
create or replace function public.colin_update_address_pcode(v_text character varying,
                                                             v_remove boolean,
                                                             v_us boolean) returns character varying
  immutable
  language plpgsql
as $$
declare
  test_val varchar(50);
  test_code varchar(50);
begin
  -- Empty value do nothing.
  if v_text is null or LENGTH(v_text) < 4 then
    return null;
  end if;
  -- Try CA format first
  test_val := UPPER(TRIM(v_text));
  test_code := RIGHT(test_val, 7);
  if REGEXP_MATCHES(test_code, '^[A-Za-z]\d[A-Za-z][ -]?\d[A-Za-z]\d$','gi') is not null then
    if v_remove then
      return trim(substr(TRIM(v_text), 1, length(TRIM(v_text)) - length(test_code)));
    else
      test_code := REPLACE(test_code, ' ', '');
      test_code := REPLACE(test_code, '-', '');
      return SUBSTR(test_code, 1, 3) || ' ' || SUBSTR(test_code, 4);
    end if;
  elsif not v_us then
    return null;
  else
    if position('BOX' in test_val) > 0 or position('PO ' in test_val) > 0  or position('P.O ' in test_val) > 0 
                or position('POB ' in test_val) > 0 
                or position('CP ' in test_val) > 0 then
      return null;
    end if;
    -- Test if last token is all digits and short or long format US zip code.
    test_code := SPLIT_PART(TRIM(v_text), ' ', -1);
    if LENGTH(test_code) not in (5, 9, 10) then
      return null;
    end if;
    if LENGTH(test_code) in (5, 9) then
      if REGEXP_MATCHES(test_code,'^[0-9]+$','gi') is not null then
        if v_remove then
          return trim(substr(TRIM(v_text), 1, length(TRIM(v_text)) - length(test_code)));
        else
          return test_code;
        end if;
      end if;
    elsif REGEXP_MATCHES(REPLACE(test_code, '-', ''),'^[0-9]+$','gi') is not null then 
      if v_remove then
        return trim(substr(TRIM(v_text), 1, length(TRIM(v_text)) - length(test_code)));
      else
        return test_code;
      end if;
    end if;
  end if;
  return null;
end;
$$;


--
-- Try and extract a country code from address text: city, then address_line_3, then address_line_2
-- For US the match may be the second to last token (zip code last) splitting on space characters.
--
create or replace function public.colin_update_address_country(v_text character varying, v_remove boolean) returns character varying
  immutable
  language plpgsql
as $$
declare
  countries text[] := ARRAY[ARRAY['U.S.A.', 'US'],
                            ARRAY['USA','US'],
                            ARRAY['CANADA','CA'],
                            ARRAY['SOUTH AUSTRALIA','AU'],
                            ARRAY['WEST AUSTRALIA','AU'],
                            ARRAY['WESTERN AUSTRALIA','AU'],
                            ARRAY['AUSTRALIA','AU'],
                            ARRAY['BARBADOS','BB'],
                            ARRAY['PEOPLES REPUBLIC OF CHINA','CN'],
                            ARRAY['P R OF CHINA','CN'],
                            ARRAY['TAIWAN REPUBLIC OF CHINA','TW'],
                            ARRAY['CHINA','CN'],
                            ARRAY['PRC','CN'],
                            ARRAY['ENGLAND','GB'],
                            ARRAY['UK','GB'],
                            ARRAY['SCOTLAND','GB'],
                            ARRAY['GERMANY','DE'],
                            ARRAY['HONG KONG','HK'],
                            ARRAY['H.K.','HK'],
                            ARRAY['HK','HK'],
                            ARRAY['IT -','IT'],
                            ARRAY['ITALY','IT'], -- IT -
                            ARRAY['JAPAN','JP'],
                            ARRAY['KOREA','KR'],
                            ARRAY['EAST MALAYSIA','MY'],
                            ARRAY['MALAYSIA','MY'],
                            ARRAY['MONACO','MC'],
                            ARRAY['PHILIPPINES','PH'],
                            ARRAY['SINGAPORE','SG'],
                            ARRAY['SWEDEN','SE'],
                            ARRAY['SWITZERLAND','CH'],
                            ARRAY['TAIWAN','TW'],
                            ARRAY['UKRAINE','UA'],
                            ARRAY['VIETNAM','VN']];
  country text[];
  base_text varchar(50);
  test_text varchar(50);
  test_country varchar(50);
  test_country2 varchar(50);
begin
  -- Empty value do nothing.
  if v_text is null or LENGTH(v_text) < 2 then
    return null;
  else
    base_text := REPLACE(TRIM(v_text), '  ', ' ');
    test_text := UPPER(base_text);
    test_country := SPLIT_PART(test_text, ' ', -1);
    if SPLIT_PART(test_text, ' ', -2) is not null then
      test_country2 := SPLIT_PART(test_text, ' ', -2);
    else
      test_country2 := '';
    end if;
    foreach country slice 1 in array countries
     loop
       -- Check last word first
       if country[1] = test_country then
         if v_remove then
           -- Safer than replacing
           return trim(substr(base_text, 1, length(base_text) - length(country[1])));
         else
           return country[2];
         end if;
       elsif country[1] = test_country2 and (country[1] != 'CANADA' or test_text not like '%TRANS CANADA%') then
         if v_remove then
           test_text := substr(base_text, 1, length(base_text) - length(country[1]) - length(test_country) - 1);
           return trim(trim(test_text) || ' ' || test_country);
         else
           return country[2];
         end if;
       elsif country[1] in ('PEOPLES REPUBLIC OF CHINA', 'P R OF CHINA', 'TAIWAN REPUBLIC OF CHINA', 'EAST MALAYSIA', 'HONG KONG') and 
             POSITION(country[1] in test_text) > 0 then
         if v_remove then
           return trim(substr(TRIM(v_text), 1, length(TRIM(v_text)) - length(country[1])));
         else
           return country[2];
         end if;
       end if;
     end loop;
  end if;
  return null;
end;
$$;


--
-- Try and extract a Canada province/region code from address text: city, then address_line_3, then address_line_2  
--
create or replace function public.colin_update_address_ca_province(v_text character varying, v_remove boolean) returns character varying
  immutable
  language plpgsql
as $$
declare
  provinces text[] := ARRAY[ARRAY['BRITISH COLUMBIA', 'BC'],
                            ARRAY['BC .','BC'],
                            ARRAY['B C','BC'],
                            ARRAY['B .C.','BC'],
                            ARRAY['B. C.','BC'],
                            ARRAY['BC,','BC'],
                            ARRAY['B.C. )','BC'],                            
                            ARRAY['BC)','BC'],                            
                            ARRAY['BC','BC'],
                            ARRAY['B.C.,','BC'],
                            ARRAY['B.C.','BC'],
                            ARRAY['B.C','BC'],
                            ARRAY['BC..','BC'],
                            ARRAY['BC.','BC'],
                            ARRAY['B,C.','BC'],
                            ARRAY['B.C..','BC'],
                            ARRAY['B.C .','BC'],                        
                            ARRAY['AB','AB'],
                            ARRAY['ALBERTA','AB'],
                            ARRAY['SK','SK'],
                            ARRAY['SASKATCHEWAN','SK'],
                            ARRAY['MB','MB'],
                            ARRAY['ON','ON'],
                            ARRAY['ONTARIO','ON'],
                            ARRAY['QC','QC'],
                            ARRAY['QUE','QC'],
                            ARRAY['QUEBEC','QC'],
                            ARRAY['NS','NS'],
                            ARRAY['NOVA SCOTIA','NS'],
                            ARRAY['YK','YK'],
                            ARRAY['YUKON','YK'],
                            ARRAY['NL','NL'],
                            ARRAY['NEWFOUNDLAND','NL']];
  province text[];
  test_text varchar(50);
  test_region varchar(50);
  test_region2 varchar(50);
  test_region_comma varchar(50);
begin
  -- Empty value do nothing.
  if v_text is null or LENGTH(v_text) < 2 then
    return null;
  else
    test_text := UPPER(TRIM(v_text));
    test_region := SPLIT_PART(test_text, ' ', -1);
    test_region_comma := SPLIT_PART(test_text, ',', -1);
    if SPLIT_PART(test_text, ' ', -2) is not null then
      test_region2 := SPLIT_PART(test_text, ' ', -2) || ' ' || test_region;
    else
      test_region2 := '';
    end if;
    foreach province slice 1 in array provinces
     loop
       -- Check last word first
       if province[1] = test_region or province[1] = test_region2 or province[1] = test_region_comma then
         if v_remove then
           -- Safer than replacing
           return trim(substr(TRIM(v_text), 1, length(TRIM(v_text)) - length(province[1])));
         else
           return province[2];
         end if;
       end if;
     end loop;
  end if;
  return null;
end;
$$;


--
-- Try and extract a US state code from address text: city, then address_line_3, then address_line_2  
--
create or replace function public.colin_update_address_us_state(v_text character varying, v_remove boolean) returns character varying
  immutable
  language plpgsql
as $$
declare
  us_states text[] := ARRAY[ARRAY['CA', 'CA'],
                            ARRAY['CALIFORNIA','CA'],
                            ARRAY['WA','WA'],
                            ARRAY['OR','OR'],
                            ARRAY['OREGON','OR'],
                            ARRAY['CO','CO'],
                            ARRAY['COLORADO','CO'],
                            ARRAY['HAWAII','HI'],
                            ARRAY['HI','HI'],
                            ARRAY['NY','NY'],
                            ARRAY['NEW YORK','NY'],
                            ARRAY['FLORIDA','FL'],
                            ARRAY['ALABAMA','AL'],
                            ARRAY['TEXAS','TX'],
                            ARRAY['TX','TX'],
                            ARRAY['VIRGINIA','VI'],
                            ARRAY['WI','WI']];
  us_state text[];
  test_text varchar(50);
  test_region varchar(50);
  test_region2 varchar(50);
  test_region_comma varchar(50);
begin
  -- Empty value do nothing.
  if v_text is null or LENGTH(v_text) < 2 then
    return null;
  else
    test_text := UPPER(TRIM(v_text));
    test_region := SPLIT_PART(test_text, ' ', -1);
    if SPLIT_PART(test_text, ' ', -2) is not null then
      test_region2 := SPLIT_PART(test_text, ' ', -2) || ' ' || test_region;
    else
      test_region2 := '';
    end if;
    foreach us_state slice 1 in array us_states
     loop
       -- Check last word first
       if us_state[1] = test_region or us_state[1] = test_region2 or us_state[1] = test_region_comma then
         if v_remove then
           -- Safer than replacing
           return trim(substr(TRIM(v_text), 1, length(TRIM(v_text)) - length(us_state[1])));
         else
           return us_state[2];
         end if;
       end if;
     end loop;
  end if;
  return null;
end;
$$;


--
-- Transpose corp_party address mailing and delivery country from addr_line3 and addr_line2.
-- call colin_address_transpose_country();
--
CREATE OR REPLACE PROCEDURE public.colin_address_transpose_country()
LANGUAGE plpgsql
AS $$
BEGIN
    -- Delivery/Mailing line 3
    update address
       set country_typ_cd = colin_update_address_country(addr_line_3, false),
           addr_line_3 = colin_update_address_country(addr_line_3, true)
    where addr_id in
    (
    select distinct a.addr_id
      from corp_state cs, corp_party cp, address a
     where cs.corp_num = cp.corp_num
       and cs.op_state_type_cd = 'ACT'
       and cs.end_event_id is null
       and (cp.end_event_id is null or cp.end_event_id = 0)
       and (cp.mailing_addr_id = a.addr_id or cp.delivery_addr_id = a.addr_id)
       and (a.country_typ_cd is null or trim(a.country_typ_cd) = '')
       and a.addr_line_3 is not null and trim(a.addr_line_3) != ''
       and (a.addr_line_3 like '%AUSTRALIA%' or
            a.addr_line_3 like '%BARBADOS%' or
            a.addr_line_3 like '%CANADA%' or
            a.addr_line_3 like '%CHINA%' or
            a.addr_line_3 like '% PRC%' or
            a.addr_line_3 like '%ENGLAND%' or
            a.addr_line_3 like '%GERMANY%' or
            a.addr_line_3 like '% UK%' or
            a.addr_line_3 like '%HONG KONG%' or
            a.addr_line_3 like '%H.K.%' or
            a.addr_line_3 like '%ITALY%' or
            a.addr_line_3 like 'IT -%' or
            a.addr_line_3 like '%JAPAN%' or
            a.addr_line_3 like '%KOREA%' or
            a.addr_line_3 like '%MALAYSIA%' or
            a.addr_line_3 like '%MONACO%' or
            a.addr_line_3 like '%PHILIPPINES%' or
            a.addr_line_3 like '%SINGAPORE%' or
            a.addr_line_3 like '%SWEDEN%' or
            a.addr_line_3 like '%SWITZERLAND%' or
            a.addr_line_3 like '%TAIWAN%' or
            a.addr_line_3 like '%USA%' or
            a.addr_line_3 like '%U.S.A.%' or
            a.addr_line_3 like '%VIETNAM%')
    )
    and colin_update_address_country(addr_line_3, false) is not null;
    COMMIT;

    -- Delivery/Mailing line 2
    update address
       set country_typ_cd = colin_update_address_country(addr_line_2, false),
           addr_line_2 = colin_update_address_country(addr_line_2, true)
    where addr_id in
    (
    select distinct a.addr_id
      from corp_state cs, corp_party cp, address a
     where cs.corp_num = cp.corp_num
       and cs.op_state_type_cd = 'ACT'
       and cs.end_event_id is null
       and (cp.end_event_id is null or cp.end_event_id = 0)
       and (cp.mailing_addr_id = a.addr_id or cp.delivery_addr_id = a.addr_id)
       and (a.country_typ_cd is null or trim(a.country_typ_cd) = '')
       and a.addr_line_2 is not null and trim(a.addr_line_2) != ''
       and (a.addr_line_2 like '%AUSTRALIA%' or
            a.addr_line_2 like '%BARBADOS%' or
            a.addr_line_2 like '%CANADA%' or
            a.addr_line_2 like '%CHINA%' or
            a.addr_line_2 like '% PRC%' or
            a.addr_line_2 like '%ENGLAND%' or
            a.addr_line_2 like '%GERMANY%' or
            a.addr_line_2 like '% UK%' or
            a.addr_line_2 like '%HONG KONG%' or
            a.addr_line_2 like '%H.K.%' or
            a.addr_line_2 like '%ITALY%' or
            a.addr_line_2 like 'IT -%' or
            a.addr_line_2 like '%JAPAN%' or
            a.addr_line_2 like '%KOREA%' or
            a.addr_line_2 like '%MALAYSIA%' or
            a.addr_line_2 like '%MONACO%' or
            a.addr_line_2 like '%PHILIPPINES%' or
            a.addr_line_2 like '%SINGAPORE%' or
            a.addr_line_2 like '%SWEDEN%' or
            a.addr_line_2 like '%SWITZERLAND%' or
            a.addr_line_2 like '%TAIWAN%' or
            a.addr_line_2 like '%USA%' or
            a.addr_line_2 like '%U.S.A.%' or
            a.addr_line_2 like '%VIETNAM%')
    )
    and colin_update_address_country(addr_line_2, false) is not null;
    COMMIT;

END;
$$;


--
-- Remove duplicate country from city, address line 3, address line 2.
-- call colin_address_duplicate_country();
--
CREATE OR REPLACE PROCEDURE public.colin_address_duplicate_country()
LANGUAGE plpgsql
AS $$
BEGIN
    -- Corp party delivery/mailing city
    update address
       set city = colin_update_address_country(city, true)
    where addr_id in
    (
    select distinct a.addr_id
      from corp_state cs, corp_party cp, address a
     where cs.corp_num = cp.corp_num
       and cs.op_state_type_cd = 'ACT'
       and cs.end_event_id is null
       and (cp.end_event_id is null or cp.end_event_id = 0)
       and (cp.mailing_addr_id = a.addr_id or cp.delivery_addr_id = a.addr_id)
       and a.country_typ_cd is not null and trim(a.country_typ_cd) != ''
       and a.city is not null and trim(a.city) != ''
       and upper(a.city) not like '%TRANS CANADA%'
       and upper(a.city) not like '%TRANS-CANADA%'
       and upper(a.city) not like '%CANADA PLACE%'
       and upper(a.city) not like '%PETRO CANADA%'
       and upper(a.city) not like '%CANADA SQUARE%'
       and upper(a.city) not like '%HONG KONG%'
       and upper(a.city) not like '%SINGAPORE%'
       and a.country_typ_cd not in ('HK', 'SG', 'MC')
       and (a.city like '%AUSTRALIA%' or
            a.city like '%BARBADOS%' or
            upper(a.city) like '%CANADA%' or
            a.city like '%CHINA%' or
            a.city like '% PRC%' or
            a.city like '%ENGLAND%' or
            a.city like '%GERMANY%' or
            a.city like '% UK%' or
            a.city like '%HONG KONG%' or
            a.city like '%H.K.%' or
            a.city like '%ITALY%' or
            a.city like 'IT -%' or
            a.city like '%JAPAN%' or
            a.city like '%KOREA%' or
            a.city like '%MALAYSIA%' or
            a.city like '%MONACO%' or
            a.city like '%PHILIPPINES%' or
            a.city like '%SINGAPORE%' or
            a.city like '%SWEDEN%' or
            a.city like '%SWITZERLAND%' or
            a.city like '%TAIWAN%' or
            a.city like '%USA%' or
            a.city like '%U.S.A.%' or
            a.city like '%VIETNAM%')
    )
    and country_typ_cd = colin_update_address_country(city, false);
    COMMIT;

    -- Corp party delivery/mailing line 3
    update address
       set addr_line_3 = colin_update_address_country(addr_line_3, true)
    where addr_id in
    (
    select distinct a.addr_id
      from corp_state cs, corp_party cp, address a
     where cs.corp_num = cp.corp_num
       and cs.op_state_type_cd = 'ACT'
       and cs.end_event_id is null
       and (cp.end_event_id is null or cp.end_event_id = 0)
       and (cp.mailing_addr_id = a.addr_id or cp.delivery_addr_id = a.addr_id)
       and a.country_typ_cd is not null and trim(a.country_typ_cd) != ''
       and a.addr_line_3 is not null and trim(a.addr_line_3) != ''
       and upper(a.addr_line_3) not like '%TRANS CANADA%'
       and upper(a.addr_line_3) not like '%TRANS-CANADA%'
       and upper(a.addr_line_3) not like '%CANADA PLACE%'
       and upper(a.addr_line_3) not like '%PETRO CANADA%'
       and upper(a.addr_line_3) not like '%CANADA SQUARE%'
       and a.country_typ_cd not in ('HK', 'SG', 'MC')
       and (a.addr_line_3 like '%AUSTRALIA%' or
            a.addr_line_3 like '%BARBADOS%' or
            upper(a.addr_line_3) like '%CANADA%' or
            a.addr_line_3 like '%CHINA%' or
            a.addr_line_3 like '% PRC%' or
            a.addr_line_3 like '%ENGLAND%' or
            a.addr_line_3 like '%GERMANY%' or
            a.addr_line_3 like '% UK%' or
            a.addr_line_3 like '%HONG KONG%' or
            a.addr_line_3 like '%H.K.%' or
            a.addr_line_3 like '%ITALY%' or
            a.addr_line_3 like 'IT -%' or
            a.addr_line_3 like '%JAPAN%' or
            a.addr_line_3 like '%KOREA%' or
            a.addr_line_3 like '%MALAYSIA%' or
            a.addr_line_3 like '%MONACO%' or
            a.addr_line_3 like '%PHILIPPINES%' or
            a.addr_line_3 like '%SINGAPORE%' or
            a.addr_line_3 like '%SWEDEN%' or
            a.addr_line_3 like '%SWITZERLAND%' or
            a.addr_line_3 like '%TAIWAN%' or
            a.addr_line_3 like '%USA%' or
            a.addr_line_3 like '%U.S.A.%' or
            a.addr_line_3 like '%VIETNAM%')
    )
    and country_typ_cd = colin_update_address_country(addr_line_3, false);
    COMMIT;

    -- Corp party delivery/mailing line 2
    update address
       set addr_line_2 = colin_update_address_country(addr_line_2, true)
    where addr_id in
    (
    select distinct a.addr_id
      from corp_state cs, corp_party cp, address a
     where cs.corp_num = cp.corp_num
       and cs.op_state_type_cd = 'ACT'
       and cs.end_event_id is null
       and (cp.end_event_id is null or cp.end_event_id = 0)
       and (cp.mailing_addr_id = a.addr_id or cp.delivery_addr_id = a.addr_id)
       and a.country_typ_cd is not null and trim(a.country_typ_cd) != ''
       and a.addr_line_2 is not null and trim(a.addr_line_2) != ''
       and upper(a.addr_line_2) not like '%TRANS CANADA%'
       and upper(a.addr_line_2) not like '%TRANS-CANADA%'
       and upper(a.addr_line_2) not like '%CANADA PLACE%'
       and upper(a.addr_line_2) not like '%PETRO CANADA%'
       and upper(a.addr_line_2) not like '%CANADA SQUARE%'
       and a.country_typ_cd not in ('HK', 'SG', 'MC')
       and (a.addr_line_2 like '%AUSTRALIA%' or
            a.addr_line_2 like '%BARBADOS%' or
            upper(a.addr_line_2) like '%CANADA%' or
            a.addr_line_2 like '%CHINA%' or
            a.addr_line_2 like '% PRC%' or
            a.addr_line_2 like '%ENGLAND%' or
            a.addr_line_2 like '%GERMANY%' or
            a.addr_line_2 like '% UK%' or
            a.addr_line_2 like '%HONG KONG%' or
            a.addr_line_2 like '%H.K.%' or
            a.addr_line_2 like '%ITALY%' or
            a.addr_line_2 like 'IT -%' or
            a.addr_line_2 like '%JAPAN%' or
            a.addr_line_2 like '%KOREA%' or
            a.addr_line_2 like '%MALAYSIA%' or
            a.addr_line_2 like '%MONACO%' or
            a.addr_line_2 like '%PHILIPPINES%' or
            a.addr_line_2 like '%SINGAPORE%' or
            a.addr_line_2 like '%SWEDEN%' or
            a.addr_line_2 like '%SWITZERLAND%' or
            a.addr_line_2 like '%TAIWAN%' or
            a.addr_line_2 like '%USA%' or
            a.addr_line_2 like '%U.S.A.%' or
            a.addr_line_2 like '%VIETNAM%')
    )
    and country_typ_cd = colin_update_address_country(addr_line_2, false);
    COMMIT;

END;
$$;


--
-- Transpose corp_party address mailing and delivery postal/us zip code from city, addr_line3, and addr_line2.
-- call colin_address_transpose_pcode();
--
CREATE OR REPLACE PROCEDURE public.colin_address_transpose_pcode()
LANGUAGE plpgsql
AS $$
BEGIN
    -- Corp party delivery/mailing city
    update address
       set postal_cd = colin_update_address_pcode(city, false, false),
           city = colin_update_address_pcode(city, true, false)
    where addr_id in
    (
    select distinct a.addr_id
      from corp_state cs, corp_party cp, address a
     where cs.corp_num = cp.corp_num
       and cs.op_state_type_cd = 'ACT'
       and cs.end_event_id is null
       and (cp.end_event_id is null or cp.end_event_id = 0)
       and (cp.mailing_addr_id = a.addr_id or cp.delivery_addr_id = a.addr_id)
       and (a.country_typ_cd is null or trim(a.country_typ_cd) = '' or a.country_typ_cd = 'CA')
       and (a.postal_cd is null or trim(a.postal_cd) = '')
       and a.city is not null and trim(a.city) != ''
       and length(trim(a.city)) > 5
    )
      and colin_update_address_pcode(city, false, false) is not null;
    COMMIT;
    update address
       set postal_cd = colin_update_address_pcode(city, false, true),
           city = colin_update_address_pcode(city, true, true)
    where addr_id in
    (
    select distinct a.addr_id
      from corp_state cs, corp_party cp, address a
     where cs.corp_num = cp.corp_num
       and cs.op_state_type_cd = 'ACT'
       and cs.end_event_id is null
       and (cp.end_event_id is null or cp.end_event_id = 0)
       and (cp.mailing_addr_id = a.addr_id or cp.delivery_addr_id = a.addr_id)
       and (a.country_typ_cd is not null and a.country_typ_cd = 'US')
       and (a.postal_cd is null or trim(a.postal_cd) = '')
       and a.city is not null and trim(a.city) != ''
       and length(trim(a.city)) >= 5
    )
      and colin_update_address_pcode(city, false, true) is not null;
    COMMIT;

    -- Corp party delivery/mailing line 3
    update address
       set postal_cd = colin_update_address_pcode(addr_line_3, false, false),
           addr_line_3 = colin_update_address_pcode(addr_line_3, true, false)
    where addr_id in
    (
    select distinct a.addr_id
      from corp_state cs, corp_party cp, address a
     where cs.corp_num = cp.corp_num
       and cs.op_state_type_cd = 'ACT'
       and cs.end_event_id is null
       and (cp.end_event_id is null or cp.end_event_id = 0)
       and (cp.mailing_addr_id = a.addr_id or cp.delivery_addr_id = a.addr_id)
       and (a.country_typ_cd is null or trim(a.country_typ_cd) = '' or a.country_typ_cd = 'CA')
       and (a.postal_cd is null or trim(a.postal_cd) = '')
       and a.addr_line_3 is not null and trim(a.addr_line_3) != ''
       and length(trim(a.addr_line_3)) > 5
    )
      and colin_update_address_pcode(addr_line_3, false, false) is not null;
    COMMIT;
    update address
       set postal_cd = colin_update_address_pcode(addr_line_3, false, true),
           addr_line_3 = colin_update_address_pcode(addr_line_3, true, true)
    where addr_id in
    (
    select distinct a.addr_id
      from corp_state cs, corp_party cp, address a
     where cs.corp_num = cp.corp_num
       and cs.op_state_type_cd = 'ACT'
       and cs.end_event_id is null
       and (cp.end_event_id is null or cp.end_event_id = 0)
       and (cp.mailing_addr_id = a.addr_id or cp.delivery_addr_id = a.addr_id)
       and (a.country_typ_cd is not null and a.country_typ_cd = 'US')
       and (a.postal_cd is null or trim(a.postal_cd) = '')
       and a.addr_line_3 is not null and trim(a.addr_line_3) != ''
       and length(trim(a.addr_line_3)) >= 5
    )
      and colin_update_address_pcode(addr_line_3, false, true) is not null;
    COMMIT;

    -- Corp party delivery/mailing line 2
    update address
       set postal_cd = colin_update_address_pcode(addr_line_2, false, false),
           addr_line_2 = colin_update_address_pcode(addr_line_2, true, false)
    where addr_id in
    (
    select distinct a.addr_id
      from corp_state cs, corp_party cp, address a
     where cs.corp_num = cp.corp_num
       and cs.op_state_type_cd = 'ACT'
       and cs.end_event_id is null
       and (cp.end_event_id is null or cp.end_event_id = 0)
       and (cp.mailing_addr_id = a.addr_id or cp.delivery_addr_id = a.addr_id)
       and (a.country_typ_cd is null or trim(a.country_typ_cd) = '' or a.country_typ_cd = 'CA')
       and (a.postal_cd is null or trim(a.postal_cd) = '')
       and a.addr_line_2 is not null and trim(a.addr_line_2) != ''
       and length(trim(a.addr_line_2)) > 5
    )
      and colin_update_address_pcode(addr_line_2, false, false) is not null;
    COMMIT;
    update address
       set postal_cd = colin_update_address_pcode(addr_line_2, false, true),
           addr_line_2 = colin_update_address_pcode(addr_line_2, true, true)
    where addr_id in
    (
    select distinct a.addr_id
      from corp_state cs, corp_party cp, address a
     where cs.corp_num = cp.corp_num
       and cs.op_state_type_cd = 'ACT'
       and cs.end_event_id is null
       and (cp.end_event_id is null or cp.end_event_id = 0)
       and (cp.mailing_addr_id = a.addr_id or cp.delivery_addr_id = a.addr_id)
       and (a.country_typ_cd is not null and a.country_typ_cd = 'US')
       and (a.postal_cd is null or trim(a.postal_cd) = '')
       and a.addr_line_2 is not null and trim(a.addr_line_2) != ''
       and length(trim(a.addr_line_2)) >= 5
    )
      and colin_update_address_pcode(addr_line_2, false, true) is not null;
    COMMIT;

    -- Office delivery/mailing city
    update address
       set postal_cd = colin_update_address_pcode(city, false, false),
           city = colin_update_address_pcode(city, true, false)
    where addr_id in
    (
    select distinct a.addr_id
      from corp_state cs, office o, address a
     where cs.corp_num = o.corp_num
       and cs.op_state_type_cd = 'ACT'
       and cs.end_event_id is null
       and (o.end_event_id is null or o.end_event_id = 0)
       and (o.mailing_addr_id = a.addr_id or o.delivery_addr_id = a.addr_id)
       and (a.country_typ_cd is null or trim(a.country_typ_cd) = '' or a.country_typ_cd = 'CA')
       and (a.postal_cd is null or trim(a.postal_cd) = '')
       and a.city is not null and trim(a.city) != ''
       and length(trim(a.city)) > 5
    )
      and colin_update_address_pcode(city, false, false) is not null;
    COMMIT;

END;
$$;


--
-- Format and remove duplicate CA postal codes from city, address line 3, address line 2.
-- call colin_address_duplicate_pcode();
--
CREATE OR REPLACE PROCEDURE public.colin_address_duplicate_pcode()
LANGUAGE plpgsql
AS $$
BEGIN
    -- Corp party format delivery/mailing
    update address
       set postal_cd = UPPER(LEFT(postal_cd, 3) || ' ' || RIGHT(postal_cd, 3))
    where addr_id in
    (
    select distinct a.addr_id
      from corp_state cs, corp_party cp, address a
     where cs.corp_num = cp.corp_num
       and cs.op_state_type_cd = 'ACT'
       and cs.end_event_id is null
       and (cp.end_event_id is null or cp.end_event_id = 0)
       and (cp.mailing_addr_id = a.addr_id or cp.delivery_addr_id = a.addr_id)
       and (a.country_typ_cd is null or trim(a.country_typ_cd) = '' or a.country_typ_cd = 'CA')
       and a.postal_cd is not null and length(trim(a.postal_cd)) = 6
       and a.postal_cd ~ '^[A-Za-z]\d[A-Za-z]\d[A-Za-z]\d$'
    );
    COMMIT;

    -- Office format delivery/mailing
    update address
       set postal_cd = UPPER(LEFT(postal_cd, 3) || ' ' || RIGHT(postal_cd, 3))
    where addr_id in
    (
    select distinct a.addr_id
      from corp_state cs, office o, address a
     where cs.corp_num = o.corp_num
       and cs.op_state_type_cd = 'ACT'
       and cs.end_event_id is null
       and (o.end_event_id is null or o.end_event_id = 0)
       and (o.mailing_addr_id = a.addr_id or o.delivery_addr_id = a.addr_id)
       and (a.country_typ_cd is null or trim(a.country_typ_cd) = '' or a.country_typ_cd = 'CA')
       and a.postal_cd is not null and length(trim(a.postal_cd)) = 6
       and a.postal_cd ~ '^[A-Za-z]\d[A-Za-z]\d[A-Za-z]\d$'
    );
    COMMIT;

    -- Corp party delivery/mailing city
    update address
       set city = colin_update_address_pcode(city, true, false)
    where addr_id in
    (
    select distinct a.addr_id
      from corp_state cs, corp_party cp, address a
     where cs.corp_num = cp.corp_num
       and cs.op_state_type_cd = 'ACT'
       and cs.end_event_id is null
       and (cp.end_event_id is null or cp.end_event_id = 0)
       and (cp.mailing_addr_id = a.addr_id or cp.delivery_addr_id = a.addr_id)
       and (a.country_typ_cd is null or trim(a.country_typ_cd) = '' or a.country_typ_cd = 'CA')
       and a.postal_cd is not null and length(trim(a.postal_cd)) = 7
       and a.postal_cd ~ '^[A-Za-z]\d[A-Za-z][ ]\d[A-Za-z]\d$'
       and a.city is not null and trim(a.city) != ''
       and length(trim(a.city)) > 5
       and trim(right(a.city, 7)) ~ '^[A-Za-z]\d[A-Za-z][ -]?\d[A-Za-z]\d$'
    )
      and postal_cd = colin_update_address_pcode(city, false, false);
    COMMIT;

    -- Corp party delivery/mailing line 3
    update address
       set addr_line_3 = colin_update_address_pcode(addr_line_3, true, false)
    where addr_id in
    (
    select distinct a.addr_id
      from corp_state cs, corp_party cp, address a
     where cs.corp_num = cp.corp_num
       and cs.op_state_type_cd = 'ACT'
       and cs.end_event_id is null
       and (cp.end_event_id is null or cp.end_event_id = 0)
       and (cp.mailing_addr_id = a.addr_id or cp.delivery_addr_id = a.addr_id)
       and (a.country_typ_cd is null or trim(a.country_typ_cd) = '' or a.country_typ_cd = 'CA')
       and a.postal_cd is not null and length(trim(a.postal_cd)) = 7
       and a.postal_cd ~ '^[A-Za-z]\d[A-Za-z][ ]\d[A-Za-z]\d$'
       and a.addr_line_3 is not null and trim(a.addr_line_3) != ''
       and length(trim(a.addr_line_3)) > 5
       and trim(right(a.addr_line_3, 7)) ~ '^[A-Za-z]\d[A-Za-z][ -]?\d[A-Za-z]\d$'
    )
      and postal_cd = colin_update_address_pcode(addr_line_3, false, false);
    COMMIT;

    -- Corp party delivery/mailing line 2
    update address
       set addr_line_2 = colin_update_address_pcode(addr_line_2, true, false)
    where addr_id in
    (
    select distinct a.addr_id
      from corp_state cs, corp_party cp, address a
     where cs.corp_num = cp.corp_num
       and cs.op_state_type_cd = 'ACT'
       and cs.end_event_id is null
       and (cp.end_event_id is null or cp.end_event_id = 0)
       and (cp.mailing_addr_id = a.addr_id or cp.delivery_addr_id = a.addr_id)
       and (a.country_typ_cd is null or trim(a.country_typ_cd) = '' or a.country_typ_cd = 'CA')
       and a.postal_cd is not null and length(trim(a.postal_cd)) = 7
       and a.postal_cd ~ '^[A-Za-z]\d[A-Za-z][ ]\d[A-Za-z]\d$'
       and a.addr_line_2 is not null and trim(a.addr_line_2) != ''
       and length(trim(a.addr_line_2)) > 5
       and trim(right(a.addr_line_2, 7)) ~ '^[A-Za-z]\d[A-Za-z][ -]?\d[A-Za-z]\d$'
    )
      and postal_cd = colin_update_address_pcode(addr_line_2, false, false);
    COMMIT;
END;
$$;


--
-- Transpose corp_party address mailing and delivery province/region code from city, addr_line3, and addr_line2.
-- call colin_address_transpose_region();
--
CREATE OR REPLACE PROCEDURE public.colin_address_transpose_region()
LANGUAGE plpgsql
AS $$
BEGIN
    -- Corp party skipping city: no mailing/delivery addresses exist with a CA/US region in the city.

    -- Corp party delivery/mailing line 3
    update address
       set province = colin_update_address_ca_province(addr_line_3, false),
           addr_line_3 = colin_update_address_ca_province(addr_line_3, true)
    where addr_id in
    (
    select distinct a.addr_id
      from corp_state cs, corp_party cp, address a
     where cs.corp_num = cp.corp_num
       and cs.op_state_type_cd = 'ACT'
       and cs.end_event_id is null
       and (cp.end_event_id is null or cp.end_event_id = 0)
       and (cp.mailing_addr_id = a.addr_id or cp.delivery_addr_id = a.addr_id)
       and (a.province is null or trim(a.province) = '')
       and (a.country_typ_cd is null or trim(a.country_typ_cd) = '' or a.country_typ_cd = 'CA')
       and a.addr_line_3 is not null and trim(a.addr_line_3) != ''
       and (right(a.addr_line_3, 2) in ('BC', 'AB', 'QC', 'MB', 'SK', 'ON', 'NS', 'YK') or
            right(a.addr_line_3, 3) in ('B.C', 'B C', 'BC.', 'BC,', 'BC)') or
            right(a.addr_line_3, 4) in ('B.C.', 'QUE.', 'B,C.', 'BC..','BC .') or
            right(a.addr_line_3, 5) in ('B.C.,', 'B .C.', 'B.C..', 'B.C .') or
            a.addr_line_3 like '% B.C. )' or
            a.addr_line_3 like '% B. C.%' or
            a.addr_line_3 like '%BRITISH COLUMBIA' or
            a.addr_line_3 like '% QUEBEC' or
            a.addr_line_3 like '%SASKATCHEWAN' or
            a.addr_line_3 like '% ONTARIO' or
            a.addr_line_3 like '% NEWFOUNDLAND' or
            a.addr_line_3 like '% ALBERTA%' or 
            a.addr_line_3 like '% NOVA SCOTIA' or
            a.addr_line_3 like '% YUKON')
    )
      and colin_update_address_ca_province(addr_line_3, false) is not null;
    COMMIT;
    update address
       set province = colin_update_address_us_state(addr_line_3, false),
           addr_line_3 = colin_update_address_us_state(addr_line_3, true)
    where addr_id in
    (
    select distinct a.addr_id
      from corp_state cs, corp_party cp, address a
     where cs.corp_num = cp.corp_num
       and cs.op_state_type_cd = 'ACT'
       and cs.end_event_id is null
       and (cp.end_event_id is null or cp.end_event_id = 0)
       and (cp.mailing_addr_id = a.addr_id or cp.delivery_addr_id = a.addr_id)
       and (a.province is null or trim(a.province) = '')
       and (a.country_typ_cd is null or trim(a.country_typ_cd) = '' or a.country_typ_cd = 'US')
       and a.addr_line_3 is not null and trim(a.addr_line_3) != ''
       and (right(a.addr_line_3, 2) in ('WA') or
            right(a.addr_line_3, 3) in (' CA',' OR', ' NY', ' TX', ' WI') or
            a.addr_line_3 like '% OR %' or
            a.addr_line_3 like '% WA %' or
            a.addr_line_3 like '% CA %' or
            a.addr_line_3 like '% TX%' or
            a.addr_line_3 like '% CALIFORNIA%' or
            a.addr_line_3 like '% HAWAII%' or
            a.addr_line_3 like '% ALABAMA%' or
            a.addr_line_3 like '% COLORADO%' or
            a.addr_line_3 like '% OREGON%' or
            a.addr_line_3 like '% TEXAS%' or
            a.addr_line_3 like '% VIRGINIA%' or
            a.addr_line_3 like '% FLORIDA%' or
            a.addr_line_3 like '% NY %')
    )
      and colin_update_address_us_state(addr_line_3, false) is not null;
    COMMIT;

    -- Corp party delivery/mailing line 2
    update address
       set province = colin_update_address_ca_province(addr_line_2, false),
           addr_line_2 = colin_update_address_ca_province(addr_line_2, true)
    where addr_id in
    (
    select distinct a.addr_id
      from corp_state cs, corp_party cp, address a
     where cs.corp_num = cp.corp_num
       and cs.op_state_type_cd = 'ACT'
       and cs.end_event_id is null
       and (cp.end_event_id is null or cp.end_event_id = 0)
       and (cp.mailing_addr_id = a.addr_id or cp.delivery_addr_id = a.addr_id)
       and (a.province is null or trim(a.province) = '')
       and (a.country_typ_cd is null or trim(a.country_typ_cd) = '' or a.country_typ_cd = 'CA')
       and a.addr_line_2 is not null and trim(a.addr_line_2) != ''
       and (right(a.addr_line_2, 2) in ('BC', 'AB', 'QC', 'MB', 'SK', 'ON', 'NS', 'YK') or
            right(a.addr_line_2, 3) in ('B.C', 'B C', 'BC.', 'BC,', 'BC)') or
            right(a.addr_line_2, 4) in ('B.C.', 'QUE.', 'B,C.', 'BC..','BC .') or
            right(a.addr_line_2, 5) in ('B.C.,', 'B .C.', 'B.C..', 'B.C .') or
            a.addr_line_2 like '% B.C. )' or
            a.addr_line_2 like '% B. C.%' or
            a.addr_line_2 like '%BRITISH COLUMBIA' or
            a.addr_line_2 like '% QUEBEC' or
            a.addr_line_2 like '%SASKATCHEWAN' or
            a.addr_line_2 like '% ONTARIO' or
            a.addr_line_2 like '% NEWFOUNDLAND' or
            a.addr_line_2 like '% ALBERTA%' or 
            a.addr_line_2 like '% NOVA SCOTIA' or
            a.addr_line_2 like '% YUKON')
    )
      and colin_update_address_ca_province(addr_line_2, false) is not null;
    COMMIT;
    update address
       set province = colin_update_address_us_state(addr_line_2, false),
           addr_line_2 = colin_update_address_us_state(addr_line_2, true)
    where addr_id in
    (
    select distinct a.addr_id
      from corp_state cs, corp_party cp, address a
     where cs.corp_num = cp.corp_num
       and cs.op_state_type_cd = 'ACT'
       and cs.end_event_id is null
       and (cp.end_event_id is null or cp.end_event_id = 0)
       and (cp.mailing_addr_id = a.addr_id or cp.delivery_addr_id = a.addr_id)
       and (a.province is null or trim(a.province) = '')
       and (a.country_typ_cd is null or trim(a.country_typ_cd) = '' or a.country_typ_cd = 'US')
       and a.addr_line_2 is not null and trim(a.addr_line_2) != ''
       and (right(a.addr_line_2, 2) in ('WA') or
            right(a.addr_line_2, 3) in (' CA',' OR', ' NY', ' TX', ' WI') or
            a.addr_line_2 like '% OR %' or
            a.addr_line_2 like '% WA %' or
            a.addr_line_2 like '% CA %' or
            a.addr_line_2 like '% TX%' or
            a.addr_line_2 like '% CALIFORNIA%' or
            a.addr_line_2 like '% HAWAII%' or
            a.addr_line_2 like '% ALABAMA%' or
            a.addr_line_2 like '% COLORADO%' or
            a.addr_line_2 like '% OREGON%' or
            a.addr_line_2 like '% TEXAS%' or
            a.addr_line_2 like '% VIRGINIA%' or
            a.addr_line_2 like '% FLORIDA%' or
            a.addr_line_2 like '% NY %')
    )
      and colin_update_address_us_state(addr_line_2, false) is not null;
    COMMIT;
END;
$$;


--
-- Remove duplicate corp_party address mailing and delivery province/region codes from city, addr_line3, and addr_line2.
-- call colin_address_duplicate_region();
--
CREATE OR REPLACE PROCEDURE public.colin_address_duplicate_region()
LANGUAGE plpgsql
AS $$
BEGIN
    -- Corp party delivery/mailing city
    update address
       set city = colin_update_address_ca_province(city, true)
    where addr_id in
    (
    select distinct a.addr_id
      from corp_state cs, corp_party cp, address a
     where cs.corp_num = cp.corp_num
       and cs.op_state_type_cd = 'ACT'
       and cs.end_event_id is null
       and (cp.end_event_id is null or cp.end_event_id = 0)
       and (cp.mailing_addr_id = a.addr_id or cp.delivery_addr_id = a.addr_id)
       and (a.country_typ_cd is null or trim(a.country_typ_cd) = '' or a.country_typ_cd = 'CA')
       and a.province is not null and a.province in ('BC', 'AB', 'SK', 'MN', 'ON', 'QC', 'NS', 'NL', 'YK')
       and a.city is not null and trim(a.city) != ''
       and (right(a.city, 2) in ('BC', 'AB', 'QC', 'MB', 'SK', 'ON', 'NS', 'YK') or
            right(a.city, 3) in ('B.C', 'B C', 'BC.','BC,') or
            right(a.city, 4) in ('B.C.', 'QUE.', 'B,C.', 'BC..','BC .') or
            right(a.city, 5) in ('B.C.,', 'B .C.', 'B.C..', 'B.C .') or
            a.city like '% B. C.%' or
            a.city like '%BRITISH COLUMBIA' or
            a.city like '% QUEBEC' or
            a.city like '%SASKATCHEWAN' or
            a.city like '% ONTARIO' or
            a.city like '% NEWFOUNDLAND' or
            a.city like '% ALBERTA%' or 
            a.city like '% NOVA SCOTIA' or
            a.city like '% YUKON')
    )
    and province = colin_update_address_ca_province(city, false);
    COMMIT;

    -- Corp party delivery/mailing line 3
    update address
       set addr_line_3 = colin_update_address_ca_province(addr_line_3, true)
    where addr_id in
    (
    select distinct a.addr_id
      from corp_state cs, corp_party cp, address a
     where cs.corp_num = cp.corp_num
       and cs.op_state_type_cd = 'ACT'
       and cs.end_event_id is null
       and (cp.end_event_id is null or cp.end_event_id = 0)
       and (cp.mailing_addr_id = a.addr_id or cp.delivery_addr_id = a.addr_id)
       and (a.country_typ_cd is null or trim(a.country_typ_cd) = '' or a.country_typ_cd = 'CA')
       and a.province is not null and a.province in ('BC', 'AB', 'SK', 'MN', 'ON', 'QC', 'NS', 'NL', 'YK')
       and a.addr_line_3 is not null and trim(a.addr_line_3) != ''
       and (right(a.addr_line_3, 2) in ('BC', 'AB', 'QC', 'MB', 'SK', 'ON', 'NS', 'YK') or
            right(a.addr_line_3, 3) in ('B.C', 'B C', 'BC.','BC,') or
            right(a.addr_line_3, 4) in ('B.C.', 'QUE.', 'B,C.', 'BC..','BC .') or
            right(a.addr_line_3, 5) in ('B.C.,', 'B .C.', 'B.C..', 'B.C .') or
            a.addr_line_3 like '% B. C.%' or
            a.addr_line_3 like '%BRITISH COLUMBIA' or
            a.addr_line_3 like '% QUEBEC' or
            a.addr_line_3 like '%SASKATCHEWAN' or
            a.addr_line_3 like '% ONTARIO' or
            a.addr_line_3 like '% NEWFOUNDLAND' or
            a.addr_line_3 like '% ALBERTA%' or 
            a.addr_line_3 like '% NOVA SCOTIA' or
            a.addr_line_3 like '% YUKON')
    )
    and province = colin_update_address_ca_province(addr_line_3, false);
    COMMIT;

    -- Corp party delivery/mailing line 2
    update address
       set addr_line_2 = colin_update_address_ca_province(addr_line_2, true)
    where addr_id in
    (
    select distinct a.addr_id
      from corp_state cs, corp_party cp, address a
     where cs.corp_num = cp.corp_num
       and cs.op_state_type_cd = 'ACT'
       and cs.end_event_id is null
       and (cp.end_event_id is null or cp.end_event_id = 0)
       and (cp.mailing_addr_id = a.addr_id or cp.delivery_addr_id = a.addr_id)
       and (a.country_typ_cd is null or trim(a.country_typ_cd) = '' or a.country_typ_cd = 'CA')
       and a.province is not null and a.province in ('BC', 'AB', 'SK', 'MN', 'ON', 'QC', 'NS', 'NL', 'YK')
       and a.addr_line_2 is not null and trim(a.addr_line_2) != ''
       and (right(a.addr_line_2, 2) in ('BC', 'AB', 'QC', 'MB', 'SK', 'ON', 'NS', 'YK') or
            right(a.addr_line_2, 3) in ('B.C', 'B C', 'BC.','BC,') or
            right(a.addr_line_2, 4) in ('B.C.', 'QUE.', 'B,C.', 'BC..','BC .') or
            right(a.addr_line_2, 5) in ('B.C.,', 'B .C.', 'B.C..', 'B.C .') or
            a.addr_line_2 like '% B. C.%' or
            a.addr_line_2 like '%BRITISH COLUMBIA' or
            a.addr_line_2 like '% QUEBEC' or
            a.addr_line_2 like '%SASKATCHEWAN' or
            a.addr_line_2 like '% ONTARIO' or
            a.addr_line_2 like '% NEWFOUNDLAND' or
            a.addr_line_2 like '% ALBERTA%' or 
            a.addr_line_2 like '% NOVA SCOTIA' or
            a.addr_line_2 like '% YUKON')
    )
    and province = colin_update_address_ca_province(addr_line_2, false);
    COMMIT;

END;
$$;


--
-- Transpose office and corp_party address mailing and delivery null city from addr_line3, and addr_line2.
-- call colin_address_transpose_city();
--
CREATE OR REPLACE PROCEDURE public.colin_address_transpose_city()
LANGUAGE plpgsql
AS $$
BEGIN
    -- Corp party delivery/mailing line 3
    update address
       set city = addr_line_3, addr_line_3 = null
    where addr_id in
    (
    select distinct a.addr_id
      from corp_state cs, corp_party cp, address a
     where cs.corp_num = cp.corp_num
       and cs.op_state_type_cd = 'ACT'
       and cs.end_event_id is null
       and (cp.end_event_id is null or cp.end_event_id = 0)
       and (cp.mailing_addr_id = a.addr_id or cp.delivery_addr_id = a.addr_id)
       and (a.city is null or trim(a.city) = '')
       and a.addr_line_3 is not null
       and length(trim(a.addr_line_3)) between 1 and 40
       and upper(a.addr_line_3) not like '%NAME:%'
       and upper(a.addr_line_3) not like '%FULL NAME%'
       and upper(a.addr_line_3) not like 'F/N%'
       and upper(a.addr_line_3) not like '%ALSO KNOWN %'
       and upper(a.addr_line_3) not like '%AKA:%'
    );
    COMMIT;

    -- Corp party delivery/mailing line 2
    update address
       set city = addr_line_2, addr_line_2 = null
    where addr_id in
    (
    select distinct a.addr_id
      from corp_state cs, corp_party cp, address a
     where cs.corp_num = cp.corp_num
       and cs.op_state_type_cd = 'ACT'
       and cs.end_event_id is null
       and (cp.end_event_id is null or cp.end_event_id = 0)
       and (cp.mailing_addr_id = a.addr_id or cp.delivery_addr_id = a.addr_id)
       and (a.city is null or trim(a.city) = '')
       and a.addr_line_2 is not null
       and length(trim(a.addr_line_2)) between 1 and 40
       and upper(a.addr_line_2) not like '%NAME:%'
       and upper(a.addr_line_2) not like '%FULL NAME%'
       and upper(a.addr_line_2) not like 'F/N%'
       and upper(a.addr_line_2) not like '%ALSO KNOWN %'
       and upper(a.addr_line_2) not like '%AKA:%'
    );
    COMMIT;

    -- Office delivery/mailing line 3
    update address
       set city = addr_line_3, addr_line_3 = null
    where addr_id in
    (
    select distinct a.addr_id
      from corp_state cs, office o, address a
     where cs.corp_num = o.corp_num
       and cs.op_state_type_cd = 'ACT'
       and cs.end_event_id is null
       and (o.end_event_id is null or o.end_event_id = 0)
       and (o.mailing_addr_id = a.addr_id or o.delivery_addr_id = a.addr_id)
       and (a.city is null or trim(a.city) = '')
       and a.addr_line_3 is not null
       and length(trim(a.addr_line_3)) between 1 and 40
       and upper(a.addr_line_3) not like '%NAME:%'
       and upper(a.addr_line_3) not like '%FULL NAME%'
       and upper(a.addr_line_3) not like 'F/N%'
       and upper(a.addr_line_3) not like '%ALSO KNOWN %'
       and upper(a.addr_line_3) not like '%AKA:%'
    );
    COMMIT;

    -- Office delivery/mailing line 2
    update address
       set city = addr_line_2, addr_line_2 = null
    where addr_id in
    (
    select distinct a.addr_id
      from corp_state cs, office o, address a
     where cs.corp_num = o.corp_num
       and cs.op_state_type_cd = 'ACT'
       and cs.end_event_id is null
       and (o.end_event_id is null or o.end_event_id = 0)
       and (o.mailing_addr_id = a.addr_id or o.delivery_addr_id = a.addr_id)
       and (a.city is null or trim(a.city) = '')
       and a.addr_line_2 is not null
       and length(trim(a.addr_line_2)) between 1 and 40
       and upper(a.addr_line_2) not like '%NAME:%'
       and upper(a.addr_line_2) not like '%FULL NAME%'
       and upper(a.addr_line_2) not like 'F/N%'
       and upper(a.addr_line_2) not like '%ALSO KNOWN %'
       and upper(a.addr_line_2) not like '%AKA:%'
    );
    COMMIT;

END;
$$;


--
-- Final transpose step: cleanup.
-- Trim address city, address lines 1,2,3
-- Remove trailing comma characters from city, addresses lines 2 and 3.
-- call colin_address_transpose_cleanup();
--
CREATE OR REPLACE PROCEDURE public.colin_address_transpose_cleanup()
LANGUAGE plpgsql
AS $$
BEGIN
    -- Trim corp party delivery/mailing city: 104613
    update address
       set city = trim(city)
    where addr_id in
    (
    select distinct a.addr_id
      from corp_state cs, corp_party cp, address a
     where cs.corp_num = cp.corp_num
       and cs.op_state_type_cd = 'ACT'
       and cs.end_event_id is null
       and (cp.end_event_id is null or cp.end_event_id = 0)
       and (cp.mailing_addr_id = a.addr_id or cp.delivery_addr_id = a.addr_id)
       and a.city is not null 
       and a.city != trim(a.city)
    );
    COMMIT;

    -- Trim corp party delivery/mailing line 3: 1032
    update address
       set addr_line_3 = trim(addr_line_3)
    where addr_id in
    (
    select distinct a.addr_id
      from corp_state cs, corp_party cp, address a
     where cs.corp_num = cp.corp_num
       and cs.op_state_type_cd = 'ACT'
       and cs.end_event_id is null
       and (cp.end_event_id is null or cp.end_event_id = 0)
       and (cp.mailing_addr_id = a.addr_id or cp.delivery_addr_id = a.addr_id)
       and a.addr_line_3 is not null 
       and a.addr_line_3 != trim(a.addr_line_3)
    );
    COMMIT;

    -- Trim corp party delivery/mailing line 2: 9951
    update address
       set addr_line_2 = trim(addr_line_2)
    where addr_id in
    (
    select distinct a.addr_id
      from corp_state cs, corp_party cp, address a
     where cs.corp_num = cp.corp_num
       and cs.op_state_type_cd = 'ACT'
       and cs.end_event_id is null
       and (cp.end_event_id is null or cp.end_event_id = 0)
       and (cp.mailing_addr_id = a.addr_id or cp.delivery_addr_id = a.addr_id)
       and a.addr_line_2 is not null 
       and a.addr_line_2 != trim(a.addr_line_2)
    );
    COMMIT;

    -- Trim corp party delivery/mailing line 1: 153445
    update address
       set addr_line_1 = trim(addr_line_1)
    where addr_id in
    (
    select distinct a.addr_id
      from corp_state cs, corp_party cp, address a
     where cs.corp_num = cp.corp_num
       and cs.op_state_type_cd = 'ACT'
       and cs.end_event_id is null
       and (cp.end_event_id is null or cp.end_event_id = 0)
       and (cp.mailing_addr_id = a.addr_id or cp.delivery_addr_id = a.addr_id)
       and a.addr_line_1 is not null 
       and a.addr_line_1 != trim(a.addr_line_1)
    );
    COMMIT;

    -- Trim office delivery/mailing city: 48497
    update address
       set city = trim(city)
    where addr_id in
    (
    select distinct a.addr_id
      from corp_state cs, office o, address a
     where cs.corp_num = o.corp_num
       and cs.op_state_type_cd = 'ACT'
       and cs.end_event_id is null
       and (o.end_event_id is null or o.end_event_id = 0)
       and (o.mailing_addr_id = a.addr_id or o.delivery_addr_id = a.addr_id)
       and a.city is not null 
       and a.city != trim(a.city)
    );
    COMMIT;

    -- Trim office delivery/mailing line 3: 532
    update address
       set addr_line_3 = trim(addr_line_3)
    where addr_id in
    (
    select distinct a.addr_id
      from corp_state cs, office o, address a
     where cs.corp_num = o.corp_num
       and cs.op_state_type_cd = 'ACT'
       and cs.end_event_id is null
       and (o.end_event_id is null or o.end_event_id = 0)
       and (o.mailing_addr_id = a.addr_id or o.delivery_addr_id = a.addr_id)
       and a.addr_line_3 is not null 
       and a.addr_line_3 != trim(a.addr_line_3)
    );
    COMMIT;

    -- Trim office delivery/mailing line 2: 5926
    update address
       set addr_line_2 = trim(addr_line_2)
    where addr_id in
    (
    select distinct a.addr_id
      from corp_state cs, office o, address a
     where cs.corp_num = o.corp_num
       and cs.op_state_type_cd = 'ACT'
       and cs.end_event_id is null
       and (o.end_event_id is null or o.end_event_id = 0)
       and (o.mailing_addr_id = a.addr_id or o.delivery_addr_id = a.addr_id)
       and a.addr_line_2 is not null 
       and a.addr_line_2 != trim(a.addr_line_2)
    );
    COMMIT;

    -- Trim office delivery/mailing line 1: 69062
    update address
       set addr_line_1 = trim(addr_line_1)
    where addr_id in
    (
    select distinct a.addr_id
      from corp_state cs, office o, address a
     where cs.corp_num = o.corp_num
       and cs.op_state_type_cd = 'ACT'
       and cs.end_event_id is null
       and (o.end_event_id is null or o.end_event_id = 0)
       and (o.mailing_addr_id = a.addr_id or o.delivery_addr_id = a.addr_id)
       and a.addr_line_1 is not null 
       and a.addr_line_1 != trim(a.addr_line_1)
    );
    COMMIT;

    -- Remove trailing comma corp party delivery/mailing city: 20928
    update address
       set city = substr(city, 1, length(city) - 1)
    where addr_id in
    (
    select distinct a.addr_id
      from corp_state cs, corp_party cp, address a
     where cs.corp_num = cp.corp_num
       and cs.op_state_type_cd = 'ACT'
       and cs.end_event_id is null
       and (cp.end_event_id is null or cp.end_event_id = 0)
       and (cp.mailing_addr_id = a.addr_id or cp.delivery_addr_id = a.addr_id)
       and a.city is not null 
       and right(a.city, 1) = ','
    );
    COMMIT;

    -- Remove trailing comma corp party delivery/mailing line 3: 1109
    update address
       set addr_line_3 = substr(addr_line_3, 1, length(addr_line_3) - 1)
    where addr_id in
    (
    select distinct a.addr_id
      from corp_state cs, corp_party cp, address a
     where cs.corp_num = cp.corp_num
       and cs.op_state_type_cd = 'ACT'
       and cs.end_event_id is null
       and (cp.end_event_id is null or cp.end_event_id = 0)
       and (cp.mailing_addr_id = a.addr_id or cp.delivery_addr_id = a.addr_id)
       and a.addr_line_3 is not null 
       and right(a.addr_line_3, 1) = ','
    );
    COMMIT;

    -- Remove trailing comma corp party delivery/mailing line 2: 14957
    update address
       set addr_line_2 = substr(addr_line_2, 1, length(addr_line_2) - 1)
    where addr_id in
    (
    select distinct a.addr_id
      from corp_state cs, corp_party cp, address a
     where cs.corp_num = cp.corp_num
       and cs.op_state_type_cd = 'ACT'
       and cs.end_event_id is null
       and (cp.end_event_id is null or cp.end_event_id = 0)
       and (cp.mailing_addr_id = a.addr_id or cp.delivery_addr_id = a.addr_id)
       and a.addr_line_2 is not null 
       and right(a.addr_line_2, 1) = ','
    );
    COMMIT;

    -- Remove trailing comma office delivery/mailing city: 1665
    update address
       set city = substr(city, 1, length(city) - 1)
    where addr_id in
    (
    select distinct a.addr_id
      from corp_state cs, office o, address a
     where cs.corp_num = o.corp_num
       and cs.op_state_type_cd = 'ACT'
       and cs.end_event_id is null
       and (o.end_event_id is null or o.end_event_id = 0)
       and (o.mailing_addr_id = a.addr_id or o.delivery_addr_id = a.addr_id)
       and a.city is not null 
       and right(a.city, 1) = ','
    );
    COMMIT;

    -- Remove trailing comma office delivery/mailing line 3: 992
    update address
       set addr_line_3 = substr(addr_line_3, 1, length(addr_line_3) - 1)
    where addr_id in
    (
    select distinct a.addr_id
      from corp_state cs, office o, address a
     where cs.corp_num = o.corp_num
       and cs.op_state_type_cd = 'ACT'
       and cs.end_event_id is null
       and (o.end_event_id is null or o.end_event_id = 0)
       and (o.mailing_addr_id = a.addr_id or o.delivery_addr_id = a.addr_id)
       and a.addr_line_3 is not null 
       and right(a.addr_line_3, 1) = ','
    );
    COMMIT;

    -- Remove trailing comma office delivery/mailing line 2: 87
    update address
       set addr_line_2 = substr(addr_line_2, 1, length(addr_line_2) - 1)
    where addr_id in
    (
    select distinct a.addr_id
      from corp_state cs, office o, address a
     where cs.corp_num = o.corp_num
       and cs.op_state_type_cd = 'ACT'
       and cs.end_event_id is null
       and (o.end_event_id is null or o.end_event_id = 0)
       and (o.mailing_addr_id = a.addr_id or o.delivery_addr_id = a.addr_id)
       and a.addr_line_2 is not null 
       and right(a.addr_line_2, 1) = ','
    );
    COMMIT;

END;
$$;


--
-- Execute all transpose changes to active addresses belonging to active businesses:
-- 1. Transpose corp_party address mailing and delivery country from addr_line3 and addr_line2.
-- 2. Remove duplicate country from city, addr_line3, addr_line2.
-- 3. Transpose corp_party address mailing and delivery postal/us zip code from city, addr_line3, and addr_line2.
-- 4. Format CA postal codes and remove duplicate CA postal codes from city, addr_line3, addr_line2.
-- 5. Transpose corp_party address mailing and delivery CA and US province/region codes from city, addr_line3, and addr_line2.
-- 6. Remove duplicate corp_party address mailing and delivery CA province/region codes from city, addr_line3, and addr_line2.
-- 7. Transpose office and corp_party address mailing and delivery null city from addr_line3 and addr_line2.
-- 8. Trim address city, addr_line3, addr_line2, addr_line1. Remove trailing comma characters from city, addr_line3, addr_line2.
-- call colin_address_transpose();
--
CREATE OR REPLACE PROCEDURE public.colin_address_transpose()
LANGUAGE plpgsql
AS $$
BEGIN
call colin_address_transpose_country();
call colin_address_duplicate_country();
call colin_address_transpose_pcode();
call colin_address_duplicate_pcode();
call colin_address_transpose_region();
call colin_address_duplicate_region();
call colin_address_transpose_city();
call colin_address_transpose_cleanup();
END;
$$;
