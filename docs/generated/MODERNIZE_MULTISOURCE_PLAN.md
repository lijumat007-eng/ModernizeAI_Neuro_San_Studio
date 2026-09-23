# Plan: ModernizeAI UI — Multi-Source Projects panel (Phase 1 finish)

> **This is a working design doc, not a record of finished work.** The UI
> plan below (Section 1) is proposed, not yet implemented. The archived plan
> further down covers Phases 2–6 (databases, SSH/shell, wiki/docs, the
> cross-technology Stitcher, and the optional AI layer) — none of those are
> built yet either. For what's actually done and verified, see
> [`MODERNIZE_PROGRESS_AND_ROADMAP.md`](MODERNIZE_PROGRESS_AND_ROADMAP.md).

## Context
Phase 1 of the multi-source fabric plan (see the archived plan below this line) is done on the backend: `coded_tools/modernize/sources/` (Project/Source model, local/git/S3 connectors, `ProjectScanner`), `graph/graph_builder.py` and `graph/store.py`, and 11 new `/api/projects/*` endpoints in `apps/modernizeai_ui/server.py` — all committed (`c052119`) and covered by 121 passing tests, including full HTTP round-trips. None of it is reachable from the browser yet: `templates/index.html` and `static/app.js` only know the old single-repo `/api/scan` flow (one source, POSTs to `/api/scan`, wipes the graph every time) and render `artifacts/modernize_graph.html`, a static file the old flow writes — never the new per-project graph sitting in `projects/<name>/graph.sqlite3`. This plan wires the UI to the new backend so a user can actually create a project, attach several sources, scan them without losing earlier ones, and see the combined graph.

## Scope for this pass
**In scope:** a new "Projects" nav view — project create/select, a source list (add Local/Git/S3, test connection, scan one, remove), "Scan All", and rendering that project's persisted graph with a working node inspector.
**Explicitly out of scope, called out to the user rather than silently attempted:** the Copilot, 6R Cockpit, and Rules & Risks views still read from the old global singleton fabric (`get_knowledge_graph()`/`get_memory_fabric()`, populated only by `/api/scan`), which is a separate, larger rework — making those project-aware needs the swarm coordinator and scoring/rules tools to accept a `project_name` and load from `graph_store`, not just a UI change. The old "Ingestion Hub" view and `/api/scan` are left untouched so today's demo keeps working.
**Known limitation to state in the UI, not hide:** `SqliteGraphStore` persists nodes/edges only, not raw file content, so a node's source-code snippet is only available in the same session it was scanned (before a server restart). The inspector will show "Rescan to view snippet" rather than a blank/broken panel when it's missing.

## Design

### Backend additions (small, reusing existing code)
- `GET /api/projects/{name}/graph/html` — loads the project's graph via `graph_store`, calls the **existing** `GraphVisualizer.render_html(kg.graph, output_path=...)` (`coded_tools/modernize/graph/visualizer.py`, already used by the old flow) to `artifacts/projects/<name>/graph.html`, and returns that path. The `/artifacts` mount already serves this directory tree, so the iframe just points at the returned URL.
- `GET /api/projects/{name}/node_details/{node_id}` — same shape as the existing `/api/node_details/{node_id}` (`server.py`), but reads from `graph_store.load(name)` instead of the global singleton. Snippet lookup is best-effort: if the project's `MemoryFabric` isn't held in memory (i.e. a restart happened since the last scan), `snippet` comes back `None` and the UI shows the "rescan to view" message instead of erroring.
- `coded_tools/modernize/graph/visualizer.py`: extend `COLOR_PALETTE` with the new node types `graph_builder.py` introduces (`Class`, `Interface`, `View`, `Trigger`, `Program`, `Copybook`, `BatchJob`, `External`) so they render distinctly instead of one fallback color.

### Frontend: new "Projects" view
- `templates/index.html`: new sidebar nav item `view-projects` ("🗂️ Multi-Source Projects"), placed above "Ingestion Hub". Its section has:
  - A project bar: `<select>` populated from `GET /api/projects`, a "+ New Project" button (`POST /api/projects`), a "Delete Project" button.
  - A source list panel: cards from `GET /api/projects/{name}` → `sources[]`, each showing type badge, a one-line config summary, last scan status/time (`last_scan_status`, `last_scanned_at`, `last_scan_message`), and **Test** / **Scan** / **Remove** buttons per card.
  - An "Add Source" form reusing the existing Local/Git/S3 tab markup pattern already in the Ingestion Hub view (`source-tabs` / `source-form-panel` in `index.html`) — same three tabs, submitting to `POST /api/projects/{name}/sources` (and, per a "scan immediately" checkbox, chaining a scan call).
  - A "Scan All" button → `POST /api/projects/{name}/scan`, and the existing terminal-log box pattern (`appendTerminal`, already in `app.js`) reused to print one line per source's result.
  - A graph panel reusing the existing `canvas-panel`/iframe pattern, pointed at `/api/projects/{name}/graph/html` after each scan, with the existing node-inspector drawer wired to the new `/api/projects/{name}/node_details/{id}` endpoint instead of the global one when this view is active.
- `static/app.js`: new `initProjectsPanel()` function (called from the `DOMContentLoaded` listener alongside the existing `init*` calls), following the same structure as `initSourceWizard()`/`executeIngestion()` already there — no new libraries, same fetch/DOM patterns as the rest of the file.
- `static/style.css`: reuse existing classes (`glass-panel`, `btn`, `source-tabs`, `form-control`, `terminal-box`, `canvas-panel`) wherever the markup matches; only add new rules for the source-card list and status badges, which have no existing equivalent.

## Files touched
- `apps/modernizeai_ui/server.py` (2 new endpoints)
- `coded_tools/modernize/graph/visualizer.py` (palette extension only)
- `apps/modernizeai_ui/templates/index.html` (new nav item + view section)
- `apps/modernizeai_ui/static/app.js` (new `initProjectsPanel()` + helpers)
- `apps/modernizeai_ui/static/style.css` (a handful of new rules for source cards/status badges)

## Verification
- Existing suite stays green: `.venv\Scripts\python.exe -m unittest` over the parser/sources/graph/fabric test modules (129 tests currently).
- New backend tests in `tests/apps/modernizeai_ui/test_project_api.py`: add cases for `/graph/html` (asserts the returned file exists and contains the scanned nodes) and `/node_details` (found node, not-found node, and the no-fabric-in-memory snippet fallback).
- Manual/browser pass using the `run` skill or `preview_start`: start `apps/modernizeai_ui/server.py`, open the Projects view, create a project, add two local folder sources pointing at two different subsets of `data/insurance_claims_app` (simulating two repos), scan each, confirm the combined graph shows nodes from both without either disappearing, click a node to confirm the inspector opens, and confirm "Scan All" on an unchanged project reports "unchanged" for both sources.

---
# (Archived) Plan: Multi-source, end-to-end Workflow Knowledge Fabric

## Context
Real legacy estates are spread across many sources: several Git repos, live databases (Oracle, SQL Server, Postgres, DB2), Unix servers holding shell/Python scripts and crontabs, wiki pages and workflow documents. The goal is one fabric that joins all of these, so a user can follow a business flow end to end. For example: a cron entry starts a shell script, which runs `sqlplus`, which calls `SP_PROCESS_CLAIM`, which updates `POLICY_MASTER`, which `ClaimService.java` in another repo also reads, and which the wiki page "Claims Settlement" describes.

### Analysis: can the current system do this? No.
Checked in `apps/modernizeai_ui/server.py`, `static/app.js` and `memory/raw_memory.py`:

| Need | Current state |
|---|---|
| More than one source per project | `ScanRequest` accepts exactly one source, and every scan **wipes memory and the graph** (server.py:172-176). A second repo replaces the first instead of adding to it. |
| Local folder | The browser folder picker only builds the string `data/<folderName>` (app.js:108). It uploads nothing, so it only works for folders already under `data/`. |
| S3 | **Fake.** It logs "Verifying IAM credentials… Sync verified" and creates an empty folder (server.py:160-165), then scans the default demo repo. |
| Private Git | No token support. Shallow clone of a public URL only. |
| Live DB / SSH / Confluence / docx / pdf | No connectors exist. |
| Shell, Python, cron | Not ingested (`raw_memory` extension list) and not parsed. |
| Identity across sources | Node IDs are bare names such as `ClaimService` and `POLICY_MASTER`, so two repos with a `Utils` class collide. Nothing records which source a file came from. |
| Links across technologies | None. Nothing connects a shell `sqlplus @x.sql` to a procedure, cron to a script, a doc to the code it describes, or a REST client call to an endpoint in another repo. |
| Persistence | Global in-memory singletons. Everything is lost on restart, there is no incremental re-scan, and only one project exists at a time. |

The new parser layer (Java, C/C++, SQL, all behind one IR + Linker) is the right foundation. What's missing is **ingestion from many sources**, **source-qualified identity**, **cross-technology linking** and **persistence**.

## Design

```
Project ─┬─ Source[git]  ─┐
         ├─ Source[db]   ─┤  SourceConnector.fetch()  →  SourceDocument(source_id, path, content, kind, meta)
         ├─ Source[ssh]  ─┤                                    │
         ├─ Source[wiki] ─┤                         ParserRegistry (Java/C/C++/SQL + shell/python/cron/docs)
         └─ Source[docs] ─┘                                    │  IR (source-qualified)
                                          Linker (in-language) + Stitcher (cross-technology)
                                                               │
                                     Kuzu embedded graph store  ⇄  NetworkX view for algorithms
                                                               │
                                     Flow API (trigger → … → table) + UI Flow Explorer
```

### 1. Project & Source model (`coded_tools/modernize/sources/`)
- `models.py`: `Project(name, sources[])` and `Source(source_id, type, config, credential_ref, last_fingerprint)`. Saved to `projects/<name>/project.json`, which never contains secrets.
- `base.py`: `SourceConnector` ABC with `test_connection()` and `fetch(since_fingerprint) -> Iterable[SourceDocument]`. It also returns the new fingerprint (commit SHA, DB `LAST_DDL_TIME`, file mtimes/sha256) so re-scans are incremental.
- Credentials (your choice): `credential_ref` is an env-var **name**, e.g. `ORACLE_PROD` resolves to `ORACLE_PROD_USER` and `ORACLE_PROD_PASSWORD` from the environment or `.env` (`python-dotenv` is already a dependency). The UI never receives a secret. Secrets are redacted from logs.

### 2. Connectors (one file each, same interface)
| Connector | How | Output |
|---|---|---|
| `local.py` | Server-side path plus include/exclude globs. Replaces the fake browser picker. | Files |
| `git.py` | Many repos per project, branch/tag, token via `credential_ref` (GitHub/GitLab/Bitbucket/Azure DevOps), incremental by commit SHA | Files |
| `s3.py` | Real `boto3` sync (botocore is already a dependency), replacing the fake flow | Files |
| `database.py` | SQLAlchemy plus `oracledb`/`pyodbc`/`psycopg`/`ibm_db`. Reads the catalog read-only (Oracle `ALL_TABLES/ALL_CONSTRAINTS/ALL_SOURCE`, SQL Server `sys.sql_modules`, Postgres `pg_proc/information_schema`, DB2 `SYSCAT`), regenerates DDL and procedure source as text, and feeds it into the **existing SQL parser**. Virtual path is `db://<source_id>/<schema>/<object>.sql`. | SQL text |
| `ssh.py` | `paramiko` SFTP with path globs, strict host-key checking, and `crontab -l` / `/etc/cron.d` capture | Scripts, crontab |
| `confluence.py` | REST API over a space or page tree, storage format converted to Markdown, keeping the page URL for provenance | Markdown |
| `documents.py` | `.docx` (python-docx), `.pdf` (pypdf, already a dependency), `.md`/`.txt`, from any connector | Text with headings |

### 3. Source-qualified identity
- `RawMemory` records are keyed by `<source_id>/<path>` and store `source_id`, `source_type` and `uri`. Provenance becomes `source_id + path + lines`, which the UI shows as a clickable Git URL, DB object or Confluence link.
- Code symbol IDs become `<source_id>::<qualified_name>`, so identical class names no longer collide.
- **Shared-resource entities are canonical, not per-source.** Tables, procedures, endpoints, queues and files use a canonical key such as `table:<db_alias>.<SCHEMA>.<NAME>`. A `db_alias` mapping in the project config (for example repo JDBC `jdbc:oracle:…/CLAIMS` → source `ORACLE_PROD`) lets Java SQL in repo A land on the same `POLICY_MASTER` node that the live DB connection created. Unmapped references stay separate with confidence 0.5 until they're mapped.

### 4. New parsers (plug into the existing `ParserRegistry` / IR)
- `lang/shell.py` (tree-sitter `bash`): functions, sourced scripts, invoked programs (`java -cp … Main`, `python x.py`, `./x.sh`), SQL clients (`sqlplus @f.sql`, `sqlplus … <<EOF … EOF` heredocs, `psql -f`, `sqlcmd -i`, `bcp`, `db2 -tvf`), file reads and writes (`>`, `cp`, `mv`, `ftp/sftp put`).
- `lang/python.py` (tree-sitter `python`): modules, classes, functions, imports, DB-API/SQLAlchemy SQL strings via the existing `embedded_sql`, `subprocess` calls, `requests` URLs.
- `lang/cron.py`: schedule plus command. Produces `SCHEDULES` edges to the script.
- `lang/docs.py`: replaces `doc_parser.py`. Splits into sections by heading and produces `MENTIONS` references for every token matching a known symbol or table name (exact match 0.9, fuzzy 0.6), resolved after linking.

### 5. Cross-technology Stitcher (`coded_tools/modernize/fabric/stitcher.py`)
It runs after the per-language Linker over all sources and resolves the unresolved/external references into cross-source edges, each with evidence and confidence:
- cron → script (`SCHEDULES`); script → script/program/Java main class/Python module (`EXECUTES`)
- script → `.sql` file / procedure (`EXECUTES`, via sqlplus/psql/sqlcmd arguments or heredoc SQL)
- code/procedure → canonical table (`READS_FROM`/`WRITES_TO`, via the `db_alias` mapping)
- HTTP client URL → `APIEndpoint` in another repo (route template match) (`CALLS`)
- job A writes file F and job B reads F (`DATA_FLOW`)
- doc section → symbol (`DOCUMENTS`)
- JCL `EXEC PGM=` → COBOL program, once the COBOL/JCL parsers land.

### 6. Storage: Kuzu embedded graph DB (`graph/store.py`)
- Nodes and edges are persisted under `projects/<name>/graph.kuzu`, so they survive restarts and several projects can coexist.
- Incremental re-scan: for changed documents only, delete the nodes and edges they own (tracked via `origin_doc`) and re-insert them. Then re-run the Stitcher.
- The existing algorithms (blast radius, Louvain, PageRank) keep running on a NetworkX view loaded from the store (whole graph or subgraph), so `graph/algorithms.py` is reused unchanged.
- Prerequisite from the earlier plan: `graph/graph_builder.py` (IR → graph) must replace the per-language code in `knowledge_graph_tool.build_graph`. The graph builder writes to the store.

### 7. Flow traversal ("follow the business logic")
- `GET /api/flows?entry=<node>`: ordered paths from entry points (cron entries, JCL jobs, REST endpoints, UI screens) through scripts, programs and procedures to tables. Each hop carries its edge type, evidence snippet, source link and confidence.
- `GET /api/flows/through?node=POLICY_MASTER`: every end-to-end flow that touches a node (the reverse question).
- The UI **Flow Explorer** shows a swimlane per technology (Scheduler | Shell | App | DB | Docs). Clicking a hop opens the existing node inspector with its code snippet.

### 8. API & UI changes
- `server.py`: add `/api/projects` (CRUD), `/api/projects/{p}/sources` (CRUD plus `POST …/test`), `POST /api/projects/{p}/scan` (all sources or changed only, runs in the background with per-source progress), and `/api/flows`. Remove the global wipe. Remove the fake S3 and fake folder-picker paths.
- `index.html` / `app.js`: a project selector, a **Sources** panel (add Git/DB/SSH/Confluence/Folder/S3 with type-specific forms, `credential_ref` name field, test-connection button, status and last scan per source), a "Scan all / Rescan changed" action, and the Flow Explorer tab.

## Where AI (LLM) is used, and where it is not
Rule: **deterministic code extracts the facts; the LLM only interprets them, suggests links, and explains them.** Nothing the LLM says becomes a graph fact unless deterministic code can check it against the source text.

| Step | Approach | Why |
|---|---|---|
| Connectors, parsing, IR, in-language Linker, DB catalog reads | **Deterministic only** | These are facts with exact file:line or DB-object provenance, and they are reproducible. An LLM here would add hallucination risk and cost. |
| Stitcher rules (cron→script, sqlplus→proc, code→table, URL→endpoint, file data-flow) | **Deterministic only** | Pattern and name matching with evidence. |
| Doc/wiki → code linking | Deterministic exact/fuzzy name match first. **LLM second pass** only for sections with no match (e.g. "the nightly settlement job" → `settle_claims.sh`) | Prose rarely uses exact identifiers. |
| Unresolved references (dynamic SQL, `EXECUTE IMMEDIATE v_sql`, reflection, table names built at runtime) | **LLM suggests** a likely target from the surrounding code | Static analysis cannot know these values. |
| Business-rule naming/summaries, flow narration ("what does this job do, step by step") | **LLM** over the deterministic subgraph and snippets, with every sentence citing node IDs | Turns a graph into language a business user can read. |
| Doc vs code vs SME discrepancies (replaces the hardcoded DISC-01) | Deterministic extraction of numbers and constraints per entity. **LLM decides** whether two statements actually conflict | Deciding whether two statements conflict is a meaning problem. |
| Q&A copilot and 6R recommendations | **LLM** (Graph-RAG over the store, the existing Neuro SAN agents) | Reasoning and explanation. |

Guardrails for every LLM output:
- It is stored as a **suggested** edge or annotation with `extractor="llm"`, the model name, the prompt hash, and confidence capped at 0.6. It is drawn dashed in the UI.
- It must cite source spans that exist in Raw Memory. `ProvenanceValidator.verify_provenance` rejects anything uncited or out-of-range.
- It is never used as an input to blast radius or scoring unless a user accepts it in a **review queue**. An accepted suggestion becomes `extractor="human_verified"`.
- It is optional per project (on/off switch). The deterministic fabric works fully with the LLM disabled.
- It uses the model already configured in `registries/generated/modernizeai.hocon` (Gemini, with Ollama qwen2.5 as a local option for air-gapped clients).

## Phases (each ends with tests green and a commit)
1. **Foundation:** Project/Source model, connector ABC, local and multi-Git connectors, real S3, source-qualified RawMemory, GraphBuilder, Kuzu store, multi-source scan without wiping, Sources panel.
2. **Databases:** `database.py` for Oracle, SQL Server, Postgres and DB2, catalog → existing SQL parser, `db_alias` mapping, canonical table entities.
3. **Unix servers:** `ssh.py`, `shell.py`, `python.py`, `cron.py`.
4. **Wiki & documents:** `confluence.py`, `documents.py`, `docs.py` with `MENTIONS`/`DOCUMENTS` linking.
5. **Stitcher + flows:** cross-technology edges, `/api/flows`, the Flow Explorer UI.
6. **AI assist layer:** LLM suggestions for doc links, dynamic SQL and discrepancies, flow narration, the review queue, and the per-project LLM switch.
(The remaining parser track, C#, COBOL/copybooks/JCL, can run in parallel. Each is just a new `LanguageParser` behind the same registry.)

## New dependencies
`kuzu`, `sqlalchemy`, `oracledb` (thin mode, no Oracle client needed), `pyodbc`, `psycopg[binary]`, `ibm_db` (optional extra), `paramiko`, `python-docx`, `boto3`, `atlassian-python-api` (or plain `requests`). The DB drivers are optional imports, so a missing driver only disables that database type.

## Security guardrails
Read-only DB accounts (document the minimal grants per engine). Catalog queries only, never user data. SSH uses strict host keys and a path allowlist. No secrets in project files, the UI or logs. Every connector call has a timeout. Scans run as background jobs so the UI never blocks.

## Verification
- **Unit:** each connector is tested against fakes/fixtures: a local bare Git repo, a `moto` S3 mock, SQLite plus recorded Oracle/SQL Server catalog rows, a paramiko in-process SFTP server, recorded Confluence JSON, and small docx/pdf fixtures. Each new parser gets golden fixtures (shell heredoc SQL, `sqlplus @`, crontab lines, Python DB-API SQL).
- **Stitcher:** a synthetic multi-source scenario built from the existing ClaimCore app split across sources. Repo A holds the Java, repo B holds `batch/settle_claims.sh` (calls `sqlplus … @process_claim.sql`) plus a crontab. The "DB" source is the Postgres/SQLite DDL and procedure. A Markdown "wiki" page describes settlement. Assert that `/api/flows?entry=cron:settle_claims` returns cron → shell → SP_PROCESS_CLAIM → POLICY_MASTER, that `ClaimService` also links to that same `POLICY_MASTER` node, and that the wiki page is linked with `DOCUMENTS`.
- **Persistence:** restart the server and confirm the graph reloads. Change one file, rescan, and confirm only that file's nodes changed.
- **Regression:** all 54 parser tests and 8 fabric tests stay green.
- **Deterministic core:** run the full multi-source scenario twice with the LLM switched off. The graphs must be identical (same node and edge sets and hashes), and every flow assertion above must pass without any LLM.
- **AI layer:** with a stubbed LLM, confirm that suggestions arrive as dashed `extractor="llm"` edges with confidence ≤ 0.6, that uncited or out-of-range citations are rejected, and that suggestions affect blast radius only after they are accepted in the review queue.
- **End to end in the browser:** start `apps/modernizeai_ui/server.py`, create a project, add the sources above through the Sources panel, run "Scan all", open the Flow Explorer, click through each hop and confirm that the provenance links open the right file, DB object or wiki page.
