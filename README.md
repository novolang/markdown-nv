# markdown-nv

**Status: NOT IMPLEMENTED — interface only.**

Every public function below is published with its signature and its
effect row, and every body is `todo()`. Installing this package works;
calling it panics with `not implemented`.

## What this is

CommonMark plus GFM tables, as three surfaces over one parser.

- `mdparse` — a pull parser: events out, one at a time, over a source
  string the caller keeps;
- `mdtree` — the same document as a flat-arena tree, for the callers
  that have to look backwards;
- `mdhtml` — the HTML renderer, appending to a buffer the caller owns.

```
novo pkg add markdown-nv
novo pkg build
novo test
```

## The one example that will work — a site build

```novo ignore
use mdhtml

// 58 pages, one buffer, and the only effect is the caller's write.
fn render_all(pages: [Str]) -> [u8]
    let options = mdhtml.default_options()
    var out = []
    for page in pages
        out = mdhtml.render(out, page, options)
    out
```

## The load-bearing interface

```novo ignore
pub fn next(p: MdParser) -> ?MdStep []

pub struct MdStep
    parser: MdParser
    event: MdEvent

pub struct MdRange          // a byte range into the caller's source
    start: Int
    end: Int
```

**Every event carries a byte range, not a string.** The parser
allocates nothing per event; a caller that wants text slices the source
it already has. That is the difference between a parser that can be
`core` and one that cannot, and it is what lets a link checker walk a
document without building a copy of it.

**The honest exception is `MdChar`.** Some text in a Markdown document
is not a substring of the document: `&amp;` is one ampersand, `\*` is
one asterisk, and neither appears in the source as the character it
means. A parser that returned only ranges would have to lie about
those, and one that returned strings would allocate for every document.
So there are two text events — `MdText(MdRange)` for the verbatim runs
and `MdChar(Int)` for the decoded ones. pulldown-cmark solves the same
problem with a copy-on-write string; this is the same answer without
the string.

**`next` returns the parser rather than mutating it**, so a caller can
look at an event and decide not to consume it. That is not a stylistic
choice: deciding whether a list is loose or tight requires looking past
the end of the list, and a parser that could not be held still could
not do it.

**There is no error type, and no `Result` anywhere.** CommonMark has no
parse errors — every sequence of bytes is a valid document. What
replaces them is a bounded machine: `MdLimits` caps the nesting depth,
the reference definitions and the open delimiters; a document past a
bound has the excess rendered as literal text; and `parser_truncated`
says so afterwards. A `core` parser with unbounded recursion is a
`core` parser with a stack overflow, and every pathological CommonMark
input is one line long.

## Which of the two existing implementations this graduates

The plan's row says *the site generator's parser graduates*. There are
two candidates, and it is worth being exact, because neither of them is
a parser in the sense this package is.

**The site generator has no Markdown parser.**
`orbit/static-site-generator/src/main.nv` calls `markdown.to_html` and
then does string surgery on the result. What it owns is the surgery,
not the parsing: `wrap_tables` substitutes `<table>\n`,
`rewrite_md_hrefs` scans the output for `href="`, `mark_effects`
replaces every literal `[io]` in the HTML with a span, and
`page_outline` re-scans the *Markdown* for `##` lines with its own
fence tracker so it can build a table of contents. Four passes over
rendered HTML, doing four things a parser already knew.

**The parser is `novo_markdown_to_html` in `bin/novo_rt.c`** — about
750 lines of C behind `std.markdown` — and that is what graduates. It
is a line-oriented block scanner with a pending-inline buffer and a
hand-written inline pass. It serves every README on the registry and
every page on novo-lang.org today.

**What the C renderer does that this package must not lose:**

| it does | why it matters |
| --- | --- |
| strips HTML comments before rendering, exempting fenced code | `gen_stdlib_docs.py` brackets its generated tables with `<!-- BEGIN … -->` markers, and 53 pages were displaying them as body text |
| accumulates soft-wrapped lines into one block before rendering inline | the documentation is hard-wrapped at 72 columns, and 67 pages showed a stray `**` where a wrap split a delimiter |
| Pandoc `{#id}` heading anchors | the documentation's deep links are written against them |
| a bounded inline recursion depth | it is the same protection `MdLimits` generalises |
| left- and right-flanking rules for `_` runs | added 2026-09-10; without it `_emphasis_` rendered as literal underscores |

**What it does not do, and this package does:**

- **No reference links.** `[foo][bar]` with `[bar]: /url` elsewhere is
  not resolved; it renders as literal brackets.
- **No nested lists.** A list is a flat run of `<li>`; an indented
  sub-list becomes items of the same list.
- **No loose/tight distinction.** Every item's content is inline,
  never a paragraph.
- **No setext headings**, no indented code blocks, and no `<ol start=>`
  — an ordered list always begins at 1.
- **The inline pass has no delimiter stack.** `**` and `*` are matched
  by "find the next closer whose preceding character is not
  whitespace", so `***both***` and the CommonMark precedence rules are
  approximations, and `___` is deliberately left as text rather than
  guessed at.
- **No character references.** `&amp;` reaches the page as `&amp;`
  because the whole document is escaped before inline substitution
  runs, which is also why no tag a README writes can survive.
- **No events, no tree, no positions.** It is one function from `Str`
  to `Str`, and the only way to ask it anything is to search its
  output — which is exactly what the site generator and the registry
  both do.

**What happens to the C renderer.** Nothing, until this package has
bodies. `std.markdown` keeps its surface, the site keeps building, and
the registry keeps rendering READMEs. When the implementation lands,
the migration is three steps and the order matters: the site generator
moves first (it is one call and four string passes, all of which become
event handling), then `orbit/website`'s package pages, and only then
does `std.markdown.to_html` become a thin call into this package — at
which point the 750 lines of C go, and `novo_markdown_strip`,
`extract_links`, `extract_code`, `extract_sections` and
`extract_tables` go with them, because every one of them is a walk of
the event stream.

The builders — `markdown.heading`, `markdown.bold`, `markdown.table`
and their siblings — are a different package's job: they *write*
Markdown rather than read it, and they stay where they are.

## The dependency, and why it is genuine

**unicode-nv**, and only because CommonMark is defined in terms of
Unicode in three places where an ASCII approximation renders a
different document:

- **§ 6.2, the flanking rules.** "Left-flanking delimiter run" is
  written in terms of *Unicode whitespace character* and *Unicode
  punctuation character*, and since CommonMark 0.30 the second means
  the P categories **and** the S categories. That is
  `uclass.is_whitespace`, `uclass.is_punctuation` and
  `uclass.is_symbol`, and it decides whether a `*` opens emphasis,
  closes it, or is literal text.
- **§ 4.7, link reference matching.** Labels are compared after
  *Unicode case fold*, so `[STRASSE]` has to find `[straße]: /url`.
  `str.lower` gets exactly that case wrong; `ucase.fold` is what the
  spec means.
- **§ 2.1.** A character is a Unicode codepoint, which makes
  `uclass.is_valid_scalar` the check on a numeric character reference —
  `&#xD800;` is not a character and must become U+FFFD.

Those three are published as `mdparse.is_unicode_whitespace`,
`mdparse.is_unicode_punctuation` and `mdparse.reference_label_key`, so
a consumer comparing this parser with another one can ask the same
questions it asked.

`core`, so `dep-layer` holds. It is a path dependency in this tree and
becomes `unicode-nv = "^0.0.1"` at publish; unicode-nv is published
first, because a package cannot be published ahead of what it depends
on.

**html-nv is not a dependency**, and the decision is deliberate. This
renderer needs to escape five characters and to decide whether a URL
may be emitted. The first is five `match` arms with no table, and
making a `text` package depend on a `web` package for them inverts the
direction a reader expects. The second is a *policy*, and a policy
belongs to the caller: `MdUrlRule` is a `fn(Str) -> Bool` the caller
supplies, the same shape textwrap-nv uses for its width rule, and
`web_urls()` is the supplied default. A caller that wants html-nv's
full sanitiser composes the two — render, then parse, then sanitise —
and that composition is the honest cost of wanting a tree-level
allow-list.

## The two places this disagrees with CommonMark, on purpose

Both are about whose document is being rendered, and both are
reachable: `commonmark_options()` is the spec's answer, named, and it
is what the spec suite runs under.

**Raw HTML is escaped by default.** CommonMark says to pass it
through. A renderer whose input is a README somebody published is a
renderer whose input is hostile, and passing `<script>` through is that
document running code on the reader's origin. `MdRawHtml` has three
values — `RawEscape` (the default), `RawPass` (the spec), `RawDrop`
(for a plain-text summary) — so the choice is visible in a review.

**A link destination has to pass a rule.** `javascript:` in an `href`
is script on the origin, and a link's destination is the one thing a
document author writes that reaches the page as markup rather than as
text. `web_urls()` is the default: `http:`, `https:`, `mailto:`, a `#`
fragment, or a `/` site-absolute path, and everything else becomes `#`.

That default is the novo-lang registry's own `safe_href`, which is
twenty lines in `orbit/website/src/packages.nv` today, landed here as a
value so the next renderer does not write it again. It is also safe
there only by accident of composition — `sanitize_hrefs` rewrites
`href="` occurrences by searching the rendered HTML, which is exact
only because `markdown.to_html` escapes the whole document first and
emits an `href` from exactly one place. Doing it during rendering needs
no such argument.

## The layer, and the device claim

`core` — no effects. A parser over a string the caller already holds,
events that are pairs of integers, and a renderer that appends to the
caller's buffer.

**No `@tier(embedded)` claim, and none is intended.** The surface is
`Str` throughout, the tree is a growable list, and the reference-
definition table is a map — none of which belongs in firmware. The
audit's `core-embedded` row passes as *makes no device claim*, which is
the honest reading. unicode-nv, which this depends on, does make a
claim, and it covers the half of unicode-nv this package does not use.

## Where the names come from, and the ones that were taken

Public type names are unique across the whole assembly, dependencies
included.

| here | the obvious name | why not |
| --- | --- | --- |
| `MdEvent` | `Event` | an orbit package already publishes `Event`, and `EventKind` is a standard-library type |
| `MdTag` | `Tag` | generic enough that html-nv would want it too, in this same lane |
| `MdRange` | `Range`, `Span` | `ElfRange` and `ZipRange` are the precedent; `Span` is a module name already in use |
| `MdParser` | `Parser` | an orbit package publishes `Parser`, and ansi-nv publishes `AnsiParser` for the same reason |
| `MdNode` | `Node` | certain to collide — html-nv wants it in this same lane |
| `MdDoc` | `Document` | `TomlDoc`, `YamlDoc`, `JsonDoc` and `XmlDoc` are the standard library's precedent for exactly this |
| `MdLink` | `Link` | generic |
| `MdOptions` | `Options` | generic; and `PngOptions`, `QoiOptions` and `JpegOptions` are the precedent |
| module `mdparse`, `mdtree`, `mdhtml` | `markdown`, `parse`, `tree`, `html` | **`markdown` is a standard-library module name** — `use text.markdown` resolves to it — so this package may not own its own name; `html` is html-nv's, in this same lane |

The module row is the one that cost something: `novo pkg init
--interface markdown-nv` scaffolds `src/markdown.nv`, which is exactly
the name the publishing rules forbid, and the build does not refuse it.
That is filed as a toolchain defect rather than worked around.

## The reference implementation

**pulldown-cmark** for the whole shape: a pull parser, events with
borrowed text, the tree as a separate concern, and the HTML renderer as
a consumer of the events rather than the core. **cmark** for the tree
model and the arena. **comrak** for the GFM extension set and for
keeping the extensions as named options rather than a dialect.
**`novo_markdown_to_html`** for what the documentation this package
renders actually needs, which is where the HTML-comment stripping, the
soft-wrap accumulation and the Pandoc anchors come from.

The oracle is the CommonMark spec's own appendix — 652 examples, each
an input and the HTML it must produce — plus the GFM spec's table,
strikethrough, task-list and footnote sections. `tests/` carries the
examples that explain what the rules are *for*; the generated
whole-appendix suite lands with the bodies.

Deliberately left out, and where it goes instead:

- **Writing Markdown.** `markdown.heading`, `markdown.bold` and their
  siblings in `std.markdown` build documents; this package reads them.
  A builder is a different package.
- **Syntax highlighting.** A fenced block's info string is reported;
  what to do with it is the caller's.
- **Math, definition lists, admonitions, front matter.** Not in
  CommonMark and not in GFM. Front matter in particular is the site
  generator's own `split_front`, and it is three lines because the
  format is `key: value` — it does not need a package.
- **Sanitising a tree.** html-nv, which is where an allow-list belongs.

## Status

Every function is `todo()`. Three suites, all red, all for the same
reason — every assertion reaches `not implemented: markdown-nv.<fn>`,
which is the expected result until the bodies land.

```
novo test --isolate tests/mdparse_tests.nv   # the events, the ranges, the bounds
novo test --isolate tests/mdhtml_tests.nv    # the CommonMark and GFM spec examples
novo test --isolate tests/mdtree_tests.nv    # the tree, and that it replays as events
```

`novo doc` renders and its examples compile.
