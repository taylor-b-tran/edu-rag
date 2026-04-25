# Document Parser Evaluation

## 1. Samples Tested

| No | File | Format | Parser |
|----|------|--------|--------|
| 1 | CSIT321_Week01_2026.pdf | PDF | PyMuPDF, pdfplumber |
| 2 | CSIT321_Week02_2026.pdf | PDF | PyMuPDF, pdfplumber |
| 3 | CSIT321_Week03_2026.pdf | PDF | PyMuPDF, pdfplumber |
| 4 | Week4 - Cybersecurity Kill Chain II.pdf | PDF | PyMuPDF, pdfplumber |
| 5 | Week 5 - Malware Attack Technologies.pdf | PDF | PyMuPDF, pdfplumber |
| 6 | Week 6 - Law Regulation.pdf | PDF | PyMuPDF, pdfplumber |
| 7 | Week 7 - Data Forensics.pdf | PDF | PyMuPDF, pdfplumber |
| 8 | 8. deepfake detection.pdf | PDF | PyMuPDF, pdfplumber |
| 9 | 9. malware detection.pdf | PDF | PyMuPDF, pdfplumber |
| 10 | 10. network intrusion detection.pdf | PDF | PyMuPDF, pdfplumber |
| 11 | Developmental Psychology Week 10.pptx | PPTX | python-pptx |
| 12 | Air Polution -in Vietnam-.pptx | PPTX | python-pptx |
| 13 | 900053 W7-8 Circulatory system.pptx | PPTX | python-pptx |
| 14 | music.pptx | PPTX | python-pptx |
| 15 | MATH255 Lab Week 12 Spring 2024.pptx | PPTX | python-pptx |
| 16 | CSIT377 MODULE NOTES.docx | DOCX | python-docx |
| 17 | CSCI203 EXAM NOTES.docx | DOCX | python-docx |
| 18 | CSCI262 NOTES for final exam.docx | DOCX | python-docx |
| 19 | biol214.docx | DOCX | python-docx |
| 20 | csit115-lecture-notes.docx | DOCX | python-docx |

---

## 2. Quality Comparison Matrix

| Criterion | PyMuPDF | pdfplumber | python-pptx | python-docx |
|-----------|---------|------------|-------------|-------------|
| Plain text accuracy | Clean, consistent | Clean, consistent | Clean per shape | Clean, consistent |
| Reading order | Correct | Correct | Shape order only | Correct |
| Real tables detected | All found, precise | All found | All found | All found |
| False positive tables | None | High, 11+ ghost tables | None | None |
| Table cell accuracy | Accurate | Accurate where real | Accurate | Accurate |
| Multi-column layout | Collapsed to one row | Collapsed to one row | Shape-by-shape | Not applicable |
| Equations | Plain text only | Plain text only | Plain text only | Plain text only |
| Code blocks | No formatting kept | No formatting kept | No formatting kept | Font detectable |
| Special characters | No issues | PUA garbage chars | No issues | PUA chars (biol214) |
| Image-only pages | Explicit placeholder | Silent empty string | Shape skipped | Not applicable |
| Garbage output risk | Low | High | Low | Low |

### Parser Strengths and Weaknesses

| Parser | Strengths | Weaknesses |
|--------|-----------|------------|
| PyMuPDF | Precise tables, clean text, no false positives | Fragments reference-list rules into fake tables |
| pdfplumber | Detects rotated text other parsers miss | Very high false positive rate on slide-based PDFs |
| python-pptx | Native PPTX XML, no rendering artifacts | Shape order does not match visual reading order |
| python-docx | Cleanest overall result, zero noise | Cannot process PDF or PPTX files |

---

## 3. Extraction Quality

### 3.1 PyMuPDF

PyMuPDF produced reliable, clean text extraction across all 10 PDF samples. Text output was well-structured, consistently ordered, and matched the visual page content. On the CSIT321 weekly slide PDFs (Week01 to Week03), it correctly identified 4, 2, and 2 real tables respectively with zero false positives. Across the five remaining samples (Week05–07, malware detection, data forensics) no tables were found, which is correct since those files contain only text and images.

On the research paper PDFs (`8. deepfake detection.pdf`, `10. network intrusion detection.pdf`), PyMuPDF produced fragmented table output on reference list pages. A single citation was spread across 7 to 16 cells in a one-row table. This is caused by thin horizontal rules beneath each reference being misread as table borders, not by a flaw in the parser logic.

### 3.2 pdfplumber

pdfplumber matched PyMuPDF on plain text quality across all 10 PDF samples. The same real tables were detected on the same pages with equal cell accuracy. However, pdfplumber produced significantly more false positives. Across the three CSIT321 weekly PDFs it returned 15 table results compared to PyMuPDF's 8, with the extra results being empty tables from decorative slide borders and image placeholder frames. This behaviour was consistent across all slide-based PDFs tested.

One notable exception: on `9. malware detection.pdf` page 10, pdfplumber extracted a rotated vertical axis label that PyMuPDF skipped entirely. The output was `s i s y l a n A e r a w l a M` — "Malware Analysis" reversed with spaces between each character. While not directly usable, this shows pdfplumber can surface content that PyMuPDF misses in certain layout configurations.

### 3.3 python-pptx

python-pptx was tested on 5 PPTX files from different subjects. Only one file (Developmental Psychology Week 10) contained an embedded table, which was extracted correctly as 4 rows × 2 columns with accurate cell content. The remaining 4 files had no tables and python-pptx correctly reported none.

Text extraction across all slides was clean and complete. The parser reads each shape's text frame independently, so visually adjacent content blocks on a slide are extracted as separate items. Layout relationships between shapes are not preserved — only the text within each shape is returned. Because python-pptx reads the native `.pptx` XML source directly, it is unaffected by the PDF rendering artifacts and font substitution issues that affect the two PDF parsers.

### 3.4 python-docx

python-docx produced the cleanest overall extraction of the four parsers. Across 5 DOCX files, all real tables were found with correct structure and zero false positives. The CSIT377 MODULE NOTES file alone contained 15 tables, all extracted with correct column counts and accurate cell content.

In `CSCI262 NOTES for final exam.docx`, several 1×1 table cells contained code-like content such as process scheduling sequences and shell commands. The author had used Word table formatting to visually box code snippets rather than a Code paragraph style. python-docx extracted the content correctly but cannot distinguish these from ordinary data tables. In `biol214.docx`, arrow symbols stored as Wingdings font characters appeared in output as raw Unicode Private Use Area codepoints (`\uf0e0`), which is a source document encoding issue rather than a parser failure.

---

## 4. Tables, Equations, and Code Blocks

### 4.1 Tables

**Best for PDF tables: PyMuPDF**

PyMuPDF found all real tables across all 10 PDF samples with zero false positives. For the CSIT321 assessment schedule (7 columns × 7 rows, Week01 page 39) and the Complex Computing Problem matrix (10 rows × 3 columns, Week01 page 26), PyMuPDF produced accurate cell-level output. pdfplumber found the same real tables but cannot be recommended for slide-based PDFs due to the volume of ghost tables it generates from decorative borders.

**Best for PPTX tables: python-pptx**

python-pptx is the only parser in this evaluation capable of reading `.pptx` files natively. It correctly extracted the one real table found in the PPTX test set (4 rows × 2 columns, nature-nurture definitions table). No alternative parser exists for this file format.

**Best for DOCX tables: python-docx**

python-docx extracted all 15 tables in CSIT377 MODULE NOTES with correct structure, ranging from 2-column attribute tables to 4-column architecture comparison tables. No false positives were produced across any of the 5 DOCX samples.

### 4.2 Equations

None of the four parsers handle mathematical equations as structured notation. All four render any equation content as plain text characters with no MathML or LaTeX output. The samples tested did not contain formal mathematical equations, so this limitation could not be directly observed. It is a known constraint of all four libraries. A dedicated tool such as MathPix or a PDF-to-LaTeX pipeline would be required if equation extraction is needed.

### 4.3 Code Blocks

No parser in this evaluation preserves code block formatting. PyMuPDF and pdfplumber extract code as plain text with no indentation or structure retained. python-pptx returns code slide content as regular paragraph text, indistinguishable from prose. python-docx is the closest to supporting code detection: monospace font runs (Courier New, Consolas) can be identified by inspecting `run.font.name` programmatically after extraction, allowing code to be separated from body text in a post-processing step. However, python-docx does not do this automatically.

In `CSCI262 NOTES for final exam.docx`, code content appeared inside 1×1 table cells. The content was preserved accurately — examples extracted include `$ gcc hello.c # Compile program $ ./a.out` and `ping -l 65527 IP-address` — but the cells were not flagged as code.

---

## 5. Edge Cases That Produce Garbage Output

### Case 1 — pdfplumber: False Positive Tables from Slide Layout Boxes

**Files:** CSIT321_Week01 pages 19–20, 34, 72 / Week02 pages 14, 17, 19 / Week03 pages 21, 23, 43

**Observed output:** Rows of empty strings — `['', '']`, `['', '', '', '']`

**Cause:** pdfplumber treats any closed rectangular border as a table regardless of whether it contains data. Slide templates use bordered boxes for image placeholders and decorative frames, which are all misidentified as tables.

**Impact:** High noise in output — 11 ghost tables across the three weekly PDFs alone. Downstream code must filter empty tables before any further processing.

---

### Case 2 — pdfplumber: Unicode Private Use Area Character in Slide Text

**File:** CSIT321_Week01_2026.pdf, page 34

**Observed output:** `Emailing \uf075 To have your requests respond`

**Cause:** The slide uses a Wingdings or Webdings icon font to render a bullet arrow symbol. pdfplumber extracts the raw Unicode codepoint `\uf075`, which has no standard meaning. PyMuPDF drops or normalises the same character silently.

**Fix:** Apply a regex filter before writing output:
```python
re.sub(r'[\uf000-\uf8ff]', '', text)
```

---

### Case 3 — Both PDF Parsers: Reference List Rules Fragmented into Fake Tables

**Files:** `8. deepfake detection.pdf` pages 9–10 / `10. network intrusion detection.pdf` pages 29–44

**Observed output:**
```
['Zong, W., Chow, Y.W. and Susilo, W., 202', 'dimensional visualization of  network int',
'achine learning.', 'Future Generation Computer Systems,', '102', ', pp.292', '-306.']
```

**Cause:** Reference list pages use thin horizontal rules beneath each citation entry. Both parsers read these decorative lines as table borders and split the citation text across columns at arbitrary word boundaries. A single readable citation becomes a 1-row table with 7 to 16 fragmented cells.

**Impact:** Severe for `10. network intrusion detection.pdf` — 16 garbage tables produced across pages 29–44. Citations are unusable without reconstruction. No real tabular data exists on any of those pages.

---

### Case 4 — pdfplumber: Rotated Text Extracted as Reversed Character Sequence

**File:** `9. malware detection.pdf`, page 10

**Observed output:** `['', 's i s y l a n A e r a w l a M', 'Static Dynamic']`

**Cause:** A vertical axis label reading "Malware Analysis" is rotated 90 degrees in the PDF. pdfplumber extracted the characters in reverse order with a space inserted between each letter. PyMuPDF skipped the element entirely.

**Impact:** The string is not readable as intended. Post-processing to detect and reverse spaced single-character sequences would be required to recover the original text.

---

### Case 5 — python-docx: Code Blocks Stored as Single-Cell Tables

**File:** `CSCI262 NOTES for final exam.docx`

**Observed output:**
```
['$ gcc hello.c # Compile program $ ./a.ou']
['ping -l 65527 IP-address']
```

**Cause:** The document author used Word's table border style to visually box code snippets rather than a Code paragraph style. python-docx extracts the content correctly as table cells but has no way to identify them as code. They are structurally identical to any other single-cell table.

**Impact:** Low — content is preserved and readable. Automated pipelines treating all 1×1 tables as data tables would need a separate handling rule for these cells.

---

### Case 6 — python-docx: Wingdings Arrow Symbols as Unreadable Codepoints

**File:** `biol214.docx`

**Observed output:** `['\uf0e0', 'Acetyl CoA', 'Acetyl CoA', ...]`

**Cause:** The source document uses Wingdings font for arrow symbols. python-docx extracts the raw Private Use Area codepoint `\uf0e0` without substituting a readable equivalent.

**Impact:** Same as Case 2 — apply the PUA regex filter. This is a source document encoding issue, not a parser failure, but it produces unreadable characters in output.

---

### Case 7 — Both PDF Parsers: Sparse WBS Table Appears Broken

**File:** CSIT321_Week03_2026.pdf, page 49

**Observed output:** 5 rows × 6 columns, most cells empty:
```
['Problem 1.1.1 Analysis', '', '', '', '', '']
```

**Cause:** The work breakdown structure table uses merged cells and blank spacing columns. Both parsers correctly detect the table structure, but the output resembles a failed extraction.

**Impact:** Low — manual verification against the source PDF confirms the blank cells are genuine. This is correct parser behaviour, not garbage output, but it can be misread as an extraction error without cross-referencing the original file.

---

## 6. Recommendations

| Use Case | Recommended Parser | Reason |
|----------|--------------------|--------|
| PDF table extraction | PyMuPDF | Zero false positives, precise structure detection |
| PDF plain text | PyMuPDF or pdfplumber | Both produce equivalent quality for prose content |
| PDF complex slide layout | PyMuPDF with `pymupdf_layout` | Package flagged in output for improved layout analysis |
| PPTX files | python-pptx | Only option for native PPTX XML, no rendering artifacts |
| DOCX files | python-docx | Cleanest extraction overall, zero false positives |
| Avoid pdfplumber when | Processing slide-based PDFs | False positive rate too high from decorative borders |
| Post-processing needed | All parsers | Filter PUA range `[\uf000-\uf8ff]` and skip empty tables |
