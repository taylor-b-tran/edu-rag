"""PDF fixtures exercise row association without hard-coding a particular course."""
import fitz
import pytest
from src.document_processor.chunker import _pdf_page_text, extract_and_chunk, chunk_text


def make_table(path, headers=("Assessment", "Weight", "Note"), rows=None,
               bold_header=True, merge=False):
    rows = rows or [("Task Alpha", "15%", "Due 04/03/2027"),
                    ("Task Beta", "20%", "Due 18/05/2027"),
                    ("Task Gamma", "30%", "Due 29/08/2027")]
    doc = fitz.open()
    page = doc.new_page(width=600, height=800)
    page.insert_text((40, 35), "Course assessment details")
    xs = [40, 205, 305, 560]
    ys = [70 + 45 * i for i in range(len(rows) + 2)]
    for y in ys:
        page.draw_line((xs[0], y), (xs[-1], y))
    for c, x in enumerate(xs):
        if merge and c == 1:
            page.draw_line((x, ys[0]), (x, ys[1]))
            page.draw_line((x, ys[2]), (x, ys[-1]))
        else:
            page.draw_line((x, ys[0]), (x, ys[-1]))
    for r, values in enumerate([headers, *rows]):
        for c, text in enumerate(values):
            if merge and r == 1 and c == 1:
                continue
            # Dates precede labels in sorted flat text, as in the reported PDF.
            y = ys[r] + (28 if r and c == 0 else 16)
            page.insert_text((xs[c] + 6, y), text, fontsize=10,
                             fontname="hebo" if r == 0 and bold_header else "helv")
    page.insert_text((40, ys[-1] + 35), "Check the original course outline.")
    doc.save(path)
    doc.close()
    return path


def legacy(page):
    return " ".join(page.get_text("text", sort=True).split())


def test_pdf_ingestion_keeps_each_task_with_its_own_date(tmp_path):
    path = make_table(tmp_path / "assessments.pdf")
    chunks = extract_and_chunk(path)
    text = "\n".join(c["text"] for c in chunks)
    assert "Assessment: Task Beta | Weight: 20% | Note: Due 18/05/2027" in text
    assert "Assessment: Task Gamma | Weight: 30% | Note: Due 29/08/2027" in text
    assert text.count("Task Beta") == 1
    assert text.count("18/05/2027") == 1
    assert "Course assessment details" in text
    assert "Check the original course outline." in text
    assert all(c["metadata"] == {"page_number": 1, "source": path.name, "format": "pdf"}
               for c in chunks)


@pytest.mark.parametrize("option", ["unheaded", "duplicate_header", "merged"])
def test_ambiguous_tables_keep_the_original_extraction(tmp_path, option):
    path = make_table(tmp_path / f"{option}.pdf",
                      headers=("Assessment", "Note", "Note") if option == "duplicate_header"
                      else ("Assessment", "Weight", "Note"),
                      bold_header=option != "unheaded", merge=option == "merged")
    with fitz.open(path) as doc:
        assert _pdf_page_text(doc[0], 1024) == legacy(doc[0])


def test_overlong_serialised_rows_fall_back_instead_of_losing_association(tmp_path):
    path = make_table(tmp_path / "small_chunk.pdf")
    with fitz.open(path) as doc:
        assert _pdf_page_text(doc[0], 30) == legacy(doc[0])


def test_blank_cells_do_not_shift_other_values(tmp_path):
    path = make_table(tmp_path / "blank.pdf",
                      rows=[("Task Delta", "", "Due 02/02/2028"),
                            ("Task Epsilon", "25%", "Due 03/03/2028")])
    text = "\n".join(c["text"] for c in extract_and_chunk(path))
    assert "Assessment: Task Delta | Weight:  | Note: Due 02/02/2028" in text
    assert "Assessment: Task Epsilon | Weight: 25% | Note: Due 03/03/2028" in text


def test_detection_failure_does_not_break_document_ingestion(tmp_path, monkeypatch):
    path = make_table(tmp_path / "failure.pdf")
    def unavailable(*args, **kwargs):
        raise RuntimeError("detector unavailable")
    monkeypatch.setattr(fitz.Page, "find_tables", unavailable)
    with fitz.open(path) as doc:
        expected = chunk_text(legacy(doc[0]))
    assert [c["text"] for c in extract_and_chunk(path)] == expected


def test_non_table_and_empty_pages_keep_their_text_and_page_metadata(tmp_path):
    path = tmp_path / "pages.pdf"
    doc = fitz.open()
    doc.new_page().insert_text((50, 50), "First page ordinary text.")
    doc.new_page()
    doc.new_page().insert_text((50, 50), "Third page ordinary text.")
    doc.save(path)
    doc.close()
    chunks = extract_and_chunk(path)
    assert [(c["text"], c["metadata"]["page_number"]) for c in chunks] == [
        ("First page ordinary text.", 1), ("Third page ordinary text.", 3)]
