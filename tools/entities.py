#!/usr/bin/env python3
"""Write src/mdentity.nv, the HTML5 named character references.

CommonMark section 2.5 recognises every entity name in the HTML5
specification's table, and only those.  Python's html.entities.html5 is
that table.  The names without a closing semicolon are the legacy forms
HTML allows and CommonMark does not, so they are left out.

Run from the package root:  python3 tools/entities.py
"""
import html.entities
import subprocess

entries = []
for name, text in sorted(html.entities.html5.items()):
    if not name.endswith(';'):
        continue
    cps = ','.join('%x' % ord(c) for c in text)
    entries.append('|%s%s' % (name, cps))
table = ''.join(entries) + '|'

out = '''// mdentity.nv — the HTML5 named character references.
//
// Written by tools/entities.py from the HTML5 specification's table;
// do not edit by hand.  CommonMark section 2.5 recognises exactly these
// names.  Each entry is `|name;` followed by the codepoints it stands
// for, in hexadecimal and separated by commas.  %d names.

use std.str
use std.list

// The table, searched as text: an entity reference is rare in a
// document, and one string is cheaper to hold than a map built on every
// parse.
const TABLE = "%s"

// The codepoints the reference `&name;` stands for, one or two of
// them, or an empty list when `name` is not an HTML5 entity name.
// `name` is given without the ampersand and without the semicolon.
fn lookup(name: Str) -> [Int]
    var out: [Int] = []
    match str.index(TABLE, "|" + name + ";")
        None    =>
            return out
        Some(k) =>
            var at = k + str.len(name) + 2
            var v = 0
            for _ in 0..16
                let c = str.byte_at_or(TABLE, at, 124)
                if c == 124 or c == 44
                    list.push(out, v)
                    v = 0
                    if c == 124
                        break
                elif c >= 97
                    v = v * 16 + (c - 87)
                else
                    v = v * 16 + (c - 48)
                at = at + 1
    out
''' % (len(entries), table)
open('src/mdentity.nv', 'w').write(out)
subprocess.run(['novo', 'fmt', 'src/mdentity.nv'], check=False)
