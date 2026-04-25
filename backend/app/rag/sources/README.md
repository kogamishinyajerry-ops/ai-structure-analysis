# RAG Corpus Sources (P1-04b)

The five corpus sources for the AI-Structure-FEA knowledge base, per Notion task `AI-FEA-P1-04b RAG 知识库建库 / 扩充` and the empirical SCRATCH-REBUILD evidence from P1-04a (PR #13).

## Source 1 — CalculiX Reference Manual

- **Location:** [CalculiX Manual v2.21](http://www.dhondt.de/ccx_2.21.pdf) (PDF, ~1500 pages)
- **Scope:** keyword cards, element library, material models, output requests
- **Why:** primary numerical truth source per ADR-002; agents must answer "what does `*STATIC` accept?" type questions correctly
- **Ingestion notes:** PDF needs section-aware splitting; OCR not required (text-extractable)

## Source 2 — Strength of Materials / Mechanics of Solids textbooks

- **Reference candidates:** Hibbeler, Beer & Johnston, Timoshenko (public-domain or licensed copy)
- **Scope:** beam theory, stress concentrations, plate theory, buckling — analytical formulas the validator + theory scripts use
- **Why:** the GS theory scripts (`golden_samples/<id>/*_theory.py`) ground their formulas in textbook canon; surrogate hint provider checks against these
- **Ingestion notes:** chapter-level chunking; LaTeX equations should be preserved (not stripped)

## Source 3 — FEA Best Practices guidance

- **Reference candidates:** NAFEMS guidelines, ASME PTC 60, internal FEA process docs
- **Scope:** mesh quality criteria, element selection, BC application, convergence checks
- **Why:** Reviewer agent / fault-routing (ADR-004) needs domain heuristics for diagnosis
- **Ingestion notes:** policy-style content; bullet/numbered list preservation matters

## Source 4 — Project ADRs + FailurePatterns

- **Location:** `docs/adr/`, `docs/failure_patterns/` in this repo
- **Scope:** ADR-001 to ADR-013, FP-001/002/003, future FPs
- **Why:** project-specific governance + empirical fault attribution; agents should know "have we seen this before?"
- **Ingestion notes:** markdown-aware splitter; cross-references (e.g. `ADR-011 §HF1.7`) must round-trip

## Source 5 — Golden Samples READMEs + theory scripts

- **Location:** `golden_samples/GS-*/README.md` + `golden_samples/GS-*/*_theory.py`
- **Scope:** case-specific theory + expected_results structure
- **Why:** retrieval-augmented hint generation per case (when surrogate-hint provider needs case-specific context)
- **Ingestion notes:** small per-doc footprint; one chunk per file usually sufficient

## Ingestion contract

Each source produces `Document` objects with fields:

```python
Document(
    doc_id=f"{source_label}:{section_id}",
    source=<one of: "calculix-manual", "mechanics-textbook", "fea-best-practices",
                    "project-adr-fp", "gs-theory">,
    title=...,
    text=...,
    metadata=<source-specific dict>,
)
```

The five sources above use `source_label` = the dashed slug.

## Status (P1-04b PR initial)

This PR ships the **infrastructure** (embedder, store, chunker, KnowledgeBase orchestrator) — actual corpus ingestion is staged separately:

1. CalculiX Manual ingestion script — follow-up PR (depends on PDF text extraction lib choice; pdfplumber vs pypdf2)
2. Project ADRs+FPs ingestion script — follow-up PR (lightweight; markdown-aware)
3. GS theory ingestion script — follow-up PR
4. Mechanics textbooks ingestion — depends on copyright-cleared corpus selection (T0 decision)
5. FEA best-practices ingestion — depends on NAFEMS license / internal doc availability

Each follow-up PR uses the `KnowledgeBase.ingest()` API; no schema changes expected.
