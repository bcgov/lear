-- Acquire a session-level advisory lock so subset load/refresh runs do not overlap on the same target DB.
-- Advisory locks are scoped to the current Postgres database, so the same keys are safe across separate DBs.

SELECT pg_advisory_lock(
    hashtext('lear:data-tool:colin_subset_extract'),
    hashtext('subset_run')
);
