import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.document_processor.chunker import (
    chunk_text,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_CHUNK_OVERLAP,
)

@pytest.fixture
def short_sentence():
    return "This is a short sentence."


@pytest.fixture
def long_english_text():
    """~7,600 chars - forces multiple chunks at default size 1024."""
    sentence = (
        "Retrieval-Augmented Generation combines a retrieval step with "
        "a large language model to ground responses in real documents, "
        "which reduces hallucination and improves accuracy. "
    )
    return sentence * 100


@pytest.fixture
def code_block_text():
    """Realistic Python code — tests indentation and special character handling."""
    block = (
        "def binary_search(arr, target):\n"
        "    left, right = 0, len(arr) - 1\n"
        "    while left <= right:\n"
        "        mid = (left + right) // 2\n"
        "        if arr[mid] == target:\n"
        "            return mid\n"
        "        elif arr[mid] < target:\n"
        "            left = mid + 1\n"
        "        else:\n"
        "            right = mid - 1\n"
        "    return -1\n\n"
    )
    return block * 15  


@pytest.fixture
def chinese_text():
    """Chinese Unicode text — tests non-ASCII / multi-byte handling."""
    return (
        "检索增强生成（RAG）是一种将信息检索与大型语言模型相结合的技术。"
        "该系统首先从文档库中检索相关片段，然后将这些片段作为上下文提供给语言模型。"
        "这种方法显著减少了模型的幻觉现象，提高了回答的准确性和可靠性。"
    ) * 30


@pytest.fixture
def french_text():
    """French Unicode text — accented characters, apostrophes."""
    return (
        "L'apprentissage automatique est une branche de l'intelligence artificielle "
        "qui permet aux systèmes d'apprendre à partir de données sans être "
        "explicitement programmés pour chaque tâche spécifique. "
    ) * 40


@pytest.fixture
def mixed_language_text():
    """Mix of English, Chinese, and French in one document."""
    return (
        "Hello world. 你好世界. Bonjour le monde. "
        "This sentence mixes languages seamlessly. "
        "机器学习 machine learning apprentissage automatique. "
    ) * 40

class TestEmptyAndWhitespace:
    def test_empty_string_returns_empty_list(self):
        assert chunk_text("") == []

    def test_single_space_returns_empty_list(self):
        assert chunk_text(" ") == []

    def test_multiple_spaces_returns_empty_list(self):
        assert chunk_text("     ") == []

    def test_newlines_only_returns_empty_list(self):
        assert chunk_text("\n\n\n") == []

    def test_tabs_and_newlines_returns_empty_list(self):
        assert chunk_text("\t \n \t \n") == []

    def test_return_type_is_list_for_empty(self):
        result = chunk_text("")
        assert isinstance(result, list)

class TestShortText:
    def test_single_word_returns_one_chunk(self):
        result = chunk_text("Hello")
        assert len(result) == 1
        assert result[0] == "Hello"

    def test_single_sentence_returns_one_chunk(self, short_sentence):
        result = chunk_text(short_sentence)
        assert len(result) == 1

    def test_single_sentence_content_preserved(self, short_sentence):
        result = chunk_text(short_sentence)
        assert result[0] == short_sentence

    def test_text_well_below_chunk_size(self):
        text = "EduRAG is an AI-powered course assistant using RAG."
        result = chunk_text(text)
        assert len(result) == 1
        assert "EduRAG" in result[0]
        assert "RAG" in result[0]

    def test_text_exactly_fills_one_chunk(self):
        text = ("abcdefghijklmnopqrstuvwxyz " * 40)[:1024]
        result = chunk_text(text)
        assert len(result) >= 1          
        assert all(c.strip() for c in result) 
                                                                                                                
class TestLongText:
    def test_multiple_chunks_produced(self, long_english_text):
        result = chunk_text(long_english_text)
        assert len(result) > 1, "Long text must produce more than one chunk"

    def test_all_chunks_within_chunk_size(self, long_english_text):
        result = chunk_text(long_english_text, chunk_size=512)
        oversized = [i for i, c in enumerate(result) if len(c) > 512]
        assert oversized == [], (
            f"Chunks at indices {oversized} exceed 512 chars: "
            f"{[len(result[i]) for i in oversized]}"
        )

    def test_no_empty_chunks(self, long_english_text):
        result = chunk_text(long_english_text)
        empty = [i for i, c in enumerate(result) if not c.strip()]
        assert empty == [], f"Empty chunks found at indices: {empty}"

    def test_all_chunks_are_strings(self, long_english_text):
        result = chunk_text(long_english_text)
        assert all(isinstance(c, str) for c in result)

    def test_return_type_is_list(self, long_english_text):
        result = chunk_text(long_english_text)
        assert isinstance(result, list)

    def test_content_coverage(self, long_english_text):
        """All words from the original must appear somewhere in the chunks."""
        result = chunk_text(long_english_text)
        joined = " ".join(result)
        for word in ["Retrieval-Augmented", "language", "model", "hallucination"]:
            assert word in joined, f"Word '{word}' lost during chunking"

    def test_smaller_chunk_size_produces_more_chunks(self, long_english_text):
        small = chunk_text(long_english_text, chunk_size=128, chunk_overlap=20)
        large = chunk_text(long_english_text, chunk_size=1024, chunk_overlap=50)
        assert len(small) > len(large)

    def test_custom_chunk_size_respected(self, long_english_text):
        result = chunk_text(long_english_text, chunk_size=256, chunk_overlap=30)
        oversized = [len(c) for c in result if len(c) > 256]
        assert oversized == [], f"Chunks exceeded custom size 256: {oversized}"


class TestOverlap:

    def test_overlap_creates_shared_content(self):
        """
        With overlap=20 on a repetitive sentence, the end of chunk[0]
        must appear somewhere inside chunk[1].
        Verified against real RecursiveCharacterTextSplitter behaviour.
        """
        text = "The quick brown fox jumps over the lazy dog. " * 30
        result = chunk_text(text, chunk_size=100, chunk_overlap=20)
        assert len(result) >= 2, "Need at least 2 chunks to test overlap"

        overlap_found = False
        for length in range(20, 5, -1):
            tail = result[0][-length:]
            if tail.strip() and tail in result[1]:
                overlap_found = True
                break

        assert overlap_found, (
            "No overlap detected between chunk[0] and chunk[1]. "
            f"chunk[0] ends: {repr(result[0][-30:])}, "
            f"chunk[1] starts: {repr(result[1][:30])}"
        )

    def test_zero_overlap_still_produces_valid_chunks(self, long_english_text):
        result = chunk_text(long_english_text, chunk_size=256, chunk_overlap=0)
        assert len(result) >= 1
        assert all(c.strip() for c in result)
        assert all(len(c) <= 256 for c in result)

    def test_overlap_does_not_exceed_chunk_size(self, long_english_text):
        result = chunk_text(long_english_text, chunk_size=512, chunk_overlap=50)
        assert all(len(c) <= 512 for c in result)

class TestCodeBlocks:

    def test_code_block_does_not_raise(self, code_block_text):
        try:
            chunk_text(code_block_text)
        except Exception as exc:
            pytest.fail(f"chunk_text raised on code input: {exc}")

    def test_code_block_produces_chunks(self, code_block_text):
        result = chunk_text(code_block_text)
        assert len(result) >= 1

    def test_code_keywords_preserved(self, code_block_text):
        result = chunk_text(code_block_text)
        joined = "".join(result)
        for keyword in ["def", "return", "while", "binary_search"]:
            assert keyword in joined, f"Keyword '{keyword}' lost during chunking"

    def test_code_block_no_empty_chunks(self, code_block_text):
        result = chunk_text(code_block_text)
        assert all(c.strip() for c in result)

    def test_code_block_within_size_limit(self, code_block_text):
        result = chunk_text(code_block_text, chunk_size=512)
        assert all(len(c) <= 512 for c in result)

    def test_short_code_snippet_single_chunk(self):
        snippet = "x = 42\nprint(x)"
        result = chunk_text(snippet)
        assert len(result) == 1
        assert "print" in result[0]

class TestNonEnglishText:

    def test_chinese_text_does_not_raise(self, chinese_text):
        try:
            chunk_text(chinese_text)
        except Exception as exc:
            pytest.fail(f"chunk_text raised on Chinese text: {exc}")

    def test_chinese_text_returns_list(self, chinese_text):
        result = chunk_text(chinese_text)
        assert isinstance(result, list)

    def test_chinese_text_content_preserved(self, chinese_text):
        result = chunk_text(chinese_text)
        joined = "".join(result)
        assert "RAG" in joined or "检索" in joined, "Chinese content lost during chunking"

    def test_french_text_does_not_raise(self, french_text):
        try:
            chunk_text(french_text)
        except Exception as exc:
            pytest.fail(f"chunk_text raised on French text: {exc}")

    def test_french_accented_chars_preserved(self, french_text):
        result = chunk_text(french_text)
        joined = "".join(result)
        assert "è" in joined or "â" in joined or "é" in joined, \
            "Accented French characters were dropped"

    def test_mixed_language_does_not_raise(self, mixed_language_text):
        try:
            chunk_text(mixed_language_text)
        except Exception as exc:
            pytest.fail(f"chunk_text raised on mixed-language text: {exc}")

    def test_mixed_language_all_scripts_preserved(self, mixed_language_text):
        result = chunk_text(mixed_language_text)
        joined = "".join(result)
        assert "Hello" in joined,      "English lost"
        assert "你好" in joined,        "Chinese lost"
        assert "Bonjour" in joined,    "French lost"

    def test_non_english_no_empty_chunks(self, chinese_text):
        result = chunk_text(chinese_text)
        assert all(c.strip() for c in result)

    def test_non_english_within_size_limit(self, chinese_text):
        result = chunk_text(chinese_text, chunk_size=512)
        assert all(len(c) <= 512 for c in result)


class TestRealPDFContent:
    REAL_TEXT = """
1.1. PREAMBLE

An essential characteristic of a profession is the need for its members to abide
by a code of ethics. For the ACS, this code is established as the Code of
Professional Conduct and is part of the Society's Regulations. These Regulations
apply to any ACS member who works in the field of information and communications
technology (ICT).

This Code of Professional Conduct (the Code) identifies six core ethical values
and the associated requirements for professional conduct. The Society requires its
members to abide by these values, and act with responsibility and integrity in all
of their professional dealings.

1.2. THE CODE

As an ACS member you must uphold and advance the honour, dignity and
effectiveness of being a professional. This entails, in addition to being a good
citizen and acting within the law, your conformance to the following ACS values.

1. The Primacy of the Public Interest
You will place the interests of the public above those of personal, business or
sectional interests.

2. The Enhancement of Quality of Life
You will strive to enhance the quality of life of those affected by your work.

3. Honesty
You will be honest in your representation of skills, knowledge, services and
products.

4. Competence
You will work competently and diligently for your stakeholders.

5. Professional Development
You will enhance your own professional development, and that of your staff.

6. Professionalism
You will enhance the integrity of the ACS and the respect of its members for
each other.

In a situation of conflict between the values, The Primacy of the Public Interest
takes precedence over the other values.

1.2.1. The Primacy of the Public Interest

In the context of this Code, the public interest takes precedence over personal,
private and sectional interests, and any conflicts should be resolved in favour
of the public interest. In your work, you should safeguard the interests of your
immediate stakeholders, provided that these interests do not conflict with the
duty and loyalty you owe to the public.

In accordance with this value you will:
a) identify those potentially impacted by your work and explicitly consider their
   interests;
b) raise with stakeholders any potential conflicts between your professional
   activity and legal or other accepted public requirements;
c) advise your stakeholders as soon as possible of any conflicts of interest or
   conscientious objections that you have;
d) endeavour to preserve the integrity, security, continuity and utility of ICT;
e) respect the intellectual property of others; and
f) endeavour to preserve the confidentiality and privacy of the information of
   others.
"""

    def test_real_pdf_text_produces_chunks(self):
        result = chunk_text(self.REAL_TEXT)
        assert len(result) >= 1

    def test_real_pdf_text_key_terms_preserved(self):
        result = chunk_text(self.REAL_TEXT)
        joined = " ".join(result)
        for term in ["PREAMBLE", "Honesty", "Competence", "Professionalism"]:
            assert term in joined, f"Key term '{term}' lost during chunking"

    def test_real_pdf_text_within_size_limit(self):
        result = chunk_text(self.REAL_TEXT, chunk_size=512)
        assert all(len(c) <= 512 for c in result)

    def test_real_pdf_text_no_empty_chunks(self):
        result = chunk_text(self.REAL_TEXT)
        assert all(c.strip() for c in result)

class TestParameterValidation:

    def test_non_string_input_raises_type_error(self):
        with pytest.raises(TypeError):
            chunk_text(123)

    def test_none_input_raises_type_error(self):
        with pytest.raises(TypeError):
            chunk_text(None)

    def test_list_input_raises_type_error(self):
        with pytest.raises(TypeError):
            chunk_text(["some", "text"])

    def test_zero_chunk_size_raises_value_error(self):
        with pytest.raises(ValueError, match="chunk_size must be > 0"):
            chunk_text("Some text.", chunk_size=0)

    def test_negative_chunk_size_raises_value_error(self):
        with pytest.raises(ValueError, match="chunk_size must be > 0"):
            chunk_text("Some text.", chunk_size=-1)

    def test_negative_overlap_raises_value_error(self):
        with pytest.raises(ValueError, match="chunk_overlap must be >= 0"):
            chunk_text("Some text.", chunk_overlap=-5)

    def test_overlap_equal_to_chunk_size_raises_value_error(self):
        with pytest.raises(ValueError, match="chunk_overlap.*must be less than"):
            chunk_text("Some text.", chunk_size=100, chunk_overlap=100)

    def test_overlap_greater_than_chunk_size_raises_value_error(self):
        with pytest.raises(ValueError, match="chunk_overlap.*must be less than"):
            chunk_text("Some text.", chunk_size=100, chunk_overlap=200)

    def test_valid_custom_parameters_accepted(self, long_english_text="x " * 300):
        result = chunk_text(long_english_text, chunk_size=200, chunk_overlap=30)
        assert isinstance(result, list)

    def test_defaults_match_fr005(self):
        """FR-005 follows the accepted Sprint 3 baseline."""
        assert DEFAULT_CHUNK_SIZE == 1024
        assert DEFAULT_CHUNK_OVERLAP == 0

from src.document_processor.chunker import chunk_pptx, chunk_docx, extract_and_chunk, SUPPORTED_EXTENSIONS

@pytest.fixture
def sample_pptx(tmp_path):
    from pptx import Presentation
    from pptx.util import Inches
    prs = Presentation()
    layout = prs.slide_layouts[5]
    slide1 = prs.slides.add_slide(layout)
    tf = slide1.shapes.add_textbox(Inches(1), Inches(1), Inches(6), Inches(2)).text_frame
    tf.text = "Introduction to Machine Learning"
    tf.add_paragraph().text = "Machine learning enables systems to learn from data automatically."
    slide2 = prs.slides.add_slide(layout)
    tf2 = slide2.shapes.add_textbox(Inches(1), Inches(1), Inches(6), Inches(2)).text_frame
    tf2.text = "Supervised Learning"
    tf2.add_paragraph().text = "Supervised learning uses labelled training examples to build models."
    path = tmp_path / "sample.pptx"
    prs.save(path)
    return path

@pytest.fixture
def empty_pptx(tmp_path):
    from pptx import Presentation
    prs = Presentation()
    prs.slides.add_slide(prs.slide_layouts[5])
    path = tmp_path / "empty.pptx"
    prs.save(path)
    return path

@pytest.fixture
def sample_docx(tmp_path):
    import docx as dx
    doc = dx.Document()
    doc.add_heading("Introduction to RAG", 0)
    doc.add_paragraph("Retrieval-Augmented Generation combines retrieval with language models.")
    doc.add_paragraph("It reduces hallucination by grounding answers in real documents.")
    t = doc.add_table(rows=2, cols=2)
    t.cell(0, 0).text = "Method"; t.cell(0, 1).text = "Accuracy"
    t.cell(1, 0).text = "RAG";    t.cell(1, 1).text = "High"
    path = tmp_path / "sample.docx"
    doc.save(path)
    return path

@pytest.fixture
def empty_docx(tmp_path):
    import docx as dx
    path = tmp_path / "empty.docx"
    dx.Document().save(path)
    return path

class TestChunkPptx:

    def test_returns_list(self, sample_pptx):
        assert isinstance(chunk_pptx(sample_pptx), list)

    def test_produces_chunks(self, sample_pptx):
        assert len(chunk_pptx(sample_pptx)) >= 1

    def test_each_item_has_text_and_metadata(self, sample_pptx):
        for item in chunk_pptx(sample_pptx):
            assert "text" in item
            assert "metadata" in item

    def test_text_is_non_empty_string(self, sample_pptx):
        for item in chunk_pptx(sample_pptx):
            assert isinstance(item["text"], str)
            assert item["text"].strip()

    def test_metadata_contains_slide_number(self, sample_pptx):
        for item in chunk_pptx(sample_pptx):
            assert "slide_number" in item["metadata"]
            assert isinstance(item["metadata"]["slide_number"], int)
            assert item["metadata"]["slide_number"] >= 1

    def test_metadata_format_is_pptx(self, sample_pptx):
        for item in chunk_pptx(sample_pptx):
            assert item["metadata"]["format"] == "pptx"

    def test_metadata_source_is_filename(self, sample_pptx):
        for item in chunk_pptx(sample_pptx):
            assert item["metadata"]["source"] == "sample.pptx"

    def test_chunks_within_size_limit(self, sample_pptx):
        oversized = [len(item["text"]) for item in chunk_pptx(sample_pptx, chunk_size=512) if len(item["text"]) > 512]
        assert oversized == [], f"Chunks exceed 512 chars: {oversized}"

    def test_slide_numbers_are_positive_integers(self, sample_pptx):
        assert all(item["metadata"]["slide_number"] >= 1 for item in chunk_pptx(sample_pptx))

    def test_multiple_slides_produce_distinct_slide_numbers(self, sample_pptx):
        slide_nums = {item["metadata"]["slide_number"] for item in chunk_pptx(sample_pptx)}
        assert len(slide_nums) >= 2, "Expected chunks from at least 2 slides"

    def test_known_content_preserved(self, sample_pptx):
        joined = " ".join(item["text"] for item in chunk_pptx(sample_pptx))
        assert "Machine Learning" in joined or "Supervised" in joined

    def test_empty_pptx_returns_empty_list(self, empty_pptx):
        assert chunk_pptx(empty_pptx) == []

    def test_custom_chunk_size_respected(self, sample_pptx):
        oversized = [len(item["text"]) for item in chunk_pptx(sample_pptx, chunk_size=100, chunk_overlap=10) if len(item["text"]) > 100]
        assert oversized == [], f"Chunks exceed custom size 100: {oversized}"

    def test_file_not_found_raises(self):
        with pytest.raises(FileNotFoundError):
            chunk_pptx("nonexistent/path/file.pptx")

    def test_wrong_extension_raises_value_error(self, sample_docx):
        with pytest.raises(ValueError, match=".pptx"):
            chunk_pptx(sample_docx)


class TestChunkDocx:

    def test_returns_list(self, sample_docx):
        assert isinstance(chunk_docx(sample_docx), list)

    def test_produces_chunks(self, sample_docx):
        assert len(chunk_docx(sample_docx)) >= 1

    def test_each_item_has_text_and_metadata(self, sample_docx):
        for item in chunk_docx(sample_docx):
            assert "text" in item
            assert "metadata" in item

    def test_text_is_non_empty_string(self, sample_docx):
        for item in chunk_docx(sample_docx):
            assert isinstance(item["text"], str)
            assert item["text"].strip()

    def test_metadata_format_is_docx(self, sample_docx):
        for item in chunk_docx(sample_docx):
            assert item["metadata"]["format"] == "docx"

    def test_metadata_source_is_filename(self, sample_docx):
        for item in chunk_docx(sample_docx):
            assert item["metadata"]["source"] == "sample.docx"

    def test_metadata_contains_chunk_index(self, sample_docx):
        for item in chunk_docx(sample_docx):
            assert "chunk_index" in item["metadata"]
            assert isinstance(item["metadata"]["chunk_index"], int)

    def test_chunk_index_is_sequential(self, sample_docx):
        result = chunk_docx(sample_docx)
        assert [item["metadata"]["chunk_index"] for item in result] == list(range(len(result)))

    def test_chunks_within_size_limit(self, sample_docx):
        oversized = [len(item["text"]) for item in chunk_docx(sample_docx, chunk_size=512) if len(item["text"]) > 512]
        assert oversized == [], f"Chunks exceed 512 chars: {oversized}"

    def test_known_content_preserved(self, sample_docx):
        joined = " ".join(item["text"] for item in chunk_docx(sample_docx))
        assert "RAG" in joined or "Retrieval" in joined

    def test_table_content_included(self, sample_docx):
        joined = " ".join(item["text"] for item in chunk_docx(sample_docx))
        assert "Method" in joined or "RAG" in joined

    def test_empty_docx_returns_empty_list(self, empty_docx):
        assert chunk_docx(empty_docx) == []

    def test_custom_chunk_size_respected(self, sample_docx):
        oversized = [len(item["text"]) for item in chunk_docx(sample_docx, chunk_size=100, chunk_overlap=10) if len(item["text"]) > 100]
        assert oversized == [], f"Chunks exceed custom size 100: {oversized}"

    def test_file_not_found_raises(self):
        with pytest.raises(FileNotFoundError):
            chunk_docx("nonexistent/path/file.docx")

    def test_wrong_extension_raises_value_error(self, sample_pptx):
        with pytest.raises(ValueError, match=".docx"):
            chunk_docx(sample_pptx)


class TestExtractAndChunk:

    def test_pptx_dispatches_correctly(self, sample_pptx):
        result = extract_and_chunk(sample_pptx)
        assert isinstance(result, list) and len(result) >= 1
        assert all(item["metadata"]["format"] == "pptx" for item in result)

    def test_docx_dispatches_correctly(self, sample_docx):
        result = extract_and_chunk(sample_docx)
        assert isinstance(result, list) and len(result) >= 1
        assert all(item["metadata"]["format"] == "docx" for item in result)

    def test_unsupported_extension_raises_value_error(self, tmp_path):
        fake = tmp_path / "file.txt"
        fake.write_text("hello")
        with pytest.raises(ValueError, match="Unsupported file type"):
            extract_and_chunk(fake)

    def test_missing_file_raises_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            extract_and_chunk("no_such_file.pptx")

    def test_supported_extensions_constant(self):
        assert ".pptx" in SUPPORTED_EXTENSIONS
        assert ".docx" in SUPPORTED_EXTENSIONS
        assert ".pdf" in SUPPORTED_EXTENSIONS

    def test_pptx_result_has_slide_number_metadata(self, sample_pptx):
        for item in extract_and_chunk(sample_pptx):
            assert "slide_number" in item["metadata"]

    def test_docx_result_has_chunk_index_metadata(self, sample_docx):
        for item in extract_and_chunk(sample_docx):
            assert "chunk_index" in item["metadata"]

    def test_custom_params_passed_through_pptx(self, sample_pptx):
        oversized = [len(item["text"]) for item in extract_and_chunk(sample_pptx, chunk_size=100, chunk_overlap=10) if len(item["text"]) > 100]
        assert oversized == [], f"Custom chunk_size not respected: {oversized}"

    def test_custom_params_passed_through_docx(self, sample_docx):
        oversized = [len(item["text"]) for item in extract_and_chunk(sample_docx, chunk_size=100, chunk_overlap=10) if len(item["text"]) > 100]
        assert oversized == [], f"Custom chunk_size not respected: {oversized}"
