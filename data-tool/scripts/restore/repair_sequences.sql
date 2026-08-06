DO $$
DECLARE
  r record;
  max_val bigint;
BEGIN
  FOR r IN
    -- For SERIAL/IDENTITY columns (auto-dependency from sequence to column)
    SELECT seq.relname AS seq,
           tbl.relname AS tbl,
           col.attname AS col
    FROM pg_class seq
    JOIN pg_depend d ON d.objid = seq.oid AND d.deptype = 'a'
    JOIN pg_class tbl  ON tbl.oid = d.refobjid
    JOIN pg_attribute col
           ON col.attrelid = tbl.oid AND col.attnum = d.refobjsubid
    WHERE  seq.relkind = 'S'
    UNION ALL
    -- For columns with DEFAULT nextval('sequence') (normal dependency from column default to sequence)
    SELECT
      seq.relname as seq,
      tbl.relname as tbl,
      col.attname as col
    FROM pg_depend d
    JOIN pg_class seq ON seq.oid = d.refobjid AND seq.relkind = 'S'
    JOIN pg_attrdef ad ON ad.oid = d.objid AND d.classid = 'pg_attrdef'::regclass
    JOIN pg_attribute col ON col.attrelid = ad.adrelid AND col.attnum = ad.adnum
    JOIN pg_class tbl ON tbl.oid = ad.adrelid
    WHERE d.deptype = 'n'
  LOOP
    EXECUTE format('SELECT MAX(%I) FROM %I', r.col, r.tbl) INTO max_val;
    IF max_val IS NULL THEN
      -- Table is empty, reset sequence to start at 1. The next call to nextval() will return 1.
      EXECUTE format('SELECT setval(%L, 1, false);', r.seq);
    ELSE
      -- Table has data, set sequence so nextval() returns max_val + 1.
      EXECUTE format('SELECT setval(%L, %s);', r.seq, max_val);
    END IF;
  END LOOP;
END;
$$;
