# EduRAG Privacy Policy - Sprint 3 Draft

## 1. Purpose And Scope

This document records the Sprint 3 privacy position for EduRAG, a student-facing course assistant that answers natural-language questions using Retrieval-Augmented Generation (RAG) over lecturer-provided course materials. The policy is written for the current prototype scope and should be read as a project design baseline rather than a final production privacy notice.

In the Sprint 3 design, students ask questions about enrolled courses, while lecturers and admins manage course materials and system oversight functions. Student-side document upload is out of scope for this prototype.

## 2. Data Collected

The Sprint 3 design intends to collect only the data needed to authenticate users, scope retrieval to the correct course, support document management, and preserve basic accountability.

### Account Data

- username
- email
- role
- hashed password
- last login timestamp

### Course Material Metadata

- document name
- course identifier
- uploader identity
- upload timestamp
- file type
- file size
- processing status

### Course Material Content

- lecturer-uploaded course files
- extracted text chunks used for retrieval
- chunk metadata such as page number, chunk order, and course scope

### Conversation Data

- user question
- generated answer
- cited sources
- session identifier
- timestamps linked to the conversation flow

### Audit And Security Data

- login events
- upload events
- query events
- delete events
- indexing events
- administrative review events where implemented

## 3. Data Not Collected

The Sprint 3 prototype should avoid collecting unnecessary categories of personal data. In particular, the intended scope does not include:

- advertising or marketing profile data
- payment data
- government identity data
- unrelated personal demographic profiling
- student-side document uploads as a normal workflow

The project also does not intend to use user data to train external foundation models.

## 4. How Data Is Used

The collected data is used only for core system functions:

- authenticating users and enforcing role-based access control
- retrieving answers from course-scoped materials
- maintaining conversation continuity during a study session
- allowing lecturers or admins to upload, index, and manage course documents
- supporting monitoring, debugging, and audit review for prototype reliability and security

Where the prototype uses an LLM to generate answers, the intended design is to use retrieved course context first and to label fallback responses when no sufficiently relevant course chunks are found. User data is not intended for advertising, profiling, or external model training.

## 5. Storage And Retention

Retention should be defined by data category rather than with a single blanket period.

| Data category | Example contents | Intended retention approach |
|---|---|---|
| Account data | username, email, role, hashed password, last login | Kept while the account is active for the prototype and deleted or archived when the account is removed or the project is retired. |
| Course material metadata | filename, course id, uploader, status | Kept while the linked course material remains available in the system and removed when the document is deleted or the prototype data set is retired. |
| Course material content | uploaded files, extracted text chunks, vector metadata | Kept only as long as needed to support course retrieval and deleted when the source document is removed or the knowledge base is reset. |
| Conversation data | question, answer, sources, session id | Kept for prototype session history and evaluation, then reviewed for deletion or anonymisation after the academic project period. |
| Audit and security data | login, upload, query, delete, indexing events | Kept longer than ordinary session data where needed for accountability, troubleshooting, and security review, then removed when no longer necessary for the prototype. |

Exact retention periods should be finalised in Sprint 4 after supervisor guidance on acceptable prototype data handling.

## 6. Access Control And User Rights

The implemented prototype should enforce access by role rather than by broad developer access.

- Students should only access their own authorised course interactions and study views.
- Lecturers should manage course documents only for courses they are authorised to maintain.
- Admins should access monitoring and audit functions needed for oversight and system maintenance.

Expected user rights for the prototype include:

- the ability to understand what categories of data are held
- the ability to request deletion of removable account or session data where feasible in the project setting
- the ability to stop using the system at any time

Because this is a university project prototype, formal operational processes may still be incomplete, but the design intent is to align with role separation and minimal data exposure.

## 7. Security Controls

Sprint 3 evidence shows that the system design intends to apply several baseline controls:

- password hashing for stored credentials
- JWT-based authentication for protected endpoints
- role-based access control across Student, Lecturer, and Admin roles
- course-scoped retrieval using `course_id` metadata to reduce cross-course leakage
- audit logging for important system events
- secrets management as a project requirement rather than hard-coded credentials
- safe fallback labelling when answers are not grounded in course material

Some controls are design targets rather than fully production-hardened implementations. Where a control is still incomplete, it should be treated as a Sprint 4 handoff item instead of being presented as fully deployed.

## 8. GDPR-Awareness And Privacy Principles

Although EduRAG is a student project prototype, the privacy approach is intended to follow common privacy principles that are consistent with GDPR-style thinking:

- data minimisation: collect only what is needed for authentication, retrieval, and accountability
- transparency: describe what data categories are collected and why
- purpose limitation: use the data for study support and prototype operations only
- storage limitation: avoid retaining data longer than necessary
- access control: restrict data access according to role and authorised scope

## 9. Requirement Mapping

| Requirement | Privacy relevance | Sprint 3 alignment |
|---|---|---|
| `NFR-018 Minimal Data Collection` | Limits collection to information needed for system operation. | Reflected in the scoped data categories and explicit exclusion of unnecessary personal data. |
| `NFR-019 Access Control by Role` | Requires data access to be constrained by role. | Reflected in Student, Lecturer, and Admin separation and course-scoped access expectations. |
| `FR-017 Secrets Management` | Protects credentials and environment secrets from unsafe exposure. | Treated as a required security control for the prototype environment. |
| `FR-018 Password Hashing` | Prevents plaintext password storage. | Reflected in the use of hashed passwords in the account data model. |
| `NFR-016 Audit Logging` | Preserves accountability for sensitive operations. | Reflected in the intended logging of login, upload, query, delete, and indexing events. |

## 10. Open Implementation Items

- Confirm exact retention periods with supervisor guidance for a student prototype.
- Finalise deletion and anonymisation workflows for conversation history.
- Verify that all protected routes consistently apply role checks and audit logging.
- Confirm how uploaded course materials are stored and removed across PostgreSQL, file storage, and vector storage.
- Review whether any external model fallback path introduces extra privacy obligations before Sprint 4.
