SEED_DOCUMENTS = [
    # Week 1 – RAG Fundamentals
    {
        "doc_id"     : "csit321-w1-rag-intro",
        "source_file": "Week1_RAG_Introduction.pdf",
        "page_number": 1,
        "topic"      : "RAG Fundamentals",
        "week"       : "Week 1",
        "text"       : (
            "Retrieval-Augmented Generation (RAG) is a technique introduced by Lewis et al. (2020) "
            "that combines a dense retrieval step with a generative language model. "
            "RAG stands for Retrieval-Augmented Generation. "
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
        "doc_id"     : "csit321-w1-rag-components",
        "source_file": "Week1_RAG_Introduction.pdf",
        "page_number": 2,
        "topic"      : "RAG Fundamentals",
        "week"       : "Week 1",
        "text"       : (
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

    # Week 2 – Vector Embeddings & Chunking
    {
        "doc_id"     : "csit321-w2-embeddings",
        "source_file": "Week2_Vector_Embeddings.pdf",
        "page_number": 1,
        "topic"      : "Vector Embeddings",
        "week"       : "Week 2",
        "text"       : (
            "A vector embedding is a numeric representation of text in a high-dimensional space "
            "where semantically similar texts are placed close together. "
            "SentenceTransformers (Reimers and Gurevych, 2019) provides pre-trained models "
            "that produce these embeddings efficiently. "
            "The embedding model used in EduRAG is all-MiniLM-L6-v2, which produces "
            "384-dimensional vectors and achieves a strong balance between speed and retrieval "
            "quality. The output size is 384 dimensions. "
            "Embeddings are generated once during document ingestion and stored in ChromaDB. "
            "At query time, the same model embeds the student's question, and cosine similarity "
            "is computed between the question vector and all stored chunk vectors."
        ),
    },
    {
        "doc_id"     : "csit321-w2-chunking",
        "source_file": "Week2_Vector_Embeddings.pdf",
        "page_number": 3,
        "topic"      : "Vector Embeddings",
        "week"       : "Week 2",
        "text"       : (
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

    # Week 3 – ChromaDB Vector Store
    {
        "doc_id"     : "csit321-w3-chromadb",
        "source_file": "Week3_ChromaDB_VectorStore.pdf",
        "page_number": 1,
        "topic"      : "ChromaDB",
        "week"       : "Week 3",
        "text"       : (
            "ChromaDB is an open-source vector database designed for embedding storage and "
            "similarity search. It supports persistent storage, metadata filtering, and an "
            "HTTP API that makes it straightforward to deploy as a Docker container. "
            "In EduRAG, ChromaDB serves as the vector store for all course-indexed chunks. "
            "Each chunk is stored with metadata fields including course_id, source_file, "
            "page_number, chunk_index, and topic. "
            "The course_id metadata field is critical for multi-course isolation: it allows "
            "the retrieval module to apply a where filter so that a query for CSIT321 never "
            "returns chunks from another course, preventing cross-course retrieval leakage. "
            "ChromaDB was chosen over FAISS because it provides built-in metadata filtering, "
            "persistent storage without manual serialisation, and a REST HTTP API suitable "
            "for Docker-based deployment. FAISS is an in-memory library that requires custom "
            "persistence and does not natively support metadata-scoped queries."
        ),
    },
    {
        "doc_id"     : "csit321-w3-chromadb-api",
        "source_file": "Week3_ChromaDB_VectorStore.pdf",
        "page_number": 2,
        "topic"      : "ChromaDB",
        "week"       : "Week 3",
        "text"       : (
            "The ChromaDB Python client provides a simple API for collections. "
            "A collection is created with client.get_or_create_collection(name, ...). "
            "Documents are added with collection.add(ids, documents, embeddings, metadatas). "
            "Retrieval is performed with collection.query(query_embeddings, n_results, where). "
            "The where parameter accepts MongoDB-style filter expressions such as "
            "{'course_id': {'$eq': 'CSIT321'}} to scope results to a single course. "
            "Results include documents, distances, and metadatas, which together provide "
            "everything needed to display a grounded answer with source citations. "
            "EduRAG connects to ChromaDB via its HTTP client when CHROMA_HOST is set, "
            "enabling the same code to work against both a local PersistentClient in "
            "development and a Dockerised ChromaDB service in production."
        ),
    },

    # Week 4 – Flask API & Authentication
    {
        "doc_id"     : "csit321-w4-flask",
        "source_file": "Week4_Flask_WebApplication.pdf",
        "page_number": 1,
        "topic"      : "Flask API",
        "week"       : "Week 4",
        "text"       : (
            "Flask is a lightweight Python web framework used in EduRAG as the web application "
            "layer. It exposes REST endpoints for authentication, document upload, query "
            "submission, and session management. "
            "The key routes are: POST /api/auth/login to issue an access token; "
            "POST /api/auth/signup to register a student or lecturer; POST /api/query to accept "
            "a student question and return a grounded answer; POST /api/documents/upload to "
            "accept a Lecturer's document and trigger asynchronous indexing; "
            "GET /api/documents to list indexed documents for a course; "
            "GET /api/health for a liveness check. "
            "EduRAG accepts PDF, DOCX, and PPTX file formats for document upload. "
            "Flask's blueprint system separates auth, query, document, and admin routes "
            "into distinct modules, forming a modular monolith architecture."
        ),
    },
    {
        "doc_id"     : "csit321-w4-jwt-rbac",
        "source_file": "Week4_Flask_WebApplication.pdf",
        "page_number": 3,
        "topic"      : "Flask API",
        "week"       : "Week 4",
        "text"       : (
            "Authentication in EduRAG uses opaque bearer tokens held server-side, "
            "rather than self-describing tokens such as JWTs. "
            "On successful login the server issues an access token and a refresh token, and "
            "records the user_id, role, enrolled_courses and expiry time against them. "
            "Holding the tokens server-side is what lets logout revoke access immediately; "
            "a stateless token could not be withdrawn before it expired on its own. "
            "Access tokens expire after 3600 seconds (one hour) and refresh tokens after "
            "fourteen days. A refresh token is single-use and is retired as it is spent. "
            "Every protected endpoint validates the Authorization: Bearer <token> header "
            "before processing. "
            "Role-Based Access Control (RBAC) enforces three roles: "
            "Student (query only), Lecturer (upload and document management), "
            "Admin (system configuration, metrics, user management). "
            "Expired or tampered tokens receive an HTTP 401 response. "
            "Rate limiting is applied per authenticated user_id taken from the token, "
            "so the rate limit window is tied to the token's identity, not just the IP address. "
            "This prevents a single user from abusing the query endpoint even across "
            "network changes."
        ),
    },
    {
        "doc_id"     : "csit321-w4-architecture",
        "source_file": "Week4_Flask_WebApplication.pdf",
        "page_number": 5,
        "topic"      : "Flask API",
        "week"       : "Week 4",
        "text"       : (
            "EduRAG uses a modular monolith architecture: all components (API, RAG pipeline, "
            "document processor) run in a single deployable unit but are organised into "
            "distinct Python packages with clear boundaries. "
            "This gives the team the simplicity of a single deployment process while "
            "maintaining the internal structure needed to refactor individual components "
            "without touching unrelated code. "
            "Compared to a microservices architecture, the modular monolith avoids network "
            "latency between internal calls, removes the need for service discovery and "
            "inter-service authentication, and greatly simplifies local development and "
            "debugging. "
            "The document upload flow is asynchronous: the API accepts the file, queues an "
            "indexing job, and returns a job_id immediately so the lecturer is not blocked "
            "waiting for embedding generation. "
            "The query flow is synchronous because the student expects a real-time answer "
            "and the retrieval + generation latency is bounded and predictable."
        ),
    },

    # Week 5 – Ollama & LLM Generation
    {
        "doc_id"     : "csit321-w5-ollama",
        "source_file": "Week5_Ollama_Generation.pdf",
        "page_number": 1,
        "topic"      : "Ollama & LLM Generation",
        "week"       : "Week 5",
        "text"       : (
            "Ollama is a local LLM runtime that allows developers to run open-weight language "
            "models on their own hardware without requiring cloud API keys or internet "
            "connectivity during development. "
            "EduRAG uses Ollama during development instead of the OpenAI API for three reasons: "
            "(1) privacy – student queries and course material never leave the institution's "
            "infrastructure; (2) cost – no per-token API charges during development and testing; "
            "(3) offline capability – the system works without internet access in lab environments. "
            "Ollama exposes an HTTP API at http://localhost:11434 (or the CHROMA_HOST equivalent "
            "in Docker). The generate endpoint accepts a model name, a prompt, and options such "
            "as temperature and num_predict. "
            "The default model is llama3.2, configurable via OLLAMA_MODEL environment variable. "
            "In production, the same LLMResponseGeneration module can switch to the OpenAI API "
            "by changing a single environment variable."
        ),
    },
    {
        "doc_id"     : "csit321-w5-prompt-engineering",
        "source_file": "Week5_Ollama_Generation.pdf",
        "page_number": 2,
        "topic"      : "Ollama & LLM Generation",
        "week"       : "Week 5",
        "text"       : (
            "Prompt construction is critical to grounded answer quality. "
            "EduRAG uses a structured prompt template with four sections: "
            "(1) a system instruction telling the model to answer only from the provided context "
            "and to state clearly when it cannot find relevant information; "
            "(2) an optional conversation history block containing the last three student–Paedia "
            "exchanges, injected so the model can resolve pronouns and follow-up questions; "
            "if the prompt would exceed the context window, the oldest history turns are dropped; "
            "(3) a context block containing the top-k retrieved chunks, each labelled with its "
            "source file and page number; "
            "(4) the student's current question. "
            "When no chunks exceed the similarity threshold, the context block is replaced with "
            "a notice and the model is instructed to label its response as general knowledge "
            "not verified against course materials. "
            "If the LLM provider is unreachable, the system returns a service-unavailable "
            "message and preserves the retrieved citations so the operator can retry or "
            "switch to the fallback OpenAI provider."
        ),
    },
    {
        "doc_id"     : "csit321-w5-latency",
        "source_file": "Week5_Ollama_Generation.pdf",
        "page_number": 4,
        "topic"      : "Ollama & LLM Generation",
        "week"       : "Week 5",
        "text"       : (
            "The EduRAG query response time target is under 5 seconds for a typical student "
            "question on standard development hardware. "
            "The two main latency contributors are: "
            "(1) vector retrieval – ChromaDB cosine search across the indexed collection, "
            "typically under 100 ms for collections up to 10,000 chunks; "
            "(2) LLM generation – the time for Ollama to produce the answer token-by-token, "
            "which depends on model size, hardware (CPU vs GPU), and prompt length. "
            "On GPU-accelerated hardware with qwen3:14b, generation averages 2-4 seconds. "
            "On CPU-only hardware, generation can exceed 60 seconds for large models, "
            "which is why llama3.2 (3B parameters) is used as the CPU-safe default."
        ),
    },

    # Week 6 – Evaluation & Fallback
    {
        "doc_id"     : "csit321-w6-evaluation",
        "source_file": "Week6_RAG_Evaluation.pdf",
        "page_number": 1,
        "topic"      : "RAG Evaluation",
        "week"       : "Week 6",
        "text"       : (
            "RAG evaluation requires measuring both retrieval quality and generation quality. "
            "Retrieval quality is assessed with information-retrieval metrics: "
            "Precision@K measures the fraction of the top-K retrieved chunks that are actually "
            "relevant to the query; Recall@K measures the fraction of all relevant chunks that "
            "appear in the top-K results. "
            "EduRAG targets Precision@5 >= 0.7 and Recall@10 >= 0.8 on the labelled pilot set. "
            "Generation quality is assessed by checking whether the answer is faithfully grounded "
            "in the retrieved evidence (groundedness) and whether the source citations correctly "
            "identify the supporting chunk (citation accuracy). "
            "A lightweight automated option is Ragas (Es et al., 2023), which scores "
            "faithfulness and answer relevance without requiring human labels."
        ),
    },
    {
        "doc_id"     : "csit321-w6-fallback",
        "source_file": "Week6_RAG_Evaluation.pdf",
        "page_number": 2,
        "topic"      : "RAG Evaluation",
        "week"       : "Week 6",
        "text"       : (
            "Fallback behaviour is an essential safety control in a RAG system. "
            "When no retrieved chunk exceeds the cosine similarity threshold (SIMILARITY_THRESHOLD, "
            "default 0.35 in EduRAG's local configuration, equivalent to cosine distance 0.65), "
            "the system must not silently use general model knowledge as if it were course material. "
            "Instead, the response is labelled: 'Based on general knowledge — not verified "
            "against course materials.' "
            "This label protects academic trust by making the epistemic status of every answer "
            "visible to the student. "
            "The threshold should be tuned on the labelled query set: a threshold that is too "
            "high causes frequent unnecessary fallbacks; a threshold that is too low allows "
            "weakly relevant chunks to pollute the context."
        ),
    },

    # Week 7 – Security, Deployment & Data Storage
    {
        "doc_id"     : "csit321-w7-security",
        "source_file": "Week7_Security_Deployment.pdf",
        "page_number": 1,
        "topic"      : "Security & Deployment",
        "week"       : "Week 7",
        "text"       : (
            "EduRAG treats prompts, retrieved chunks, and uploaded files as untrusted input. "
            "Prompt injection is mitigated by placing system instructions at the highest priority "
            "position and validating that retrieved chunks do not contain adversarial instruction "
            "overrides before insertion into the prompt. "
            "Uploaded documents are validated for MIME type and file size before any parsing. "
            "Passwords are hashed with bcrypt (cost factor >= 12) before storage in PostgreSQL. "
            "All API keys and secrets are loaded from environment variables; no secrets are "
            "hardcoded or committed to version control. "
            "These controls address the OWASP Top 10 for LLM Applications (2025) items on "
            "prompt injection and sensitive information disclosure. "
            "Rate limiting is applied per user_id to prevent query flooding. "
            "The system is considered secure for development use; a full security audit "
            "is recommended before production deployment."
        ),
    },
    {
        "doc_id"     : "csit321-w7-docker",
        "source_file": "Week7_Security_Deployment.pdf",
        "page_number": 3,
        "topic"      : "Security & Deployment",
        "week"       : "Week 7",
        "text"       : (
            "EduRAG is deployed as a Docker Compose multi-container stack with four services: "
            "the Flask API container, the ChromaDB vector store container (HTTP API on port 8000), "
            "the PostgreSQL relational database container, and the Ollama LLM container. "
            "Persistent Docker volumes are used for uploaded files, relational data, and vector "
            "indexes so container restarts do not erase system state. "
            "The CHROMA_HOST and CHROMA_PORT environment variables tell the ingestion and "
            "retrieval code to connect to the ChromaDB HTTP service rather than a local "
            "PersistentClient, making the same Python code work in both local dev and Docker. "
            "For sprint demonstrations, the LLM provider can switch from Ollama to the OpenAI "
            "API by changing a single OPENAI_API_KEY environment variable."
        ),
    },
    {
        "doc_id"     : "csit321-w7-database",
        "source_file": "Week7_Security_Deployment.pdf",
        "page_number": 5,
        "topic"      : "Security & Deployment",
        "week"       : "Week 7",
        "text"       : (
            "EduRAG uses PostgreSQL alongside ChromaDB because they serve different data needs. "
            "ChromaDB stores vector embeddings and supports similarity search — it is optimised "
            "for the retrieval step of the RAG pipeline. "
            "PostgreSQL stores relational data: user accounts, authentication tokens, course "
            "enrolments, document metadata, upload records, and audit logs. "
            "Using ChromaDB for all storage is not appropriate because ChromaDB has no support "
            "for relational integrity, foreign key constraints, transactional writes, or "
            "complex joins. "
            "When a lecturer deletes a document, the system must perform two operations to "
            "preserve consistency: (1) remove the document's chunks from ChromaDB by their "
            "stored IDs to prevent stale vectors from being retrieved; (2) delete the document "
            "record and associated metadata from PostgreSQL. "
            "Both operations must succeed or both must be rolled back to avoid a state where "
            "the database record is gone but orphan vectors remain searchable."
        ),
    },

    # System Overview – for ambiguous queries
    {
        "doc_id"     : "csit321-overview-system",
        "source_file": "Week1_RAG_Introduction.pdf",
        "page_number": 3,
        "topic"      : "System Overview",
        "week"       : "Week 1",
        "text"       : (
            "EduRAG (Paedia) is a Retrieval-Augmented Generation system for university courses. "
            "The system works as follows: a student submits a question through the Streamlit "
            "chat interface; the Flask API authenticates the bearer token; the RAG pipeline "
            "encodes the question as a vector embedding using all-MiniLM-L6-v2; ChromaDB is "
            "queried for the top-5 most similar chunks filtered by the student's course_id; "
            "if chunks exceed the similarity threshold, they are inserted into a structured "
            "prompt and sent to the Ollama LLM (llama3.2 or qwen3:14b); the answer is returned "
            "with source citations showing the originating PDF file and page number. "
            "If the system encounters an error, students should check that Ollama is running "
            "('ollama serve'), that ChromaDB is reachable, and that the corpus has been ingested. "
            "Administrators can re-ingest the corpus via POST /api/ingest with force=true."
        ),
    },
]