# ModernizeAI: Progress Log & Roadmap

This document tracks what has actually been built and verified (as opposed to
what the original demo claimed), and what's next. It supersedes the "Phase 1
Implementation & Optimization Milestone" section of
[`MODERNIZE_AI_GUIDE.md`](MODERNIZE_AI_GUIDE.md) for anything parser- or
ingestion-related — that section describes the original regex-based
prototype; this one describes the real-grammar, multi-source rebuild
currently on branch `feature/multilang-parsers`.

---

## 1. Why this rebuild happened

An initial review of the shipped demo found that its "deterministic 80%"
extraction was regex over a handful of hand-written demo files, not real
parsing, and that its multi-source ingestion (S3, the browser folder picker)
was faked — logging success messages without touching the claimed source. See
the review that started this work for the full list of findings. The rebuild
replaces both, one verified layer at a time.

## 2. What's done

### 2.1 Real parsers (tree-sitter + sqlglot), not regex

| Language | Engine | Handles |
|---|---|---|
| Java | tree-sitter | Nested classes, generics, lambdas, multi-line signatures, inheritance, receiver-typed calls, Spring endpoint annotations, string-concatenated SQL |
| C / C++ | tree-sitter | Namespaces, out-of-line `Class::method` definitions (with field-type propagation so calls inside them still resolve), templates, adjacent-string-literal SQL concatenation, `.h` dispatched to C or C++ by content sniff |
| SQL / PL-SQL | sqlglot + a hand-written procedural-block scanner | `CREATE TABLE`/`INDEX`/`VIEW`/`ALTER TABLE` via sqlglot's real grammar; procedure/function/trigger/package bodies across **Oracle, T-SQL, and Postgres** dialects (sqlglot alone cannot parse a bare Oracle `IS ... BEGIN ... END;` header, so this is a custom depth-aware `BEGIN...END`/`$$...$$` scanner); `SELECT ... INTO var FROM` and `FOR UPDATE` locking correctly handled |

Common infrastructure: one IR (`coded_tools/modernize/parsers/ir.py`) every
parser emits into, a `ParserRegistry` (`registry.py`) that dispatches by
extension, and a `Linker` (`linker.py`) that resolves cross-file references
with a real confidence score (exact-import match 1.0, unique-name match 0.8,
ambiguous 0.5, unresolved → external, never a guess presented as fact).

`java_parser.py` / `ddl_parser.py` are now thin backward-compatible shims
over the real parsers, so every existing tool (`RulesExtractor`,
`KnowledgeGraphTool`, the original test suite) kept working unchanged
throughout.

**Not yet built:** C#, COBOL (+copybooks), JCL.

### 2.2 Multi-source project foundation

The original app could only ever hold one source, and every scan **wiped the
entire graph** before rebuilding it from that one source — S3 and the folder
picker didn't do what they claimed. This is now a real multi-source model:

- **`coded_tools/modernize/sources/`**: a `Project` holds many `Source`s
  (`models.py`, JSON-persisted, credentials referenced only by an env-var
  *name*, never stored). Connectors (`local.py`, `git.py`, `s3.py`) share one
  interface (`base.py`) and are dispatched by `registry.py`. Git supports
  multiple repos, private-repo tokens, and incremental fetch by commit SHA.
  S3 uses real `boto3` (tested against a `moto`-mocked bucket) instead of the
  old fake log lines.
- **`coded_tools/modernize/graph/graph_builder.py`**: turns the linked IR
  into class-level graph nodes/edges. Code entities (classes, programs) are
  source-qualified (`repoA::com.x.Foo`) so two repos' same-named classes
  never collide; shared resources (tables, views, procedures) are
  **canonical** (never qualified), so a table a Java repo reads and the DB
  source that defines it land on the same node — including the case where
  the table is referenced before its defining source is ever scanned (it
  gets a low-confidence placeholder, upgraded in place later, never
  duplicated). Repeated calls between the same two owners collapse into one
  edge with a weight and evidence list instead of one edge per call site.
- **`coded_tools/modernize/graph/store.py`**: `SqliteGraphStore` persists
  each project's graph so it survives a restart. This sits behind a
  `GraphStore` interface; the original plan called for the embedded **Kuzu**
  graph database, but Kuzu currently has no Windows wheel for Python 3.14,
  so SQLite is the default until that's available (or the app runs on
  Linux/WSL), with no caller-visible change when it's swapped in.
- **`coded_tools/modernize/sources/scanner.py`**: `ProjectScanner` ties a
  scan together — fetch → ingest → parse → rebuild only that source's graph
  nodes → persist. Scanning source B never erases source A's contribution.
- **New API** in `apps/modernizeai_ui/server.py`: `/api/projects`,
  `/api/projects/{p}/sources` (add/remove/test), `/api/projects/{p}/scan`,
  `/api/projects/{p}/graph`. The original single-repo demo endpoints
  (`/api/scan`, etc.) are untouched, so the current dashboard still works —
  the new endpoints are not yet wired into the UI (see Next below).

### 2.3 Verification

249 tests currently pass: the original 8 fabric tests (unchanged behavior,
proven via the backward-compatible shims) plus 121 new tests for the parser
layer, connectors, graph builder, store, and full HTTP round-trips through
the new project API (`tests/coded_tools/modernize/`, `tests/apps/`). Run
with `.venv\Scripts\python.exe -m unittest <module> ...` (no pytest in this
project). Notable bugs found and fixed along the way: a `BEGIN` keyword
defeating the first-statement verb check in every SQL procedure body, a
`PACKAGE BODY`'s first member's `END` being misread as the package's own
close (silently dropping every member after it), a Windows-illegal directory
name from a naive path split in the Git connector, and a compound
source-qualified storage key leaking into file-path provenance.

## 3. What's next

1. **UI wiring** (in progress): a "Projects" panel in
   `apps/modernizeai_ui/templates/index.html` / `static/app.js` — project
   create/select, a source list with add/test/scan/remove, "Scan All", and
   the persisted graph rendered via the existing `GraphVisualizer`. The
   Copilot/6R Cockpit/Rules views still read the old global singleton fabric
   populated only by `/api/scan`; making them project-aware is a separate,
   larger piece of work than the UI wiring itself.
2. **Database connector**: Oracle/SQL Server/Postgres/DB2 catalog reads,
   feeding the existing SQL parser directly (no new parsing work needed).
3. **Unix/SSH connector**: shell, Python, and cron parsers, so a scheduled
   job → script → `sqlplus` → procedure chain is traceable.
4. **Wiki/document connector**: Confluence, docx, pdf.
5. **Cross-technology Stitcher**: resolves the edges no single language
   parser can (cron→script, script→SQL client call, doc→code), and a
   `/api/flows` endpoint to walk an end-to-end business flow.
6. **Optional AI-assist layer**: LLM suggestions (doc↔code linking,
   discrepancy triage, flow narration) stored as low-confidence, dashed,
   human-reviewable suggestions — never a graph fact on their own. The
   deterministic fabric works fully with this switched off.
7. **Remaining parsers**: C#, COBOL/copybooks, JCL.

Full design detail for the UI wiring and items 2–6 lives in
[`MODERNIZE_MULTISOURCE_PLAN.md`](MODERNIZE_MULTISOURCE_PLAN.md) — a working
design doc, not a record of finished work.
