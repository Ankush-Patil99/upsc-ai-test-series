# Scripts — Developer Utilities

This folder contains one-off utility and maintenance scripts used during development.
They are NOT part of the main application — the core pipeline lives in src/ and api/.

---

## Database Inspection

| Script | Purpose |
|---|---|
| check_db.py | Print summary of all PostgreSQL tables and row counts |
| view_database.py | Inspect raw rows in the questions/articles tables |
| check_progress.py | Monitor ingestion progress — how many chunks are embedded |
| audit_questions.py | Quality audit: check for malformed MCQs in the database |
| verify_injected.py | Verify a specific batch of questions was correctly inserted |

## Data Ingestion Utilities

| Script | Purpose |
|---|---|
| ingest_question_bank.py | Bulk import of PYQ (Past Year Question) bank into pgvector |
| ingest_v2.py | Updated ingestion with deduplication and subject tagging |
| ingest_prototype.py | Early prototype ingestion (kept for reference) |
| import_test_series.py | Import a structured test series JSON into the database |
| inject_test.py | Inject a small test batch of questions for manual verification |
| inject_test_100.py | Inject the 100-question mock set for CBT frontend testing |
| inject_clean.py | Clean-insert with duplicate checking before each insert |
| smoke_test_ingest.py | Lightweight smoke test: ingest 5 articles and verify embeddings |

## Question Generation Utilities

| Script | Purpose |
|---|---|
| generate_universal_bank.py | Batch-generate MCQs across all UPSC subjects into the database |
| enrich_mains_hints.py | Post-process existing MCQs to add/improve mains_hint fields |
| quality_gate.py | Quality checks on generated MCQs — flags low-quality outputs |

## Frontend / CSS Patches

| Script | Purpose |
|---|---|
| append_css.py | Append CSS patch to frontend/style.css |
| append_css2.py | Second iteration CSS patch |
| append_css3.py | Third iteration CSS patch |
| fix_css.py | Fix specific CSS selector conflicts |
| fix_css2.py | Follow-up CSS fix pass |

## Vision Parser (vision_parser/)

Scripts to parse VisionIAS PDF content into structured JSON for pgvector ingestion.

| Script | Purpose |
|---|---|
| extract_paper1.py | Extract GS Paper 1 content from VisionIAS monthly PDF |
| parse_paper1.py | Parse extracted content into structured chunks |
| parse_paper1_v2.py | Improved parser with better section detection |
| finalize_paper1.py | Final cleanup and DB insert for parsed content |
| fix_paper1.py | Patch malformed entries from the parsing step |
| make_vision_js.py | Generate JS data file from parsed Vision content |
| inspect_cols.py | Inspect column types and data in the vision table |
| check_json.py | Validate JSON output before insertion |
| patch.py | Targeted patch for specific malformed rows |
