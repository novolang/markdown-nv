#!/usr/bin/env bash
# tools/spec_run.sh — the whole CommonMark specification, and GFM's
# table, strikethrough and autolink examples, through this package.
#
# Usage: bash tools/spec_run.sh <spec.json> [gfm_spec.txt]
#
# Builds tests/spec_harness.nv as a program inside a copy of the
# package and prints each example whose HTML differs.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PKG="$(cd "$HERE/.." && pwd)"
NOVO="${NOVO:-$HOME/.novo/bin/novo}"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/markdown-nv-spec.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT
cp -r "$PKG" "$WORK/pkg"
rm -rf "$WORK/pkg/_novo"
cp "$PKG/tests/spec_harness.nv" "$WORK/pkg/src/spec_harness.nv"
printf '\n[[bin]]\nname = "spec-harness"\npath = "src/spec_harness.nv"\n' >>"$WORK/pkg/novo.toml"
( cd "$WORK/pkg" && NOVO_LEAK_CHECK=0 timeout 900 "$NOVO" pkg build --bin spec-harness ) \
    >"$WORK/build.log" 2>&1 || { echo "the harness did not build"; grep -E 'error' -A3 "$WORK/build.log" | head -20; exit 1; }
python3 - "$1" "$WORK/cm.txt" <<'PY'
import json, sys
ex = json.load(open(sys.argv[1]))
open(sys.argv[2], 'w').write(''.join('\x01%d\x02%s\x03%s' % (e['example'], e['markdown'], e['html']) for e in ex))
PY
"$WORK/pkg/spec-harness" "$WORK/cm.txt" commonmark
if [ $# -gt 1 ]; then
  python3 - "$2" "$WORK/gfm.txt" <<'PY'
import re, sys
text = open(sys.argv[1]).read()
fence = '`' * 32
out = []
for m in re.finditer(fence + r' example (table|strikethrough|autolink|tasklist)\n(.*?)\n\.\n(.*?)' + fence, text, re.S):
    md = m.group(2).replace('→', '\t')
    html = m.group(3).replace('→', '\t')
    if md: md += '\n'
    out.append('\x01%d\x02%s\x03%s' % (len(out) + 1, md, html))
open(sys.argv[2], 'w').write(''.join(out))
PY
  "$WORK/pkg/spec-harness" "$WORK/gfm.txt" gfm
fi
