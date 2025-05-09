vset cli.settings.ignore_errors=false
vset cli.settings.transfer_threads=8
vset format.date=YYYY-MM-dd'T'hh:mm:ss'Z'
vset format.timestamp=YYYY-MM-dd'T'hh:mm:ss'Z'

connect cprd_pg;

learn schema public;


-- disable triggers
ALTER TABLE corporation DISABLE TRIGGER ALL;
ALTER TABLE corp_name DISABLE TRIGGER ALL;
ALTER TABLE corp_state DISABLE TRIGGER ALL;
ALTER TABLE event DISABLE TRIGGER ALL;
ALTER TABLE filing DISABLE TRIGGER ALL;
ALTER TABLE filing_user DISABLE TRIGGER ALL;
ALTER TABLE office DISABLE TRIGGER ALL;
ALTER TABLE address DISABLE TRIGGER ALL;
ALTER TABLE corp_comments DISABLE TRIGGER ALL;
ALTER TABLE ledger_text DISABLE TRIGGER ALL;
ALTER TABLE corp_party DISABLE TRIGGER ALL;
ALTER TABLE corp_party_relationship DISABLE TRIGGER ALL;
ALTER TABLE offices_held DISABLE TRIGGER ALL;
ALTER TABLE completing_party DISABLE TRIGGER ALL;
ALTER TABLE submitting_party DISABLE TRIGGER ALL;
ALTER TABLE corp_flag DISABLE TRIGGER ALL;
ALTER TABLE cont_out DISABLE TRIGGER ALL;
ALTER TABLE conv_event DISABLE TRIGGER ALL;
ALTER TABLE conv_ledger DISABLE TRIGGER ALL;
ALTER TABLE corp_involved_amalgamating DISABLE TRIGGER ALL;
ALTER TABLE corp_involved_cont_in DISABLE TRIGGER ALL;
ALTER TABLE corp_restriction DISABLE TRIGGER ALL;
ALTER TABLE correction DISABLE TRIGGER ALL;
ALTER TABLE jurisdiction DISABLE TRIGGER ALL;
ALTER TABLE resolution DISABLE TRIGGER ALL;
ALTER TABLE share_series DISABLE TRIGGER ALL;
ALTER TABLE share_struct DISABLE TRIGGER ALL;
ALTER TABLE share_struct_cls DISABLE TRIGGER ALL;
ALTER TABLE notification DISABLE TRIGGER ALL;
ALTER TABLE notification_resend DISABLE TRIGGER ALL;
ALTER TABLE party_notification DISABLE TRIGGER ALL;


-- alter tables
alter table corporation alter column send_ar_ind type integer using send_ar_ind::integer;
alter table filing
   alter column arrangement_ind type integer using arrangement_ind::integer,
   alter column court_appr_ind type integer using court_appr_ind::integer;
alter table share_struct_cls
   alter column max_share_ind type integer using max_share_ind::integer,
   alter column spec_rights_ind type integer using spec_rights_ind::integer,
   alter column par_value_ind type integer using par_value_ind::integer;
alter table conv_event alter report_corp_ind type integer using report_corp_ind::integer;
alter table corp_involved_amalgamating alter adopted_corp_ind type integer using adopted_corp_ind::integer;
alter table corp_restriction alter restriction_ind type integer using restriction_ind::integer;
alter table share_series
   alter column max_share_ind type integer using max_share_ind::integer,
   alter column spec_right_ind type integer using spec_right_ind::integer;


-- corporation
transfer public.corporation from cprd using
with corporation_cte as (
    select c.*
        from corporation c
        where c.CORP_NUM not in (
            select c.corp_num
            from corporation c
                , event e
                , filing f
                , filing_user u
            where e.CORP_NUM = c.CORP_NUM
                and f.event_id = e.event_id
                and u.event_id = e.event_id
                and u.user_id = 'BCOMPS'
                and f.filing_typ_cd in ('BEINC', 'ICORP', 'ICORU', 'ICORC', 'CONTB', 'CONTI', 'CONTU', 'CONTC')
        )
        and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
        
         -- altered from BC to BEN then BEN to BC before directed launch
        and c.CORP_NUM not in ('0460007', '1255957', '1186381')
)
select case
           when c.CORP_TYP_CD in ('BC', 'ULC', 'CC') then 'BC' || c.CORP_NUM
           else c.CORP_NUM
       end CORP_NUM,
       CORP_FROZEN_TYP_CD as corp_frozen_type_cd,
       case
           when c.CORP_TYP_CD in ('QA', 'QB', 'QC', 'QD', 'QE') then 'BC'
           else c.CORP_TYP_CD
       end CORP_TYPE_CD,
       CORP_PASSWORD,
       RECOGNITION_DTS,
       BN_9,
       bn_15,
       admin_email,
       ACCESSION_NUM,
       LAST_AR_FILED_DT,
       case SEND_AR_IND
           when 'N' then 0
           when 'Y' then 1
           else 1
           end               SEND_AR_IND,
       (select
            to_number(to_char(max(date_1), 'YYYY'))
        from eml_log e, rep_data r
        where 
            e.corp_num=c.corp_num
            and e.param_id=r.param_id
            and e.corp_num=r.t20_1) as LAST_AR_REMINDER_YEAR
from corporation_cte c
order by corp_num;



-- event
transfer public.event from cprd using
with corporation_cte as (
    select c.*
        from corporation c
        where c.CORP_NUM not in (
            select c.corp_num
            from corporation c
                , event e
                , filing f
                , filing_user u
            where e.CORP_NUM = c.CORP_NUM
                and f.event_id = e.event_id
                and u.event_id = e.event_id
                and u.user_id = 'BCOMPS'
                and f.filing_typ_cd in ('BEINC', 'ICORP', 'ICORU', 'ICORC', 'CONTB', 'CONTI', 'CONTU', 'CONTC')
        )
        and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
        
         -- altered from BC to BEN then BEN to BC before directed launch
        and c.CORP_NUM not in ('0460007', '1255957', '1186381')
)
select e.event_id,
       case
           when c.CORP_TYP_CD in ('BC', 'ULC', 'CC') then 'BC' || c.CORP_NUM
           else c.CORP_NUM
       end CORP_NUM,
       e.event_typ_cd as event_type_cd,
       e.event_timestmp as event_timerstamp,
       e.trigger_dts
from event e
   , corporation_cte c
where c.corp_num = e.corp_num
  and event_typ_cd not in ('BNUPD','ADDLEDGR') --not doing anything
order by e.event_id desc;



-- corp_name
transfer public.corp_name from cprd using
with corporation_cte as (
    select c.*
        from corporation c
        where c.CORP_NUM not in (
            select c.corp_num
            from corporation c
                , event e
                , filing f
                , filing_user u
            where e.CORP_NUM = c.CORP_NUM
                and f.event_id = e.event_id
                and u.event_id = e.event_id
                and u.user_id = 'BCOMPS'
                and f.filing_typ_cd in ('BEINC', 'ICORP', 'ICORU', 'ICORC', 'CONTB', 'CONTI', 'CONTU', 'CONTC')
        )
        and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
        
         -- altered from BC to BEN then BEN to BC before directed launch
        and c.CORP_NUM not in ('0460007', '1255957', '1186381')
)
select case
           when c.CORP_TYP_CD in ('BC', 'ULC', 'CC') then 'BC' || c.CORP_NUM
           else c.CORP_NUM
       end CORP_NUM,
       cn.CORP_NAME_TYP_CD,
       cn.start_event_id,
       cn.end_event_id,
       cn.CORP_NME as corp_name
from CORP_NAME cn
   , corporation_cte c
where cn.corp_num = c.corp_num
order by c.corp_num, start_event_id;



-- corp_state
transfer public.corp_state from cprd using
with corporation_cte as (
    select c.*
        from corporation c
        where c.CORP_NUM not in (
            select c.corp_num
            from corporation c
                , event e
                , filing f
                , filing_user u
            where e.CORP_NUM = c.CORP_NUM
                and f.event_id = e.event_id
                and u.event_id = e.event_id
                and u.user_id = 'BCOMPS'
                and f.filing_typ_cd in ('BEINC', 'ICORP', 'ICORU', 'ICORC', 'CONTB', 'CONTI', 'CONTU', 'CONTC')
        )
        and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
        
         -- altered from BC to BEN then BEN to BC before directed launch
        and c.CORP_NUM not in ('0460007', '1255957', '1186381')
)
select case
           when c.CORP_TYP_CD in ('BC', 'ULC', 'CC') then 'BC' || c.CORP_NUM
           else c.CORP_NUM
       end CORP_NUM,
       cs.STATE_TYP_CD as state_type_cd,
       cos.op_state_typ_cd as op_state_type_cd,
       cs.start_event_id,
       cs.end_event_id
from CORP_STATE cs
   , corporation_cte c
   , corp_op_state cos
where cs.corp_num = c.corp_num
  and cos.state_typ_cd = cs.state_typ_cd
order by c.corp_num, start_event_id;



-- filing
transfer public.filing from cprd using
with corporation_cte as (
    select c.*
        from corporation c
        where c.CORP_NUM not in (
            select c.corp_num
            from corporation c
                , event e
                , filing f
                , filing_user u
            where e.CORP_NUM = c.CORP_NUM
                and f.event_id = e.event_id
                and u.event_id = e.event_id
                and u.user_id = 'BCOMPS'
                and f.filing_typ_cd in ('BEINC', 'ICORP', 'ICORU', 'ICORC', 'CONTB', 'CONTI', 'CONTU', 'CONTC')
        )
        and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
        
         -- altered from BC to BEN then BEN to BC before directed launch
        and c.CORP_NUM not in ('0460007', '1255957', '1186381')
)
select e.event_id,
       f.filing_typ_cd    as filing_type_cd,
       f.effective_dt,
       f.withdrawn_event_id,
       trim(f.ods_typ_cd) as ods_type_cd,
       f.nr_num,
       f.COURT_ORDER_NUM,
       f.CHANGE_DT,
       f.PERIOD_END_DT,
       case f.ARRANGEMENT_IND
           when 'N' then 0
           when 'Y' then 1
           else 1
           end               ARRANGEMENT_IND,
       f.AUTH_SIGN_DT,
       case f.COURT_APPR_IND
           when 'N' then 0
           when 'Y' then 1
           else 1
           end               COURT_APPR_IND
from event e
   , filing f
   , corporation_cte c
where e.event_id = f.event_id
  and c.corp_num = e.corp_num
order by e.event_id;



-- filing_user
transfer public.filing_user from cprd using
with corporation_cte as (
    select c.*
        from corporation c
        where c.CORP_NUM not in (
            select c.corp_num
            from corporation c
                , event e
                , filing f
                , filing_user u
            where e.CORP_NUM = c.CORP_NUM
                and f.event_id = e.event_id
                and u.event_id = e.event_id
                and u.user_id = 'BCOMPS'
                and f.filing_typ_cd in ('BEINC', 'ICORP', 'ICORU', 'ICORC', 'CONTB', 'CONTI', 'CONTU', 'CONTC')
        )
        and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
        
         -- altered from BC to BEN then BEN to BC before directed launch
        and c.CORP_NUM not in ('0460007', '1255957', '1186381')
)
select e.event_id,
       u.user_id,
       u.last_nme as last_name,
       u.first_nme as first_name,
       u.middle_nme as middle_name,
       u.email_addr,
       u.BCOL_ACCT_NUM,
       u.ROLE_TYP_CD
from event e
   , filing_user u
   , corporation_cte c
where e.event_id = u.event_id
  and c.corp_num = e.corp_num
order by e.event_id;



-- office
transfer public.office from cprd using
with corporation_cte as (
    select c.*
        from corporation c
        where c.CORP_NUM not in (
            select c.corp_num
            from corporation c
                , event e
                , filing f
                , filing_user u
            where e.CORP_NUM = c.CORP_NUM
                and f.event_id = e.event_id
                and u.event_id = e.event_id
                and u.user_id = 'BCOMPS'
                and f.filing_typ_cd in ('BEINC', 'ICORP', 'ICORU', 'ICORC', 'CONTB', 'CONTI', 'CONTU', 'CONTC')
        )
        and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
        
         -- altered from BC to BEN then BEN to BC before directed launch
        and c.CORP_NUM not in ('0460007', '1255957', '1186381')
)
select case
           when c.CORP_TYP_CD in ('BC', 'ULC', 'CC') then 'BC' || c.CORP_NUM
           else c.CORP_NUM
       end CORP_NUM,
       o.office_typ_cd,
       o.start_event_id,
       o.end_event_id,
       o.mailing_addr_id,
       o.delivery_addr_id
from office o
   , corporation_cte c
where o.corp_num = c.corp_num
order by c.corp_num, start_event_id;


vset cli.settings.transfer_threads=3
-- address
transfer public.address from cprd using
with corporation_cte as (
    select c.*
        from corporation c
        where c.CORP_NUM not in (
            select c.corp_num
            from corporation c
                , event e
                , filing f
                , filing_user u
            where e.CORP_NUM = c.CORP_NUM
                and f.event_id = e.event_id
                and u.event_id = e.event_id
                and u.user_id = 'BCOMPS'
                and f.filing_typ_cd in ('BEINC', 'ICORP', 'ICORU', 'ICORC', 'CONTB', 'CONTI', 'CONTU', 'CONTC')
        )
        and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
        
         -- altered from BC to BEN then BEN to BC before directed launch
        and c.CORP_NUM not in ('0460007', '1255957', '1186381')
)
select distinct ADDR_ID,
                PROVINCE,
                COUNTRY_TYP_CD,
                replace(POSTAL_CD, CHR(0), '') as POSTAL_CD,
                ADDR_LINE_1,
                replace(ADDR_LINE_2, CHR(0), '') as ADDR_LINE_2,
                ADDR_LINE_3,
                CITY
from (select a.*
      from address a
         , corp_party x
         , corporation_cte c
      where x.corp_num = c.corp_num
        and (delivery_addr_id = a.addr_id or mailing_addr_id = a.addr_id)
      UNION ALL
      select a.*
      from address a
         , office x
         , corporation_cte c
      where x.corp_num = c.corp_num
        and (delivery_addr_id = a.addr_id or mailing_addr_id = a.addr_id)
      UNION ALL
      select a.*
      from address a
         , completing_party x
         , corporation_cte c
         , event e
      where x.event_id = e.event_id
        and e.corp_num = c.corp_num
        and mailing_addr_id = a.addr_id
      UNION ALL
      select a.*
      from address a
         , notification x
         , corporation_cte c
         , event e
      where x.event_id = e.event_id
        and e.corp_num = c.corp_num
        and mailing_addr_id = a.addr_id
      UNION ALL
      select a.*
      from address a
         , submitting_party x
         , corporation_cte c
         , event e
      where x.event_id = e.event_id
        and e.corp_num = c.corp_num
        and (notify_addr_id = a.addr_id or mailing_addr_id = a.addr_id)
      UNION ALL
      select a.*
      from address a
         , party_notification x
         , corporation_cte c
         , corp_party p
      where x.party_id = p.corp_party_id
        and p.corp_num = c.corp_num
        and x.mailing_addr_id = a.addr_id
        )
order by addr_id;


vset cli.settings.transfer_threads=8
-- corp_comments
transfer public.corp_comments from cprd using
with corporation_cte as (
    select c.*
        from corporation c
        where c.CORP_NUM not in (
            select c.corp_num
            from corporation c
                , event e
                , filing f
                , filing_user u
            where e.CORP_NUM = c.CORP_NUM
                and f.event_id = e.event_id
                and u.event_id = e.event_id
                and u.user_id = 'BCOMPS'
                and f.filing_typ_cd in ('BEINC', 'ICORP', 'ICORU', 'ICORC', 'CONTB', 'CONTI', 'CONTU', 'CONTC')
        )
        and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
        
         -- altered from BC to BEN then BEN to BC before directed launch
        and c.CORP_NUM not in ('0460007', '1255957', '1186381')
)
select cc.comment_dts,
       case
           when c.CORP_TYP_CD in ('BC', 'ULC', 'CC') then 'BC' || c.CORP_NUM
           else c.CORP_NUM
       end CORP_NUM,
       cc.comments,
       cc.USER_ID,
       cc.FIRST_NME,
       cc.LAST_NME,
       cc.MIDDLE_NME,
       cc.ACCESSION_COMMENTS
from corp_comments cc
   , corporation_cte c
where c.corp_num = cc.corp_num
order by c.corp_num, comment_dts;



-- ledger_text
transfer public.ledger_text from cprd using
with corporation_cte as (
    select c.*
        from corporation c
        where c.CORP_NUM not in (
            select c.corp_num
            from corporation c
                , event e
                , filing f
                , filing_user u
            where e.CORP_NUM = c.CORP_NUM
                and f.event_id = e.event_id
                and u.event_id = e.event_id
                and u.user_id = 'BCOMPS'
                and f.filing_typ_cd in ('BEINC', 'ICORP', 'ICORU', 'ICORC', 'CONTB', 'CONTI', 'CONTU', 'CONTC')
        )
        and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
        
         -- altered from BC to BEN then BEN to BC before directed launch
        and c.CORP_NUM not in ('0460007', '1255957', '1186381')
)
select e.event_id,
       l.notation,
       l.USER_ID,
       l.LEDGER_TEXT_DTS
from ledger_text l
   , event e
   , corporation_cte c
where e.event_id = l.event_id
  and c.corp_num = e.corp_num
order by e.event_id;



-- corp_party
transfer public.corp_party from cprd using
with corporation_cte as (
    select c.*
        from corporation c
        where c.CORP_NUM not in (
            select c.corp_num
            from corporation c
                , event e
                , filing f
                , filing_user u
            where e.CORP_NUM = c.CORP_NUM
                and f.event_id = e.event_id
                and u.event_id = e.event_id
                and u.user_id = 'BCOMPS'
                and f.filing_typ_cd in ('BEINC', 'ICORP', 'ICORU', 'ICORC', 'CONTB', 'CONTI', 'CONTU', 'CONTC')
        )
        and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
        
         -- altered from BC to BEN then BEN to BC before directed launch
        and c.CORP_NUM not in ('0460007', '1255957', '1186381')
)
select p.corp_party_id,
       p.mailing_addr_id,
       p.delivery_addr_id,
       case
           when c.CORP_TYP_CD in ('BC', 'ULC', 'CC') then 'BC' || c.CORP_NUM
           else c.CORP_NUM
       end                     CORP_NUM,
       nvl(p.party_typ_cd, ' ') as party_typ_cd,
       p.start_event_id,
       p.end_event_id,
       p.prev_party_id,
       p.appointment_dt,
       p.cessation_dt,
       nvl(p.LAST_NME, ' ')     as last_name,
       nvl(p.MIDDLE_NME, ' ')   as middle_name,
       nvl(p.FIRST_NME, ' ')    as first_name,
       nvl(p.BUSINESS_NME, ' ') as business_name,
       p.BUS_COMPANY_NUM,
       p.CORR_TYP_CD,
       p.OFFICE_NOTIFICATION_DT
from corp_party p
   , corporation_cte c
where p.corp_num = c.corp_num
order by c.corp_num, corp_party_id;



-- corp_party_relationship
transfer public.CORP_PARTY_RELATIONSHIP from cprd using
with corporation_cte as (
    select c.*
        from corporation c
        where c.CORP_NUM not in (
            select c.corp_num
            from corporation c
                , event e
                , filing f
                , filing_user u
            where e.CORP_NUM = c.CORP_NUM
                and f.event_id = e.event_id
                and u.event_id = e.event_id
                and u.user_id = 'BCOMPS'
                and f.filing_typ_cd in ('BEINC', 'ICORP', 'ICORU', 'ICORC', 'CONTB', 'CONTI', 'CONTU', 'CONTC')
        )
        and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
        
         -- altered from BC to BEN then BEN to BC before directed launch
        and c.CORP_NUM not in ('0460007', '1255957', '1186381')
)
select cpr.CORP_PARTY_ID, cpr.RELATIONSHIP_TYP_CD
from CORP_PARTY_RELATIONSHIP cpr,
     corp_party p
        ,
     corporation_cte c
where p.corp_num = c.corp_num
  and cpr.corp_party_id = p.corp_party_id
order by c.corp_num, corp_party_id;



-- offices_held
transfer public.OFFICES_HELD from cprd using
with corporation_cte as (
    select c.*
        from corporation c
        where c.CORP_NUM not in (
            select c.corp_num
            from corporation c
                , event e
                , filing f
                , filing_user u
            where e.CORP_NUM = c.CORP_NUM
                and f.event_id = e.event_id
                and u.event_id = e.event_id
                and u.user_id = 'BCOMPS'
                and f.filing_typ_cd in ('BEINC', 'ICORP', 'ICORU', 'ICORC', 'CONTB', 'CONTI', 'CONTU', 'CONTC')
        )
        and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
        
         -- altered from BC to BEN then BEN to BC before directed launch
        and c.CORP_NUM not in ('0460007', '1255957', '1186381')
)
select oh.CORP_PARTY_ID, oh.OFFICER_TYP_CD
from OFFICES_HELD oh,
     corp_party p
        ,
     corporation_cte c
where p.corp_num = c.corp_num
  and oh.corp_party_id = p.corp_party_id
order by c.corp_num, corp_party_id;



-- completing_party
transfer public.completing_party from cprd using
with corporation_cte as (
    select c.*
        from corporation c
        where c.CORP_NUM not in (
            select c.corp_num
            from corporation c
                , event e
                , filing f
                , filing_user u
            where e.CORP_NUM = c.CORP_NUM
                and f.event_id = e.event_id
                and u.event_id = e.event_id
                and u.user_id = 'BCOMPS'
                and f.filing_typ_cd in ('BEINC', 'ICORP', 'ICORU', 'ICORC', 'CONTB', 'CONTI', 'CONTU', 'CONTC')
        )
        and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
        
         -- altered from BC to BEN then BEN to BC before directed launch
        and c.CORP_NUM not in ('0460007', '1255957', '1186381')
)
select e.event_id,
       cp.MAILING_ADDR_ID,
       cp.FIRST_NME,
       cp.LAST_NME,
       cp.MIDDLE_NME,
       cp.EMAIL_REQ_ADDRESS
from event e
   , completing_party cp
   , corporation_cte c
where e.event_id = cp.event_id
  and c.corp_num = e.corp_num
order by e.event_id;



-- submitting_party
transfer public.SUBMITTING_PARTY from cprd using
with corporation_cte as (
    select c.*
        from corporation c
        where c.CORP_NUM not in (
            select c.corp_num
            from corporation c
                , event e
                , filing f
                , filing_user u
            where e.CORP_NUM = c.CORP_NUM
                and f.event_id = e.event_id
                and u.event_id = e.event_id
                and u.user_id = 'BCOMPS'
                and f.filing_typ_cd in ('BEINC', 'ICORP', 'ICORU', 'ICORC', 'CONTB', 'CONTI', 'CONTU', 'CONTC')
        )
        and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
        
         -- altered from BC to BEN then BEN to BC before directed launch
        and c.CORP_NUM not in ('0460007', '1255957', '1186381')
)
select e.event_id,
       sp.MAILING_ADDR_ID,
       sp.NOTIFY_ADDR_ID,
       sp.METHOD_TYP_CD,
       sp.FIRST_NME,
       sp.LAST_NME,
       sp.MIDDLE_NME,
       sp.EMAIL_REQ_ADDRESS,
       sp.PICKUP_BY,
       sp.BUSINESS_NME,
       sp.NOTIFY_FIRST_NME,
       sp.NOTIFY_LAST_NME,
       sp.NOTIFY_MIDDLE_NME,
       sp.PHONE_NUMBER
from event e
   , SUBMITTING_PARTY sp
   , corporation_cte c
where e.event_id = sp.event_id
  and c.corp_num = e.corp_num
order by e.event_id;



-- corp_flag
transfer public.corp_flag from cprd using
with corporation_cte as (
    select c.*
        from corporation c
        where c.CORP_NUM not in (
            select c.corp_num
            from corporation c
                , event e
                , filing f
                , filing_user u
            where e.CORP_NUM = c.CORP_NUM
                and f.event_id = e.event_id
                and u.event_id = e.event_id
                and u.user_id = 'BCOMPS'
                and f.filing_typ_cd in ('BEINC', 'ICORP', 'ICORU', 'ICORC', 'CONTB', 'CONTI', 'CONTU', 'CONTC')
        )
        and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
        
         -- altered from BC to BEN then BEN to BC before directed launch
        and c.CORP_NUM not in ('0460007', '1255957', '1186381')
)
select case
           when c.CORP_TYP_CD in ('BC', 'ULC', 'CC') then 'BC' || c.CORP_NUM
           else c.CORP_NUM
       end CORP_NUM,
       cf.CORP_FLAG_TYPE_CD,
       cf.start_event_id,
       cf.end_event_id
from corp_flag cf
   , corporation_cte c
where cf.corp_num = c.corp_num
order by c.corp_num, cf.start_event_id;



-- cont_out
transfer public.CONT_OUT from cprd using
with corporation_cte as (
    select c.*
        from corporation c
        where c.CORP_NUM not in (
            select c.corp_num
            from corporation c
                , event e
                , filing f
                , filing_user u
            where e.CORP_NUM = c.CORP_NUM
                and f.event_id = e.event_id
                and u.event_id = e.event_id
                and u.user_id = 'BCOMPS'
                and f.filing_typ_cd in ('BEINC', 'ICORP', 'ICORU', 'ICORC', 'CONTB', 'CONTI', 'CONTU', 'CONTC')
        )
        and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
        
         -- altered from BC to BEN then BEN to BC before directed launch
        and c.CORP_NUM not in ('0460007', '1255957', '1186381')
)
select case
           when c.CORP_TYP_CD in ('BC', 'ULC', 'CC') then 'BC' || c.CORP_NUM
           else c.CORP_NUM
       end CORP_NUM,
       co.CAN_JUR_TYP_CD,
       co.CONT_OUT_DT,
       co.OTHR_JURI_DESC,
       co.HOME_COMPANY_NME,
       co.start_event_id,
       co.end_event_id
from CONT_OUT co
   , corporation_cte c
where co.corp_num = c.corp_num
order by c.corp_num, co.start_event_id;



-- conv_event
transfer public.CONV_EVENT from cprd using
with corporation_cte as (
    select c.*
        from corporation c
        where c.CORP_NUM not in (
            select c.corp_num
            from corporation c
                , event e
                , filing f
                , filing_user u
            where e.CORP_NUM = c.CORP_NUM
                and f.event_id = e.event_id
                and u.event_id = e.event_id
                and u.user_id = 'BCOMPS'
                and f.filing_typ_cd in ('BEINC', 'ICORP', 'ICORU', 'ICORC', 'CONTB', 'CONTI', 'CONTU', 'CONTC')
        )
        and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
        
         -- altered from BC to BEN then BEN to BC before directed launch
        and c.CORP_NUM not in ('0460007', '1255957', '1186381')
)
select e.event_id,
       ce.effective_dt,
       case ce.REPORT_CORP_IND
           when 'N' then 0
           when 'Y' then 1
           else 1
           end REPORT_CORP_IND,
       ce.ACTIVITY_USER_ID,
       ce.ACTIVITY_DT,
       ce.ANNUAL_FILE_DT,
       ce.ACCESSION_NUM,
       ce.REMARKS
from event e
   , CONV_EVENT ce
   , corporation_cte c
where e.event_id = ce.event_id
  and c.corp_num = e.corp_num
order by e.event_id;



-- conv_ledger
transfer public.CONV_LEDGER from cprd using
with corporation_cte as (
    select c.*
        from corporation c
        where c.CORP_NUM not in (
            select c.corp_num
            from corporation c
                , event e
                , filing f
                , filing_user u
            where e.CORP_NUM = c.CORP_NUM
                and f.event_id = e.event_id
                and u.event_id = e.event_id
                and u.user_id = 'BCOMPS'
                and f.filing_typ_cd in ('BEINC', 'ICORP', 'ICORU', 'ICORC', 'CONTB', 'CONTI', 'CONTU', 'CONTC')
        )
        and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
        
         -- altered from BC to BEN then BEN to BC before directed launch
        and c.CORP_NUM not in ('0460007', '1255957', '1186381')
)
select e.event_id,
    cl.LEDGER_TITLE_TXT,
    cl.LEDGER_DESC
from event e
   , CONV_LEDGER cl
   , corporation_cte c
where e.event_id = cl.event_id
  and c.corp_num = e.corp_num
order by e.event_id;



-- corp_involved - amalgamaTING_businesses
transfer public.corp_involved_amalgamating from cprd using
with corporation_cte as (
    select c.*
        from corporation c
        where c.CORP_NUM not in (
            select c.corp_num
            from corporation c
                , event e
                , filing f
                , filing_user u
            where e.CORP_NUM = c.CORP_NUM
                and f.event_id = e.event_id
                and u.event_id = e.event_id
                and u.user_id = 'BCOMPS'
                and f.filing_typ_cd in ('BEINC', 'ICORP', 'ICORU', 'ICORC', 'CONTB', 'CONTI', 'CONTU', 'CONTC')
        )
        and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
        
         -- altered from BC to BEN then BEN to BC before directed launch
        and c.CORP_NUM not in ('0460007', '1255957', '1186381')
)
select *
from (select e.event_id, -- SELECT BY EVENT
             case
                 when c.CORP_TYP_CD in ('BC', 'ULC', 'CC') then 'BC' || c.CORP_NUM
                 else c.CORP_NUM
             end TED_CORP_NUM,
             case
                 when c2.corp_typ_cd in ('BC', 'ULC', 'CC') then 'BC' || c2.corp_num
                 else c2.corp_num
             end TING_CORP_NUM,
             ci.CORP_INVOLVE_ID,
             ci.CAN_JUR_TYP_CD,
             case ci.ADOPTED_CORP_IND
                 when 'N' then 0
                 when 'Y' then 1
                 else 0
                 end ADOPTED_CORP_IND,
             ci.HOME_JURI_NUM,
             ci.OTHR_JURI_DESC,
             ci.FOREIGN_NME
      from event e
         , CORP_INVOLVED ci
         , corporation_cte c
        , corporation c2
      where e.event_id = ci.event_id
        and c.corp_num = e.corp_num
        and event_typ_cd = 'CONVAMAL'
        and c2.corp_num = ci.corp_num
      UNION ALL
      select e.event_id, -- SELECT BY FILING
             case
                 when c.CORP_TYP_CD in ('BC', 'ULC', 'CC') then 'BC' || c.CORP_NUM
                 else c.CORP_NUM
             end TED_CORP_NUM,
             case
	              when c2.corp_typ_cd in ('BC', 'ULC', 'CC') then 'BC' || c2.corp_num
	              else c2.corp_num
	          end TING_CORP_NUM,
             ci.CORP_INVOLVE_ID,
             ci.CAN_JUR_TYP_CD,
             case ci.ADOPTED_CORP_IND
                 when 'N' then 0
                 when 'Y' then 1
                 else 0
                 end ADOPTED_CORP_IND,
             ci.HOME_JURI_NUM,
             ci.OTHR_JURI_DESC,
             ci.FOREIGN_NME
      from event e
         , CORP_INVOLVED ci
         , corporation_cte c
         , corporation c2
         , filing f
      where e.event_id = ci.event_id
        and c.corp_num = e.corp_num
        and c2.corp_num = ci.corp_num
        and e.event_id = f.event_id
        and filing_typ_cd in ('AMALH', 'AMALV', 'AMALR', 'AMLHU', 'AMLVU', 'AMLRU', 'AMLHC', 'AMLVC', 'AMLRC')
     )
order by event_id;



-- corp_involved - continue_in_historical_xpro
transfer public.corp_involved_cont_in from cprd using
with corporation_cte as (
    select c.*
        from corporation c
        where c.CORP_NUM not in (
            select c.corp_num
            from corporation c
                , event e
                , filing f
                , filing_user u
            where e.CORP_NUM = c.CORP_NUM
                and f.event_id = e.event_id
                and u.event_id = e.event_id
                and u.user_id = 'BCOMPS'
                and f.filing_typ_cd in ('BEINC', 'ICORP', 'ICORU', 'ICORC', 'CONTB', 'CONTI', 'CONTU', 'CONTC')
        )
        and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
        
         -- altered from BC to BEN then BEN to BC before directed launch
        and c.CORP_NUM not in ('0460007', '1255957', '1186381')
)
select e.event_id,
       case
           when c.CORP_TYP_CD in ('BC', 'ULC', 'CC') then 'BC' || c.CORP_NUM
           else c.CORP_NUM
       end CORP_NUM
from event e
   , CORP_INVOLVED ci
   , corporation_cte c
   , filing f
where e.event_id = ci.event_id
  and c.corp_num = e.corp_num
  and e.event_id = f.event_id
  and filing_typ_cd in ('CONTI', 'CONTU', 'CONTC')
order by e.event_id;



-- corp_restriction
transfer public.CORP_RESTRICTION from cprd using
with corporation_cte as (
    select c.*
        from corporation c
        where c.CORP_NUM not in (
            select c.corp_num
            from corporation c
                , event e
                , filing f
                , filing_user u
            where e.CORP_NUM = c.CORP_NUM
                and f.event_id = e.event_id
                and u.event_id = e.event_id
                and u.user_id = 'BCOMPS'
                and f.filing_typ_cd in ('BEINC', 'ICORP', 'ICORU', 'ICORC', 'CONTB', 'CONTI', 'CONTU', 'CONTC')
        )
        and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
        
         -- altered from BC to BEN then BEN to BC before directed launch
        and c.CORP_NUM not in ('0460007', '1255957', '1186381')
)
select case
           when c.CORP_TYP_CD in ('BC', 'ULC', 'CC') then 'BC' || c.CORP_NUM
           else c.CORP_NUM
       end CORP_NUM,
       case cr.RESTRICTION_IND
           when 'N' then 0
           when 'Y' then 1
           else 0
           end RESTRICTION_IND,
       cr.start_event_id,
       cr.end_event_id
from CORP_RESTRICTION cr
   , corporation_cte c
where cr.corp_num = c.corp_num
order by c.corp_num, cr.start_event_id;



-- correction
transfer public.CORRECTION from cprd using
with corporation_cte as (
    select c.*
        from corporation c
        where c.CORP_NUM not in (
            select c.corp_num
            from corporation c
                , event e
                , filing f
                , filing_user u
            where e.CORP_NUM = c.CORP_NUM
                and f.event_id = e.event_id
                and u.event_id = e.event_id
                and u.user_id = 'BCOMPS'
                and f.filing_typ_cd in ('BEINC', 'ICORP', 'ICORU', 'ICORC', 'CONTB', 'CONTI', 'CONTU', 'CONTC')
        )
        and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
        
         -- altered from BC to BEN then BEN to BC before directed launch
        and c.CORP_NUM not in ('0460007', '1255957', '1186381')
)
select e.event_id,
       case
           when c.CORP_TYP_CD in ('BC', 'ULC', 'CC') then 'BC' || c.CORP_NUM
           else c.CORP_NUM
       end CORP_NUM,
       corr.ASSOCIATED_DOC_DESC
from event e
   , CORRECTION corr
   , corporation_cte c
where e.event_id = corr.event_id
  and c.corp_num = e.corp_num
order by e.event_id;



-- continued_in_from_jurisdiction
transfer public.jurisdiction from cprd using
with corporation_cte as (
    select c.*
        from corporation c
        where c.CORP_NUM not in (
            select c.corp_num
            from corporation c
                , event e
                , filing f
                , filing_user u
            where e.CORP_NUM = c.CORP_NUM
                and f.event_id = e.event_id
                and u.event_id = e.event_id
                and u.user_id = 'BCOMPS'
                and f.filing_typ_cd in ('BEINC', 'ICORP', 'ICORU', 'ICORC', 'CONTB', 'CONTI', 'CONTU', 'CONTC')
        )
        and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
        
         -- altered from BC to BEN then BEN to BC before directed launch
        and c.CORP_NUM not in ('0460007', '1255957', '1186381')
)
select case
           when c.CORP_TYP_CD in ('BC', 'ULC', 'CC') then 'BC' || c.CORP_NUM
           else c.CORP_NUM
       end CORP_NUM,
       j.CAN_JUR_TYP_CD,
       j.XPRO_TYP_CD,
       j.HOME_RECOGN_DT,
       j.OTHR_JURIS_DESC,
       j.HOME_JURIS_NUM,
       j.BC_XPRO_NUM,
       j.HOME_COMPANY_NME,
       j.start_event_id
from JURISDICTION j
   , corporation_cte c
where j.corp_num = c.corp_num
order by c.corp_num, j.start_event_id;



-- resolution
transfer public.RESOLUTION from cprd using
with corporation_cte as (
    select c.*
        from corporation c
        where c.CORP_NUM not in (
            select c.corp_num
            from corporation c
                , event e
                , filing f
                , filing_user u
            where e.CORP_NUM = c.CORP_NUM
                and f.event_id = e.event_id
                and u.event_id = e.event_id
                and u.user_id = 'BCOMPS'
                and f.filing_typ_cd in ('BEINC', 'ICORP', 'ICORU', 'ICORC', 'CONTB', 'CONTI', 'CONTU', 'CONTC')
        )
        and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
        
         -- altered from BC to BEN then BEN to BC before directed launch
        and c.CORP_NUM not in ('0460007', '1255957', '1186381')
)
select case
           when c.CORP_TYP_CD in ('BC', 'ULC', 'CC') then 'BC' || c.CORP_NUM
           else c.CORP_NUM
       end CORP_NUM,
       r.RESOLUTION_DT,
       r.RESOLUTION_TYPE_CODE,
       r.start_event_id,
       r.end_event_id
from RESOLUTION r
   , corporation_cte c
where r.corp_num = c.corp_num
order by c.corp_num, r.start_event_id;



-- share_struct
transfer public.SHARE_STRUCT from cprd using
with corporation_cte as (
    select c.*
        from corporation c
        where c.CORP_NUM not in (
            select c.corp_num
            from corporation c
                , event e
                , filing f
                , filing_user u
            where e.CORP_NUM = c.CORP_NUM
                and f.event_id = e.event_id
                and u.event_id = e.event_id
                and u.user_id = 'BCOMPS'
                and f.filing_typ_cd in ('BEINC', 'ICORP', 'ICORU', 'ICORC', 'CONTB', 'CONTI', 'CONTU', 'CONTC')
        )
        and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
        
         -- altered from BC to BEN then BEN to BC before directed launch
        and c.CORP_NUM not in ('0460007', '1255957', '1186381')
)
select case
           when c.CORP_TYP_CD in ('BC', 'ULC', 'CC') then 'BC' || c.CORP_NUM
           else c.CORP_NUM
       end CORP_NUM,
       ss.start_event_id,
       ss.end_event_id
from SHARE_STRUCT ss
   , corporation_cte c
where ss.corp_num = c.corp_num
order by c.corp_num, ss.start_event_id;



--share_struct_cls
transfer public.SHARE_STRUCT_CLS from cprd using
with corporation_cte as (
    select c.*
        from corporation c
        where c.CORP_NUM not in (
            select c.corp_num
            from corporation c
                , event e
                , filing f
                , filing_user u
            where e.CORP_NUM = c.CORP_NUM
                and f.event_id = e.event_id
                and u.event_id = e.event_id
                and u.user_id = 'BCOMPS'
                and f.filing_typ_cd in ('BEINC', 'ICORP', 'ICORU', 'ICORC', 'CONTB', 'CONTI', 'CONTU', 'CONTC')
        )
        and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
        
         -- altered from BC to BEN then BEN to BC before directed launch
        and c.CORP_NUM not in ('0460007', '1255957', '1186381')
)
select case
           when c.CORP_TYP_CD in ('BC', 'ULC', 'CC') then 'BC' || c.CORP_NUM
           else c.CORP_NUM
       end CORP_NUM,
       ssc.SHARE_CLASS_ID,
       replace(ssc.CLASS_NME, CHR(0), '') as CLASS_NME,
       ssc.CURRENCY_TYP_CD,
       case ssc.MAX_SHARE_IND
           when 'N' then 0
           when 'Y' then 1
           else 0
           end MAX_SHARE_IND,
       ssc.SHARE_QUANTITY,
       case ssc.SPEC_RIGHTS_IND
           when 'N' then 0
           when 'Y' then 1
           else 0
           end SPEC_RIGHTS_IND,
       case ssc.PAR_VALUE_IND
           when 'N' then 0
           when 'Y' then 1
           else 0
           end PAR_VALUE_IND,
       ssc.PAR_VALUE_AMT,
       ssc.OTHER_CURRENCY,
       ssc.start_event_id
from SHARE_STRUCT_CLS ssc
   , corporation_cte c
where ssc.corp_num = c.corp_num
order by c.corp_num, ssc.start_event_id;



--share_series
transfer public.SHARE_SERIES from cprd using
with corporation_cte as (
    select c.*
        from corporation c
        where c.CORP_NUM not in (
            select c.corp_num
            from corporation c
                , event e
                , filing f
                , filing_user u
            where e.CORP_NUM = c.CORP_NUM
                and f.event_id = e.event_id
                and u.event_id = e.event_id
                and u.user_id = 'BCOMPS'
                and f.filing_typ_cd in ('BEINC', 'ICORP', 'ICORU', 'ICORC', 'CONTB', 'CONTI', 'CONTU', 'CONTC')
        )
        and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
        
         -- altered from BC to BEN then BEN to BC before directed launch
        and c.CORP_NUM not in ('0460007', '1255957', '1186381')
)
select case
           when c.CORP_TYP_CD in ('BC', 'ULC', 'CC') then 'BC' || c.CORP_NUM
           else c.CORP_NUM
       end CORP_NUM,
       ss.SHARE_CLASS_ID,
       ss.SERIES_ID,
       case ss.MAX_SHARE_IND
           when 'N' then 0
           when 'Y' then 1
           else 0
           end MAX_SHARE_IND,
       ss.SHARE_QUANTITY,
       case ss.SPEC_RIGHT_IND
           when 'N' then 0
           when 'Y' then 1
           else 0
           end SPEC_RIGHT_IND,
       ss.SERIES_NME,
       ss.start_event_id
from SHARE_SERIES ss
   , corporation_cte c
where ss.corp_num = c.corp_num
order by c.corp_num, ss.start_event_id;



-- notification
transfer public.NOTIFICATION from cprd using
with corporation_cte as (
    select c.*
        from corporation c
        where c.CORP_NUM not in (
            select c.corp_num
            from corporation c
                , event e
                , filing f
                , filing_user u
            where e.CORP_NUM = c.CORP_NUM
                and f.event_id = e.event_id
                and u.event_id = e.event_id
                and u.user_id = 'BCOMPS'
                and f.filing_typ_cd in ('BEINC', 'ICORP', 'ICORU', 'ICORC', 'CONTB', 'CONTI', 'CONTU', 'CONTC')
        )
        and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
        
         -- altered from BC to BEN then BEN to BC before directed launch
        and c.CORP_NUM not in ('0460007', '1255957', '1186381')
)
select e.event_id,
       n.METHOD_TYP_CD,
       n.mailing_addr_id,
       n.FIRST_NME,
       n.LAST_NME,
       n.MIDDLE_NME,
       n.PICKUP_BY,
       n.EMAIL_ADDRESS,
       n.PHONE_NUMBER
from event e
   , NOTIFICATION n
   , corporation_cte c
where e.event_id = n.event_id
  and c.corp_num = e.corp_num
order by e.event_id;



-- notification_resend
transfer public.NOTIFICATION_RESEND from cprd using
with corporation_cte as (
    select c.*
        from corporation c
        where c.CORP_NUM not in (
            select c.corp_num
            from corporation c
                , event e
                , filing f
                , filing_user u
            where e.CORP_NUM = c.CORP_NUM
                and f.event_id = e.event_id
                and u.event_id = e.event_id
                and u.user_id = 'BCOMPS'
                and f.filing_typ_cd in ('BEINC', 'ICORP', 'ICORU', 'ICORC', 'CONTB', 'CONTI', 'CONTU', 'CONTC')
        )
        and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
        
         -- altered from BC to BEN then BEN to BC before directed launch
        and c.CORP_NUM not in ('0460007', '1255957', '1186381')
)
select e.event_id,
       nr.METHOD_TYP_CD,
       nr.mailing_addr_id,
       nr.FIRST_NME,
       nr.LAST_NME,
       nr.MIDDLE_NME,
       nr.PICKUP_BY,
       nr.EMAIL_ADDRESS,
       nr.PHONE_NUMBER
from event e
   , NOTIFICATION_RESEND nr
   , corporation_cte c
where e.event_id = nr.event_id
  and c.corp_num = e.corp_num
order by e.event_id;



-- party_notification
transfer public.PARTY_NOTIFICATION from cprd using
with corporation_cte as (
    select c.*
        from corporation c
        where c.CORP_NUM not in (
            select c.corp_num
            from corporation c
                , event e
                , filing f
                , filing_user u
            where e.CORP_NUM = c.CORP_NUM
                and f.event_id = e.event_id
                and u.event_id = e.event_id
                and u.user_id = 'BCOMPS'
                and f.filing_typ_cd in ('BEINC', 'ICORP', 'ICORU', 'ICORC', 'CONTB', 'CONTI', 'CONTU', 'CONTC')
        )
        and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
        
         -- altered from BC to BEN then BEN to BC before directed launch
        and c.CORP_NUM not in ('0460007', '1255957', '1186381')
)
select pn.PARTY_ID,
       pn.METHOD_TYP_CD,
       pn.mailing_addr_id,
       pn.FIRST_NME,
       pn.LAST_NME,
       pn.MIDDLE_NME,
       pn.BUSINESS_NME,
       pn.PICKUP_BY,
       pn.EMAIL_ADDRESS,
       pn.PHONE_NUMBER
from corp_party cp
   , PARTY_NOTIFICATION pn
   , corporation_cte c
where cp.CORP_PARTY_ID = pn.party_id
  and c.corp_num = cp.corp_num
order by c.corp_num;



-- payment
transfer public.payment from cprd using
with corporation_cte as (
    select c.*
        from corporation c
        where c.CORP_NUM not in (
            select c.corp_num
            from corporation c
                , event e
                , filing f
                , filing_user u
            where e.CORP_NUM = c.CORP_NUM
                and f.event_id = e.event_id
                and u.event_id = e.event_id
                and u.user_id = 'BCOMPS'
                and f.filing_typ_cd in ('BEINC', 'ICORP', 'ICORU', 'ICORC', 'CONTB', 'CONTI', 'CONTU', 'CONTC')
        )
        and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
        
         -- altered from BC to BEN then BEN to BC before directed launch
        and c.CORP_NUM not in ('0460007', '1255957', '1186381')
)
select p.event_id,
       p.payment_typ_cd,
       p.cc_holder_nme
from payment p
   , event e
   , corporation_cte c
where p.event_id = e.event_id
and e.corp_num = c.corp_num
order by e.event_id;



-- alter tables
alter table corporation alter column send_ar_ind type boolean using send_ar_ind::boolean;
alter table filing
   alter column arrangement_ind type boolean using arrangement_ind::boolean,
   alter column court_appr_ind type boolean using court_appr_ind::boolean;
alter table share_struct_cls
   alter column max_share_ind type boolean using max_share_ind::boolean,
   alter column spec_rights_ind type boolean using spec_rights_ind::boolean,
   alter column par_value_ind type boolean using par_value_ind::boolean;
alter table conv_event alter report_corp_ind type boolean using report_corp_ind::boolean;
alter table corp_involved_amalgamating alter adopted_corp_ind type boolean using adopted_corp_ind::boolean;
alter table corp_restriction alter restriction_ind type boolean using restriction_ind::boolean;
alter table share_series
   alter column max_share_ind type boolean using max_share_ind::boolean,
   alter column spec_right_ind type boolean using spec_right_ind::boolean;


-- enable triggers
ALTER TABLE corporation ENABLE TRIGGER ALL;
ALTER TABLE corp_name ENABLE TRIGGER ALL;
ALTER TABLE corp_state ENABLE TRIGGER ALL;
ALTER TABLE event ENABLE TRIGGER ALL;
ALTER TABLE filing ENABLE TRIGGER ALL;
ALTER TABLE filing_user ENABLE TRIGGER ALL;
ALTER TABLE office ENABLE TRIGGER ALL;
ALTER TABLE address ENABLE TRIGGER ALL;
ALTER TABLE corp_comments ENABLE TRIGGER ALL;
ALTER TABLE ledger_text ENABLE TRIGGER ALL;
ALTER TABLE corp_party ENABLE TRIGGER ALL;
ALTER TABLE corp_party_relationship ENABLE TRIGGER ALL;
ALTER TABLE offices_held ENABLE TRIGGER ALL;
ALTER TABLE completing_party ENABLE TRIGGER ALL;
ALTER TABLE submitting_party ENABLE TRIGGER ALL;
ALTER TABLE corp_flag ENABLE TRIGGER ALL;
ALTER TABLE cont_out ENABLE TRIGGER ALL;
ALTER TABLE conv_event ENABLE TRIGGER ALL;
ALTER TABLE conv_ledger ENABLE TRIGGER ALL;
ALTER TABLE corp_involved_amalgamating ENABLE TRIGGER ALL;
ALTER TABLE corp_involved_cont_in ENABLE TRIGGER ALL;
ALTER TABLE corp_restriction ENABLE TRIGGER ALL;
ALTER TABLE correction ENABLE TRIGGER ALL;
ALTER TABLE jurisdiction ENABLE TRIGGER ALL;
ALTER TABLE resolution ENABLE TRIGGER ALL;
ALTER TABLE share_series ENABLE TRIGGER ALL;
ALTER TABLE share_struct ENABLE TRIGGER ALL;
ALTER TABLE share_struct_cls ENABLE TRIGGER ALL;
ALTER TABLE notification ENABLE TRIGGER ALL;
ALTER TABLE notification_resend ENABLE TRIGGER ALL;
ALTER TABLE party_notification ENABLE TRIGGER ALL;
