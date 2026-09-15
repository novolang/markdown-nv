# markdown-nv

Markdown is a plain-text format that turns punctuation into structure:
a line starting with `#` is a heading, text between asterisks is
emphasised. The precise definition is
[CommonMark](https://spec.commonmark.org/0.31.2/), and
[GitHub Flavored Markdown](https://github.github.com/gfm/) adds tables,
strikethrough, task lists, footnotes and autolinks on top of it. This
package implements CommonMark and those extensions for novo-lang, as a
parser, a document tree and an HTML renderer. It is built on
[unicode-nv](https://novo-lang.org/packages/unicode-nv).

**Status: NOT IMPLEMENTED — interface only.** Every function is declared
with its full signature, but every body is a `todo()` that panics when
called. The package is published so its design can be reviewed and
depended on before it is implemented. Version 0.1.0 will be the first
working release.

## What it is

A **pull parser** hands out one **event** at a time and lets the caller
decide what to do with it. The events here are the start of a tag, the
end of a tag, a run of text, a decoded character, a line break and a
few others. A **tag** is a heading, a paragraph, a list, a list item, a
block quote, a code block, a table, a link, emphasis and so on.

Every event carries an **`MdRange`**, which is a pair of byte offsets
into the source string the caller passed in. Nothing is copied. A
caller that wants the text slices its own source.

Some text in a Markdown document is not a substring of the document.
`&amp;` means one ampersand and `\*` means one asterisk, and neither
appears in the source as the character it stands for. Those arrive as a
separate event, `MdChar`, carrying the codepoint.

A **link reference definition** is a line such as `[bar]: /url` that
gives a destination a name, so that `[foo][bar]` elsewhere in the
document can use it. CommonMark matches the two after case folding.

An **info string** is the word after the opening fence of a code block,
usually a language name.

A **delimiter run** is a sequence of `*` or `_` characters. Whether one
opens emphasis, closes it, or is literal text depends on what is on
either side of it, which CommonMark calls **left-flanking** and
**right-flanking**.

**CommonMark has no parse errors.** Every sequence of bytes is a valid
document. What replaces error handling here is a set of bounds: how
deeply containers may nest, how many reference definitions are
remembered, and how many delimiters the emphasis matcher holds open. A
document past a bound has the excess rendered as literal text, and the
parser records that it happened.

## Install

```
novo pkg add markdown-nv
```

## Example

```novo
use mdparse
use mdhtml

fn main() [io]
    let source = "# Title\n\nSome *emphasised* text.\n"

    // Render the whole document to HTML. Raw HTML in the source is
    // escaped, and a link destination has to pass the default URL
    // rule before it reaches the page.
    println(mdhtml.render_str(source, mdhtml.default_options()))

    // The same document as events, for a caller that inspects it
    // rather than rendering it. Every event carries byte ranges into
    // `source`, so nothing here is copied.
    var p = mdparse.parser(source)
    var more = true
    while more
        match mdparse.next(p)
            Some(step) => p = step.parser
            None       => more = false
```

Build and test with `novo pkg build` and `novo test`. Today `novo test`
fails on purpose: every test reaches a
`not implemented: markdown-nv.<module>.<fn>` panic. The tests are the
specification the implementation will have to satisfy.

## What the package contains

| Module | Contents |
| --- | --- |
| `mdparse` | The pull parser: the event and tag types, the options and bounds, and the three Unicode predicates CommonMark is defined over. |
| `mdtree` | The same document as a flat array of nodes with parent and child indices, for a caller that has to look backwards. |
| `mdhtml` | The HTML renderer, the escaping, the URL rule and the heading-anchor generator, all appending to a buffer the caller owns. |

## How to choose an entry point

**`mdhtml.render_str` is the one-line path.** Source in, HTML out.
`mdhtml.render` appends to a buffer you own, which is what a site
generator rendering many pages into one buffer wants.

**`mdparse.parser` then `mdparse.next` is the streaming path.** Use it
when you are looking for something rather than rendering: a link
checker, a table-of-contents builder, a word count. It allocates
nothing per event.

**`mdtree.build` is for a caller that has to look backwards.** The tree
is a flat array of nodes with indices, so `children`, `headings`,
`links` and `code_blocks` are walks over it. `mdtree.events` replays
the tree as the event list, and `mdhtml.render_tree` renders from it.

**`mdhtml.to_plain` throws the markup away.** It is the path for a
search index or a summary.

**`mdparse.next` returns the parser rather than changing it.** A caller
can therefore look at an event and decide not to consume it. Deciding
whether a list is loose or tight requires looking past the end of the
list, so this is a requirement rather than a preference.

## The rules a user needs

1. **Every event carries byte ranges into your source, and you must
   keep the source alive.** `mdparse.slice` turns a range into a
   string when you want one.
2. **Text arrives as two different events.** `MdText` carries a range
   of verbatim source. `MdChar` carries one decoded codepoint, for a
   character reference or a backslash escape, because those are not
   substrings of the document. A caller that handles only the first
   loses every escaped character.
3. **Raw HTML is escaped by default.** CommonMark section 6.10 says to
   pass it through, and this package does not, because the usual input
   is a document somebody else wrote. `MdRawHtml` has three values:
   `RawEscape` is the default, `RawPass` is the specification's
   behaviour, and `RawDrop` removes it. `mdhtml.commonmark_options()`
   selects the specification's answer for the whole renderer.
4. **A link destination has to pass a rule before it is emitted.**
   `MdUrlRule` is a function from a string to a boolean plus the text
   to substitute when it refuses. `web_urls()` is the default and
   admits `http:`, `https:`, `mailto:`, a `#` fragment and a `/`
   site-absolute path. Everything else becomes `#`. `any_url()` turns
   the check off. A link destination is the one thing a document author
   writes that reaches the page as markup rather than as text.
5. **The parser is bounded, and the bounds are visible.** `MdLimits`
   caps nesting at 64, reference definitions at 4096 and open
   delimiters at 4096. Excess is rendered as literal text and
   `mdparse.parser_truncated` reports it afterwards. Every pathological
   CommonMark input is one line long, so an unbounded parser is a stack
   overflow.
6. **There is no `Result` anywhere in this package.** CommonMark
   section 2.2 makes every byte sequence a valid document, so there is
   nothing to refuse.
7. **Tables and heading anchors are on by default; every other
   extension is off.** `MdOptions.tables` is on because a pipe table is
   not readable as CommonMark paragraphs. `heading_anchors` is Pandoc's
   `{#id}` syntax, on because it is inert in a renderer that ignores it
   and because the documentation this package renders uses it.
   `autolinks` is off because it changes the meaning of text nobody
   marked up, and `smart_punctuation` is off because a renderer that
   rewrites punctuation inside a code sample corrupts code samples.
8. **`mdparse.commonmark_options()` turns every extension off,
   including tables.** It is the setting the specification suite runs
   under.
9. **Emphasis depends on Unicode character classes, not ASCII ones.**
   CommonMark section 6.2 defines a left-flanking delimiter run in
   terms of Unicode whitespace and Unicode punctuation, and since
   version 0.30 the second includes the symbol categories.
   `mdparse.is_unicode_whitespace` and
   `mdparse.is_unicode_punctuation` are published so another
   implementation can be asked the same questions.
10. **Link labels are matched after Unicode case folding.** CommonMark
    section 4.7. `[STRASSE]` therefore finds `[straße]: /url`. Simple
    lowercasing gets that case wrong.
    `mdparse.reference_label_key` is the normalised key.
11. **A numeric character reference that is not a valid scalar becomes
    U+FFFD.** CommonMark section 2.1 defines a character as a Unicode
    codepoint, so `&#xD800;` is not one.
12. **`mdhtml.heading_id` takes the identifiers already used.**
    Two headings with the same text need different anchors, so the
    generator is given the list of ones already seen and a prefix.
13. **`mdtree.NO_NODE` is the absent index.** `MdNode`'s parent, child
    and sibling fields carry it where there is no such node.

## What is not included

- **Writing Markdown.** `std.markdown`'s `heading`, `bold` and `table`
  builders construct documents. This package reads them.
- **Syntax highlighting.** A fenced block's info string is reported as
  a range. What to do with it is the caller's.
- **Math, definition lists, admonitions and front matter.** None of
  them is in CommonMark or in GFM. Front matter is a `key: value`
  header a caller splits off before parsing.
- **Sanitising HTML.** This renderer escapes five characters and checks
  link destinations. A tree-level allow-list over arbitrary HTML is
  [html-nv](https://novo-lang.org/packages/html-nv)'s, and a caller
  that wants one renders, parses and then sanitises.
- **Running on a microcontroller.** The package makes no such claim and
  carries no device probe. The surface is `Str` throughout, the tree is
  a growable list, and the reference-definition table is a map.
- **Reading or writing files.** The source arrives as a string and the
  output is appended to a buffer the caller owns.

## Related packages

- [unicode-nv](https://novo-lang.org/packages/unicode-nv) is the only
  dependency, and it is needed for three specification rules rather
  than for completeness: the flanking rules, link label case folding,
  and the scalar check on a numeric character reference.
- [html-nv](https://novo-lang.org/packages/html-nv) parses and
  sanitises HTML. This package does not depend on it. Escaping five
  characters is five match arms, and a sanitising policy belongs to the
  caller.
- [textwrap-nv](https://novo-lang.org/packages/textwrap-nv) wraps the
  plain text `mdhtml.to_plain` produces, for a terminal renderer.
- `std.markdown` in the standard library renders Markdown to HTML in
  one call, and builds Markdown documents. It is what the registry and
  the project website use today. It has no events, no tree and no
  positions, so the only way to ask it a question is to search its
  output.

## Tests

The reference implementation for the shape is **pulldown-cmark**: a
pull parser, events with borrowed text, the tree as a separate concern,
and the HTML renderer as a consumer of the events rather than the core.
**cmark** is the reference for the tree model. **comrak** is the
reference for the GFM extension set and for keeping the extensions as
named options rather than a dialect.

The oracle is the CommonMark specification's own appendix, 652 examples
each of which is an input and the HTML it must produce, together with
the GFM specification's table, strikethrough, task-list and footnote
sections.

```bash
novo test --isolate tests/mdparse_tests.nv   #  9 tests: events, ranges and the bounds
novo test --isolate tests/mdhtml_tests.nv    # 16 tests: the specification examples
novo test --isolate tests/mdtree_tests.nv    #  7 tests: the tree, and its event replay
```

The suites carry the examples that explain what a rule is for. The
generated whole-appendix suite lands with the bodies. The suite asserts
that no event allocates, that an escaped character arrives as `MdChar`
rather than as text, that raw HTML is escaped under the default
options and passed under `commonmark_options`, that a `javascript:`
destination is replaced, that a document past a bound is truncated and
says so, that a link label matches after case folding, and that a tree
replayed as events renders the same HTML.

The tests compile today and fail at run, each on the
`not implemented: markdown-nv.<module>.<fn>` panic that is its body.
That is the expected state of an interface release. They turn green one
at a time as bodies land.

## Implementation status

Nothing is implemented. The table lists the surface an implementation
has to fill.

| Item | Implemented |
| --- | --- |
| `mdtree.NO_NODE` | yes (it is a constant) |
| `mdparse.default_limits`, `.default_options`, `.commonmark_options`, `.gfm_options` | no |
| `mdparse.parser`, `.parser_with`, `.next`, `.parser_truncated` | no |
| `mdparse.slice`, `.line_of`, `.line_starts`, `.reference_definitions` | no |
| `mdparse.is_unicode_whitespace`, `.is_unicode_punctuation`, `.reference_label_key` | no |
| `mdtree.build`, `.build_with`, `.root`, `.count`, `.node`, `.children` | no |
| `mdtree.text`, `.inner_text`, `.find_first`, `.events` | no |
| `mdtree.headings`, `.links`, `.code_blocks` | no |
| `mdhtml.web_urls`, `.any_url`, `.url_rule` | no |
| `mdhtml.default_options`, `.commonmark_options` | no |
| `mdhtml.render`, `.render_str`, `.render_events`, `.render_tree` | no |
| `mdhtml.escape_text`, `.escape_attr`, `.heading_id`, `.to_plain` | no |

## Licence

Apache-2.0. See `LICENSE`.

<!-- docs/writing-a-readme.md is the style guide for this page. -->
