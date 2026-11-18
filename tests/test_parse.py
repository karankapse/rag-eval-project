"""Tests for the HTML cleaner, using a tiny hand-made paper that mimics arXiv's page layout."""

from rag.ingest.parse import parse_html

FAKE_PAPER = """
<html><body>
  <nav>Skip to main content | Report GitHub Issue</nav>
  <article>
    <h1 class="ltx_title_document">Tiny Paper</h1>
    <div class="ltx_authors">Alice Smith, University of Nowhere</div>
    <div class="ltx_abstract"><h6 class="ltx_title">Abstract</h6><p>We study search.</p></div>
    <section class="ltx_section">
      <h2 class="ltx_title">1 Introduction</h2>
      <div class="ltx_para"><p>Search is
         hard. The cost is <math alttext="O(n^2)">junk</math> overall.</p></div>
      <figure class="ltx_figure">Figure 1: a pretty picture</figure>
    </section>
    <section class="ltx_section">
      <h2 class="ltx_title">2 Method</h2>
      <div class="ltx_para"><p>We rank documents.</p></div>
    </section>
    <section class="ltx_bibliography">
      <div class="ltx_para">[1] Smith. A Reference. 2020.</div>
    </section>
  </article>
</body></html>
"""


def test_keeps_prose_and_drops_page_clutter():
    # Protects against: menus, author lines, figures, and the reference list leaking into
    # the text we search over (they'd create junk matches and waste Claude's reading space).
    doc = parse_html("0000.00000v1", FAKE_PAPER)
    all_text = " ".join(s.text for s in doc.sections)
    assert "We study search." in all_text
    assert "We rank documents." in all_text
    for junk in ["Skip to main content", "University of Nowhere", "pretty picture", "A Reference"]:
        assert junk not in all_text


def test_sections_keep_their_headings_in_order():
    # Protects against: losing the paper's structure, which structure-aware chunking needs later.
    doc = parse_html("0000.00000v1", FAKE_PAPER)
    assert doc.title == "Tiny Paper"
    assert [s.heading for s in doc.sections] == ["Abstract", "1 Introduction", "2 Method"]


def test_whitespace_is_collapsed_and_math_becomes_plain_text():
    # Protects against: line breaks mid-sentence and unreadable formula markup in passages.
    doc = parse_html("0000.00000v1", FAKE_PAPER)
    intro = doc.sections[1].text
    assert intro == "Search is hard. The cost is O(n^2) overall."
