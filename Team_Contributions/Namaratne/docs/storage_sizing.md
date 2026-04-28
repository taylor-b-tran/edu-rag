# Data Store Sizing Estimate

Owner: Kahavidanage Namaratne  
Sprint: Sprint 3  
Status: Ready for consolidated report inclusion

## Scenario

The estimate uses the Sprint 3 planning scenario:

- 10 courses
- 50 documents per course
- 500 pages per document

## Corpus Size

| Item | Calculation | Result |
|---|---:|---:|
| Documents | 10 courses x 50 documents | 500 documents |
| Pages | 500 documents x 500 pages | 250,000 pages |
| Average chunks per page | Assumption | 3 chunks |
| Total chunks | 250,000 pages x 3 chunks | 750,000 chunks |

## ChromaDB Estimate

EduRAG uses `all-MiniLM-L6-v2`, which produces 384-dimensional embeddings.

| Item | Calculation | Estimate |
|---|---:|---:|
| Raw embedding per chunk | 384 floats x 4 bytes | 1,536 bytes, about 1.5 KB |
| Raw embeddings | 750,000 chunks x 1.5 KB | About 1.1 GB |
| Metadata and index overhead | Raw embedding size x 2.5 | About 2.75 GB |

Estimated ChromaDB storage: **2.5 GB to 3 GB**.

## PostgreSQL Estimate

PostgreSQL stores metadata and application state rather than full embedding vectors.

| Data Type | Estimate |
|---|---:|
| Course and document metadata | 50 MB to 100 MB |
| Chunk metadata references | 200 MB to 400 MB |
| Sessions and messages | 100 MB to 300 MB |
| Audit logs and indexing jobs | 100 MB to 300 MB |
| Indexes and overhead | 300 MB to 500 MB |

Estimated PostgreSQL storage: **1 GB to 2 GB**.

## Raw Document Storage Estimate

Assume each uploaded document averages 10 MB.

| Item | Calculation | Estimate |
|---|---:|---:|
| Raw documents | 500 documents x 10 MB | 5 GB |

Estimated raw document storage: **about 5 GB**.

## Total Estimate

| Store | Estimated Size |
|---|---:|
| ChromaDB | 2.5 GB to 3 GB |
| PostgreSQL | 1 GB to 2 GB |
| Raw documents | About 5 GB |
| Total | 8.5 GB to 10 GB |

## Conclusion

For a realistic prototype corpus of 10 courses, 50 documents per course, and 500 pages per document, EduRAG should require approximately **8.5 GB to 10 GB** of local storage. This is manageable for a Docker-based prototype. Most storage is consumed by raw uploaded files and ChromaDB embeddings, while PostgreSQL mainly stores metadata, indexing jobs, sessions, and audit logs.
