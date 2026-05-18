# EduRAG Sample Course Material Manifest

**Sprint 3 · Group 19 · CSIT321 Project 37 · University of Wollongong**  
**Prepared by:** Tung Phuong Anh Huynh  
**Last updated:** 15 May 2026

> **Storage location:** `data/samples/` (gitignored — do not commit raw files to the repository)

---

## Where to Get These Files

### Group A — From inside CSIT321 (Moodle)

Log in to Moodle with your UOW student account, go to the CSIT321 subject page, and download directly from the weekly lecture sections. No external link needed — you are enrolled so you have access.

| # | Save the file as | Where to find it on Moodle | Format |
|---|-----------------|---------------------------|--------|
| 1 | `csit321_week1_lecture.pdf` | Week 1 → "Week 1 Lecture Slides — Autumn" | PDF |
| 2 | `csit321_week1_ip_bethany.pdf` | Week 1 → "Intellectual Property by Bethany Pons" | PDF |
| 3 | `csit321_week2_lecture.pdf` | Week 2 → "Week 2 Lecture — Autumn" | PDF |
| 4 | `csit321_week3_lecture.pdf` | Week 3 → "Week 3 Lecture — Autumn" | PDF |
| 5 | `csit321_week3_uxui_genai.pdf` | Week 3 → "UX/UI Design in the Age of GenAI" | PDF |
| 6 | `csit321_code_of_conduct.pdf` | Course Resources → "Code-of-Professional-Conduct v2.1" | PDF |

> These files are downloaded by enrolled students for their own study — this is standard educational fair use. Do **not** share them outside the team or commit them to a public repository.

---

### Group B — Freely available online (direct PDF links — no login required)

All links below open a PDF directly in your browser. Right-click → Save As to download. No login, no paywall.

#### EduRAG-related: RAG, LLMs, Embeddings

| # | Save the file as | Direct PDF link | Source | License | ~Pages |
|---|-----------------|----------------|--------|---------|--------|
| 7 | `rag_survey_gao_2024.pdf` | https://arxiv.org/pdf/2312.10997 | arXiv — *RAG for Large Language Models: A Survey*, Gao et al. 2023 | Open access | ~21 |
| 8 | `rag_from_pdfs_guide.pdf` | https://arxiv.org/pdf/2410.15944 | arXiv — *Developing RAG Systems from PDFs: An Experience Report* | Open access | ~36 |
| 9 | `rag_original_paper.pdf` | https://arxiv.org/pdf/2005.11401 | arXiv — *RAG for Knowledge-Intensive NLP Tasks*, Lewis et al. (the original RAG paper) | Open access | ~20 |
| 10 | `embeddings_nlp_book.pdf` | https://josecamachocollados.com/book_embNLP_draft.pdf | Open draft textbook — *Embeddings in NLP*, Camacho-Collados | Free draft | ~164 (use ch.1–3 only) |

#### Related to CSIT321 topics: Software Engineering, Databases

| # | Save the file as | Direct PDF link | Source | License | ~Pages |
|---|-----------------|----------------|--------|---------|--------|
| 11 | `software_eng_lecture_mrcet.pdf` | https://mrcet.com/downloads/digital_notes/CSE/III%20Year/Software%20Engineering.pdf | MRCET open lecture notes — Software Engineering (covers agile, requirements, architecture) | Open university notes | ~166 |
| 12 | `databases_cambridge_lectures.pdf` | https://www.cl.cam.ac.uk/teaching/2324/Databases/djg-materials/databases_2324_1to8-D.pdf | Cambridge University — *Introduction to Databases* lectures 1–8, Greaves 2023 | Open academic material | ~171 |
| 13 | `stanford_nlp_embeddings.pdf` | https://web.stanford.edu/~jurafsky/slp3/6.pdf | Stanford — *Speech and Language Processing* Ch.6 (neural nets & embeddings), Jurafsky & Martin | Open draft textbook | ~28 |

---

## Full File Inventory

| # | Filename | Source | License | Est. Pages | Key Topics | Parser Challenges |
|---|----------|--------|---------|-----------|-----------|-----------------|
| 1 | `csit321_week1_lecture.pdf` | CSIT321 Moodle | Course material (own enrolment) | ~72 | Software engineering process, agile, project lifecycle | Bullet-heavy slides, multi-column |
| 2 | `csit321_week1_ip_bethany.pdf` | CSIT321 Moodle | Course material (own enrolment) | ~11 | Intellectual property, copyright, software licensing | Text-heavy, legal language |
| 3 | `csit321_week2_lecture.pdf` | CSIT321 Moodle | Course material (own enrolment) | ~34 | Requirements engineering, use cases, user stories | Bullet slides, diagrams |
| 4 | `csit321_week3_lecture.pdf` | CSIT321 Moodle | Course material (own enrolment) | ~52 | System architecture, design patterns, tradeshow prep | Architecture diagrams, bullets |
| 5 | `csit321_week3_uxui_genai.pdf` | CSIT321 Moodle | Course material (own enrolment) | ~29 | UX/UI design, GenAI interfaces, design systems | Image-heavy slides, mixed layout |
| 6 | `csit321_code_of_conduct.pdf` | CSIT321 Moodle | Course material (own enrolment) | ~9 | Professional conduct, ethics, academic integrity | Dense numbered clauses |
| 7 | `rag_survey_gao_2024.pdf` | arXiv | Open access | ~21 | RAG pipeline architecture, retrieval strategies, LLM grounding | Academic two-column, footnotes, references |
| 8 | `rag_from_pdfs_guide.pdf` | arXiv | Open access | ~36 | RAG from PDFs end-to-end, chunking, embedding, generation | Academic paper, code snippets |
| 9 | `rag_original_paper.pdf` | arXiv | Open access | ~20 | Original RAG paper: retriever, generator, training | Dense academic, equations |
| 10 | `embeddings_nlp_book.pdf` | Open textbook draft | Free draft | ~164 (ch.1–3) | Word embeddings, sentence embeddings, vector spaces | Textbook layout, figures, tables |
| 11 | `software_eng_lecture_mrcet.pdf` | MRCET open notes | Open university notes | ~166 (first half) | Agile, waterfall, requirements, design patterns, testing | Long prose, numbered sections |
| 12 | `databases_cambridge_lectures.pdf` | Cambridge University | Open academic | ~171 | Relational model, SQL, ER diagrams, NoSQL | Slides + prose, tables, code blocks |
| 13 | `stanford_nlp_embeddings.pdf` | Stanford (open draft) | Open draft textbook | ~28 | Neural nets, word embeddings, feedforward networks | Textbook, figures, equations |

**Total corpus: ~810 pages across 13 files**
*(For the PoC notebook you only need 1 file to start — recommend `csit321_week3_lecture.pdf` or `rag_survey_gao_2024.pdf`)*

---

## Parser Stress-Test Coverage

| Parser Challenge | Covered By |
|-----------------|-----------|
| Standard text paragraphs | Files 2, 6, 8, 11 |
| Bullet-point heavy slides | Files 1, 3, 4 |
| Multi-column slide layout | Files 1, 4, 5 |
| Image-heavy / diagram slides | Files 4, 5 |
| Academic two-column layout with footnotes | Files 7, 9 |
| Code snippets inline | Files 8, 12 |
| Mathematical equations | Files 9, 10, 13 |
| Tables with multiple columns | Files 10, 12 |
| Dense legal / policy text | Files 2, 6 |
| Long prose sections | Files 11, 12 |

---

*Document maintained by: Tung Phuong Anh Huynh — CSIT321 Project 37, Group 19*

---

## Sprint 4 Corpus Expansion Candidates (Task 16)

**Added by:** Tung Phuong Anh Huynh  
**Reviewed in sandbox:** 11 May 2026  
**Purpose:** Extend the sample corpus with DOCX and PPTX formats so Ngoc's multi-format chunker extension and Tung's API test evidence can be checked against non-PDF inputs.

> These files are listed as local sample inputs. Because `data/samples/` is ignored, the team should confirm whether to keep binary sample files outside Git or explicitly approve tracking them before merging.

### Candidate Files

| # | Filename | Format | Local location | Key topics |
|---|----------|--------|----------------|------------|
| 14 | `csit321_rag_fundamentals.docx` | DOCX | `data/samples/` | RAG pipeline, chunking strategy, embeddings, evaluation metrics |
| 15 | `csit321_system_design.pptx` | PPTX | `data/samples/` | System architecture, RBAC, upload pipeline, query flow, NFRs, design patterns |
| 16 | `csit321_database_concepts.docx` | DOCX | `data/samples/` | SQL, normalisation, ER modelling, PostgreSQL features, ChromaDB versus relational storage |

### Review Notes

The committed branch text claimed chunk counts using a `512/50 overlap` setup and a 12 May 2026 verification date. The sandbox rerun on 11 May 2026 used the current accepted project baseline, `chunk_size=1024` and `chunk_overlap=0`.

| File | Rerun chunks | Max chars | Avg chars | Metadata keys |
|------|-------------:|----------:|----------:|---------------|
| `csit321_rag_fundamentals.docx` | 4 | 1006 | 797 | source, format, chunk_index |
| `csit321_system_design.pptx` | 6 | 786 | 626 | source, format, slide_number |
| `csit321_database_concepts.docx` | 4 | 1018 | 927 | source, format, chunk_index |

The binary sample files were kept as local ignored inputs, not tracked Git content. Merge only this manifest evidence unless the team explicitly approves committing raw files under `data/samples/`.

*Document maintained by: Tung Phuong Anh Huynh — CSIT321 Project 37, Group 19*