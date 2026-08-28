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

    # ======================================================================
    # T8-13 (Sprint 8, Tung Phuong Anh Huynh) — additional real UOW subjects
    # so the corpus covers more than one course. Each entry below carries an
    # explicit "course_id" so multi-course retrieval (course_id metadata
    # filter in rag_pipeline.VectorRetriever.search) actually separates
    # results instead of every chunk silently defaulting to CSIT321.
    # ======================================================================

    # CSIT321 Week 14 (Spring session) — Introduction to Spring
    {
        "doc_id"     : "csit321-w14-spring-structure",
        "course_id"  : "CSIT321",
        "source_file": "Week14_Introduction_to_Spring.pptx",
        "page_number": 5,
        "topic"      : "Spring Session Structure",
        "week"       : "Week 14",
        "text"       : (
            "CSIT321 continues into the Spring session as Week 14 (Spring Week 1), "
            "picking up the same capstone project groups from the Autumn session. "
            "Spring lectures run in Weeks 14, 21 and 24 (Spring Weeks 1, 8 and 11); "
            "workshops run in Week 15 (partially covering A4) and Week 22 (covering A5), "
            "both delivered online. "
            "More of the work in Spring happens as group collaboration, but marking "
            "continues to be done individually, so each member's contribution still "
            "needs to be visible in the team's records. "
            "TechExpo, the project group's public demonstration event, is scheduled "
            "for Week 26 (tentatively 29 October)."
        ),
    },
    {
        "doc_id"     : "csit321-w14-assessment-schedule",
        "course_id"  : "CSIT321",
        "source_file": "Week14_Introduction_to_Spring.pptx",
        "page_number": 6,
        "topic"      : "Spring Session Structure",
        "week"       : "Week 14",
        "text"       : (
            "The CSIT321 assessment schedule spans both sessions. A1 (Initial Project "
            "Description) is due in Week 5 and marked satisfactory/unsatisfactory. "
            "A2 (Design Progress, 15%) is due Week 9 and A3 (Project Requirements and "
            "Interface Presentation, 10%) is due Week 12. "
            "In Spring, A4 (Prototype Presentation, 15%) is due in Week 15, delivered "
            "as an in-workshop presentation with a report submitted on Moodle. "
            "A5 (Final Product and Documentation, 45%) is due Week 25 and is the "
            "largest single assessment in the subject. "
            "A6 (Marketing and Technical Presentation, 15%) is due Week 26, delivered "
            "as a video presentation timed at a maximum of 20 minutes in total."
        ),
    },
    {
        "doc_id"     : "csit321-w14-a4-prototype",
        "course_id"  : "CSIT321",
        "source_file": "Week14_Introduction_to_Spring.pptx",
        "page_number": 9,
        "topic"      : "A4 Prototype Requirements",
        "week"       : "Week 14",
        "text"       : (
            "A4 (Prototype Presentation) must build on the group's initial project "
            "requirements documentation from earlier assessments. It should present a "
            "working prototype and describe the architectural aspects of the project: "
            "the functionality of the system and how a user is expected to interact "
            "with it, the interface designs, the information architecture, supporting "
            "diagrams, the code and database structure, the core technology choices, "
            "and the project's branding and style guide. "
            "The presentation itself is capped at 8 minutes including questions, with "
            "6 minutes recommended as the target length; documents are submitted as "
            "PDF and the code as a single zipped file (maximum 200 MB) through the "
            "Moodle dropbox. "
            "Groups are encouraged to use a Requirements Traceability Matrix to show "
            "what has been developed so far against what was originally proposed."
        ),
    },
    {
        "doc_id"     : "csit321-w14-a5-a6-documentation",
        "course_id"  : "CSIT321",
        "source_file": "Week14_Introduction_to_Spring.pptx",
        "page_number": 13,
        "topic"      : "A5/A6 Final Documentation",
        "week"       : "Week 14",
        "text"       : (
            "A5 (Final Product and Documentation) requires a user manual describing "
            "how to use the system for its target users, potentially with a quick-start "
            "guide for basic tasks; a technical report covering system requirements, "
            "a project summary explaining how the system met its original requirements "
            "with a requirements traceability matrix, the system design (information "
            "architecture, API design, data dictionaries), a project closeout section "
            "with lessons learned, and installation instructions; group meeting agendas "
            "and minutes; and the source code. "
            "A6 (Marketing and Technical Presentation) is a video presentation matching "
            "the group's public project image, typically split into a short marketing "
            "pitch (which can reuse TechExpo material) and a longer technical discussion "
            "that walks through the codebase in more depth than the marketing segment."
        ),
    },

    # CSIT214: IT Project Management
    # Concepts below follow standard, vendor-neutral project-management
    # frameworks (PMBOK-style process groups, the Scrum Guide, IFPUG-style
    # Function Point Analysis, COCOMO II).
    {
        "doc_id"     : "csit214-w1-pm-fundamentals",
        "course_id"  : "CSIT214",
        "source_file": "CSIT214_Week1_Introduction.pdf",
        "page_number": 1,
        "topic"      : "Introduction to IT Project Management",
        "week"       : "Week 1",
        "text"       : (
            "A project is a temporary, planned undertaking with specific objectives, "
            "carried out by a temporary team under time and resource constraints — "
            "distinct from routine operational work and from open-ended research. "
            "IT projects are considered especially challenging because software is "
            "intangible (harder to inspect progress on than physical construction), "
            "made up of many interdependent components, constrained by the need to "
            "conform to existing systems, and easy to change, which invites scope creep. "
            "Every project is bounded by the triple constraint of scope, time and cost, "
            "with quality often added as a fourth dimension: tightening one constraint "
            "generally forces a trade-off in at least one of the others. "
            "Project stakeholders include anyone affected by the project, directly or "
            "indirectly — sponsors, users, developers, and regulators — and their "
            "objectives can conflict, which is why stakeholder identification is one of "
            "the first activities in project initiation."
        ),
    },
    {
        "doc_id"     : "csit214-w1-project-charter",
        "course_id"  : "CSIT214",
        "source_file": "CSIT214_Week1_Introduction.pdf",
        "page_number": 4,
        "topic"      : "Introduction to IT Project Management",
        "week"       : "Week 1",
        "text"       : (
            "The project charter is the document that formally authorises a project "
            "and gives the project manager the authority to apply organisational "
            "resources to it. A typical charter records the project title and "
            "authorisation date, the project manager's authority level, a summary "
            "schedule and budget, the objectives and business justification, success "
            "criteria, a high-level approach, key stakeholders, and a sign-off section. "
            "Projects are usually selected using a mix of methods: aligning to broad "
            "organisational needs, categorising projects as responding to a problem, "
            "opportunity, or directive, and financial techniques such as Net Present "
            "Value (NPV), Return on Investment (ROI), payback analysis, and weighted "
            "scoring models that let decision-makers compare projects against multiple "
            "weighted criteria rather than cost alone."
        ),
    },
    {
        "doc_id"     : "csit214-w3-scope-wbs",
        "course_id"  : "CSIT214",
        "source_file": "CSIT214_Week3_ScopeManagement.pdf",
        "page_number": 2,
        "topic"      : "Project Scope Management",
        "week"       : "Week 3",
        "text"       : (
            "Scope management covers planning, collecting requirements, defining "
            "scope, creating the Work Breakdown Structure (WBS), validating scope, "
            "and controlling scope. Requirements are gathered through interviews, "
            "focus groups, workshops, questionnaires, and direct observation. "
            "The Work Breakdown Structure decomposes the total project deliverable "
            "into progressively smaller, deliverable-oriented components; the smallest "
            "unit is a work package, and each item should appear exactly once, be "
            "assigned to a single responsible person, and sum in effort to the level "
            "above it. WBS decomposition can proceed top-down from major deliverables, "
            "bottom-up from known tasks, by analogy to a similar past project, or by "
            "mind-mapping outward from the core idea. "
            "Scope creep — the tendency for scope to keep expanding without a "
            "corresponding adjustment to time or cost — is controlled by keeping "
            "stakeholders engaged throughout, maintaining clear requirements "
            "documentation, and running every proposed change through a formal "
            "change-control process rather than accepting it informally."
        ),
    },
    {
        "doc_id"     : "csit214-w4-critical-path",
        "course_id"  : "CSIT214",
        "source_file": "CSIT214_Week4_ScheduleManagement.pdf",
        "page_number": 3,
        "topic"      : "Project Schedule Management",
        "week"       : "Week 4",
        "text"       : (
            "The Critical Path Method (CPM) finds the longest sequence of dependent "
            "activities through a project network — the critical path — which "
            "determines the shortest possible project duration; any delay on that "
            "path delays the whole project, whereas non-critical activities have "
            "float (slack) and can be delayed somewhat without affecting the finish "
            "date. CPM works by a forward pass, computing each activity's Earliest "
            "Start (ES) and Earliest Finish (EF = ES + duration) from the project "
            "start, followed by a backward pass from the project end, computing "
            "Latest Finish (LF) and Latest Start (LS = LF - duration). "
            "Float is calculated as LF - ES - duration; activities with zero float "
            "lie on the critical path, and a project can have more than one critical "
            "path simultaneously. "
            "PERT extends this by using three time estimates per activity — optimistic "
            "(a), most likely (m), and pessimistic (b) — combined as the expected "
            "duration t_e = (a + 4m + b) / 6, which accounts for schedule uncertainty "
            "that a single-point estimate ignores."
        ),
    },
    {
        "doc_id"     : "csit214-w6-function-points",
        "course_id"  : "CSIT214",
        "source_file": "CSIT214_Week6_CostEstimation.pdf",
        "page_number": 2,
        "topic"      : "Cost and Effort Estimation",
        "week"       : "Week 6",
        "text"       : (
            "Function Point Analysis (the IFPUG/Albrecht method) estimates software "
            "size independently of the implementation language by counting five "
            "function types: Internal Logical Files and External Interface Files "
            "(data functions), and External Inputs, External Outputs, and External "
            "Queries (transaction functions). Each occurrence is rated low, average, "
            "or high complexity and weighted accordingly to give the Unadjusted "
            "Function Point count (UFP). "
            "The Value Adjustment Factor (VAF) then scales that count based on 14 "
            "General System Characteristics rated 0-5, using VAF = 0.65 + (0.01 x "
            "Total Degree of Influence); the final size is Function Points = UFP x VAF. "
            "Estimating methods more broadly include bottom-up estimating (summing "
            "estimates for small, well-understood tasks), top-down estimating "
            "(splitting an overall estimate by typical phase proportions), expert "
            "judgement, and estimating by analogy to a similar completed project — "
            "each trading off accuracy against the amount of project detail available "
            "at estimation time."
        ),
    },
    {
        "doc_id"     : "csit214-w6-cocomo",
        "course_id"  : "CSIT214",
        "source_file": "CSIT214_Week6_CostEstimation.pdf",
        "page_number": 5,
        "topic"      : "Cost and Effort Estimation",
        "week"       : "Week 6",
        "text"       : (
            "COCOMO (COnstructive COst MOdel) estimates development effort in "
            "person-months from an estimate of software size. The original COCOMO 81 "
            "basic model uses Effort = c x size^k (size in thousands of lines of "
            "code), with the constants c and k depending on whether the project is "
            "organic, semi-detached, or embedded, reflecting increasing project rigidity. "
            "COCOMO II refines this with Effort (person-months) = A x size^sf x "
            "(effort multipliers), where A is a calibrated constant (2.94 in the "
            "published model), sf is a scale factor derived from five qualities — "
            "precedentedness, development flexibility, architecture/risk resolution, "
            "team cohesion, and process maturity — and the effort multipliers adjust "
            "for factors such as product reliability, required reuse, platform "
            "difficulty, personnel capability, and schedule pressure. "
            "Both models illustrate a general estimating principle: effort grows "
            "faster than size once a project's scale pushes past what a small, "
            "well-coordinated team can handle, which is why the exponent in these "
            "formulas is typically greater than one."
        ),
    },
    {
        "doc_id"     : "csit214-w8-scrum-roles",
        "course_id"  : "CSIT214",
        "source_file": "CSIT214_Week8_AgileScrum.pdf",
        "page_number": 2,
        "topic"      : "Agile and Scrum",
        "week"       : "Week 8",
        "text"       : (
            "Agile is not a single method but a philosophy for delivering value "
            "iteratively, expressed in the Agile Manifesto's preference for "
            "individuals and interactions over processes and tools, working software "
            "over comprehensive documentation, customer collaboration over contract "
            "negotiation, and responding to change over following a fixed plan. "
            "Scrum, the most widely used Agile framework, defines three roles: the "
            "Product Owner, who owns the product backlog and its priorities and is "
            "accountable for the return on investment; the Scrum Master, who "
            "safeguards the Scrum process and removes impediments for the team; and "
            "the Development Team, typically five to nine cross-functional, "
            "self-organising members whose composition stays fixed for the duration "
            "of a sprint. "
            "Work is organised as a prioritised product backlog of user stories in "
            "the format 'As a <type of user>, I want <goal> so that <reason>', pulled "
            "into a time-boxed sprint (commonly two to four weeks) and tracked in a "
            "sprint backlog that the team itself maintains."
        ),
    },
    {
        "doc_id"     : "csit214-w8-scrum-ceremonies",
        "course_id"  : "CSIT214",
        "source_file": "CSIT214_Week8_AgileScrum.pdf",
        "page_number": 4,
        "topic"      : "Agile and Scrum",
        "week"       : "Week 8",
        "text"       : (
            "Scrum's four ceremonies structure the sprint. Sprint Planning selects "
            "the sprint goal and builds the sprint backlog at the start of the sprint. "
            "The Daily Scrum is a 15-minute daily stand-up for the team to say what "
            "they did yesterday, what they will do today, and what is blocking them. "
            "The Sprint Review, held at the end of the sprint, is an informal "
            "demonstration of what was actually built, involving the whole team and "
            "any interested stakeholders. The Sprint Retrospective, held immediately "
            "after, is a short session (15-30 minutes) for the team to reflect on "
            "what worked and what did not, often structured as start/stop/continue. "
            "Effort is commonly estimated in relative story points, using a Fibonacci-"
            "like scale (1, 2, 3, 5, 8, 13...) rather than absolute hours, and refined "
            "through Planning Poker, where each estimator reveals a card "
            "simultaneously so early guesses do not anchor the group's discussion."
        ),
    },
    {
        "doc_id"     : "csit214-w10-risk-management",
        "course_id"  : "CSIT214",
        "source_file": "CSIT214_Week10_RiskManagement.pdf",
        "page_number": 2,
        "topic"      : "Risk Management",
        "week"       : "Week 10",
        "text"       : (
            "A project risk is an uncertain event or condition that, if it occurs, "
            "has a positive or negative effect on project objectives. Risk "
            "management proceeds through identification (checklists from past "
            "projects, brainstorming, causal mapping), analysis and prioritisation, "
            "planning a response, and ongoing monitoring. "
            "Risk Exposure (RE) is calculated as potential damage multiplied by "
            "probability of occurrence, giving a single comparable score across "
            "risks of very different character. "
            "The five standard response strategies are risk acceptance (doing "
            "nothing because the cost of mitigation exceeds the potential damage), "
            "avoidance (removing the risky activity or approach altogether), "
            "reduction (lowering the probability of occurrence), transfer (shifting "
            "the risk to another party, such as through insurance or a fixed-price "
            "contract), and mitigation (reducing the impact if the risk does occur). "
            "Risk Reduction Leverage (RRL) — the reduction in risk exposure divided "
            "by the cost of the risk-reduction action — helps decide whether a "
            "mitigation is worth implementing: an RRL greater than 1.0 indicates the "
            "action is worth its cost."
        ),
    },
    {
        "doc_id"     : "csit214-w13-ethics",
        "course_id"  : "CSIT214",
        "source_file": "CSIT214_Week13_Ethics.pdf",
        "page_number": 3,
        "topic"      : "Professional and Ethical Responsibility",
        "week"       : "Week 13",
        "text"       : (
            "Professional codes of conduct such as the PMI Code of Ethics and "
            "Professional Conduct are organised around four values: responsibility "
            "(owning one's decisions and their consequences), respect (showing "
            "regard for people and resources), fairness (acting impartially and "
            "disclosing conflicts of interest), and honesty (communicating truthfully "
            "and not providing misleading information). Each value carries both "
            "aspirational standards, which describe the conduct the profession "
            "strives for, and mandatory standards, which describe conduct that must "
            "never be violated — such as never offering or accepting a bribe, and "
            "never knowingly providing false or incomplete information to a "
            "stakeholder. "
            "Sustainability principles extend this ethical frame to a project's wider "
            "impact: balancing social, environmental and economic interests, "
            "considering both short- and long-term consequences, and ensuring "
            "stakeholders can participate in and scrutinise decisions that affect them."
        ),
    },

    # CSCI369: Ethical Hacking (Weeks 1-5) 
    # Conceptual, defence-oriented coverage aligned with standard references
    # (NIST SP 800-115, the OWASP Testing Guide, MITRE ATT&CK, and the core
    # IETF RFCs for the protocols involved). No exploit code or step-by-step
    # attack instructions are included — this mirrors what an introductory
    # ethical hacking subject actually teaches in its early weeks: concepts,
    # legal boundaries, and how to recognise/defend against each technique.
    {
        "doc_id"     : "csci369-w1-intro-ethical-hacking",
        "course_id"  : "CSCI369",
        "source_file": "CSCI369_Week1_Introduction.pdf",
        "page_number": 1,
        "topic"      : "Introduction to Ethical Hacking",
        "week"       : "Week 1",
        "text"       : (
            "Ethical hacking is the authorised practice of probing systems, "
            "networks, or applications for security weaknesses using the same "
            "techniques an attacker would use, but under an explicit, written "
            "agreement with the system owner and for the purpose of improving "
            "security rather than causing harm. "
            "Hackers are conventionally described by the metaphor of hat colour: "
            "white-hat testers operate with authorisation and disclose findings "
            "responsibly; black-hat attackers act without authorisation and for "
            "personal or malicious gain; grey-hat actors fall between the two, "
            "often testing systems without permission but without malicious intent. "
            "Security work is commonly framed around the CIA triad — confidentiality "
            "(preventing unauthorised disclosure), integrity (preventing unauthorised "
            "modification), and availability (ensuring authorised access when "
            "needed) — and an ethical hacking engagement should be scoped in advance "
            "against these goals. "
            "In Australia, unauthorised access to, or modification of, a computer "
            "system is a criminal offence under the Criminal Code Act 1995 (Cth) "
            "Part 10.7, which is why a signed scope-of-work and rules of engagement "
            "are a legal precondition for any penetration test, not just good practice."
        ),
    },
    {
        "doc_id"     : "csci369-w1-pentest-lifecycle",
        "course_id"  : "CSCI369",
        "source_file": "CSCI369_Week1_Introduction.pdf",
        "page_number": 3,
        "topic"      : "Introduction to Ethical Hacking",
        "week"       : "Week 1",
        "text"       : (
            "NIST Special Publication 800-115 (Technical Guide to Information "
            "Security Testing and Assessment) describes a penetration test as "
            "proceeding through planning, discovery, attack, and reporting phases. "
            "Planning agrees the rules of engagement — scope, timing, permitted "
            "techniques, and emergency contacts — before any technical activity "
            "starts. Discovery covers reconnaissance and scanning to build a picture "
            "of the target. Attack covers exploitation and, where agreed, escalation "
            "of access to demonstrate real-world impact. Reporting documents "
            "findings, their severity, and concrete remediation steps for the "
            "system owner. "
            "The reporting phase is often treated as the most important deliverable "
            "of the whole engagement: a vulnerability that is found but not clearly "
            "communicated, prioritised, and reproducible for the client's engineers "
            "provides little real security benefit."
        ),
    },
    {
        "doc_id"     : "csci369-w2-pentest-concepts",
        "course_id"  : "CSCI369",
        "source_file": "CSCI369_Week2_PenTestConcepts.pdf",
        "page_number": 1,
        "topic"      : "Penetration Testing Concepts and Information Gathering",
        "week"       : "Week 2",
        "text"       : (
            "Penetration tests are commonly classified by how much information the "
            "tester is given in advance. In black-box testing the tester starts with "
            "no internal knowledge of the target, simulating an external attacker; "
            "in white-box testing the tester has full access to source code, network "
            "diagrams, and credentials, allowing deeper coverage in less time; "
            "grey-box testing sits in between, typically giving the tester the level "
            "of access a legitimate low-privilege user would have. "
            "The OWASP Testing Guide and NIST SP 800-115 both treat information "
            "gathering as the foundation the rest of the engagement is built on: "
            "the more accurately the tester maps the target's attack surface, the "
            "more efficiently later scanning and exploitation phases can be targeted."
        ),
    },
    {
        "doc_id"     : "csci369-w2-osint-footprinting",
        "course_id"  : "CSCI369",
        "source_file": "CSCI369_Week2_PenTestConcepts.pdf",
        "page_number": 3,
        "topic"      : "Penetration Testing Concepts and Information Gathering",
        "week"       : "Week 2",
        "text"       : (
            "Information gathering splits into passive and active reconnaissance. "
            "Passive reconnaissance collects information without directly "
            "interacting with the target's systems — for example reading public "
            "job listings, company websites, and social media for technology and "
            "staffing clues, or using WHOIS lookups and public DNS records to map "
            "registered domains and mail servers. This category is often called "
            "Open-Source Intelligence (OSINT) because every source is publicly "
            "available. Active reconnaissance, by contrast, involves direct contact "
            "with the target, such as querying DNS servers for zone information or "
            "requesting pages from a web server, and is more likely to be logged or "
            "detected. "
            "Because passive reconnaissance leaves no trace on the target's systems, "
            "engagements typically exhaust passive sources before moving to active "
            "techniques, both to preserve stealth where required and to avoid "
            "unnecessary noise on the client's monitoring systems."
        ),
    },
    {
        "doc_id"     : "csci369-w3-tcpip-basics",
        "course_id"  : "CSCI369",
        "source_file": "CSCI369_Week3_TCPIP_CIDR.pdf",
        "page_number": 1,
        "topic"      : "TCP/IP Basics, CIDR Addressing, Capturing Traffic",
        "week"       : "Week 3",
        "text"       : (
            "The TCP/IP model layers network communication into (from bottom to "
            "top) the link layer, the internet layer (IP), the transport layer "
            "(TCP or UDP), and the application layer (HTTP, DNS, and similar "
            "protocols). Understanding this layering matters for security testing "
            "because different attack and defence techniques operate at different "
            "layers — ARP spoofing operates at the link layer, port scanning "
            "operates at the transport layer, and injection attacks typically "
            "operate at the application layer. "
            "TCP establishes a connection using a three-way handshake: the client "
            "sends a SYN packet, the server replies with SYN-ACK, and the client "
            "completes the handshake with an ACK; the connection is only considered "
            "established once all three segments have been exchanged. UDP, by "
            "contrast, is connectionless and sends datagrams without this handshake, "
            "trading reliability for lower overhead — which is also why UDP-based "
            "scanning and attacks behave differently from TCP-based ones."
        ),
    },
    {
        "doc_id"     : "csci369-w3-cidr-capture",
        "course_id"  : "CSCI369",
        "source_file": "CSCI369_Week3_TCPIP_CIDR.pdf",
        "page_number": 3,
        "topic"      : "TCP/IP Basics, CIDR Addressing, Capturing Traffic",
        "week"       : "Week 3",
        "text"       : (
            "Classless Inter-Domain Routing (CIDR), defined in RFC 4632, expresses "
            "an IP network as an address plus a prefix length, such as "
            "192.168.1.0/24, where the /24 indicates that the first 24 bits form the "
            "network portion and the remaining 8 bits identify hosts within it — "
            "giving 254 usable host addresses. A smaller prefix such as /16 covers a "
            "much larger address range, which matters for a penetration tester when "
            "scoping how much of a network is actually in-scope for scanning. "
            "Traffic capture tools such as Wireshark and tcpdump record packets "
            "passing a network interface, typically by placing the interface into "
            "promiscuous mode so it accepts frames not addressed to it, and save "
            "captures in the pcap format for later analysis. "
            "On a switched network (as opposed to an older hub-based network), "
            "promiscuous mode alone does not let a host see other hosts' unicast "
            "traffic, because a switch forwards frames only to the port associated "
            "with the destination MAC address — this limitation is exactly why "
            "techniques like ARP poisoning (Week 5) exist as a way to redirect "
            "traffic onto an attacker-controlled path so it can be observed."
        ),
    },
    {
        "doc_id"     : "csci369-w4-scanning",
        "course_id"  : "CSCI369",
        "source_file": "CSCI369_Week4_Scanning_ARP.pdf",
        "page_number": 1,
        "topic"      : "Scanning and ARP Basics",
        "week"       : "Week 4",
        "text"       : (
            "Network scanning identifies live hosts, open ports, and running "
            "services, typically using a tool such as Nmap. A TCP connect scan "
            "completes the full three-way handshake on each target port, which is "
            "reliable but easy to log; a TCP SYN scan (often called a half-open "
            "scan) sends only the initial SYN and never completes the handshake, "
            "making it faster and quieter, though still detectable by an intrusion "
            "detection system watching for unusual SYN patterns. UDP scanning is "
            "generally slower and less reliable than TCP scanning because UDP "
            "services often do not respond at all to an unexpected probe, so an "
            "open UDP port and a filtered one can look identical. "
            "Service and version detection follows port discovery, probing open "
            "ports to identify the specific software and version listening on them, "
            "which lets the tester cross-reference known vulnerabilities for that "
            "exact version rather than testing blindly."
        ),
    },
    {
        "doc_id"     : "csci369-w4-arp-basics",
        "course_id"  : "CSCI369",
        "source_file": "CSCI369_Week4_Scanning_ARP.pdf",
        "page_number": 4,
        "topic"      : "Scanning and ARP Basics",
        "week"       : "Week 4",
        "text"       : (
            "The Address Resolution Protocol (ARP), defined in RFC 826, maps a "
            "known IPv4 address to the corresponding MAC address on a local "
            "network segment. A host that needs to send a frame to an IP address "
            "it hasn't recently contacted broadcasts an ARP request asking 'who has "
            "this IP address', and the host owning that address replies directly "
            "with its MAC address. Hosts cache these mappings in an ARP table (or "
            "ARP cache) for a short period to avoid repeating the broadcast for "
            "every packet. "
            "ARP has no built-in authentication: a host is not required to prove it "
            "actually owns the IP address it claims in an ARP reply, and most "
            "operating systems will accept an unsolicited ARP reply (a 'gratuitous "
            "ARP') and update their cache accordingly. This lack of authentication "
            "is the root cause of the ARP poisoning technique covered in Week 5."
        ),
    },
    {
        "doc_id"     : "csci369-w5-mitm-concept",
        "course_id"  : "CSCI369",
        "source_file": "CSCI369_Week5_MITM_ARP_Poisoning.pdf",
        "page_number": 1,
        "topic"      : "MITM and ARP Poisoning",
        "week"       : "Week 5",
        "text"       : (
            "A man-in-the-middle (MITM) attack positions the attacker between two "
            "communicating parties so that traffic passes through, and can be "
            "read or altered by, the attacker without either party immediately "
            "noticing. On a local network, ARP poisoning is one of the most common "
            "ways to achieve this: because ARP has no authentication, an attacker "
            "can send forged ARP replies to a victim host and to the network's "
            "default gateway, each claiming that the attacker's MAC address "
            "corresponds to the other party's IP address. Both sides then update "
            "their ARP caches and begin sending their traffic to the attacker's "
            "machine, which the attacker typically then forwards on (after "
            "inspecting or modifying it) so the victim's connection appears to keep "
            "working normally. "
            "The impact of a successful MITM position ranges from passive traffic "
            "analysis to active session hijacking or credential capture on any "
            "protocol that is not properly encrypted and authenticated end-to-end, "
            "which is exactly why protocols like HTTPS and DNSSEC exist — they "
            "remove the assumption that the network path in between can be trusted."
        ),
    },
    {
        "doc_id"     : "csci369-w5-arp-defence",
        "course_id"  : "CSCI369",
        "source_file": "CSCI369_Week5_MITM_ARP_Poisoning.pdf",
        "page_number": 3,
        "topic"      : "MITM and ARP Poisoning",
        "week"       : "Week 5",
        "text"       : (
            "Because ARP poisoning exploits the protocol's lack of authentication "
            "rather than a software bug, defences focus on detecting or preventing "
            "unexpected IP-to-MAC changes rather than patching ARP itself. Static "
            "ARP entries pin a critical host's IP-to-MAC mapping so it cannot be "
            "overwritten by a forged reply, but do not scale to large networks. "
            "Dynamic ARP Inspection (DAI), available on many managed switches, "
            "validates ARP packets against a trusted binding table (often built "
            "from DHCP snooping records) and drops ARP traffic that does not match "
            "a known-good binding. Host- and network-based intrusion detection "
            "tools can also watch for a MAC address suddenly claiming an IP address "
            "that was previously associated with a different MAC, which is the "
            "signature most ARP-poisoning detection tools alert on. "
            "From a broader defence-in-depth perspective, using encrypted, "
            "certificate-authenticated protocols (TLS/HTTPS, SSH) means that even a "
            "successful MITM position yields the attacker only encrypted, "
            "unreadable traffic rather than a genuine compromise."
        ),
    },

    # MATH202: Differential Equations. Analysis and Applications
    # Standard, public-domain mathematical content (no textbook text is
    # reproduced verbatim). Chosen as the Math subject,
    # matching UOW's applied-mathematics numbering convention for a
    # second-year subject in the School of Mathematics and Applied Statistics.
    {
        "doc_id"     : "math202-w1-first-order-ode",
        "course_id"  : "MATH202",
        "source_file": "MATH202_Week1_FirstOrderODEs.pdf",
        "page_number": 1,
        "topic"      : "First-Order Differential Equations",
        "week"       : "Week 1",
        "text"       : (
            "A differential equation relates an unknown function to one or more of "
            "its derivatives; the order of the equation is the order of the highest "
            "derivative that appears. A first-order ordinary differential equation "
            "(ODE) has the general form dy/dx = f(x, y). "
            "A separable equation is one that can be rearranged so all the y-terms "
            "sit on one side and all the x-terms on the other, i.e. g(y) dy = h(x) dx, "
            "after which both sides can be integrated independently to reach the "
            "general solution. The general solution contains an arbitrary constant "
            "of integration; a particular solution fixes that constant using an "
            "initial condition, such as a given value y(x0) = y0, which is why a "
            "problem that specifies both a differential equation and an initial "
            "condition is called an initial value problem."
        ),
    },
    {
        "doc_id"     : "math202-w2-linear-integrating-factor",
        "course_id"  : "MATH202",
        "source_file": "MATH202_Week2_LinearFirstOrder.pdf",
        "page_number": 2,
        "topic"      : "First-Order Differential Equations",
        "week"       : "Week 2",
        "text"       : (
            "A first-order linear ODE has the standard form dy/dx + P(x) y = Q(x). "
            "Because it is not generally separable, it is instead solved using an "
            "integrating factor mu(x) = e^(integral of P(x) dx). Multiplying both "
            "sides of the equation by mu(x) makes the left-hand side exactly the "
            "derivative of the product mu(x) y, so the equation reduces to "
            "d/dx [mu(x) y] = mu(x) Q(x), which can be integrated directly to solve "
            "for y. "
            "This method works because the integrating factor is chosen specifically "
            "so that the product rule collapses the left-hand side back into a "
            "single derivative — the same underlying idea used later in the course "
            "for solving systems of linear differential equations."
        ),
    },
    {
        "doc_id"     : "math202-w3-second-order-homogeneous",
        "course_id"  : "MATH202",
        "source_file": "MATH202_Week3_SecondOrderODEs.pdf",
        "page_number": 1,
        "topic"      : "Second-Order Linear Differential Equations",
        "week"       : "Week 3",
        "text"       : (
            "A second-order linear homogeneous ODE with constant coefficients has "
            "the form a y'' + b y' + c y = 0. Substituting a trial solution "
            "y = e^(rx) produces the characteristic (auxiliary) equation "
            "a r^2 + b r + c = 0, whose roots determine the shape of the general "
            "solution. Two distinct real roots r1 and r2 give a general solution "
            "y = C1 e^(r1 x) + C2 e^(r2 x). A single repeated real root r gives "
            "y = (C1 + C2 x) e^(rx), where the extra factor of x is needed because a "
            "repeated root only supplies one independent solution on its own. "
            "A pair of complex conjugate roots alpha +/- i*beta gives an "
            "oscillating solution y = e^(alpha x) [C1 cos(beta x) + C2 sin(beta x)], "
            "which is the mathematical basis for modelling damped or undamped "
            "oscillation in physical systems such as a mass on a spring."
        ),
    },
    {
        "doc_id"     : "math202-w4-modelling-applications",
        "course_id"  : "MATH202",
        "source_file": "MATH202_Week4_Applications.pdf",
        "page_number": 2,
        "topic"      : "Applications of Differential Equations",
        "week"       : "Week 4",
        "text"       : (
            "Differential equations model many real-world processes where a "
            "quantity's rate of change depends on its current state. Exponential "
            "growth or decay follows dy/dt = k y, whose solution y = y0 e^(kt) "
            "describes unconstrained population growth (k > 0) or radioactive decay "
            "(k < 0). Newton's Law of Cooling, dT/dt = -k (T - T_ambient), models "
            "how an object's temperature approaches the surrounding ambient "
            "temperature over time, with solution T(t) = T_ambient + (T0 - "
            "T_ambient) e^(-kt). "
            "A simple RC electrical circuit (a resistor and capacitor in series) is "
            "governed by the first-order linear ODE R (dq/dt) + q/C = V(t), where q "
            "is the charge on the capacitor — the same integrating-factor technique "
            "from Week 2 solves it directly. "
            "These examples illustrate a general modelling pattern in applied "
            "mathematics: translate a physical law about rates of change into a "
            "differential equation, solve it using the appropriate technique for "
            "its order and linearity, then interpret the constants of integration "
            "using the problem's initial or boundary conditions."
        ),
    },
]