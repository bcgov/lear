# Produce a fixed-width companion for a canonical detail TSV.
#
# Invoke with the same non-empty input path twice:
#   awk -v max_width=40 -f align_details.awk details.tsv details.tsv
#
# The first pass measures column widths; the second pass renders the output.
# Comment lines are not included in width calculations and pass through verbatim.

BEGIN {
  FS = "\t"
  if (max_width == "" || max_width !~ /^[0-9]+$/ || max_width < 1) {
    max_width = 40
  }
}

NR == FNR {
  if ($0 ~ /^#/) {
    next
  }

  if (NF > column_count) {
    column_count = NF
  }
  for (i = 1; i <= NF; i++) {
    cell_width = length($i)
    if (cell_width > max_width) {
      cell_width = max_width
    }
    if (cell_width > widths[i]) {
      widths[i] = cell_width
    }
  }
  next
}

function clipped(value) {
  if (length(value) <= max_width) {
    return value
  }
  return substr(value, 1, max_width - 1) "…"
}

function dashes(count,    result, i) {
  result = ""
  for (i = 0; i < count; i++) {
    result = result "-"
  }
  return result
}

function render_fields(underline,    result, value, i) {
  result = ""
  for (i = 1; i <= column_count; i++) {
    value = underline ? dashes(widths[i]) : clipped(i <= NF ? $i : "")
    if (i < column_count) {
      result = result sprintf("%-" widths[i] "s", value) "  "
    } else {
      result = result value
    }
  }
  print result
}

$0 ~ /^#/ {
  print
  next
}

{
  render_fields(0)
  if (!header_written) {
    render_fields(1)
    header_written = 1
  }
}
