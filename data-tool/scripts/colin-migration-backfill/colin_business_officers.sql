-- Try to extract/derive a region code from either the address text.
-- If replace is true, the matching value is returned if a match is found. It can then be removed from the address line.
create or replace function public.colin_hist_cars_region(v_text character varying,
                                                         v_replace boolean) returns character varying
  immutable
  language plpgsql
as $$
declare
  -- order is important within the array for removal
  bc_region text[] := '{", BC "," BC ",",BC ",",BC,","BC,","BC,"," B,.C. ",", B.C.",",B.C.",",B.C "," B.C."," B.C"," B . C. ",", B C. "' ||
                       ',"B.C. ","B C ","B..C","B. C. ","/BC/"," B,C, "," B\\C "," B,C. "," B.,C,. ",", CB ",", B. C> "' ||
                       ',", B. C "," B>C ",", B .C. "," BDC "," BXC "," B. .C "," CBC ","BRITISHCOLUMBIA","BRITISH COLUMBIA"' ||
                       ',"BRITSH COLUMBIA","BRITSH COLUMIA","BRITSH COLUMBIA","BTISH COLUMBIA","BRTISH COLUMBIA"' ||
                       ',"BRITSIH COLUMBIA","BRITIHS COLUMBIA","BRISITH COLUMBIA","BRISTISH COLUMBIA","BRISITSH COLUMBIA"' ||
                       ',"BRITISIH COLUMBIA","BRIRISH COLUMBIA","BRIISH COLUMBIA","BREITISH COLUMBIA","BRITISH COLUBIA"' ||
                       ',"BREITISH COLUMBIA","BRITISH COLUMVIA"," BC. ","BRITISH COLUMIBA"," B.B. "," BC- "," BCC ",",B .C. "' ||
                       '," BCD ", " BV "," BRITISH COLUMBI "," BRITISH  COLUMBIA "," BCV "," BCL "," BRITISH COUMBIA "," BE "' ||
                       '," BCS "," B C. "," BRITISH COLUBMIA "," BCY "," BCN "," B C, "," BX "," BRITISH COLIMBIA "," C.B. "' ||
                       '," BRITISH COLMBIA "," B.V. "," BRITISH COMUMBIA "," BGC "," BRITISH CLOUMBIA "," BCBC "," B .C "' ||
                       '," BRITISH COLUMBAI "," BRITISH COLUMIA "," BRITISH COLUMBIUA "," BRITISH COLULMBIA ", " V1BC "," VC "}';
  ab_region text[] := '{" AB "," A.B. "," AB, "," AB,"," AB. ",",AB ",",AB,"," ALTA "," ALTA. "," ALB ","ALBERT "," AL "' ||
                        ',"ALERTA ","ALBERTA ","ALBERTA,","ABLERTA ","ABERTA","ALBRTA","ALBETRA"," ALBERA "," ALBERTS " }';
  mb_region text[] := '{", MAN. "," MAN. "," MAN "," MB "," MB, "," MB,"," MB. ",",MB ",",MB","MANITOBA","MANAITOBA"' ||
                        ',"MANITOBE"}';
  sk_region text[] := '{" SK "," SK. ",", SK",", SA "," SA ","SASKATCHEWAN"," ASKATCHEWAN "," SASK. "," SASK "," SASKATACHEWAN "}';
  on_region text[] := '{" ONTARIO,"," ONTARIO "," ONTARION ","ONTARO"," ONTRIO "," ONT "," ONT. "," ON "," ON. ",", ON "' ||
                        ',",ON "," O.N. "," OT "}';
  qc_region text[] := '{" QC "," QC",", QC"," QUEBEC "," QUEBEC, "," QUE "," QU "," PQ "}';
  yt_region text[] := '{" YK "," YT ",", YT"," YUKON TERRITORIES "," YUKON TERRITORY "," YUKON "}';
  nb_region text[] := '{" NB ",", NB"," N.B. ","NEW BRUNSWICK"}';
  nl_region text[] := '{" NFLD "," NL "," N.L. ",", NL","NEWFOUNDLAND", " NF "}';
  ns_region text[] := '{" NS ",", NS","NOVA SCOTIA"}';
  nt_region text[] := '{" NWT "," N.W.T. "," N.T. "," NT ",", NT","NORTH WEST TERRITORIES","NORTHWEST TERRITORIES"}';
  nu_region text[] := '{" NUNUVIT "," NU ",", NU "}';
  pe_region text[] := '{" PEI "," P.E.I. "," PE ",", PE ","PRINCE EDWARD ISLAND"}';
  us_states text[] := ARRAY[ARRAY[' ALASKA ', 'AK'],
                            ARRAY[' ALASKA, ','AK'],
                            ARRAY[' AK ','AK'],
                            ARRAY[' AR ','AR'],
                            ARRAY[' ARKANSAS ','AR'],
                            ARRAY[' ARIZONA ','AZ'],
                            ARRAY[' ARIZONA,','AZ'],
                            ARRAY[' AZ ','AZ'],
                            ARRAY[' CALFORNIA ','CA'],
                            ARRAY[' CALIFORNIA ','CA'],
                            ARRAY[' CALIFORNIA,','CA'],
                            ARRAY[' CALIFORNAI ','CA'],                            
                            ARRAY[' CA ','CA'],
                            ARRAY[' CA. ','CA'],
                            ARRAY[' CA, ','CA'],
                            ARRAY['CALFORNIA','CA'],
                            ARRAY[' CALIF. ','CA'],
                            ARRAY[' CALIF ','CA'],
                            ARRAY[' CAL, ','CA'],
                            ARRAY[' COLORADO ','CO'],
                            ARRAY[' COLORADO, ','CO'],
                            ARRAY[' CO ','CO'],
                            ARRAY[' CO, ','CO'],
                            ARRAY['CONNECTICUT','CT'],
                            ARRAY[' CT ','CT'],
                            ARRAY[' FLORIDA ','FL'],
                            ARRAY[' FLORIDA, ','FL'],
                            ARRAY[' FL ','FL'],
                            ARRAY[' FL. ','FL'],
                            ARRAY[' GA ','GA'],
                            ARRAY[' GEORGIA ','GA'],
                            ARRAY[' HAWAII ','HI'],
                            ARRAY[' HAWAII, ','HI'],
                            ARRAY[' HI ','HI'],
                            ARRAY[' ID ','ID'],
                            ARRAY[' IDAHO ','ID'],
                            ARRAY['IDAHO ','ID'],
                            ARRAY['IDAHO,','ID'],
                            ARRAY['ILLINOIS','IL'],
                            ARRAY[' IL ','IL'],
                            ARRAY[' IA ','IA'],
                            ARRAY[' IOWA ','IA'],
                            ARRAY[' INDIANA ','IN'],
                            ARRAY[' IN ','IN'],
                            ARRAY[' KANSAS ','KS'],
                            ARRAY[' KS ','KS'],
                            ARRAY[' KY ','KY'],
                            ARRAY[' KEN. ','KY'],
                            ARRAY[' KENTUCKY ','KY'],
                            ARRAY[' LA ','LA'],
                            ARRAY[' LOUISIANA ','LA'],
                            ARRAY[' MONTANA ','MT'],
                            ARRAY[' MONTANA, ','MT'],
                            ARRAY[' MT ','MT'],
                            ARRAY['MASSACHUSETTS','MA'],
                            ARRAY[' MA ','MA'],
                            ARRAY[' MARYLAND ','MD'],
                            ARRAY[' MD ','MD'],
                            ARRAY['MICHIGAN','MI'],
                            ARRAY[' MI ','MI'],
                            ARRAY['MINNESOTA','MN'],
                            ARRAY[' MN ','MN'],
                            ARRAY[' MISSOURI ','MO'],
                            ARRAY[' MO ','MO'],
                            ARRAY[' NEBRASKA ','NE'],
                            ARRAY[' NE ','NE'],
                            ARRAY[' NEVADA ','NV'],
                            ARRAY[' NEVADA, ','NV'],
                            ARRAY[' NV ','NV'],
                            ARRAY[' NV. ','NV'],
                            ARRAY[' NORTH CAROLINA ','NC'],
                            ARRAY[' NC ','NC'],
                            ARRAY[' NORTH DAKOTA ','ND'],
                            ARRAY[' ND ','ND'],
                            ARRAY[' NEW YORK ','NY'],
                            ARRAY[' NY ','NY'],
                            ARRAY[' NY, ','NY'],
                            ARRAY[' OH ','OH'],
                            ARRAY[' OHIO,','OH'],
                            ARRAY[' OHIO ','OH'],
                            ARRAY[' OK ','OK'],
                            ARRAY[' OR. ','OR'],
                            ARRAY[' OR, ','OR'],
                            ARRAY[' OR ','OR'],
                            ARRAY[',OR ','OR'],
                            ARRAY[' OREGON ','OR'],
                            ARRAY[' ORGEON ','OR'],
                            ARRAY[', OREGON ','OR'],
                            ARRAY[' OREGON, ','OR'],
                            ARRAY[' OREGAN ','OR'],
                            ARRAY[', PA, ','PA'],
                            ARRAY[' PENNSYLVANIA ','PA'],
                            ARRAY[', PA, ','PA'],
                            ARRAY[' SOUTH CAROLINA ','SC'],
                            ARRAY[' SC ','SC'],
                            ARRAY[' TENNESSEE ','TN'],
                            ARRAY[' TENN. ','TN'],
                            ARRAY[' TN ','TN'],
                            ARRAY[' TEXAS ','TX'],
                            ARRAY[' TEXAS, ','TX'],
                            ARRAY[' TX ','TX'],
                            ARRAY[' TX. ','TX'],
                            ARRAY[' UT ','UT'],
                            ARRAY[' UTAH ','UT'],
                            ARRAY[' UTAH, ','UT'],
                            ARRAY[' VIRGINIA ','VA'],
                            ARRAY[' VIRGINIA, ','VA'],
                            ARRAY[' VA ','VA'],
                            ARRAY[' VERMONT ','VT'],
                            ARRAY[' VT ','VT'],
                            ARRAY[', WA ','WA'],
                            ARRAY[', WA. ','WA'],
                            ARRAY[' WA, ','WA'],
                            ARRAY[' WA ','WA'],
                            ARRAY[' WA ','WA'],
                            ARRAY[' WASHINGTON, DC ','DC'],
                            ARRAY[' DC ','DC'],
                            ARRAY[', WASHINGTON ','WA'],
                            ARRAY[' WAHINGTON ','WA'],
                            ARRAY[' WASHINGTON ','WA'],
                            ARRAY[' WASHINGTON,','WA'],
                            ARRAY[' WI ','WI'],
                            ARRAY[' WISCONSIN ','WI']];
  us_state text[];
begin
  -- Empty value do nothing.
  if v_text is null or v_text = '' then
    return '';
  -- Try Canada province codes first.
  else
     for i in 1 .. array_upper(bc_region, 1)
     loop
       if POSITION(bc_region[i] in v_text) > 0 then
         if v_replace then
           return bc_region[i];
         else
           return 'BC';
         end if;
       end if;
     end loop;
     for i in 1 .. array_upper(ab_region, 1)
     loop
       if POSITION(ab_region[i] in v_text) > 0 then
         if v_replace then
           return ab_region[i];
         else
           return 'AB';
         end if;
       end if;
     end loop;
     for i in 1 .. array_upper(sk_region, 1)
     loop
       if POSITION(sk_region[i] in v_text) > 0 then
         if v_replace then
           return sk_region[i];
         else
           return 'SK';
         end if;
       end if;
     end loop;
     for i in 1 .. array_upper(mb_region, 1)
     loop
       if POSITION(mb_region[i] in v_text) > 0 then
         if v_replace then
           return mb_region[i];
         else
           return 'MB';
         end if;
       end if;
     end loop;
     for i in 1 .. array_upper(on_region, 1)
     loop
       if POSITION(on_region[i] in v_text) > 0 then
         if v_replace then
           return on_region[i];
         else
           return 'ON';
         end if;
       end if;
     end loop;
     for i in 1 .. array_upper(qc_region, 1)
     loop
       if POSITION(qc_region[i] in v_text) > 0 then
         if v_replace then
           return qc_region[i];
         else
           return 'QC';
         end if;
       end if;
     end loop;
     for i in 1 .. array_upper(yt_region, 1)
     loop
       if POSITION(yt_region[i] in v_text) > 0 then
         if v_replace then
           return yt_region[i];
         else
           return 'YT';
         end if;
       end if;
     end loop;
     for i in 1 .. array_upper(nb_region, 1)
     loop
       if POSITION(nb_region[i] in v_text) > 0 then
         if v_replace then
           return nb_region[i];
         else
           return 'NB';
         end if;
       end if;
     end loop;
     for i in 1 .. array_upper(nl_region, 1)
     loop
       if POSITION(nl_region[i] in v_text) > 0 then
         if v_replace then
           return nl_region[i];
         else
           return 'NL';
         end if;
       end if;
     end loop;
     for i in 1 .. array_upper(ns_region, 1)
     loop
       if POSITION(ns_region[i] in v_text) > 0 then
         if v_replace then
           return ns_region[i];
         else
           return 'NS';
         end if;
       end if;
     end loop;
     for i in 1 .. array_upper(nt_region, 1)
     loop
       if POSITION(nt_region[i] in v_text) > 0 then
         if v_replace then
           return nt_region[i];
         else
           return 'NT';
         end if;
       end if;
     end loop;
     for i in 1 .. array_upper(nu_region, 1)
     loop
       if POSITION(nu_region[i] in v_text) > 0 then
         if v_replace then
           return nu_region[i];
         else
           return 'NU';
         end if;
       end if;
     end loop;
     for i in 1 .. array_upper(pe_region, 1)
     loop
       if POSITION(pe_region[i] in v_text) > 0 then
         if v_replace then
           return pe_region[i];
         else
           return 'PE';
         end if;
       end if;
     end loop;
     -- Try US states if get to here.
     foreach us_state slice 1 in array us_states
     loop
       if POSITION(us_state[1] in v_text) > 0 then
         if v_replace then
           return us_state[1];
         else
           return us_state[2];
         end if;
       end if;
     end loop;
  end if;
  return null;
end;
$$;

-- Try to extract/derive a country code from either the text or the region.
-- If replace is true, the matching value is returned if a match is found. It can then be removed from the address line.
create or replace function public.colin_hist_cars_country(v_text character varying,
                                                          v_region character varying,
                                                          v_replace boolean) returns character varying
  immutable
  language plpgsql
as $$
declare
  province_codes varchar(60) := ' BC AB SK MB ON QC PE YT NU NT NS NL NB ';
  state_codes varchar(200) := ' AK AR AZ CA CO CT FL GA HI ID IL IN KS KY LA MA MD MI MO MT MN ND NE NC NY NV OH OK OR PA SC' ||
                              'TN TX UT VA VT WA WI IA ME MO NH NJ NM ND PR RI SD VI WV WY ';
  countries text[] := ARRAY[ARRAY['U.S.A.', 'US'],
                            ARRAY['U.SA.','US'],
                            ARRAY[' USA ','US'],
                            ARRAY['USA ','US'],
                            ARRAY[' CA ','CA'],
                            ARRAY['CANADA','CA'],
                            ARRAY['BERMUDA','BM'],
                            ARRAY['BOTSWANA, AFRICA','BW'],
                            ARRAY['BOTSWANA','BW'],
                            ARRAY['ARMENIA','AM'],
                            ARRAY['AUSTRALIA','AU'],
                            ARRAY['AUSTRIA','AT'],
                            ARRAY['FRANCE UN','FR'],
                            ARRAY['FRANCE','FR'],
                            ARRAY['-GERMANY','DE'],
                            ARRAY['WEST GERMANY','DE'],
                            ARRAY['WEST GERMANU','DE'],
                            ARRAY['GERMANY','DE'],
                            ARRAY['HONG KONG ','HK'],
                            ARRAY['HONGKONG','HK'],
                            ARRAY[' HK ','HK'],
                            ARRAY['INDONESIA','ID'],
                            ARRAY['INDIA','IN'],
                            ARRAY['(ITALY) ITALIA','IT'],
                            ARRAY['JAPAN','JP'],
                            ARRAY['LATVIA','LV'],
                            ARRAY['MACAU','MO'],
                            ARRAY['MACAO','MO'],
                            ARRAY['MALTA','MT'],
                            ARRAY['MEXICO','MX'],
                            ARRAY['MALAYSIA','MY'],
                            ARRAY['MONGOLIA','MN'],
                            ARRAY['HOLLAND','NL'],
                            ARRAY['NETHERLANDS','NL'],
                            ARRAY['NETHERLAND','NL'],
                            ARRAY['NORWAY','NO'],
                            ARRAY['NEW ZEALAND','NZ'],
                            ARRAY['NORTHERN IRELAND','GB'],
                            ARRAY['PAPUA, NEW GUINEA','PG'],
                            ARRAY['PHILIPPINES','PH'],
                            ARRAY['PORTUGAL','PT'],
                            ARRAY['SCOTLAND','GB'],
                            ARRAY['SPAIN','ES'],
                            ARRAY[' SG ','SG'],
                            ARRAY['SWEDEN','SE'],
                            ARRAY['SWITZERLAND','CH'],
                            ARRAY['CHANNEL ISLANDS','GB'],
                            ARRAY['ENGLAND, UK','GB'],
                            ARRAY['ENGLABD','GB'],
                            ARRAY['ENGLAND','GB'],
                            ARRAY['U.A.E.','AE'],
                            ARRAY['UAE','AE'],
                            ARRAY['UNITED ARAB EMIRATES','AE'],
                            ARRAY['UNITED KINGDOM','GB'],
                            ARRAY['UNITED KINGDON','GB'],
                            ARRAY[' U.K. ','GB'],
                            ARRAY[' UK ','GB'],
                            ARRAY['VIETNAM','VN'],
                            ARRAY['ANGUILLA, BRITISH WEST INDIES','AI'],
                            ARRAY['TURKS AND CAICOS ISLANDSBRITISH WEST INDIES','TC']];
  country text[];
begin
  -- Empty value do nothing.
  if v_text is null or v_text = '' then
    return null;
  -- Try Canada province codes first.
  elsif v_region is not null and v_region != '' and POSITION(v_region in province_codes) > 0 then
    return 'CA';
  elsif v_region is not null and v_region != '' and POSITION(v_region in state_codes) > 0 then
    return 'US';
  else
     -- Try countries if get to here.
     foreach country slice 1 in array countries
     loop
       if POSITION(country[1] in v_text) > 0 then
         if v_replace then
           return country[1];
         else
           return country[2];
         end if;
       end if;
     end loop;
  end if;
  return null;
end;
$$;

-- Create carindiv table record addresses and addresses_version records.
-- Try to extract city, region, and country from the address lines.
create or replace function public.colin_hist_cars_address(p_business_id integer,
                                                          p_trans_id integer,
                                                          p_mailing_id integer,
                                                          p_delivery_id integer,
                                                          p_postal_code character varying,
                                                          p_line_1 character varying,
                                                          p_line_2 character varying,
                                                          p_line_3 character varying) returns integer
  language plpgsql
as $$
declare
  city varchar(40);
  region varchar(40);
  country varchar(40);
  line2 varchar(80); 
  temp varchar(100);
  replace_text varchar(40);
begin
  if p_line_3 is not null then
    line2 := p_line_2;
    temp := ' ' || p_line_3 || ' ';
    region := colin_hist_cars_region(temp, false);
    if region is not null then
      city := p_line_3;
      city := TRIM(REPLACE(city, colin_hist_cars_region(temp, true), ''));
    end if;
    country := colin_hist_cars_country(temp, region, false);    
  else
    line2 := null;
  end if;

  if p_line_3 is null or region is null then
    temp := ' ' || p_line_2 || ' ';
    region := colin_hist_cars_region(temp, false);
    if region is not null then
      city := p_line_2;
      city := TRIM(REPLACE(city, colin_hist_cars_region(temp, true), ''));
    end if;
    if country is null then
      country := colin_hist_cars_country(temp, region, false);
    end if;
  end if;

  if p_mailing_id is not null then
    insert into addresses_version
      values(p_mailing_id, 'mailing', p_line_1, line2, city,
             region, country, p_postal_code, null, p_business_id, p_trans_id, null, 0, null, null);
    insert into addresses
      values(p_mailing_id, 'mailing', p_line_1, line2, city,
             region, country, p_postal_code, null, p_business_id, null, null); 
  end if;

  if p_delivery_id is not null then
    insert into addresses_version
      values(p_delivery_id, 'delivery', p_line_1, line2, city,
             region, country, p_postal_code, null, p_business_id, p_trans_id, null, 0, null, null);
    insert into addresses
      values(p_delivery_id, 'delivery', p_line_1, line2, city,
             region, country, p_postal_code, null, p_business_id, null, null); 
  end if;

  return p_trans_id;
end;
$$;

--
-- Tombstone corp current officers add CARS officers that do not exist in the corp_party table.
-- Inserts into addresses, addresses_version, parties, parties_version, party_roles, party_roles_version.
-- The transaction ID should be the tombstone process transaction ID.
create or replace function public.colin_tombstone_cars_officer(p_colin_event_id integer,
                                                               p_business_id integer,
                                                               p_trans_id integer,
                                                               p_corp_num character varying) returns integer
  language plpgsql
as $$
declare
  cur_hist_officer cursor(v_colin_event_id integer, v_corp_num character varying)
     for select ci.surname as last_name,
                ci.firname as first_name,
                lower(ci.offtitle) as titles,
                case when ci.dircpoco is not null then left(ci.dircpoco, 3) || ' ' || right(ci.dircpoco, 3) else null end as postal_code,
                ci.dircaddr01 as line_1,
                case when ci.dircaddr03 is not null and ci.dircaddr04 is not null then ci.dircaddr02 || ' ' || ci.dircaddr03 else ci.dircaddr02 end as line_2,
                case when ci.dircaddr03 is not null and ci.dircaddr04 is not null then ci.dircaddr04 else ci.dircaddr03 end as line_3
           from colin_extract.conv_ledger cl, colin_extract.event e, colin_extract.carindiv ci, colin_event_ids ce, filings f, businesses b
          where e.corp_num = v_corp_num
            and e.event_id = v_colin_event_id
            and e.event_id = cl.event_id
            and e.event_id = ce.colin_event_id
            and cl.cars_docmnt_id = ci.documtid
            and ce.filing_id = f.id
            and f.business_id = b.id
            and b.identifier = e.corp_num
            and ci.offiflag = 'Y'
            and not exists (select cp.corp_party_id
                              from colin_extract.corp_party cp
                             where cp.corp_num = e.corp_num
                               and cp.party_typ_cd = 'OFF'
                               and cp.last_name = ci.surname
                               and cp.first_name = ci.firname)
            and exists (select f3.id from filings f3 where f3.business_id = b.id and f3.status = 'TOMBSTONE')
       order by b.identifier, e.event_id;

  rec_hist_officer record;
  party_id integer := 0;
  party_role_id integer := 0;
  mailing_id integer := 0;
  delivery_id integer := 0;
  titles varchar[];
  party_role varchar(30);
begin
  open cur_hist_officer(p_colin_event_id, p_corp_num);
  loop
    fetch cur_hist_officer into rec_hist_officer;
    exit when not found;
    mailing_id := nextval('addresses_id_seq');
    delivery_id := nextval('addresses_id_seq');
    party_id := nextval('parties_id_seq');
    perform colin_hist_cars_address(p_business_id,p_trans_id,mailing_id, delivery_id, rec_hist_officer.postal_code,
                                    rec_hist_officer.line_1, rec_hist_officer.line_2, rec_hist_officer.line_3); 
    insert into parties_version
      values(party_id, 'person', rec_hist_officer.first_name, null, rec_hist_officer.last_name, null,
             null, delivery_id, mailing_id, p_trans_id, null, 0, null, null, null);      
    insert into parties
      values(party_id, 'person', rec_hist_officer.first_name, null, rec_hist_officer.last_name, null,
             null, delivery_id, mailing_id, null, null, null);      

    titles := string_to_array(rec_hist_officer.titles, ',');
    for i in 1 .. array_upper(titles, 1)
    loop
      party_role := trim(replace(titles[i], 'vice president', 'vice_president'));
      party_role := trim(replace(party_role, 'other officer', 'other'));
      party_role := trim(replace(party_role, 'asst. secretary', 'assistant_secretary'));
      party_role_id := nextval('party_roles_id_seq');
      insert into party_roles_version 
        values(party_role_id, party_role, null,
               null, p_business_id, party_id, p_trans_id, null, 0, null, cast('OFFICER' as partyclasstype));
      insert into party_roles 
        values(party_role_id, party_role, null, null, p_business_id, party_id, null, cast('OFFICER' as partyclasstype));
    end loop;
  end loop;
  close cur_hist_officer;
  return p_trans_id;
end;
$$;

--
-- Tombstone corp current officers add an active officer.
-- Inserts into addresses, addresses_version, parties, parties_version, party_roles, party_roles_version.
-- The transaction ID should be the tombstone process transaction ID.
create or replace function public.colin_tombstone_officer(p_colin_event_id integer,
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
                     when cp.cessation_dt is null and (cp.prev_party_id is null or cp.prev_party_id < 1) and cp.end_event_id is not null then
                          (select cast((to_timestamp(to_char(e.event_timerstamp, 'YYYY-MM-DD') || ' 00:00:00', 'YYYY-MM-DD HH24:MI:SS') at time zone 'utc') as timestamp with time zone)
                             from colin_extract.event e
                            where e.event_id = cp.end_event_id)
                     else cp.cessation_dt end as cessation_dt,
                case when cp.last_name is not null and trim(cp.last_name) != '' then upper(cp.last_name) else null end as last_name,
                case when cp.middle_name is not null and trim(cp.middle_name) != '' then upper(cp.middle_name) else null end as middle_name,
                case when cp.first_name is not null and  trim(cp.first_name) != '' then upper(cp.first_name) else null end as first_name,
                case when cp.business_name is not null and  trim(cp.business_name) != '' then upper(cp.business_name) else null end as business_name,
                cp.email_address, cp.corp_party_id, cp.prev_party_id, cp.start_event_id, cp.end_event_id,
                (select cast((to_timestamp(to_char(e.event_timerstamp, 'YYYY-MM-DD') || ' 00:00:00', 'YYYY-MM-DD HH24:MI:SS') at time zone 'utc') as timestamp with time zone)
                   from colin_extract.event e
                  where e.event_id = v_colin_event_id) as party_date
          from colin_extract.corp_party cp 
        where cp.corp_num = v_corp_num
          and cp.start_event_id = v_colin_event_id
          and cp.party_typ_cd = 'OFF'
          and (cp.end_event_id is null or cp.cessation_dt is not null)
/*
          and not exists (select cp2.corp_party_id
                            from colin_extract.corp_party cp2
                           where cp2.corp_num = cp.corp_num
                             and cp2.party_typ_cd = cp.party_typ_cd
                             and cp2.prev_party_id is not null
                             and cp2.prev_party_id = cp.corp_party_id)
*/
        order by corp_party_id;
  cur_hist_officer_offices cursor(v_party_id integer)
    for select to_officer_role(officer_typ_cd) as party_role
      from colin_extract.offices_held
     where corp_party_id = v_party_id;
  rec_hist_party record;
  rec_hist_officer_office record;
  counter integer := 0;
  party_id integer := 0;
  party_role_id integer := 0;
begin
  open cur_hist_party(p_colin_event_id, p_corp_num);
  loop
    fetch cur_hist_party into rec_hist_party;
    exit when not found;
    counter := counter + 1;
    -- party_id := colin_hist_party_add(p_trans_id, p_business_id, null, rec_hist_party);
    party_id := nextval('parties_id_seq');
    perform colin_hist_party_change(p_business_id, p_trans_id, party_id, 0, rec_hist_party, null);
    open cur_hist_officer_offices(rec_hist_party.corp_party_id);
    loop
      fetch cur_hist_officer_offices into rec_hist_officer_office;          
      exit when not found;
      party_role_id := nextval('party_roles_id_seq');
      if rec_hist_party.appointment_dt is null then
        rec_hist_party.appointment_dt := rec_hist_party.party_date;
      end if;
      insert into party_roles_version 
        values(party_role_id, rec_hist_officer_office.party_role, rec_hist_party.appointment_dt, rec_hist_party.cessation_dt,
               p_business_id, party_id, p_trans_id, null, 0, null, cast('OFFICER' as partyclasstype));
      insert into party_roles 
        values(party_role_id, rec_hist_officer_office.party_role, rec_hist_party.appointment_dt, rec_hist_party.cessation_dt, 
               p_business_id, party_id, null, cast('OFFICER' as partyclasstype));
    end loop;
    close cur_hist_officer_offices;
  end loop;
  close cur_hist_party;
  return counter;
end;
$$;

-- Tombstone data patch to load current officers for previously migrated colin tombstone corps.
-- The colin_extract.corp_processing table defines the set of colin corps previously migrated.
-- It must accurately represent the environment load.
-- The return value is the number of corps updated. If the number is unexpected, verify the 
-- colin_extract.corp_processing and mig_corp_processing_history tables and rerun.
-- On success, mig_corp_processing_history.officer_tombstone_migrated is set to true for the corp.
-- Note: to reload a corp's active officers manually delete, including the mig_corp_processing_history table.
create or replace function public.colin_tombstone_officers(p_env character varying) returns integer
  language plpgsql
as $$
declare
  cur_outstanding_cars cursor(v_env character varying)
     for select distinct cp.id as corp_processing_id, b.id as business_id, b.identifier as corp_num, e.event_id as colin_event_id, 
                (select f2.transaction_id from filings f2 where f2.business_id = b.id and f2.status = 'TOMBSTONE') as transaction_id,
                (select count(cp2.corp_party_id)
                   from colin_extract.corp_party cp2
                  where cp2.corp_num = e.corp_num
                    and cp2.party_typ_cd = 'OFF'
                    and cp2.end_event_id is null) as exists_count
           from colin_extract.conv_ledger cl, colin_extract.event e, colin_extract.carindiv ci, colin_event_ids ce,
                filings f, businesses b,colin_extract.corp_processing cp
          where e.event_id = cl.event_id
            and e.event_id = ce.colin_event_id
            and cl.cars_docmnt_id = ci.documtid
            and ce.filing_id = f.id
            and f.business_id = b.id
            and b.identifier = e.corp_num
            and b.identifier = cp.corp_num
            and cp.environment = v_env
            and f.source = 'COLIN'
            and f.status = 'COMPLETED'
            and not exists (select mcph.corp_processing_id from mig_corp_processing_history mcph where mcph.corp_processing_id = cp.id)
            and ci.offiflag = 'Y'
            and not exists (select cp.corp_party_id
                              from colin_extract.corp_party cp
                             where cp.corp_num = e.corp_num
                               and cp.party_typ_cd = 'OFF'
                               and cp.last_name = ci.surname
                               and cp.first_name = ci.firname)
         order by b.identifier, e.event_id;
  cur_outstanding cursor(v_env character varying)
     for select distinct cp.id as corp_processing_id, b.id as business_id, b.identifier as corp_num, ce.colin_event_id,
                (select f2.transaction_id from filings f2 where f2.business_id = b.id and f2.status = 'TOMBSTONE') as transaction_id
           from businesses b, filings f, colin_event_ids ce, colin_extract.corp_processing cp, colin_extract.corp_party p
          where b.identifier = cp.corp_num
            and b.id = f.business_id
            and cp.processed_status = 'COMPLETED'
            and f.source = 'COLIN'
            and f.status = 'COMPLETED'
            and not exists (select pr.id from party_roles pr where pr.business_id = b.id and pr.party_class_type = 'OFFICER')
            and f.id = ce.filing_id
            and not exists (select mcph.corp_processing_id from mig_corp_processing_history mcph where mcph.corp_processing_id = cp.id)
            and cp.corp_num = p.corp_num
            and ce.colin_event_id = p.start_event_id
            and p.party_typ_cd = 'OFF'
            and cp.environment = v_env
       order by cp.id, ce.colin_event_id;
  rec_cars record;
  rec_officer record;
  update_counter integer := 0;
  previous_id integer := 0;
begin
  open cur_outstanding_cars(p_env);
  loop
    fetch cur_outstanding_cars into rec_cars;
    exit when not found;
    update_counter := update_counter + 1;
    perform colin_tombstone_cars_officer(cast(rec_cars.colin_event_id as integer),
                                         cast(rec_cars.business_id as integer),
                                         cast(rec_cars.transaction_id as integer),
                                         cast(rec_cars.corp_num as character varying));
    if previous_id != rec_cars.corp_processing_id then
      previous_id := rec_cars.corp_processing_id;
      if rec_cars.exists_count = 0 then
        insert into mig_corp_processing_history
          values(rec_cars.corp_processing_id, rec_cars.transaction_id, false, false, true, null, now());
      end if;
    end if;
  end loop;
  close cur_outstanding_cars;
  previous_id := 0;

  open cur_outstanding(p_env);
  loop
    fetch cur_outstanding into rec_officer;
    exit when not found;
    update_counter := update_counter + 1;
    perform colin_tombstone_officer(rec_officer.colin_event_id,
                                    rec_officer.business_id,
                                    cast(rec_officer.transaction_id as integer),
                                    rec_officer.corp_num);
    if previous_id != rec_officer.corp_processing_id then
      previous_id := rec_officer.corp_processing_id;
      insert into mig_corp_processing_history
        values(rec_officer.corp_processing_id, rec_officer.transaction_id, false, false, true, null, now());
    end if;
  end loop;
  close cur_outstanding;

  return update_counter;
end;
$$;
