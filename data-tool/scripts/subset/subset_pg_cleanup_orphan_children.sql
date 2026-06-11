-- Cleanup stale child rows that no longer have the parent rows used by refresh-mode deletes.
--
-- Why this exists:
-- - refresh-mode chunk deletes remove event-scoped rows by first looking up event_id in target `event`
-- - and remove corp-party child rows by first looking up corp_party_id in target `corp_party`
-- - so a prior failed/interleaved run can leave stale child rows behind when the parent row is missing
-- - those orphans can then collide with the next reload (for example, unique `filing.event_id`)
--
-- This cleanup is intentionally narrow:
-- - only rows whose normal refresh delete path traverses a parent lookup are removed here
-- - corp-scoped rows deleted directly by corp_num are left to the regular chunk deletes

-- Event-scoped children whose parent event row is missing.
DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.notification_resend t
WHERE NOT EXISTS (SELECT 1 FROM __DBSCHEMA_TARGET_SCHEMA__.event e WHERE e.event_id = t.event_id);

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.notification t
WHERE NOT EXISTS (SELECT 1 FROM __DBSCHEMA_TARGET_SCHEMA__.event e WHERE e.event_id = t.event_id);

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.filing_user t
WHERE NOT EXISTS (SELECT 1 FROM __DBSCHEMA_TARGET_SCHEMA__.event e WHERE e.event_id = t.event_id);

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.payment t
WHERE NOT EXISTS (SELECT 1 FROM __DBSCHEMA_TARGET_SCHEMA__.event e WHERE e.event_id = t.event_id);

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.ledger_text t
WHERE NOT EXISTS (SELECT 1 FROM __DBSCHEMA_TARGET_SCHEMA__.event e WHERE e.event_id = t.event_id);

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.conv_ledger t
WHERE NOT EXISTS (SELECT 1 FROM __DBSCHEMA_TARGET_SCHEMA__.event e WHERE e.event_id = t.event_id);

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.conv_event t
WHERE NOT EXISTS (SELECT 1 FROM __DBSCHEMA_TARGET_SCHEMA__.event e WHERE e.event_id = t.event_id);

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.completing_party t
WHERE NOT EXISTS (SELECT 1 FROM __DBSCHEMA_TARGET_SCHEMA__.event e WHERE e.event_id = t.event_id);

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.submitting_party t
WHERE NOT EXISTS (SELECT 1 FROM __DBSCHEMA_TARGET_SCHEMA__.event e WHERE e.event_id = t.event_id);

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.corp_involved_amalgamating t
WHERE t.event_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM __DBSCHEMA_TARGET_SCHEMA__.event e WHERE e.event_id = t.event_id);

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.corp_involved_cont_in t
WHERE NOT EXISTS (SELECT 1 FROM __DBSCHEMA_TARGET_SCHEMA__.event e WHERE e.event_id = t.event_id);

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.correction t
WHERE NOT EXISTS (SELECT 1 FROM __DBSCHEMA_TARGET_SCHEMA__.event e WHERE e.event_id = t.event_id);

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.filing t
WHERE NOT EXISTS (SELECT 1 FROM __DBSCHEMA_TARGET_SCHEMA__.event e WHERE e.event_id = t.event_id);

-- Corp-party children whose parent corp_party row is missing.
DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.party_notification t
WHERE NOT EXISTS (SELECT 1 FROM __DBSCHEMA_TARGET_SCHEMA__.corp_party cp WHERE cp.corp_party_id = t.party_id);

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.offices_held t
WHERE NOT EXISTS (SELECT 1 FROM __DBSCHEMA_TARGET_SCHEMA__.corp_party cp WHERE cp.corp_party_id = t.corp_party_id);

DELETE FROM __DBSCHEMA_TARGET_SCHEMA__.corp_party_relationship t
WHERE NOT EXISTS (SELECT 1 FROM __DBSCHEMA_TARGET_SCHEMA__.corp_party cp WHERE cp.corp_party_id = t.corp_party_id);
