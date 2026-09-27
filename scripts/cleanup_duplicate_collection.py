"""Sprint 10, Task 16 — remove the duplicate/orphaned ChromaDB collection (Tung).

STATUS (27 Sept 2026): DONE. The orphaned `csit321_course` collection was
backed up and deleted from the live host on 24 Sept 2026 — see Taylor's
27 Sept review of PR #134, point 5. This script is kept only as a reference
for how it was done and as a `--list`/`--verify` health check for the
future; there is nothing left to delete, and `--dry-run`/`--confirm-delete`
against `csit321_course` will now just report it doesn't exist (see
`dry_run`/`confirm_delete` below — that is the expected, harmless outcome,
not an error).

Per src/document_processor/ingest_corpus.py's own T8-13 comment, the live
collection was renamed csit321_course -> edurag_course (COLLECTION constant)
in Sprint 8, when the corpus grew to hold four subjects. Nothing in the
codebase references "csit321_course" any more -- confirmed with:

    grep -rn "csit321_course" src/ apps/ scripts/

-- so it was dead weight left over from the rename, duplicating content that
already existed under edurag_course.

This script only READS and (with --confirm-delete) deletes; it takes no
opinion on which collection is "current" beyond ingest_corpus.COLLECTION, so
if that constant ever changes, this script's target renames with it instead
of drifting out of sync.

Usage that was actually run on 24 Sept (kept for the record — do not repeat
step 4, there is nothing left to delete):

    # 1. Backup the ChromaDB volume FIRST. Done before anything else on 24/9.
    docker compose exec chromadb sh -c "tar -C /data -czf /tmp/chromadb_backup_$(date +%Y%m%d_%H%M).tar.gz ."
    docker cp <chromadb_container>:/tmp/chromadb_backup_<timestamp>.tar.gz ./chromadb_backup_<timestamp>.tar.gz

    # 2. List collections and counts (read-only, still safe to run any time).
    python scripts/cleanup_duplicate_collection.py --list

    # 3. Dry run against the specific orphaned collection (still read-only).
    python scripts/cleanup_duplicate_collection.py --target csit321_course --dry-run

    # 4. Already done on 24/9 -- do not re-run against a live host expecting
    #    a fresh collection to delete; it will correctly report there is
    #    nothing there.
    python scripts/cleanup_duplicate_collection.py --target csit321_course --confirm-delete

    # 5. Verify through the query path (a different component from the one
    #    that deleted it), per the sprint plan's done-when condition -- still
    #    useful to re-run any time as a health check:
    python scripts/cleanup_duplicate_collection.py --verify
"""
from __future__ import annotations

import argparse
import sys

from src.document_processor.ingest_corpus import COLLECTION, get_chroma_client


def list_collections(client) -> list:
    collections = client.list_collections()
    print(f"{'Collection':30s} {'Count':>10s}  Metadata")
    print("-" * 70)
    rows = []
    for c in collections:
        # chromadb>=0.5 returns Collection objects; older clients return names.
        name = getattr(c, "name", c)
        coll = client.get_collection(name)
        count = coll.count()
        meta = dict(coll.metadata or {})
        marker = "  <- COLLECTION constant (keep)" if name == COLLECTION else ""
        print(f"{name:30s} {count:>10d}  {meta}{marker}")
        rows.append((name, count, meta))
    return rows


def dry_run(client, target: str) -> None:
    if target == COLLECTION:
        print(f"REFUSING: '{target}' is the active collection "
              f"(ingest_corpus.COLLECTION). This script only removes an "
              f"orphaned collection, never the live one.")
        sys.exit(1)
    try:
        coll = client.get_collection(target)
    except Exception as exc:
        print(f"'{target}' does not exist on this ChromaDB instance ({exc}). "
              f"Nothing to do -- run --list first to see what's actually there. "
              f"If this is csit321_course, that's expected: it was already "
              f"deleted on 24 Sept 2026.")
        sys.exit(1)
    count = coll.count()
    sample = coll.peek(limit=3)
    print(f"Would delete collection '{target}' — {count} chunks.")
    print("Sample of what would be removed (first up to 3 chunks):")
    for i, doc_id in enumerate(sample.get("ids", [])):
        meta = (sample.get("metadatas") or [{}] * len(sample["ids"]))[i]
        text = (sample.get("documents") or [""] * len(sample["ids"]))[i]
        print(f"  [{doc_id}] course_id={meta.get('course_id')} "
              f"source={meta.get('source_file')}  text[:80]={text[:80]!r}")
    print("\nRe-run with --confirm-delete once the volume backup exists.")


def confirm_delete(client, target: str) -> None:
    if target == COLLECTION:
        print(f"REFUSING: '{target}' is the active collection. Not deleting it.")
        sys.exit(1)
    try:
        coll = client.get_collection(target)
    except Exception as exc:
        print(f"'{target}' does not exist ({exc}). Nothing to delete. "
              f"If this is csit321_course, that's expected: it was already "
              f"deleted on 24 Sept 2026 -- see the module docstring.")
        sys.exit(1)
    count = coll.count()
    answer = input(
        f"About to permanently delete '{target}' ({count} chunks). "
        f"Have you already taken a volume backup (step 1)? [yes/N]: "
    ).strip().lower()
    if answer != "yes":
        print("Aborted. Take the backup first.")
        sys.exit(1)
    client.delete_collection(target)
    print(f"Deleted '{target}'. Run --list to confirm, then --verify to check "
          f"the query path is still healthy.")


def verify(client) -> None:
    """The sprint plan's done-when: 'a question still returns a properly
    grounded answer', checked through a different component from the one
    that made the change — i.e. the actual retrieval path, not just a count.
    Safe and useful to re-run any time as an ongoing health check.
    """
    from src.document_processor.rag_pipeline import VectorRetriever
    retriever = VectorRetriever()
    question = "What is retrieval-augmented generation?"
    results = retriever.search(question, course_id="CSIT321", top_k=3)
    if not results:
        print("FAIL: retrieval returned zero results after cleanup. "
              "Do not consider this task done -- restore from backup and "
              "investigate before touching the collection again.")
        sys.exit(1)
    print(f"OK: retrieval for {question!r} still returns {len(results)} "
          f"grounded chunk(s) from '{COLLECTION}':")
    for r in results[:3]:
        print(f"  - {r.source_file} (p.{r.page_number}) "
              f"distance={r.distance:.4f} similarity={r.similarity:.4f}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--list", action="store_true", help="List all collections and chunk counts.")
    parser.add_argument("--target", help="Name of the collection to inspect/delete, e.g. csit321_course")
    parser.add_argument("--dry-run", action="store_true", help="Show what --target would remove, without deleting.")
    parser.add_argument("--confirm-delete", action="store_true", help="Actually delete --target, after an interactive confirmation.")
    parser.add_argument("--verify", action="store_true", help="Run a real query against the live collection to confirm it's still healthy.")
    args = parser.parse_args()

    client = get_chroma_client()

    if args.list:
        list_collections(client)
    elif args.target and args.dry_run:
        dry_run(client, args.target)
    elif args.target and args.confirm_delete:
        confirm_delete(client, args.target)
    elif args.verify:
        verify(client)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()