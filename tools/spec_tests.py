#!/usr/bin/env python3
"""Write tests/spec_tests.nv from the CommonMark and GFM specifications.

Every example of CommonMark 0.31.2 (spec.json, 652 examples) and the
table, strikethrough and autolink examples of the GFM specification
(cmark-gfm's test/spec.txt) become assertions: the Markdown, rendered
with `mdhtml.commonmark_options()` (and the GFM options for the GFM
examples), must be the HTML the specification gives, byte for byte.
One test per section of the specification.

Run from the package root:
  curl -O https://spec.commonmark.org/0.31.2/spec.json
  curl -o gfm_spec.txt https://raw.githubusercontent.com/github/cmark-gfm/master/test/spec.txt
  python3 tools/spec_tests.py spec.json gfm_spec.txt
The output is passed through `novo fmt`.
"""
import json
import re
import subprocess
import sys


def nv(s):
    out = s.replace('\\', '\\\\').replace('"', '\\"').replace('$', '\\$')
    return '"' + out.replace('\n', '\\n').replace('\t', '\\t').replace('\r', '\\r') + '"'


def ident(section):
    return re.sub(r'[^a-z0-9]+', '_', section.lower()).strip('_')


def main():
    examples = json.load(open(sys.argv[1]))
    gfm = []
    text = open(sys.argv[2]).read()
    fence = '`' * 32
    for m in re.finditer(fence + r' example (table|strikethrough|autolink)\n(.*?)\n\.\n(.*?)' + fence,
                         text, re.S):
        md = m.group(2).replace('\u2192', '\t')
        if md:
            md += '\n'
        gfm.append((m.group(1), md, m.group(3).replace('\u2192', '\t')))

    sections = []
    for e in examples:
        if not sections or sections[-1][0] != e['section']:
            sections.append((e['section'], []))
        sections[-1][1].append(e)

    lines = [
        '// spec_tests.nv — every example of the CommonMark specification, and',
        "// the GFM specification's table, strikethrough and autolink examples.",
        '//',
        '// Written by tools/spec_tests.py from CommonMark 0.31.2 (%d examples)' % len(examples),
        "// and cmark-gfm's test/spec.txt (%d examples); do not edit by hand." % len(gfm),
        '// Each example is Markdown and the HTML the specification says it',
        '// renders to, compared byte for byte.',
        '',
        'use std.test',
        'use mdparse',
        'use mdhtml',
        '',
        'fn commonmark(md: Str) -> Str',
        '    mdhtml.render_str(md, mdhtml.commonmark_options())',
        '',
        'fn gfm(md: Str) -> Str',
        '    var o = mdhtml.commonmark_options()',
        '    o.markdown = mdparse.gfm_options()',
        '    mdhtml.render_str(md, o)',
        '',
    ]
    for name, exs in sections:
        lines.append('@test')
        lines.append('fn test_%s() [io]' % ident(name))
        for e in exs:
            lines.append('    test.case("example %d")' % e['example'])
            lines.append('    test.assert(commonmark(%s)' % nv(e['markdown']))
            lines.append('                == %s)' % nv(e['html']))
        lines.append('')
    for kind in ('table', 'strikethrough', 'autolink'):
        lines.append('@test')
        lines.append('fn test_gfm_%s() [io]' % kind)
        k = 0
        for (kk, md, html) in gfm:
            if kk != kind:
                continue
            k += 1
            lines.append('    test.case("GFM %s example %d")' % (kind, k))
            lines.append('    test.assert(gfm(%s) == %s)' % (nv(md), nv(html)))
        lines.append('')
    open('tests/spec_tests.nv', 'w').write('\n'.join(lines))
    subprocess.run(['novo', 'fmt', 'tests/spec_tests.nv'], check=False)


if __name__ == '__main__':
    main()
