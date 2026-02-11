-- Transfer a chunk (or a whole subset) of corps from the SOURCE Oracle DB (cprd) into the TARGET Postgres extract DB (cprd_pg).
--
-- REQUIRED DbSchemaCLI variables (replace_variables=true):
--   target_corp_num_predicate : SQL predicate restricting the computed target_corp_num (NO trailing semicolon).
--                              Examples:
--                                target_corp_num in ('BC0460007','A1234567')
--                                (target_corp_num in (...) OR target_corp_num in (...))
--   oracle_corp_num_predicate : SQL predicate restricting Oracle corporation.corp_num (NO trailing semicolon).
--                              Examples:
--                                c.CORP_NUM in ('0460007','A1234567')
--                                (c.CORP_NUM in (...) OR c.CORP_NUM in (...))
--
-- Intended to be executed from a master DbSchemaCLI script connected to the target Postgres DB (cprd_pg).
--
-- IMPORTANT:
-- - This template intentionally avoids the boolean<->integer ALTER COLUMN hacks used in the full refresh script.
--   Instead, Oracle SELECTs emit boolean-friendly 't'/'f' strings for Postgres boolean columns.
-- - This template transfers corp-scoped tables only (no cars* tables).
--
-- Performance notes:
-- - BCOMPS exclusion is NOT computed in Oracle in this template (to avoid repeating expensive Oracle-side joins per table).
--   Instead, load the requested corp set and purge BCOMPS-excluded corps ONCE in Postgres after the transfer suite completes
--   (see: subset_pg_purge_bcomps_excluded.sql).
-- - Joins are written to start from the subset (corporation_cte) to avoid "0 rows but slow" plans.
-- - ORDER BY clauses are removed (sorting is unnecessary overhead for transfers).
--
-- Example (legacy vset mode):
-- vset target_corp_num_predicate=target_corp_num in ('BC1111585','BC1226175');
-- vset oracle_corp_num_predicate=c.CORP_NUM in ('1111585','1226175');


-- corporation
transfer public.corporation from cprd using
with corp_list as (
	select /*+ materialize */ c.corp_num
	from corporation c
	where &oracle_corp_num_predicate
		and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
		-- altered from BC to BEN then BEN to BC before directed launch
		and c.CORP_NUM not in ('0460007', '1255957', '1186381')
),
corporation_cte as (
	select *
	from (
		select c.*,
				case
					when c.CORP_TYP_CD in ('BC', 'ULC', 'CC') then 'BC' || c.CORP_NUM
					else c.CORP_NUM
				end as target_corp_num
		from corporation c
		join corp_list cl on cl.corp_num = c.corp_num
	)
	where &target_corp_num_predicate
),
last_ar as (
	select e.corp_num,
			to_number(to_char(max(date_1), 'YYYY')) as last_ar_reminder_year
	from eml_log e
	join rep_data r on r.param_id = e.param_id
		and r.t20_1 = e.corp_num
	join corp_list cl on cl.corp_num = e.corp_num
	group by e.corp_num
)
select c.target_corp_num as CORP_NUM,
		c.CORP_FROZEN_TYP_CD as corp_frozen_type_cd,
		case
			when c.CORP_TYP_CD in ('QA', 'QB', 'QC', 'QD', 'QE') then 'BC'
			else c.CORP_TYP_CD
			end as CORP_TYPE_CD,
		c.CORP_PASSWORD,
		c.RECOGNITION_DTS,
		c.BN_9,
		c.BN_15,
		c.ADMIN_EMAIL,
		c.ACCESSION_NUM,
		c.LAST_AR_FILED_DT,
		case c.SEND_AR_IND
			when 'N' then 'f'
			when 'Y' then 't'
			else 't'
			end as SEND_AR_IND,
		la.last_ar_reminder_year as LAST_AR_REMINDER_YEAR
from corporation_cte c
left join last_ar la on la.corp_num = c.corp_num;


-- event
transfer public.event from cprd using
with corp_list as (
	select /*+ materialize */ c.corp_num
	from corporation c
	where &oracle_corp_num_predicate
		and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
		and c.CORP_NUM not in ('0460007', '1255957', '1186381')
),
corporation_cte as (
    select *
    from (
		select c.*,
				case
					when c.CORP_TYP_CD in ('BC', 'ULC', 'CC') then 'BC' || c.CORP_NUM
					else c.CORP_NUM
				end as target_corp_num
		from corporation c
		join corp_list cl on cl.corp_num = c.corp_num
	)
	where &target_corp_num_predicate
)
select e.event_id,
       c.target_corp_num as CORP_NUM,
       e.event_typ_cd as event_type_cd,
       e.event_timestmp as event_timerstamp,
       e.trigger_dts
from corporation_cte c
join event e on e.corp_num = c.corp_num
-- not transferring BNUPD, ADDLEDGR events
where e.event_typ_cd not in ('BNUPD', 'ADDLEDGR');


-- corp_name
transfer public.corp_name from cprd using
with corp_list as (
	select /*+ materialize */ c.corp_num
	from corporation c
	where &oracle_corp_num_predicate
		and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
		and c.CORP_NUM not in ('0460007', '1255957', '1186381')
),
corporation_cte as (
    select *
    from (
		select c.*,
				case
					when c.CORP_TYP_CD in ('BC', 'ULC', 'CC') then 'BC' || c.CORP_NUM
					else c.CORP_NUM
				end as target_corp_num
		from corporation c
		join corp_list cl on cl.corp_num = c.corp_num
	)
	where &target_corp_num_predicate
)
select c.target_corp_num as CORP_NUM,
       cn.CORP_NAME_TYP_CD,
       cn.start_event_id,
       cn.end_event_id,
       cn.CORP_NME as corp_name
from corporation_cte c
join CORP_NAME cn on cn.corp_num = c.corp_num;


-- corp_state
transfer public.corp_state from cprd using
with corp_list as (
	select /*+ materialize */ c.corp_num
	from corporation c
	where &oracle_corp_num_predicate
		and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
		and c.CORP_NUM not in ('0460007', '1255957', '1186381')
),
corporation_cte as (
    select *
    from (
		select c.*,
				case
					when c.CORP_TYP_CD in ('BC', 'ULC', 'CC') then 'BC' || c.CORP_NUM
					else c.CORP_NUM
				end as target_corp_num
		from corporation c
		join corp_list cl on cl.corp_num = c.corp_num
	)
	where &target_corp_num_predicate
)
select c.target_corp_num as CORP_NUM,
       cs.STATE_TYP_CD as state_type_cd,
       cos.op_state_typ_cd as op_state_type_cd,
       cs.start_event_id,
       cs.end_event_id
from corporation_cte c
join CORP_STATE cs on cs.corp_num = c.corp_num
join corp_op_state cos on cos.state_typ_cd = cs.state_typ_cd;


-- filing
transfer public.filing from cprd using
with corp_list as (
	select /*+ materialize */ c.corp_num
	from corporation c
	where &oracle_corp_num_predicate
		and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
		and c.CORP_NUM not in ('0460007', '1255957', '1186381')
),
corporation_cte as (
    select *
    from (
		select c.*,
				case
					when c.CORP_TYP_CD in ('BC', 'ULC', 'CC') then 'BC' || c.CORP_NUM
					else c.CORP_NUM
				end as target_corp_num
		from corporation c
		join corp_list cl on cl.corp_num = c.corp_num
	)
	where &target_corp_num_predicate
)
select e.event_id,
		f.filing_typ_cd as filing_type_cd,
       f.effective_dt,
       f.withdrawn_event_id,
       trim(f.ods_typ_cd) as ods_type_cd,
       f.nr_num,
       f.COURT_ORDER_NUM,
       f.CHANGE_DT,
       f.PERIOD_END_DT,
       case f.ARRANGEMENT_IND
           when 'N' then 'f'
           when 'Y' then 't'
           else 't'
			end as ARRANGEMENT_IND,
       f.AUTH_SIGN_DT,
       case f.COURT_APPR_IND
           when 'N' then 'f'
           when 'Y' then 't'
           else 't'
			end as COURT_APPR_IND
from corporation_cte c
join event e on e.corp_num = c.corp_num
join filing f on f.event_id = e.event_id;


-- filing_user
transfer public.filing_user from cprd using
with corp_list as (
	select /*+ materialize */ c.corp_num
	from corporation c
	where &oracle_corp_num_predicate
		and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
		and c.CORP_NUM not in ('0460007', '1255957', '1186381')
),
corporation_cte as (
    select *
    from (
		select c.*,
				case
					when c.CORP_TYP_CD in ('BC', 'ULC', 'CC') then 'BC' || c.CORP_NUM
					else c.CORP_NUM
				end as target_corp_num
		from corporation c
		join corp_list cl on cl.corp_num = c.corp_num
	)
	where &target_corp_num_predicate
)
select e.event_id,
       u.user_id,
       u.last_nme as last_name,
       u.first_nme as first_name,
       u.middle_nme as middle_name,
       u.email_addr,
       u.BCOL_ACCT_NUM,
       u.ROLE_TYP_CD
from corporation_cte c
join event e on e.corp_num = c.corp_num
join filing_user u on u.event_id = e.event_id;


-- address (must load before office and corp_party which reference address via FK)
transfer public.address from cprd using
with corp_list as (
	select /*+ materialize */ c.corp_num
	from corporation c
	where &oracle_corp_num_predicate
		and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
		and c.CORP_NUM not in ('0460007', '1255957', '1186381')
),
corporation_cte as (
    select *
    from (
		select c.*,
				case
					when c.CORP_TYP_CD in ('BC', 'ULC', 'CC') then 'BC' || c.CORP_NUM
					else c.CORP_NUM
				end as target_corp_num
		from corporation c
		join corp_list cl on cl.corp_num = c.corp_num
	)
	where &target_corp_num_predicate
)
select distinct
		addr_id,
		province,
		country_typ_cd,
		replace(postal_cd, CHR(0), '') as POSTAL_CD,
		addr_line_1,
		replace(addr_line_2, CHR(0), '') as ADDR_LINE_2,
		addr_line_3,
		city
from (
	select a.*
	from corporation_cte c
	join corp_party x on x.corp_num = c.corp_num
	join address a on (x.delivery_addr_id = a.addr_id or x.mailing_addr_id = a.addr_id)

	UNION ALL
	select a.*
	from corporation_cte c
	join office x on x.corp_num = c.corp_num
	join address a on (x.delivery_addr_id = a.addr_id or x.mailing_addr_id = a.addr_id)

	UNION ALL
	select a.*
	from corporation_cte c
	join event e on e.corp_num = c.corp_num
	join completing_party x on x.event_id = e.event_id
	join address a on x.mailing_addr_id = a.addr_id

	UNION ALL
	select a.*
	from corporation_cte c
	join event e on e.corp_num = c.corp_num
	join notification x on x.event_id = e.event_id
	join address a on x.mailing_addr_id = a.addr_id

	UNION ALL
	select a.*
	from corporation_cte c
	join event e on e.corp_num = c.corp_num
	join submitting_party x on x.event_id = e.event_id
	join address a on (x.notify_addr_id = a.addr_id or x.mailing_addr_id = a.addr_id)

	UNION ALL
	select a.*
	from corporation_cte c
	join corp_party p on p.corp_num = c.corp_num
	join party_notification x on x.party_id = p.corp_party_id
	join address a on x.mailing_addr_id = a.addr_id
);


-- office
transfer public.office from cprd using
with corp_list as (
	select /*+ materialize */ c.corp_num
	from corporation c
	where &oracle_corp_num_predicate
		and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
		and c.CORP_NUM not in ('0460007', '1255957', '1186381')
),
corporation_cte as (
	select *
	from (
		select c.*,
				case
					when c.CORP_TYP_CD in ('BC', 'ULC', 'CC') then 'BC' || c.CORP_NUM
					else c.CORP_NUM
				end as target_corp_num
		from corporation c
		join corp_list cl on cl.corp_num = c.corp_num
	)
	where &target_corp_num_predicate
)
select c.target_corp_num as CORP_NUM,
		o.office_typ_cd,
		o.start_event_id,
		o.end_event_id,
		o.mailing_addr_id,
		o.delivery_addr_id
from corporation_cte c
join office o on o.corp_num = c.corp_num;


-- corp_comments
transfer public.corp_comments from cprd using
with corp_list as (
	select /*+ materialize */ c.corp_num
	from corporation c
	where &oracle_corp_num_predicate
		and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
		and c.CORP_NUM not in ('0460007', '1255957', '1186381')
),
corporation_cte as (
    select *
    from (
		select c.*,
				case
					when c.CORP_TYP_CD in ('BC', 'ULC', 'CC') then 'BC' || c.CORP_NUM
					else c.CORP_NUM
				end as target_corp_num
		from corporation c
		join corp_list cl on cl.corp_num = c.corp_num
	)
	where &target_corp_num_predicate
)
select cc.comment_dts,
       c.target_corp_num as CORP_NUM,
       cc.comments,
       cc.USER_ID,
       cc.FIRST_NME,
       cc.LAST_NME,
       cc.MIDDLE_NME,
       cc.ACCESSION_COMMENTS
from corporation_cte c
join corp_comments cc on cc.corp_num = c.corp_num;


-- ledger_text
transfer public.ledger_text from cprd using
with corp_list as (
	select /*+ materialize */ c.corp_num
	from corporation c
	where &oracle_corp_num_predicate
		and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
		and c.CORP_NUM not in ('0460007', '1255957', '1186381')
),
corporation_cte as (
    select *
    from (
		select c.*,
				case
					when c.CORP_TYP_CD in ('BC', 'ULC', 'CC') then 'BC' || c.CORP_NUM
					else c.CORP_NUM
				end as target_corp_num
		from corporation c
		join corp_list cl on cl.corp_num = c.corp_num
	)
	where &target_corp_num_predicate
)
select e.event_id,
       l.notation,
       l.USER_ID,
       l.LEDGER_TEXT_DTS
from corporation_cte c
join event e on e.corp_num = c.corp_num
join ledger_text l on l.event_id = e.event_id;


-- corp_party
transfer public.corp_party from cprd using
with corp_list as (
	select /*+ materialize */ c.corp_num
	from corporation c
	where &oracle_corp_num_predicate
		and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
		and c.CORP_NUM not in ('0460007', '1255957', '1186381')
),
corporation_cte as (
    select *
    from (
		select c.*,
				case
					when c.CORP_TYP_CD in ('BC', 'ULC', 'CC') then 'BC' || c.CORP_NUM
					else c.CORP_NUM
				end as target_corp_num
		from corporation c
		join corp_list cl on cl.corp_num = c.corp_num
	)
	where &target_corp_num_predicate
)
select p.corp_party_id,
       p.mailing_addr_id,
       p.delivery_addr_id,
       c.target_corp_num as CORP_NUM,
       nvl(p.party_typ_cd, ' ') as party_typ_cd,
       p.start_event_id,
       p.end_event_id,
       p.prev_party_id,
       p.appointment_dt,
       p.cessation_dt,
		nvl(p.LAST_NME, ' ') as last_name,
		nvl(p.MIDDLE_NME, ' ') as middle_name,
		nvl(p.FIRST_NME, ' ') as first_name,
       nvl(p.BUSINESS_NME, ' ') as business_name,
       p.BUS_COMPANY_NUM,
       p.CORR_TYP_CD,
       p.OFFICE_NOTIFICATION_DT
from corporation_cte c
join corp_party p on p.corp_num = c.corp_num;


-- corp_party_relationship
transfer public.corp_party_relationship from cprd using
with corp_list as (
	select /*+ materialize */ c.corp_num
	from corporation c
	where &oracle_corp_num_predicate
		and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
		and c.CORP_NUM not in ('0460007', '1255957', '1186381')
),
corporation_cte as (
    select *
    from (
		select c.*,
				case
					when c.CORP_TYP_CD in ('BC', 'ULC', 'CC') then 'BC' || c.CORP_NUM
					else c.CORP_NUM
				end as target_corp_num
		from corporation c
		join corp_list cl on cl.corp_num = c.corp_num
	)
	where &target_corp_num_predicate
)
select cpr.CORP_PARTY_ID as corp_party_id,
		cpr.RELATIONSHIP_TYP_CD as relationship_typ_cd
from corporation_cte c
join corp_party p on p.corp_num = c.corp_num
join CORP_PARTY_RELATIONSHIP cpr on cpr.corp_party_id = p.corp_party_id;


-- offices_held
transfer public.offices_held from cprd using
with corp_list as (
	select /*+ materialize */ c.corp_num
	from corporation c
	where &oracle_corp_num_predicate
		and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
		and c.CORP_NUM not in ('0460007', '1255957', '1186381')
),
corporation_cte as (
    select *
    from (
		select c.*,
				case
					when c.CORP_TYP_CD in ('BC', 'ULC', 'CC') then 'BC' || c.CORP_NUM
					else c.CORP_NUM
				end as target_corp_num
		from corporation c
		join corp_list cl on cl.corp_num = c.corp_num
	)
	where &target_corp_num_predicate
)
select oh.CORP_PARTY_ID as corp_party_id,
		oh.OFFICER_TYP_CD as officer_typ_cd
from corporation_cte c
join corp_party p on p.corp_num = c.corp_num
join OFFICES_HELD oh on oh.corp_party_id = p.corp_party_id;


-- completing_party
transfer public.completing_party from cprd using
with corp_list as (
	select /*+ materialize */ c.corp_num
	from corporation c
	where &oracle_corp_num_predicate
		and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
		and c.CORP_NUM not in ('0460007', '1255957', '1186381')
),
corporation_cte as (
    select *
    from (
		select c.*,
				case
					when c.CORP_TYP_CD in ('BC', 'ULC', 'CC') then 'BC' || c.CORP_NUM
					else c.CORP_NUM
				end as target_corp_num
		from corporation c
		join corp_list cl on cl.corp_num = c.corp_num
	)
	where &target_corp_num_predicate
)
select e.event_id,
       cp.MAILING_ADDR_ID,
       cp.FIRST_NME,
       cp.LAST_NME,
       cp.MIDDLE_NME,
       cp.EMAIL_REQ_ADDRESS
from corporation_cte c
join event e on e.corp_num = c.corp_num
join completing_party cp on cp.event_id = e.event_id;


-- submitting_party
transfer public.submitting_party from cprd using
with corp_list as (
	select /*+ materialize */ c.corp_num
	from corporation c
	where &oracle_corp_num_predicate
		and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
		and c.CORP_NUM not in ('0460007', '1255957', '1186381')
),
corporation_cte as (
    select *
    from (
		select c.*,
				case
					when c.CORP_TYP_CD in ('BC', 'ULC', 'CC') then 'BC' || c.CORP_NUM
					else c.CORP_NUM
				end as target_corp_num
		from corporation c
		join corp_list cl on cl.corp_num = c.corp_num
	)
	where &target_corp_num_predicate
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
from corporation_cte c
join event e on e.corp_num = c.corp_num
join SUBMITTING_PARTY sp on sp.event_id = e.event_id;


-- corp_flag
transfer public.corp_flag from cprd using
with corp_list as (
	select /*+ materialize */ c.corp_num
	from corporation c
	where &oracle_corp_num_predicate
		and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
		and c.CORP_NUM not in ('0460007', '1255957', '1186381')
),
corporation_cte as (
    select *
    from (
		select c.*,
				case
					when c.CORP_TYP_CD in ('BC', 'ULC', 'CC') then 'BC' || c.CORP_NUM
					else c.CORP_NUM
				end as target_corp_num
		from corporation c
		join corp_list cl on cl.corp_num = c.corp_num
	)
	where &target_corp_num_predicate
)
select c.target_corp_num as CORP_NUM,
       cf.CORP_FLAG_TYPE_CD,
       cf.start_event_id,
       cf.end_event_id
from corporation_cte c
join corp_flag cf on cf.corp_num = c.corp_num;


-- cont_out
transfer public.cont_out from cprd using
with corp_list as (
	select /*+ materialize */ c.corp_num
	from corporation c
	where &oracle_corp_num_predicate
		and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
		and c.CORP_NUM not in ('0460007', '1255957', '1186381')
),
corporation_cte as (
    select *
    from (
		select c.*,
				case
					when c.CORP_TYP_CD in ('BC', 'ULC', 'CC') then 'BC' || c.CORP_NUM
					else c.CORP_NUM
				end as target_corp_num
		from corporation c
		join corp_list cl on cl.corp_num = c.corp_num
	)
	where &target_corp_num_predicate
)
select c.target_corp_num as CORP_NUM,
       co.CAN_JUR_TYP_CD,
       co.CONT_OUT_DT,
       co.OTHR_JURI_DESC,
       co.HOME_COMPANY_NME,
       co.start_event_id,
       co.end_event_id
from corporation_cte c
join CONT_OUT co on co.corp_num = c.corp_num;


-- conv_event
transfer public.conv_event from cprd using
with corp_list as (
	select /*+ materialize */ c.corp_num
	from corporation c
	where &oracle_corp_num_predicate
		and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
		and c.CORP_NUM not in ('0460007', '1255957', '1186381')
),
corporation_cte as (
    select *
    from (
		select c.*,
				case
					when c.CORP_TYP_CD in ('BC', 'ULC', 'CC') then 'BC' || c.CORP_NUM
					else c.CORP_NUM
				end as target_corp_num
		from corporation c
		join corp_list cl on cl.corp_num = c.corp_num
	)
	where &target_corp_num_predicate
)
select e.event_id,
       ce.effective_dt,
       case ce.REPORT_CORP_IND
           when 'N' then 'f'
           when 'Y' then 't'
           else 't'
			end as REPORT_CORP_IND,
       ce.ACTIVITY_USER_ID,
       ce.ACTIVITY_DT,
       ce.ANNUAL_FILE_DT,
       ce.ACCESSION_NUM,
       ce.REMARKS
from corporation_cte c
join event e on e.corp_num = c.corp_num
join CONV_EVENT ce on ce.event_id = e.event_id;


-- conv_ledger
transfer public.conv_ledger from cprd using
with corp_list as (
	select /*+ materialize */ c.corp_num
	from corporation c
	where &oracle_corp_num_predicate
		and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
		and c.CORP_NUM not in ('0460007', '1255957', '1186381')
),
corporation_cte as (
    select *
    from (
		select c.*,
				case
					when c.CORP_TYP_CD in ('BC', 'ULC', 'CC') then 'BC' || c.CORP_NUM
					else c.CORP_NUM
				end as target_corp_num
		from corporation c
		join corp_list cl on cl.corp_num = c.corp_num
	)
	where &target_corp_num_predicate
)
select e.event_id,
       cl.LEDGER_TITLE_TXT,
       cl.LEDGER_DESC,
       cl.cars_docmnt_id
from corporation_cte c
join event e on e.corp_num = c.corp_num
join CONV_LEDGER cl on cl.event_id = e.event_id;


-- corp_involved - amalgamaTING_businesses
transfer public.corp_involved_amalgamating from cprd using
with corp_list as (
	select /*+ materialize */ c.corp_num
	from corporation c
	where &oracle_corp_num_predicate
		and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
		and c.CORP_NUM not in ('0460007', '1255957', '1186381')
),
corporation_cte as (
    select *
    from (
		select c.*,
             case
					when c.CORP_TYP_CD in ('BC', 'ULC', 'CC') then 'BC' || c.CORP_NUM
					else c.CORP_NUM
				end as target_corp_num
		from corporation c
		join corp_list cl on cl.corp_num = c.corp_num
	)
	where &target_corp_num_predicate
)
select e.event_id as event_id,
		c.target_corp_num as ted_corp_num,
		case
			when c2.corp_typ_cd in ('BC', 'ULC', 'CC') then 'BC' || c2.corp_num
			else c2.corp_num
			end as ting_corp_num,
		ci.CORP_INVOLVE_ID as corp_involve_id,
		ci.CAN_JUR_TYP_CD as can_jur_typ_cd,
		case ci.ADOPTED_CORP_IND
			when 'N' then 'f'
			when 'Y' then 't'
			else 'f'
			end as adopted_corp_ind,
		ci.HOME_JURI_NUM as home_juri_num,
		ci.OTHR_JURI_DESC as othr_juri_desc,
		ci.FOREIGN_NME as foreign_nme
from corporation_cte c
join event e on e.corp_num = c.corp_num
join CORP_INVOLVED ci on ci.event_id = e.event_id
join corporation c2 on c2.corp_num = ci.corp_num
where e.event_typ_cd = 'CONVAMAL'
UNION ALL
select e.event_id as event_id,
		c.target_corp_num as ted_corp_num,
		case
			when c2.corp_typ_cd in ('BC', 'ULC', 'CC') then 'BC' || c2.corp_num
			else c2.corp_num
			end as ting_corp_num,
		ci.CORP_INVOLVE_ID as corp_involve_id,
		ci.CAN_JUR_TYP_CD as can_jur_typ_cd,
		case ci.ADOPTED_CORP_IND
			when 'N' then 'f'
			when 'Y' then 't'
			else 'f'
			end as adopted_corp_ind,
		ci.HOME_JURI_NUM as home_juri_num,
		ci.OTHR_JURI_DESC as othr_juri_desc,
		ci.FOREIGN_NME as foreign_nme
from corporation_cte c
join event e on e.corp_num = c.corp_num
join filing f on f.event_id = e.event_id
join CORP_INVOLVED ci on ci.event_id = e.event_id
join corporation c2 on c2.corp_num = ci.corp_num
where f.filing_typ_cd in ('AMALH', 'AMALV', 'AMALR', 'AMLHU', 'AMLVU', 'AMLRU', 'AMLHC', 'AMLVC', 'AMLRC');


-- corp_involved - continue_in_historical_xpro
transfer public.corp_involved_cont_in from cprd using
with corp_list as (
	select /*+ materialize */ c.corp_num
	from corporation c
	where &oracle_corp_num_predicate
		and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
		and c.CORP_NUM not in ('0460007', '1255957', '1186381')
),
corporation_cte as (
    select *
    from (
		select c.*,
				case
					when c.CORP_TYP_CD in ('BC', 'ULC', 'CC') then 'BC' || c.CORP_NUM
					else c.CORP_NUM
				end as target_corp_num
		from corporation c
		join corp_list cl on cl.corp_num = c.corp_num
	)
	where &target_corp_num_predicate
)
select e.event_id,
       c.target_corp_num as CORP_NUM
from corporation_cte c
join event e on e.corp_num = c.corp_num
join filing f on f.event_id = e.event_id
where f.filing_typ_cd in ('CONTI', 'CONTU', 'CONTC')
	and exists (select 1 from CORP_INVOLVED ci where ci.event_id = e.event_id);


-- corp_restriction
transfer public.corp_restriction from cprd using
with corp_list as (
	select /*+ materialize */ c.corp_num
	from corporation c
	where &oracle_corp_num_predicate
		and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
		and c.CORP_NUM not in ('0460007', '1255957', '1186381')
),
corporation_cte as (
    select *
    from (
		select c.*,
				case
					when c.CORP_TYP_CD in ('BC', 'ULC', 'CC') then 'BC' || c.CORP_NUM
					else c.CORP_NUM
				end as target_corp_num
		from corporation c
		join corp_list cl on cl.corp_num = c.corp_num
	)
	where &target_corp_num_predicate
)
select c.target_corp_num as CORP_NUM,
       case cr.RESTRICTION_IND
           when 'N' then 'f'
           when 'Y' then 't'
           else 'f'
			end as RESTRICTION_IND,
       cr.start_event_id,
       cr.end_event_id
from corporation_cte c
join CORP_RESTRICTION cr on cr.corp_num = c.corp_num;


-- correction
transfer public.correction from cprd using
with corp_list as (
	select /*+ materialize */ c.corp_num
	from corporation c
	where &oracle_corp_num_predicate
		and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
		and c.CORP_NUM not in ('0460007', '1255957', '1186381')
),
corporation_cte as (
    select *
    from (
		select c.*,
				case
					when c.CORP_TYP_CD in ('BC', 'ULC', 'CC') then 'BC' || c.CORP_NUM
					else c.CORP_NUM
				end as target_corp_num
		from corporation c
		join corp_list cl on cl.corp_num = c.corp_num
	)
	where &target_corp_num_predicate
)
select e.event_id,
       c.target_corp_num as CORP_NUM,
       corr.ASSOCIATED_DOC_DESC
from corporation_cte c
join event e on e.corp_num = c.corp_num
join CORRECTION corr on corr.event_id = e.event_id;


-- continued_in_from_jurisdiction
transfer public.jurisdiction from cprd using
with corp_list as (
	select /*+ materialize */ c.corp_num
	from corporation c
	where &oracle_corp_num_predicate
		and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
		and c.CORP_NUM not in ('0460007', '1255957', '1186381')
),
corporation_cte as (
    select *
    from (
		select c.*,
				case
					when c.CORP_TYP_CD in ('BC', 'ULC', 'CC') then 'BC' || c.CORP_NUM
					else c.CORP_NUM
				end as target_corp_num
		from corporation c
		join corp_list cl on cl.corp_num = c.corp_num
	)
	where &target_corp_num_predicate
)
select c.target_corp_num as CORP_NUM,
       j.CAN_JUR_TYP_CD,
       j.XPRO_TYP_CD,
       j.HOME_RECOGN_DT,
       j.OTHR_JURIS_DESC,
       j.HOME_JURIS_NUM,
       j.BC_XPRO_NUM,
       j.HOME_COMPANY_NME,
       j.start_event_id
from corporation_cte c
join JURISDICTION j on j.corp_num = c.corp_num;


-- resolution
transfer public.resolution from cprd using
with corp_list as (
	select /*+ materialize */ c.corp_num
	from corporation c
	where &oracle_corp_num_predicate
		and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
		and c.CORP_NUM not in ('0460007', '1255957', '1186381')
),
corporation_cte as (
    select *
    from (
		select c.*,
				case
					when c.CORP_TYP_CD in ('BC', 'ULC', 'CC') then 'BC' || c.CORP_NUM
					else c.CORP_NUM
				end as target_corp_num
		from corporation c
		join corp_list cl on cl.corp_num = c.corp_num
	)
	where &target_corp_num_predicate
)
select c.target_corp_num as CORP_NUM,
       r.RESOLUTION_DT,
       r.RESOLUTION_TYPE_CODE,
       r.start_event_id,
       r.end_event_id
from corporation_cte c
join RESOLUTION r on r.corp_num = c.corp_num;


-- share_struct
transfer public.share_struct from cprd using
with corp_list as (
	select /*+ materialize */ c.corp_num
	from corporation c
	where &oracle_corp_num_predicate
		and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
		and c.CORP_NUM not in ('0460007', '1255957', '1186381')
),
corporation_cte as (
    select *
    from (
		select c.*,
				case
					when c.CORP_TYP_CD in ('BC', 'ULC', 'CC') then 'BC' || c.CORP_NUM
					else c.CORP_NUM
				end as target_corp_num
		from corporation c
		join corp_list cl on cl.corp_num = c.corp_num
	)
	where &target_corp_num_predicate
)
select c.target_corp_num as CORP_NUM,
       ss.start_event_id,
       ss.end_event_id
from corporation_cte c
join SHARE_STRUCT ss on ss.corp_num = c.corp_num;


-- share_struct_cls
transfer public.share_struct_cls from cprd using
with corp_list as (
	select /*+ materialize */ c.corp_num
	from corporation c
	where &oracle_corp_num_predicate
		and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
		and c.CORP_NUM not in ('0460007', '1255957', '1186381')
),
corporation_cte as (
    select *
    from (
		select c.*,
				case
					when c.CORP_TYP_CD in ('BC', 'ULC', 'CC') then 'BC' || c.CORP_NUM
					else c.CORP_NUM
				end as target_corp_num
		from corporation c
		join corp_list cl on cl.corp_num = c.corp_num
	)
	where &target_corp_num_predicate
)
select c.target_corp_num as CORP_NUM,
       ssc.SHARE_CLASS_ID,
       replace(ssc.CLASS_NME, CHR(0), '') as CLASS_NME,
       ssc.CURRENCY_TYP_CD,
       case ssc.MAX_SHARE_IND
           when 'N' then 'f'
           when 'Y' then 't'
           else 'f'
			end as MAX_SHARE_IND,
       ssc.SHARE_QUANTITY,
       case ssc.SPEC_RIGHTS_IND
           when 'N' then 'f'
           when 'Y' then 't'
           else 'f'
			end as SPEC_RIGHTS_IND,
       case ssc.PAR_VALUE_IND
           when 'N' then 'f'
           when 'Y' then 't'
           else 'f'
			end as PAR_VALUE_IND,
		ssc.PAR_VALUE_AMT + 0 as PAR_VALUE_AMT,
       ssc.OTHER_CURRENCY,
       ssc.start_event_id
from corporation_cte c
join SHARE_STRUCT_CLS ssc on ssc.corp_num = c.corp_num;


-- share_series
transfer public.share_series from cprd using
with corp_list as (
	select /*+ materialize */ c.corp_num
	from corporation c
	where &oracle_corp_num_predicate
		and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
		and c.CORP_NUM not in ('0460007', '1255957', '1186381')
),
corporation_cte as (
    select *
    from (
		select c.*,
				case
					when c.CORP_TYP_CD in ('BC', 'ULC', 'CC') then 'BC' || c.CORP_NUM
					else c.CORP_NUM
				end as target_corp_num
		from corporation c
		join corp_list cl on cl.corp_num = c.corp_num
	)
	where &target_corp_num_predicate
)
select c.target_corp_num as CORP_NUM,
       ss.SHARE_CLASS_ID,
       ss.SERIES_ID,
       case ss.MAX_SHARE_IND
           when 'N' then 'f'
           when 'Y' then 't'
           else 'f'
			end as MAX_SHARE_IND,
       ss.SHARE_QUANTITY,
       case ss.SPEC_RIGHT_IND
           when 'N' then 'f'
           when 'Y' then 't'
           else 'f'
			end as SPEC_RIGHT_IND,
       ss.SERIES_NME,
       ss.start_event_id
from corporation_cte c
join SHARE_SERIES ss on ss.corp_num = c.corp_num;


-- notification
transfer public.notification from cprd using
with corp_list as (
	select /*+ materialize */ c.corp_num
	from corporation c
	where &oracle_corp_num_predicate
		and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
		and c.CORP_NUM not in ('0460007', '1255957', '1186381')
),
corporation_cte as (
    select *
    from (
		select c.*,
				case
					when c.CORP_TYP_CD in ('BC', 'ULC', 'CC') then 'BC' || c.CORP_NUM
					else c.CORP_NUM
				end as target_corp_num
		from corporation c
		join corp_list cl on cl.corp_num = c.corp_num
	)
	where &target_corp_num_predicate
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
from corporation_cte c
join event e on e.corp_num = c.corp_num
join NOTIFICATION n on n.event_id = e.event_id;


-- notification_resend
transfer public.notification_resend from cprd using
with corp_list as (
	select /*+ materialize */ c.corp_num
	from corporation c
	where &oracle_corp_num_predicate
		and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
		and c.CORP_NUM not in ('0460007', '1255957', '1186381')
),
corporation_cte as (
    select *
    from (
		select c.*,
				case
					when c.CORP_TYP_CD in ('BC', 'ULC', 'CC') then 'BC' || c.CORP_NUM
					else c.CORP_NUM
				end as target_corp_num
		from corporation c
		join corp_list cl on cl.corp_num = c.corp_num
	)
	where &target_corp_num_predicate
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
from corporation_cte c
join event e on e.corp_num = c.corp_num
join NOTIFICATION_RESEND nr on nr.event_id = e.event_id;


-- party_notification
transfer public.party_notification from cprd using
with corp_list as (
	select /*+ materialize */ c.corp_num
	from corporation c
	where &oracle_corp_num_predicate
		and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
		and c.CORP_NUM not in ('0460007', '1255957', '1186381')
),
corporation_cte as (
    select *
    from (
		select c.*,
				case
					when c.CORP_TYP_CD in ('BC', 'ULC', 'CC') then 'BC' || c.CORP_NUM
					else c.CORP_NUM
				end as target_corp_num
		from corporation c
		join corp_list cl on cl.corp_num = c.corp_num
	)
	where &target_corp_num_predicate
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
from corporation_cte c
join corp_party cp on cp.corp_num = c.corp_num
join PARTY_NOTIFICATION pn on pn.party_id = cp.corp_party_id;


-- payment
transfer public.payment from cprd using
with corp_list as (
	select /*+ materialize */ c.corp_num
	from corporation c
	where &oracle_corp_num_predicate
		and c.CORP_TYP_CD in ('BC', 'C', 'ULC', 'CUL', 'CC', 'CCC', 'QA', 'QB', 'QC', 'QD', 'QE')
		and c.CORP_NUM not in ('0460007', '1255957', '1186381')
),
corporation_cte as (
    select *
    from (
		select c.*,
				case
					when c.CORP_TYP_CD in ('BC', 'ULC', 'CC') then 'BC' || c.CORP_NUM
					else c.CORP_NUM
				end as target_corp_num
		from corporation c
		join corp_list cl on cl.corp_num = c.corp_num
	)
	where &target_corp_num_predicate
)
select p.event_id,
       p.payment_typ_cd,
       p.cc_holder_nme
from corporation_cte c
join event e on e.corp_num = c.corp_num
join payment p on p.event_id = e.event_id;
