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
DELETE FROM TARGET_SCHEMA.notification_resend t
WHERE NOT EXISTS (SELECT 1 FROM TARGET_SCHEMA.event e WHERE e.event_id = t.event_id);

DELETE FROM TARGET_SCHEMA.notification t
WHERE NOT EXISTS (SELECT 1 FROM TARGET_SCHEMA.event e WHERE e.event_id = t.event_id);

DELETE FROM TARGET_SCHEMA.filing_user t
WHERE NOT EXISTS (SELECT 1 FROM TARGET_SCHEMA.event e WHERE e.event_id = t.event_id);

DELETE FROM TARGET_SCHEMA.payment t
WHERE NOT EXISTS (SELECT 1 FROM TARGET_SCHEMA.event e WHERE e.event_id = t.event_id);

DELETE FROM TARGET_SCHEMA.ledger_text t
WHERE NOT EXISTS (SELECT 1 FROM TARGET_SCHEMA.event e WHERE e.event_id = t.event_id);

DELETE FROM TARGET_SCHEMA.conv_ledger t
WHERE NOT EXISTS (SELECT 1 FROM TARGET_SCHEMA.event e WHERE e.event_id = t.event_id);

DELETE FROM TARGET_SCHEMA.conv_event t
WHERE NOT EXISTS (SELECT 1 FROM TARGET_SCHEMA.event e WHERE e.event_id = t.event_id);

DELETE FROM TARGET_SCHEMA.completing_party t
WHERE NOT EXISTS (SELECT 1 FROM TARGET_SCHEMA.event e WHERE e.event_id = t.event_id);

DELETE FROM TARGET_SCHEMA.submitting_party t
WHERE NOT EXISTS (SELECT 1 FROM TARGET_SCHEMA.event e WHERE e.event_id = t.event_id);

DELETE FROM TARGET_SCHEMA.corp_involved_amalgamating t
WHERE t.event_id IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM TARGET_SCHEMA.event e WHERE e.event_id = t.event_id);

DELETE FROM TARGET_SCHEMA.corp_involved_cont_in t
WHERE NOT EXISTS (SELECT 1 FROM TARGET_SCHEMA.event e WHERE e.event_id = t.event_id);

DELETE FROM TARGET_SCHEMA.correction t
WHERE NOT EXISTS (SELECT 1 FROM TARGET_SCHEMA.event e WHERE e.event_id = t.event_id);

DELETE FROM TARGET_SCHEMA.filing t
WHERE NOT EXISTS (SELECT 1 FROM TARGET_SCHEMA.event e WHERE e.event_id = t.event_id);

-- Corp-party children whose parent corp_party row is missing.
DELETE FROM TARGET_SCHEMA.party_notification t
WHERE NOT EXISTS (SELECT 1 FROM TARGET_SCHEMA.corp_party cp WHERE cp.corp_party_id = t.party_id);

DELETE FROM TARGET_SCHEMA.offices_held t
WHERE NOT EXISTS (SELECT 1 FROM TARGET_SCHEMA.corp_party cp WHERE cp.corp_party_id = t.corp_party_id);

DELETE FROM TARGET_SCHEMA.corp_party_relationship t
WHERE NOT EXISTS (SELECT 1 FROM TARGET_SCHEMA.corp_party cp WHERE cp.corp_party_id = t.corp_party_id);
