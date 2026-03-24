-- Release the session-level advisory lock used to serialize subset load/refresh runs.
-- If the session ends unexpectedly, Postgres releases the advisory lock automatically.

SELECT pg_advisory_unlock(
    hashtext('lear:data-tool:colin_subset_extract'),
    hashtext('subset_run')
);
