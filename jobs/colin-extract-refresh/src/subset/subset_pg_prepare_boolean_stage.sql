SET search_path TO TARGET_SCHEMA;

DROP TABLE IF EXISTS TARGET_SCHEMA.subset_corporation_bool_stage;
CREATE TABLE TARGET_SCHEMA.subset_corporation_bool_stage (
    LIKE TARGET_SCHEMA.corporation INCLUDING DEFAULTS
);
ALTER TABLE TARGET_SCHEMA.subset_corporation_bool_stage
    ALTER COLUMN send_ar_ind TYPE varchar(5);

DROP TABLE IF EXISTS TARGET_SCHEMA.subset_filing_bool_stage;
CREATE TABLE TARGET_SCHEMA.subset_filing_bool_stage (
    LIKE TARGET_SCHEMA.filing INCLUDING DEFAULTS
);
ALTER TABLE TARGET_SCHEMA.subset_filing_bool_stage
    ALTER COLUMN arrangement_ind TYPE varchar(5);
ALTER TABLE TARGET_SCHEMA.subset_filing_bool_stage
    ALTER COLUMN court_appr_ind TYPE varchar(5);

DROP TABLE IF EXISTS TARGET_SCHEMA.subset_conv_event_bool_stage;
CREATE TABLE TARGET_SCHEMA.subset_conv_event_bool_stage (
    LIKE TARGET_SCHEMA.conv_event INCLUDING DEFAULTS
);
ALTER TABLE TARGET_SCHEMA.subset_conv_event_bool_stage
    ALTER COLUMN report_corp_ind TYPE varchar(5);

DROP TABLE IF EXISTS TARGET_SCHEMA.subset_corp_involved_amalgamating_bool_stage;
CREATE TABLE TARGET_SCHEMA.subset_corp_involved_amalgamating_bool_stage (
    LIKE TARGET_SCHEMA.corp_involved_amalgamating INCLUDING DEFAULTS
);
ALTER TABLE TARGET_SCHEMA.subset_corp_involved_amalgamating_bool_stage
    ALTER COLUMN adopted_corp_ind TYPE varchar(5);

DROP TABLE IF EXISTS TARGET_SCHEMA.subset_corp_restriction_bool_stage;
CREATE TABLE TARGET_SCHEMA.subset_corp_restriction_bool_stage (
    LIKE TARGET_SCHEMA.corp_restriction INCLUDING DEFAULTS
);
ALTER TABLE TARGET_SCHEMA.subset_corp_restriction_bool_stage
    ALTER COLUMN restriction_ind TYPE varchar(5);

DROP TABLE IF EXISTS TARGET_SCHEMA.subset_share_struct_cls_bool_stage;
CREATE TABLE TARGET_SCHEMA.subset_share_struct_cls_bool_stage (
    LIKE TARGET_SCHEMA.share_struct_cls INCLUDING DEFAULTS
);
ALTER TABLE TARGET_SCHEMA.subset_share_struct_cls_bool_stage
    ALTER COLUMN max_share_ind TYPE varchar(5);
ALTER TABLE TARGET_SCHEMA.subset_share_struct_cls_bool_stage
    ALTER COLUMN spec_rights_ind TYPE varchar(5);
ALTER TABLE TARGET_SCHEMA.subset_share_struct_cls_bool_stage
    ALTER COLUMN par_value_ind TYPE varchar(5);

DROP TABLE IF EXISTS TARGET_SCHEMA.subset_share_series_bool_stage;
CREATE TABLE TARGET_SCHEMA.subset_share_series_bool_stage (
    LIKE TARGET_SCHEMA.share_series INCLUDING DEFAULTS
);
ALTER TABLE TARGET_SCHEMA.subset_share_series_bool_stage
    ALTER COLUMN max_share_ind TYPE varchar(5);
ALTER TABLE TARGET_SCHEMA.subset_share_series_bool_stage
    ALTER COLUMN spec_right_ind TYPE varchar(5);