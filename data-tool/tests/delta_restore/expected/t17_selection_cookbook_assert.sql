DO $$
DECLARE
  v_actual text[];
  c_corp_processing_include constant text := '# [corp_processing] include=new,changed';
  v_expected text[] := ARRAY[
    '# Classes: new | changed | changed_local_newer (other classes are never applyable).',
    '# Selector kinds: id: for PK tables; row: for PK-less tables; corp: only where supported.',
    '# Multiple includes union their matches; excludes subtract; --only-corps is a final intersection.',
    '#',
    '# ---------------------------------------------------------------------------',
    '# OPERATOR COOKBOOK',
    '# Everything below is commented documentation. Copy or uncomment only the',
    '# examples you intend to use. Row selectors never enable a class by themselves.',
    '# ---------------------------------------------------------------------------',
    '#',
    '# 1. Apply all NEW and CHANGED rows for a table:',
    '#',
    '# [mig_corp_batch] include=new,changed',
    '#',
    '# 2. Apply only NEW rows for a table:',
    '#',
    '# [mig_corp_batch] include=new',
    '#',
    '# 3. Apply only CHANGED rows for a table:',
    '#',
    '# [corp_processing] include=changed',
    '#',
    '# 4. Disable a table entirely:',
    '#',
    '# [mig_corp_batch] include=',
    '#',
    '# 5. Apply specific NEW rows by staged primary key.',
    '#    Lists and inclusive ranges may be mixed:',
    '#',
    '# [mig_corp_batch] include=new,changed',
    '# [mig_corp_batch] new.rows include=id:3067,7922,8241-8242',
    '#',
    '# 6. Apply every NEW row except specific IDs:',
    '#',
    '# [mig_corp_account] include=new,changed',
    '# [mig_corp_account] new.rows exclude=id:23,100-105',
    '#',
    '# 7. Combine multiple includes, then subtract exclusions.',
    '#    Include lines are unioned; exclude lines are applied afterward:',
    '#',
    c_corp_processing_include,
    '# [corp_processing] new.rows include=id:53946-53959',
    '# [corp_processing] new.rows include=corp:BC0000001,BC0000002',
    '# [corp_processing] new.rows exclude=id:53947,53952',
    '#',
    '# 8. Apply specific CHANGED rows:',
    '#',
    c_corp_processing_include,
    '# [corp_processing] changed.rows include=id:881,900-905',
    '#',
    '# 9. Apply CHANGED rows for selected corporations:',
    '#',
    c_corp_processing_include,
    '# [corp_processing] changed.rows include=corp:BC0000001,BC0000002',
    '#',
    '# 10. Explicitly opt into locally newer rows.',
    '#     CAUTION: these may overwrite more recently modified local values:',
    '#',
    '# [corp_processing] include=new,changed,changed_local_newer',
    '# [corp_processing] changed_local_newer.rows include=id:901',
    '#',
    '# 11. Select rows from a PK-less table using the staged row ordinal:',
    '#',
    '# [email_domain_groups] include=new',
    '# [email_domain_groups] new.rows include=row:4,10-15',
    '#',
    '# 12. Parent dependency reminder:',
    '#     A selected NEW child whose preserved parent is also NEW requires that',
    '#     parent row to remain selected.',
    '#',
    '# [mig_batch] include=new',
    '# [mig_batch] new.rows include=id:152',
    '# [mig_corp_account] include=new',
    '# [mig_corp_account] new.rows include=id:23643-23658',
    '#',
    '# 13. --only-corps is an additional global intersection:',
    '#',
    '# ./delta_restore_extract.sh ... ' || chr(92),
    '#   --selection-file selection.conf ' || chr(92),
    '#   --only-corps selected_corps.txt'
  ];
  v_line_no integer;
BEGIN
  SELECT array_agg(line ORDER BY ord)
    INTO v_actual
  FROM delta_ctl.render_selection_cookbook() WITH ORDINALITY AS cookbook(line, ord);

  IF v_actual IS DISTINCT FROM v_expected THEN
    FOR v_line_no IN 1..GREATEST(
      COALESCE(array_length(v_expected, 1), 0),
      COALESCE(array_length(v_actual, 1), 0))
    LOOP
      IF v_expected[v_line_no] IS DISTINCT FROM v_actual[v_line_no] THEN
        RAISE EXCEPTION 'selection cookbook differs at line %: expected=% actual=%',
          v_line_no, v_expected[v_line_no], v_actual[v_line_no];
      END IF;
    END LOOP;
    RAISE EXCEPTION 'selection cookbook array metadata differs despite equal lines';
  END IF;
END $$;
