from textwrap import dedent

from .mymarkup import render


def test_headings():
    assert render("# Heading 1") == "<h1>Heading 1</h1>"
    assert render("## Heading 2") == "<h2>Heading 2</h2>"
    assert render("### Heading 3") == "<h3>Heading 3</h3>"

    assert render("# Heading 1 #") == '<h1 class="center">Heading 1</h1>'
    assert render("## Heading 2 ##") == '<h2 class="center">Heading 2</h2>'
    assert render("### Heading 3 ###") == '<h3 class="center">Heading 3</h3>'

    assert render("#Not a heading") == "<p>#Not a heading</p>"

    assert render("# Heading with *bold*") == (
        "<h1>Heading with <strong>bold</strong></h1>"
    )

    assert render("# Heading with `code`") == (
        "<h1>Heading with <code>code</code></h1>"
    )

    assert render("# Heading with [link](https://example.com)") == (
        '<h1>Heading with <a href="https://example.com">link</a></h1>'
    )


def test_paragraphs():
    assert render(
        dedent("""
            Line one
            Line two
        """).strip()
    ) == "<p>Line one Line two</p>"

    assert render(
        dedent("""
            First paragraph

            Second paragraph
        """).strip()
    ) == "<p>First paragraph</p><p>Second paragraph</p>"


def test_lists():
    assert render(" - item 1\n - item 2") == "<ul><li><p>item 1</p></li><li><p>item 2</p></li></ul>"

    assert render(" # First\n # Second\n # Third") == "<ol><li><p>First</p></li><li><p>Second</p></li><li><p>Third</p></li></ol>"

    assert render(" item\n\n #item") == "<p>item</p><p>#item</p>"

    assert render(" - item with *bold*") == (
        "<ul><li><p>item with <strong>bold</strong></p></li></ul>"
    )

    assert render(" - item with `code`") == (
        "<ul><li><p>item with <code>code</code></p></li></ul>"
    )

    assert render(" - item with [link](https://example.com)") == (
        '<ul><li><p>item with <a href="https://example.com">link</a></p></li></ul>'
    )


def test_nested_lists():
    assert render(
        dedent("""
        test
         - Parent
            - Child
               - Grandchild
        """).strip()
    ) == (
        "<p>test</p><ul><li><p>Parent</p>"
        "<ul><li><p>Child</p>"
        "<ul><li><p>Grandchild</p></li></ul>"
        "</li></ul>"
        "</li></ul>"
    )


def test_mixed_lists():
    assert render(
        dedent("""
        test
         - Item
            # Step one
            # Step two
         - Item two
        """).strip()
    ) == (
        "<p>test</p><ul><li><p>Item</p>"
        "<ol><li><p>Step one</p></li><li><p>Step two</p></li></ol>"
        "</li><li><p>Item two</p></li></ul>"
    )


def test_list_item_continuation():
    assert render(
        dedent("""
        test
         - This is a list item
           continued here
           and continued here
         - and this is the next item
        """).strip()
    ) == "<p>test</p><ul><li><p>This is a list item continued here and continued here</p></li><li><p>and this is the next item</p></li></ul>"


def test_inline_markup():
    assert render("*bold*") == "<p><strong>bold</strong></p>"

    assert render("*bold and `code` inside*") == (
        "<p><strong>bold and <code>code</code> inside</strong></p>"
    )

    assert render("`*not bold* [not a link]`") == (
        "<p><code>*not bold* [not a link]</code></p>"
    )

    assert render("word*bold*") == "<p>word<strong>bold</strong></p>"
    assert render("*bold*word") == "<p><strong>bold</strong>word</p>"
    assert render("word*bold*word") == "<p>word<strong>bold</strong>word</p>"

    assert render("word *bold*") == "<p>word <strong>bold</strong></p>"
    assert render("*bold* word") == "<p><strong>bold</strong> word</p>"
    assert render("word *bold* word") == (
        "<p>word <strong>bold</strong> word</p>"
    )

    assert render("*") == "<p>*</p>"
    assert render("**") == "<p>**</p>"
    assert render("***") == "<p>***</p>"
    assert render("* *") == "<p>* *</p>"

    assert render("*bold `code` [link](link.html) test*") == (
        '<p><strong>bold <code>code</code> '
        '<a href="link.html">link</a> test</strong></p>'
    )

    assert render("[*bold link*](https://example.com)") == (
        '<p><a href="https://example.com">'
        '<strong>bold link</strong>'
        "</a></p>"
    )

    assert render("[`code link`](https://example.com)") == (
        '<p><a href="https://example.com">'
        "<code>code link</code>"
        "</a></p>"
    )

    assert render("[link](link.html) and *bold* and `code`") == (
        '<p><a href="link.html">link</a> '
        "and <strong>bold</strong> "
        "and <code>code</code></p>"
    )

    assert render("*bold.*") == "<p>*bold.*</p>"
    assert render("(*bold*)") == "<p>(<strong>bold</strong>)</p>"
    assert render("word (*bold*) word") == (
        "<p>word (<strong>bold</strong>) word</p>"
    )
    assert render("*bold*,") == "<p><strong>bold</strong>,</p>"
    assert render("*bold*!") == "<p><strong>bold</strong>!</p>"
    assert render("*bold*?") == "<p><strong>bold</strong>?</p>"
    assert render("*bold*.") == "<p><strong>bold</strong>.</p>"

    assert render("word*bold*.") == "<p>word<strong>bold</strong>.</p>"
    assert render("(*bold*word)") == "<p>(<strong>bold</strong>word)</p>"
    assert render("(word*bold*)") == "<p>(word<strong>bold</strong>)</p>"

    assert render("Use `foo_bar()` here") == (
        "<p>Use <code>foo_bar()</code> here</p>"
    )

    assert render("Call `obj.method()`.") == (
        "<p>Call <code>obj.method()</code>.</p>"
    )

    assert render("prefix`code`suffix") == (
        "<p>prefix<code>code</code>suffix</p>"
    )

    assert render("`not closed") == "<p>`not closed</p>"


def test_empty_or_invalid_inline_markup():
    assert render("**") == "<p>**</p>"
    assert render("``") == "<p>``</p>"
    assert render("[link]()") == "<p>[link]()</p>"
    assert render("*not bold") == "<p>*not bold</p>"


def test_regular_links():
    assert render("[Example](https://example.com)") == (
        '<p><a href="https://example.com">Example</a></p>'
    )
    assert render("[Wiki page](wiki-page.html)") == (
        '<p><a href="wiki-page.html">Wiki page</a></p>'
    )


def test_bare_urls():
    assert render(
        dedent("""
            https://example.com
        """).strip()
    ) == (
        '<p><a href="https://example.com">'
        "https://example.com"
        "</a></p>"
    )


def test_images():
    assert render("[https://example.com/image.png]") == (
        '<p><img src="https://example.com/image.png"></p>'
    )

    assert render("[/images/cat.webp]") == (
        '<p><img src="/images/cat.webp"></p>'
    )

    assert render("[cat.svg]") == '<p><img src="cat.svg"></p>'


def test_fenced_code_blocks():
    assert render(
        dedent("""
            ```
            print("hello")
            ```
        """).strip()
    ) == dedent("""
        <pre><code>print(&quot;hello&quot;)</code></pre>
    """).strip()

    assert render(
        dedent("""
            ```python
            print("hello")
            print("hello")
            ```
        """).strip()
    ) == dedent("""
        <pre><code class="language-python">print(&quot;hello&quot;)
        print(&quot;hello&quot;)</code></pre>
    """).strip()


def test_variable_length_code_fences():
    assert render(
        dedent("""
            ````markdown
            ```
            nested code fence
            ```
            ````
        """).strip()
    ) == dedent("""
        <pre><code class="language-markdown">```
        nested code fence
        ```</code></pre>
    """).strip()


def test_horizontal_rules():
    assert render("---") == "<hr>"
    assert render("-----") == "<hr>"


def test_blockquotes():
    assert render("> quoted text") == (
        "<blockquote><p>quoted text</p></blockquote>"
    )

    assert render(
        dedent("""
            > quoted line one
            > quoted line two
        """).strip()
    ) == (
        "<blockquote><p>"
        "quoted line one quoted line two"
        "</p></blockquote>"
    )


def test_xss():
    assert render("<script>alert(1)</script>") == (
        "<p>&lt;script&gt;alert(1)&lt;/script&gt;</p>"
    )
    assert render('[x](" onclick="alert(1)') == '<p><a href="&quot; onclick=&quot;alert(1">x</a></p>'
    assert render("[example](https://example.com?q=<script>)") == (
        '<p><a href="https://example.com?q=&lt;script&gt;">example</a></p>'
    )


def main():
    test_headings()
    test_paragraphs()
    test_lists()
    test_nested_lists()
    test_mixed_lists()
    test_list_item_continuation()
    test_inline_markup()
    test_empty_or_invalid_inline_markup()
    test_regular_links()
    test_bare_urls()
    # test_images()
    test_fenced_code_blocks()
    test_variable_length_code_fences()
    test_horizontal_rules()
    test_blockquotes()
    test_xss()

    print("All tests passed")


if __name__ == "__main__":
    main()
