from sidebrain_back.rag.rag_document_parser import RagDocumentParser
from sidebrain_back.rag.rag_html_parser import RagHtmlParser


def test_html_parser_keeps_main_article_and_code_language():
    html = """
    <html><head><title>fallback title</title>
      <link rel="canonical" href="https://docs.example/guide">
    </head><body>
      <nav>Navigation that must not be indexed</nav>
      <main><h1>JavaScript guide</h1><h2>Promises</h2>
        <p>A promise represents an eventual result.</p>
        <pre><code class="language-javascript">const answer = 42;</code></pre>
        <footer>Footer that must not be indexed</footer>
      </main>
    </body></html>
    """

    document = RagHtmlParser().parse(
        html, source_url="https://docs.example/requested"
    )

    assert document.title == "JavaScript guide"
    assert document.canonical_url == "https://docs.example/guide"
    assert len(document.sections) == 1
    section = document.sections[0]
    assert section.section_path == "JavaScript guide > Promises"
    assert "promise represents" in section.text
    assert "```javascript" in section.text
    assert "const answer = 42;" in section.text
    assert "Navigation that must not be indexed" not in section.text
    assert "Footer that must not be indexed" not in section.text


def test_markdown_parser_preserves_heading_path_and_fenced_code():
    document = RagDocumentParser().parse_markdown(
        """# Tutorial

## Data structures

Lists preserve insertion order.

```python
items = [1, 2]
```
""",
        source_url="https://docs.example/tutorial.md",
    )

    assert document.title == "Tutorial"
    assert document.sections[0].section_path == "Tutorial > Data structures"
    assert "Lists preserve insertion order." in document.sections[0].text
    assert "```python\nitems = [1, 2]\n```" in document.sections[0].text


def test_rst_parser_preserves_sections_and_code_blocks():
    document = RagDocumentParser().parse_rst(
        """Tutorial
========

Data structures
---------------

Lists preserve insertion order.

.. code-block:: python

   items = [1, 2]
""",
        source_url="https://docs.example/tutorial.rst",
    )

    assert document.title == "Tutorial"
    assert document.sections[0].section_path == "Tutorial > Data structures"
    assert "Lists preserve insertion order." in document.sections[0].text
    assert "```python\nitems = [1, 2]\n```" in document.sections[0].text
