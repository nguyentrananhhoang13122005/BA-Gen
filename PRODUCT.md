# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Business Analysts (BAs), Requirements Engineers (REs), Product Owners, and Software Architects working in bilingual (Vietnamese and English) software engineering teams. They ingest raw, unstructured business descriptions (`.docx`, `.txt`, or raw stakeholder notes) and need to transform them into auditable, unambiguous engineering specifications.

## Product Purpose

BA-Gen (ReqAssist-NLP) automates the requirements engineering workflow: splitting raw business narratives into atomic requirements, classifying them into Functional (FR) vs. Non-Functional (NFR) with ISO/IEC 25010 sub-categories, detecting ambiguous wording and missing actors/metrics, synthesizing SMART rewrites, generating Agile User Stories with Gherkin BDD acceptance criteria, rendering UML 2.5 Use Case diagrams, exporting IEEE 830 / ISO 29148 SRS documents, and syncing directly to Jira, GitHub Issues, and Trello.

## Positioning

A 3-Tier Hybrid NLP & Multi-LLM Requirements Engineering Workbench with deterministic offline fallback (TF-IDF + LinearSVC + Circuit-Breaker), bilingual ambiguity lexicon detection, Human-in-the-Loop specification refinement, and 5-Fold Stratified Cross-Validation benchmarking on a 35-item gold dataset.

## Operating Context

Used during requirement elicitation, backlog grooming, and SRS authoring sessions on desktop workstations. Analysts inspect sentence-level telemetry, compare original vague clauses against SMART rewrites, override classification labels with instant downstream artifact re-synchronization, preview IEEE 830 specifications, and push stories to Jira Cloud, GitHub Issues, or Trello Kanban.

## Capabilities and Constraints

- 6-Stage Processing Pipeline: Ingestion/Segmentation -> Hybrid FR/NFR Classification -> Ambiguity & SMART Rewrite -> Agile User Story & Gherkin BDD Generation -> PlantUML Use Case Diagram -> IEEE 830 SRS Export & PM Tool Sync.
- Multi-provider AI routing: Groq, OpenRouter, Google Gemini, local Ollama, and 100% Offline ML fallback.
- Stack: Python, Streamlit, Pydantic, SQLite (SHA-256 caching), scikit-learn, python-docx.

## Evidence on Hand

- Sample Vietnamese E-commerce requirement document (`data/sample_ecommerce_vi.txt`).
- Bilingual Ambiguity Lexicon (`data/ambiguity_lexicon.json`).
- 35-item Gold Benchmark Dataset (`data/benchmark_35_reqs.json`).

## Product Principles

1. **Precision over Decoration:** Every visual indicator encodes engineering state — classification type, ISO 25010 quality attribute, confidence score, or ambiguity defect.
2. **Traceability by Design:** Every User Story (`US-xx`), Gherkin scenario, and Use Case node traces back to an atomic Requirement ID (`REQ-xx`).
3. **Human-in-the-Loop Control:** Analysts can refine text, apply SMART rewrites, or reclassify FR/NFR labels and immediately propagate changes across all downstream artifacts.
4. **Transparent Pipeline Telemetry:** Processing stages, routing tiers, and execution timings are visible and verifiable.
