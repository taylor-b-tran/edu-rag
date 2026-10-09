"""The seed course text makes no claim the product cannot back up.

The seed chunks are embedded as CSIT321 course material, so students receive
their sentences as grounded, cited answers. They used to promise a cloud LLM
switch, a preserved-citations failure path, audit logs and an ingest endpoint,
none of which exist. These tests keep those claims out, and keep the identity
of every chunk fixed, because the retrieval evaluation sets and citations
depend on the doc ids, files and pages.
"""
from __future__ import annotations

import re

from src.document_processor.seed_documents import SEED_DOCUMENTS

_IDENTITY_KEYS = ("doc_id", "source_file", "page_number", "topic", "week")

PINNED_IDENTITY = [
    ('csit321-w1-rag-intro', 'Week1_RAG_Introduction.pdf', 1, 'RAG Fundamentals', 'Week 1'),
    ('csit321-w1-rag-components', 'Week1_RAG_Introduction.pdf', 2, 'RAG Fundamentals', 'Week 1'),
    ('csit321-w2-embeddings', 'Week2_Vector_Embeddings.pdf', 1, 'Vector Embeddings', 'Week 2'),
    ('csit321-w2-chunking', 'Week2_Vector_Embeddings.pdf', 3, 'Vector Embeddings', 'Week 2'),
    ('csit321-w3-chromadb', 'Week3_ChromaDB_VectorStore.pdf', 1, 'ChromaDB', 'Week 3'),
    ('csit321-w3-chromadb-api', 'Week3_ChromaDB_VectorStore.pdf', 2, 'ChromaDB', 'Week 3'),
    ('csit321-w4-flask', 'Week4_Flask_WebApplication.pdf', 1, 'Flask API', 'Week 4'),
    ('csit321-w4-jwt-rbac', 'Week4_Flask_WebApplication.pdf', 3, 'Flask API', 'Week 4'),
    ('csit321-w4-architecture', 'Week4_Flask_WebApplication.pdf', 5, 'Flask API', 'Week 4'),
    ('csit321-w5-ollama', 'Week5_Ollama_Generation.pdf', 1, 'Ollama & LLM Generation', 'Week 5'),
    ('csit321-w5-prompt-engineering', 'Week5_Ollama_Generation.pdf', 2, 'Ollama & LLM Generation', 'Week 5'),
    ('csit321-w5-latency', 'Week5_Ollama_Generation.pdf', 4, 'Ollama & LLM Generation', 'Week 5'),
    ('csit321-w6-evaluation', 'Week6_RAG_Evaluation.pdf', 1, 'RAG Evaluation', 'Week 6'),
    ('csit321-w6-fallback', 'Week6_RAG_Evaluation.pdf', 2, 'RAG Evaluation', 'Week 6'),
    ('csit321-w7-security', 'Week7_Security_Deployment.pdf', 1, 'Security & Deployment', 'Week 7'),
    ('csit321-w7-docker', 'Week7_Security_Deployment.pdf', 3, 'Security & Deployment', 'Week 7'),
    ('csit321-w7-database', 'Week7_Security_Deployment.pdf', 5, 'Security & Deployment', 'Week 7'),
    ('csit321-overview-system', 'Week1_RAG_Introduction.pdf', 3, 'System Overview', 'Week 1'),
    ('csit321-w14-spring-structure', 'Week14_Introduction_to_Spring.pptx', 5, 'Spring Session Structure', 'Week 14'),
    ('csit321-w14-assessment-schedule', 'Week14_Introduction_to_Spring.pptx', 6, 'Spring Session Structure', 'Week 14'),
    ('csit321-w14-a4-prototype', 'Week14_Introduction_to_Spring.pptx', 9, 'A4 Prototype Requirements', 'Week 14'),
    ('csit321-w14-a5-a6-documentation', 'Week14_Introduction_to_Spring.pptx', 13, 'A5/A6 Final Documentation', 'Week 14'),
    ('csit214-w1-pm-fundamentals', 'CSIT214_Week1_Introduction.pdf', 1, 'Introduction to IT Project Management', 'Week 1'),
    ('csit214-w1-project-charter', 'CSIT214_Week1_Introduction.pdf', 4, 'Introduction to IT Project Management', 'Week 1'),
    ('csit214-w3-scope-wbs', 'CSIT214_Week3_ScopeManagement.pdf', 2, 'Project Scope Management', 'Week 3'),
    ('csit214-w4-critical-path', 'CSIT214_Week4_ScheduleManagement.pdf', 3, 'Project Schedule Management', 'Week 4'),
    ('csit214-w6-function-points', 'CSIT214_Week6_CostEstimation.pdf', 2, 'Cost and Effort Estimation', 'Week 6'),
    ('csit214-w6-cocomo', 'CSIT214_Week6_CostEstimation.pdf', 5, 'Cost and Effort Estimation', 'Week 6'),
    ('csit214-w8-scrum-roles', 'CSIT214_Week8_AgileScrum.pdf', 2, 'Agile and Scrum', 'Week 8'),
    ('csit214-w8-scrum-ceremonies', 'CSIT214_Week8_AgileScrum.pdf', 4, 'Agile and Scrum', 'Week 8'),
    ('csit214-w10-risk-management', 'CSIT214_Week10_RiskManagement.pdf', 2, 'Risk Management', 'Week 10'),
    ('csit214-w13-ethics', 'CSIT214_Week13_Ethics.pdf', 3, 'Professional and Ethical Responsibility', 'Week 13'),
    ('csci369-w1-intro-ethical-hacking', 'CSCI369_Week1_Introduction.pdf', 1, 'Introduction to Ethical Hacking', 'Week 1'),
    ('csci369-w1-pentest-lifecycle', 'CSCI369_Week1_Introduction.pdf', 3, 'Introduction to Ethical Hacking', 'Week 1'),
    ('csci369-w2-pentest-concepts', 'CSCI369_Week2_PenTestConcepts.pdf', 1, 'Penetration Testing Concepts and Information Gathering', 'Week 2'),
    ('csci369-w2-osint-footprinting', 'CSCI369_Week2_PenTestConcepts.pdf', 3, 'Penetration Testing Concepts and Information Gathering', 'Week 2'),
    ('csci369-w3-tcpip-basics', 'CSCI369_Week3_TCPIP_CIDR.pdf', 1, 'TCP/IP Basics, CIDR Addressing, Capturing Traffic', 'Week 3'),
    ('csci369-w3-cidr-capture', 'CSCI369_Week3_TCPIP_CIDR.pdf', 3, 'TCP/IP Basics, CIDR Addressing, Capturing Traffic', 'Week 3'),
    ('csci369-w4-scanning', 'CSCI369_Week4_Scanning_ARP.pdf', 1, 'Scanning and ARP Basics', 'Week 4'),
    ('csci369-w4-arp-basics', 'CSCI369_Week4_Scanning_ARP.pdf', 4, 'Scanning and ARP Basics', 'Week 4'),
    ('csci369-w5-mitm-concept', 'CSCI369_Week5_MITM_ARP_Poisoning.pdf', 1, 'MITM and ARP Poisoning', 'Week 5'),
    ('csci369-w5-arp-defence', 'CSCI369_Week5_MITM_ARP_Poisoning.pdf', 3, 'MITM and ARP Poisoning', 'Week 5'),
    ('math202-w1-first-order-ode', 'MATH202_Week1_FirstOrderODEs.pdf', 1, 'First-Order Differential Equations', 'Week 1'),
    ('math202-w2-linear-integrating-factor', 'MATH202_Week2_LinearFirstOrder.pdf', 2, 'First-Order Differential Equations', 'Week 2'),
    ('math202-w3-second-order-homogeneous', 'MATH202_Week3_SecondOrderODEs.pdf', 1, 'Second-Order Linear Differential Equations', 'Week 3'),
    ('math202-w4-modelling-applications', 'MATH202_Week4_Applications.pdf', 2, 'Applications of Differential Equations', 'Week 4'),
]

_OPENAI_SWITCH = re.compile(
    r"switch\w*\s+(?:\w+\s+){0,6}(?:to\s+)?the\s+(?:fallback\s+)?OpenAI|OpenAI provider",
    re.IGNORECASE,
)

# Claims that were false for this release, each with the text that carried it.
_STALE_CLAIMS = (
    "OPENAI_API_KEY",
    "CHROMA_HOST equivalent",
    "oldest history turns are dropped",
    "preserves the retrieved citations",
    "qwen3:14b",
    "llama3.2",
    "four services",
    "MIME type",
    "adversarial instruction",
    "audit logs",
    "POST /api/ingest",
)


def _text(doc_id: str) -> str:
    return next(d["text"] for d in SEED_DOCUMENTS if d["doc_id"] == doc_id)


def test_seed_text_makes_no_openai_provider_claim():
    offenders = [
        d["doc_id"] for d in SEED_DOCUMENTS
        if "OPENAI_API_KEY" in d["text"] or _OPENAI_SWITCH.search(d["text"])
    ]
    assert offenders == []


def test_seed_text_has_no_stale_product_claims():
    offenders = {
        d["doc_id"]: [c for c in _STALE_CLAIMS if c.lower() in d["text"].lower()]
        for d in SEED_DOCUMENTS
    }
    assert {k: v for k, v in offenders.items() if v} == {}


def test_seed_identity_unchanged():
    identity = [tuple(d.get(k) for k in _IDENTITY_KEYS) for d in SEED_DOCUMENTS]
    assert len(SEED_DOCUMENTS) == 46
    assert identity == PINNED_IDENTITY


def test_ollama_rationale_kept():
    text = _text("csit321-w5-ollama").lower()
    for word in ("privacy", "cost", "offline"):
        assert word in text


def test_generation_failure_text_matches_the_api():
    text = _text("csit321-w5-prompt-engineering")
    assert "503" in text and "stores nothing" in text
