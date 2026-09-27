# Changelog

All notable changes to markdown-nv are recorded here. The format is
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
package follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
with the pre-1.0 rule that a breaking change bumps the MINOR number.

## 0.1.0 — 2026-09-27

The first implementation of the interface published as 0.0.1: all 652
examples of CommonMark 0.31.2 and the GFM table, strikethrough and
autolink examples render as their specifications say.

### Changed, breaking

- `MdParser` reads the whole document when it is made and gains
  `events`, `spans`, `definitions` and `lines`; `at` is the index of the
  next event.  CommonMark needs the whole document before it can
  resolve a reference link or say whether a list is loose.
- `MdLink` gains `prefix`, the `mailto:` or `http://` an autolink's
  destination is written with, and `autolink`, since an autolink's
  destination is taken as written.
- `MdHtmlOptions` gains `markdown`, the options `render`, `render_str`
  and `to_plain` read the source with.  `commonmark_options()` reads
  strict CommonMark; `default_options()` reads the parser's defaults.
  `xhtml` is on in both, since the specification's examples write
  `<br />`.
- Every function that appends to a caller's buffer takes it as a `var`
  parameter: `render`, `render_events`, `render_tree`, `escape_text`,
  `escape_attr` and `to_plain`.
- `escape_text` escapes `"` as well, as the renderer does in text.
- `reference_definitions` answers the label of each definition.
- `is_unicode_whitespace` is the specification's definition, the Zs
  category and four controls, rather than the White_Space property.

### Behaviour the interface left open

- Task list markers are written as the GFM specification writes them,
  `<input disabled="" type="checkbox">`.  Footnote definitions are
  written in place, as pulldown-cmark writes them, and numbered in the
  order they are first referenced.
- An extended autolink stops at `*`, `~`, a bracket or a backtick as
  well as at whitespace and `<`, since GFM finds them in text nodes
  after the inline parse.  `www.` counts toward the period a domain
  needs, as in cmark-gfm.
- The interface's tests expected `escape_text` of `a<b` to be seven
  bytes and a table under strict CommonMark; they now expect six bytes
  and a table under the default options.

## 0.0.3 — 2026-09-25

Every field of `MdOptions` and of `MdHtmlOptions` is now declared `var`.
Under novo 0.10.0 a field is assigned only when it is declared that way,
and the way to turn an extension on or change the rendering is to take
the defaults and set the fields that differ.  This is a change to two
public declarations, but no program that built against 0.0.2 stops
building.  Every body is still `todo()`.

## 0.0.2 — 2026-09-15

README rewritten to the package README style guide (docs/writing-a-readme.md); no change to the interface.

## 0.0.1 — 2026-09-11

The **interface**: every signature and every effect row, and no bodies.
`stability = "draft"`, and the release is recorded `implemented = false`.

### Added

- `mdparse` — the pull parser. Events carry `MdRange` byte offsets into
  the caller's source rather than copied strings, with `MdChar` beside
  `MdText` for the character references and backslash escapes that are
  not substrings of the document. `next` returns the parser rather than
  mutating it, because deciding whether a list is loose requires
  looking past its end.
- `mdtree` — a flat-arena tree built from the same events, with
  `previous_sibling` and a whole-node `span`, for the callers that have
  to look backwards: linters, transforms, and anything that rewrites
  the original document.
- `mdhtml` — the renderer, appending to a buffer the caller owns.
  `MdUrlRule` is a `fn(Str) -> Bool` the caller supplies, and
  `web_urls()` is the novo-lang registry's own `safe_href` landed as a
  value.

### Known

- **Raw HTML is escaped by default, which is not what CommonMark
  says.** The spec's answer is reachable as `commonmark_options()` and
  is what the spec suite runs under; the default is the safe one
  because the input to a Markdown renderer is usually a document
  somebody else wrote.
- **There is no error type**, because CommonMark has no parse errors.
  A document past an `MdLimits` bound renders the excess as literal
  text and sets `parser_truncated`.
- **unicode-nv is a path dependency in this tree** and becomes
  `unicode-nv = "^0.0.1"` at publish. A path dependency is refused by
  `novo pkg publish`.
- **No `@tier(embedded)` claim.** The surface is `Str` throughout and
  the tree is a growable list.
- **This graduates `novo_markdown_to_html`, not the site generator's
  code.** The site generator has no parser — it calls `std.markdown`
  and does four string passes over the result. The README says what the
  C renderer does that this must not lose, and what it does not do.

### Design notes

What graduates into this package is `novo_markdown_to_html` in
`bin/novo_rt.c`, about 750 lines behind `std.markdown`, which renders
every README on the registry and every page on novo-lang.org today.
Five behaviours of it must not be lost: HTML comments stripped before
rendering with fenced code exempted, because generated tables are
bracketed with marker comments; soft-wrapped lines accumulated into one
block before the inline pass, because the documentation is hard-wrapped
at 72 columns; Pandoc `{#id}` heading anchors, which the documentation's
deep links are written against; a bounded inline recursion depth, which
`MdLimits` generalises; and the left- and right-flanking rules for `_`
runs.

What the C renderer does not do, and this package does: reference
links, nested lists, the loose and tight distinction, setext headings,
indented code blocks, `<ol start=>`, a real delimiter stack, character
references, and any surface other than one function from `Str` to
`Str`.

The migration order when the bodies land: the site generator first, as
it is one call plus four passes of string surgery over rendered HTML
that all become event handling; then the website's package pages; and
only then `std.markdown.to_html` as a thin call into this package, at
which point the C renderer and its `strip`, `extract_links`,
`extract_code`, `extract_sections` and `extract_tables` helpers go, each
being a walk of the event stream. The Markdown builders stay where they
are: they write Markdown rather than read it.

The module names. `markdown` is a standard-library module name, so this
package may not own its own name, and `html` belongs to html-nv. Hence
`mdparse`, `mdtree` and `mdhtml`, and the `Md` prefix on every public
type for the same reason.
