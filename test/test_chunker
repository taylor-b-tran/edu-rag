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
    """~3,600 chars — forces multiple chunks at default size 512."""
    sentence = (
        "Retrieval-Augmented Generation combines a retrieval step with "
        "a large language model to ground responses in real documents, "
        "which reduces hallucination and improves accuracy. "
    )
    return sentence * 50


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
    return block * 15  # ~1,800 chars — forces multiple chunks


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
    """chunk_text must return [] for all empty / whitespace inputs."""

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
    """Very short documents must come back as a single chunk, unchanged."""

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
        # 512 chars of a-z repeated — exactly at the default limit
        text = ("abcdefghijklmnopqrstuvwxyz " * 20)[:512]
        result = chunk_text(text)
        assert len(result) >= 1           # at least one chunk
        assert all(c.strip() for c in result)  # no empty chunks
                                                                                                                
class TestLongText:
    """Long documents must be split into multiple chunks within size limits."""

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
        # Check a few key words from our fixture sentence
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
    """Verify that chunk_overlap creates shared content between adjacent chunks."""

    def test_overlap_creates_shared_content(self):
        """
        With overlap=20 on a repetitive sentence, the end of chunk[0]
        must appear somewhere inside chunk[1].
        Verified against real RecursiveCharacterTextSplitter behaviour.
        """
        text = "The quick brown fox jumps over the lazy dog. " * 30
        result = chunk_text(text, chunk_size=100, chunk_overlap=20)
        assert len(result) >= 2, "Need at least 2 chunks to test overlap"

        # Find any shared suffix of chunk[0] in chunk[1]
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
    """Code block input must not crash and must preserve key content."""

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
    """Splitter must handle Unicode text from any language without errors."""

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
    """
    Tests using realistic text extracted from a real PDF
    (ACS Code of Professional Conduct — uploaded in Sprint 3).
    No file I/O: the text is embedded directly so tests run anywhere.
    """

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
    """chunk_text must reject invalid parameters with clear errors."""

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
        """FR-005 specifies chunk_size=512, chunk_overlap=50."""
        assert DEFAULT_CHUNK_SIZE == 512
        assert DEFAULT_CHUNK_OVERLAP == 50
