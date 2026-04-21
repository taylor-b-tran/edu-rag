# EduRAG Git Branch Workflow (Official)

## 1) Branches to use

- `main`: production/release branch
- `develop`: team integration branch
- each member works on short-lived branches from `develop`

**Function:** keep repo stable and easy to manage.  
**Technique used:** two long-lived branches + task branches.

---

## 2) Branch naming syntax

Format:

`<type>/s<sprint>-<task>`

Allowed `type`:

- `feature`, `fix`, `docs`, `test`, `chore`

Examples:

- `feature/s3-chunker`
- `feature/s3-ui-prototype`
- `fix/s3-empty-query`
- `docs/s3-api-spec`
- `test/s3-retrieval-cases`

---

## 3) Daily Git steps (for every member)

```bash
# Function: sync latest integration code before starting work.
# Technique used: always branch from updated develop.
git checkout develop
git pull origin develop

# Function: create branch for one task.
# Technique used: sprint-based branch naming.
git checkout -b feature/s3-your-task

# Function: save and publish your task branch.
# Technique used: commit + upstream push.
git add .
git commit -m "feat(rag): implement your task"
git push -u origin feature/s3-your-task
```

Then create PR:

- base branch: `develop`
- compare branch: your task branch

After PR merged:

```bash
# Function: clean merged branch.
# Technique used: local + remote branch deletion.
git checkout develop
git pull origin develop
git branch -d feature/s3-your-task
git push origin --delete feature/s3-your-task
```

---

## 4) Merge direction (important)

- normal work: `task branch` -> `develop`
- sprint release: `develop` -> `main`
- never merge directly `task branch` -> `main`
- never push directly to `main` or `develop`

---

## 5) Sprint 3 branch plan (create now)

Create these starter branches from `develop`:

- Binh: `feature/s3-rag-pipeline`
- Ngoc: `feature/s3-doc-processor`
- Anmoldeep: `feature/s3-streamlit-ui`
- Namaratne: `feature/s3-db-schema`
- Tai: `docs/s3-core-docs`
- Tung: `test/s3-test-assets`

Leader can pre-create remote branches:

```bash
# Function: create Sprint 3 starter branches for all members.
# Technique used: create local branches from develop and push upstream.
git checkout develop
git pull origin develop

git checkout -b feature/s3-rag-pipeline && git push -u origin feature/s3-rag-pipeline && git checkout develop
git checkout -b feature/s3-doc-processor && git push -u origin feature/s3-doc-processor && git checkout develop
git checkout -b feature/s3-streamlit-ui && git push -u origin feature/s3-streamlit-ui && git checkout develop
git checkout -b feature/s3-db-schema && git push -u origin feature/s3-db-schema && git checkout develop
git checkout -b docs/s3-core-docs && git push -u origin docs/s3-core-docs && git checkout develop
git checkout -b test/s3-test-assets && git push -u origin test/s3-test-assets && git checkout develop
```

Members then pull and continue with sub-task branches if needed (example: `feature/s3-doc-processor-chunker`).

---

## 6) Sprint-end release steps

```bash
# Function: release integrated sprint work.
# Technique used: PR merge develop->main and annotated version tag.
# PR on GitHub: base=main, compare=develop

git checkout main
git pull origin main
git tag -a v0.3 -m "Sprint 3 release"
git push origin v0.3
```
