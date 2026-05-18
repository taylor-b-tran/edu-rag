SEED_DOCUMENTS = [
    # ── Week 1: RAG Fundamentals ──────────────────────────────────────────
    {
        "doc_id": "csit321-w1-rag-intro",
        "source_file": "Week1_RAG_Introduction.pdf",
        "page_number": 1,
        "topic": "RAG Fundamentals",
        "week": "Week 1",
        "text": (
            "Retrieval-Augmented Generation (RAG) is a technique introduced by Lewis et al. (2020) "
            "that combines a dense retrieval step with a generative language model. "
            "The system first retrieves relevant passages from a knowledge base using semantic search, "
            "then conditions its generated answer on those passages. "
            "This approach addresses the hallucination problem in large language models: "
            "by grounding the answer in retrieved evidence, the model is less likely to produce "
            "confident but factually incorrect statements. "
            "RAG is particularly suited to closed-domain question answering over private corpora "
            "such as course materials, legal documents, or internal company knowledge bases."
        ),
    },
    {
        "doc_id": "csit321-w1-rag-components",
        "source_file": "Week1_RAG_Introduction.pdf",
        "page_number": 2,
        "topic": "RAG Fundamentals",
        "week": "Week 1",
        "text": (
            "A RAG pipeline has three core components: "
            "(1) a document ingestion pipeline that extracts text, splits it into chunks, "
            "and encodes each chunk as a dense vector embedding; "
            "(2) a vector store (such as ChromaDB or FAISS) that indexes those embeddings "
            "and supports approximate nearest-neighbour search; "
            "(3) a generation module that receives the original query together with the top-k "
            "retrieved chunks and produces a grounded natural-language answer. "
            "The retrieval step uses cosine similarity between the query embedding and the stored "
            "chunk embeddings to rank candidates. The generation step uses a large language model "
            "such as Ollama (local) or OpenAI GPT-4 (cloud) to synthesise the final response."
        ),
    },
    # ── Week 2: Vector Embeddings ─────────────────────────────────────────
    {
        "doc_id": "csit321-w2-embeddings",
        "source_file": "Week2_Vector_Embeddings.pdf",
        "page_number": 1,
        "topic": "Vector Embeddings",
        "week": "Week 2",
        "text": (
            "A vector embedding is a numeric representation of text in a high-dimensional space "
            "where semantically similar texts are placed close together. "
            "SentenceTransformers (Reimers and Gurevych, 2019) provides pre-trained models "
            "that produce these embeddings efficiently. "
            "The model used in EduRAG is all-MiniLM-L6-v2, which produces 384-dimensional vectors "
            "and achieves a strong balance between speed and retrieval quality. "
            "Embeddings are generated once during document ingestion and stored in ChromaDB. "
            "At query time, the same model embeds the student's question, and cosine similarity "
            "is computed between the question vector and all stored chunk vectors."
        ),
    },
    {
        "doc_id": "csit321-w2-chunking",
        "source_file": "Week2_Vector_Embeddings.pdf",
        "page_number": 3,
        "topic": "Vector Embeddings",
        "week": "Week 2",
        "text": (
            "Chunking strategy significantly affects retrieval quality. "
            "A chunk that is too short loses context; a chunk that is too long dilutes the "
            "similarity signal. The EduRAG baseline uses chunk_size=1024 characters with "
            "chunk_overlap=0. "
            "This was chosen because CSIT321 lecture slides tend to contain self-contained "
            "explanatory paragraphs of roughly that length. "
            "Overlap is set to zero for the initial benchmark to keep chunk boundaries clean "
            "and citation metadata unambiguous. "
            "After baseline evaluation, overlap values of 128-256 characters may be tested "
            "to see whether they improve Recall@10 on hard reasoning queries."
        ),
    },
    # ── Week 3: ChromaDB ──────────────────────────────────────────────────
    {
        "doc_id": "csit321-w3-chromadb",
        "source_file": "Week3_ChromaDB_VectorStore.pdf",
        "page_number": 1,
        "topic": "ChromaDB",
        "week": "Week 3",
        "text": (
            "ChromaDB is an open-source vector database designed for embedding storage and "
            "similarity search. It supports persistent storage, metadata filtering, and an "
            "HTTP API that makes it straightforward to deploy as a Docker container. "
            "In EduRAG, ChromaDB is used as the vector store for all course-indexed chunks. "
            "Each chunk is stored with metadata fields including course_id, source_file, "
            "page_number, chunk_index, and topic. "
            "The course_id metadata field is critical: it allows the retrieval module to apply "
            "a where filter so that a query for CSIT321 never returns chunks from another course."
        ),
    },
    {
        "doc_id": "csit321-w3-chromadb-api",
        "source_file": "Week3_ChromaDB_VectorStore.pdf",
        "page_number": 2,
        "topic": "ChromaDB",
        "week": "Week 3",
        "text": (
            "The ChromaDB Python client provides a simple API for collections. "
            "A collection is created with client.get_or_create_collection(name, ...). "
            "Documents are added with collection.add(ids, documents, embeddings, metadatas). "
            "Retrieval is performed with collection.query(query_embeddings, n_results, where). "
            "The where parameter accepts MongoDB-style filter expressions such as "
            "{'course_id': {'$eq': 'CSIT321'}} to scope results to a single course. "
            "Results include documents, distances, and metadatas, which together provide "
            "everything needed to display a grounded answer with source citations."
        ),
    },
    # ── Week 4: Flask API ─────────────────────────────────────────────────
    {
        "doc_id": "csit321-w4-flask",
        "source_file": "Week4_Flask_WebApplication.pdf",
        "page_number": 1,
        "topic": "Flask API",
        "week": "Week 4",
        "text": (
            "Flask is a lightweight Python web framework used in EduRAG as the WebApplication layer. "
            "It exposes REST endpoints for authentication, document upload, query submission, "
            "and session management. "
            "The key routes are: POST /api/auth/login to issue a JWT; POST /api/query to accept "
            "a student question and return a grounded answer; POST /api/upload to accept a "
            "Lecturer's document and trigger asynchronous indexing; GET /api/documents to list "
            "indexed documents for a course; GET /api/health for a liveness check. "
            "Flask's blueprint system is used to separate auth, query, and admin routes "
            "into distinct modules."
        ),
    },
    {
        "doc_id": "csit321-w4-jwt-rbac",
        "source_file": "Week4_Flask_WebApplication.pdf",
        "page_number": 3,
        "topic": "Flask API",
        "week": "Week 4",
        "text": (
            "Authentication in EduRAG uses JSON Web Tokens (JWT, RFC 7519). "
            "On successful login, the server issues a signed token containing the user_id, role, "
            "and expiry time. Every protected endpoint validates this token before processing. "
            "Role-Based Access Control (RBAC) enforces three roles: "
            "Student (query only), Lecturer (upload and document management), "
            "Admin (system configuration, metrics, user management). "
            "Tokens are validated with a decorator that checks the Authorization header. "
            "Expired or tampered tokens receive an HTTP 401 response."
        ),
    },
    # ── Week 5: Ollama & LLM Generation ──────────────────────────────────
    {
        "doc_id": "csit321-w5-ollama",
        "source_file": "Week5_Ollama_Generation.pdf",
        "page_number": 1,
        "topic": "Ollama & LLM Generation",
        "week": "Week 5",
        "text": (
            "Ollama is a local LLM runtime that allows developers to run open-weight language models "
            "on their own hardware without requiring cloud API keys or internet connectivity during "
            "development. EduRAG uses Ollama as its development LLM provider, with the "
            "llama3.2 model as the default. "
            "Ollama exposes an HTTP API at http://localhost:11434. "
            "The generate endpoint accepts a model name, a prompt string, and optional parameters "
            "such as temperature and num_predict. "
            "In EduRAG's LLMResponseGeneration module, the retrieved chunks are formatted into "
            "a context block and prepended to the student's question before being sent to Ollama."
        ),
    },
    {
        "doc_id": "csit321-w5-prompt-engineering",
        "source_file": "Week5_Ollama_Generation.pdf",
        "page_number": 2,
        "topic": "Ollama & LLM Generation",
        "week": "Week 5",
        "text": (
            "Prompt construction is critical to grounded answer quality. "
            "EduRAG uses a structured prompt template with three sections: "
            "(1) a system instruction that tells the model to answer only from the provided context "
            "and to explicitly state when it cannot find relevant information; "
            "(2) a context block containing the top-k retrieved chunks, each labelled with its "
            "source file and page number; "
            "(3) the student's question. "
            "The instruction section is placed first to exploit position-based attention weighting. "
            "When no chunks exceed the similarity threshold, the context block is replaced with "
            "a notice and the model is instructed to label its response as general knowledge "
            "not verified against course materials."
        ),
    },
    # ── Week 6: Evaluation ────────────────────────────────────────────────
    {
        "doc_id": "csit321-w6-evaluation",
        "source_file": "Week6_RAG_Evaluation.pdf",
        "page_number": 1,
        "topic": "RAG Evaluation",
        "week": "Week 6",
        "text": (
            "RAG evaluation requires measuring both retrieval quality and generation quality. "
            "Retrieval quality is assessed with information-retrieval metrics: "
            "Precision@K measures the fraction of the top-K retrieved chunks that are actually "
            "relevant to the query; Recall@K measures the fraction of all relevant chunks that "
            "appear in the top-K results. "
            "EduRAG targets Precision@5 >= 0.7 and Recall@10 >= 0.8 on the labelled pilot set. "
            "Generation quality is assessed manually by checking whether the answer is "
            "faithfully grounded in the retrieved evidence (groundedness) and whether the "
            "source citations correctly identify the supporting chunk (citation accuracy). "
            "A lightweight automated option is Ragas (Es et al., 2023), which scores "
            "faithfulness and answer relevance without requiring human labels."
        ),
    },
    {
        "doc_id": "csit321-w6-fallback",
        "source_file": "Week6_RAG_Evaluation.pdf",
        "page_number": 2,
        "topic": "RAG Evaluation",
        "week": "Week 6",
        "text": (
            "Fallback behaviour is an essential safety control in a RAG system. "
            "When no retrieved chunk exceeds the cosine similarity threshold (default 0.35 in "
            "EduRAG's local ChromaDB configuration), the system must not silently use general "
            "model knowledge as if it were course material. "
            "Instead, the response is labelled: 'Based on general knowledge — not verified "
            "against course materials.' "
            "This label protects academic trust by making the epistemic status of every answer "
            "visible to the student. "
            "The threshold value should be tuned on the labelled query set: a threshold that "
            "is too high causes frequent unnecessary fallbacks; a threshold that is too low "
            "allows weakly relevant chunks to pollute the context."
        ),
    },
    # ── Week 7: Security & Deployment ────────────────────────────────────
    {
        "doc_id": "csit321-w7-security",
        "source_file": "Week7_Security_Deployment.pdf",
        "page_number": 1,
        "topic": "Security & Deployment",
        "week": "Week 7",
        "text": (
            "EduRAG treats prompts, retrieved chunks, and uploaded files as untrusted input. "
            "Prompt injection is mitigated by placing system instructions at the highest priority "
            "position and by validating that retrieved chunks do not contain adversarial "
            "instruction overrides before they are inserted into the prompt. "
            "Uploaded documents are validated for MIME type and file size before any parsing "
            "is attempted. "
            "Passwords are hashed with bcrypt (cost factor >= 12) before storage in PostgreSQL. "
            "All API keys and secrets are loaded from environment variables; no secrets are "
            "hardcoded or committed to version control. "
            "These controls address the OWASP Top 10 for LLM Applications (2025) items on "
            "prompt injection and sensitive information disclosure."
        ),
    },
    {
        "doc_id": "csit321-w7-docker",
        "source_file": "Week7_Security_Deployment.pdf",
        "page_number": 3,
        "topic": "Security & Deployment",
        "week": "Week 7",
        "text": (
            "EduRAG is deployed as a Docker Compose multi-container stack. "
            "Three containers run on the same host: the Flask application container, "
            "the ChromaDB container (accessed via its HTTP API), and the PostgreSQL container. "
            "Persistent Docker volumes are used for uploaded files, relational data, and vector "
            "indexes so that container restarts do not erase system state. "
            "The LLM provider is the only external dependency: Ollama runs as a host service "
            "during development and is reached from the application container over the Docker "
            "host network bridge. For sprint demonstrations, the same module can switch to "
            "the OpenAI API by changing a single environment variable."
        ),
    },
]
