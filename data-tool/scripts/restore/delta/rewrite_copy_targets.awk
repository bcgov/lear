# Rewrite pg_restore COPY targets from public.<table> to delta_stage.<table>.
# Also captures the dump column list as: table<TAB>col1,col2,...
#
# Contract:
#   - expected=<path> contains one expected table name per line.
#   - sidecar=<path> is overwritten with captured columns.
#   - COPY headers must look like: COPY public.<lowercase_ident> (cols) FROM stdin;
#   - Every expected table must be seen exactly once.
#   - Client-version-only SET commands unsupported by older targets may be
#     neutralized outside COPY data only.

function fail(message) {
  fatal = 1
  print "rewrite_copy_targets.awk: " message > "/dev/stderr"
  print "SELECT 1/0 AS rewrite_copy_targets_failed;"
  exit 2
}

function trim(value) {
  gsub(/^[[:space:]]+/, "", value)
  gsub(/[[:space:]]+$/, "", value)
  return value
}

BEGIN {
  state = "OUTSIDE"

  if (expected == "") {
    fail("missing -v expected=<path>")
  }
  if (sidecar == "") {
    fail("missing -v sidecar=<path>")
  }

  while ((getline table < expected) > 0) {
    table = trim(table)
    if (table == "" || table ~ /^#/) {
      continue
    }
    if (table !~ /^[a-z_][a-z0-9_]*$/) {
      fail("invalid expected table identifier: " table)
    }
    if (wanted[table]) {
      fail("duplicate expected table: " table)
    }
    wanted[table] = 1
    expected_count++
  }
  close(expected)

  # Truncate the sidecar before the first capture.
  printf "" > sidecar
  close(sidecar)
}

{
  line = $0

  if (state == "OUTSIDE") {
    # pg_dump/pg_restore from newer PostgreSQL clients can emit this SET, but
    # older target servers reject the parameter. It is only a timeout guard, and
    # delta session SQL already disables relevant timeouts, so skip it outside
    # COPY data while leaving payload rows untouched.
    if (line ~ /^SET transaction_timeout = /) {
      print "-- skipped unsupported client-only setting: " line
      next
    }

    if (line ~ /^COPY public\./) {
      if (line !~ /^COPY public\.[a-z_][a-z0-9_]*[[:space:]]*\(.+\) FROM stdin;$/) {
        fail("unexpected COPY header form: " line)
      }

      table = line
      sub(/^COPY public\./, "", table)
      sub(/[[:space:]]*\(.*/, "", table)

      if (!wanted[table]) {
        fail("COPY header table is not expected: " table)
      }
      if (seen[table]) {
        fail("duplicate COPY stream for table: " table)
      }
      seen[table] = 1
      seen_count++

      cols = line
      sub(/^COPY public\.[a-z_][a-z0-9_]*[[:space:]]*\(/, "", cols)
      sub(/\) FROM stdin;$/, "", cols)
      gsub(/[[:space:]]*,[[:space:]]*/, ",", cols)
      cols = trim(cols)

      print table "\t" cols >> sidecar
      close(sidecar)

      sub(/^COPY public\./, "COPY delta_stage.", line)
      print line
      state = "INSIDE"
      next
    }

    print line
    next
  }

  print line
  if (line == "\\.") {
    state = "OUTSIDE"
  }
}

END {
  if (fatal) {
    exit 2
  }
  if (state != "OUTSIDE") {
    print "rewrite_copy_targets.awk: input ended inside COPY data" > "/dev/stderr"
    exit 2
  }
  if (seen_count != expected_count) {
    for (table in wanted) {
      if (!seen[table]) {
        print "rewrite_copy_targets.awk: expected table was not seen: " table > "/dev/stderr"
      }
    }
    print "SELECT 1/0 AS rewrite_copy_targets_missing_expected_table;"
    exit 2
  }
}
