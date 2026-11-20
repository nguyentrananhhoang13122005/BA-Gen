# Design System — BA-Gen (ReqAssist-NLP)

## Visual World & Aesthetic Direction
**Swiss Architectural Specification Studio** — Inspired by European ISO/DIN Engineering Standards Manuals, Swiss Typographic Grids, and high-density technical workbenches.
- **Anti-Vibecode Commitment:** Zero emoji icons (`📋`, `🚀`, `⚡` eliminated across all surfaces), zero gradient text, zero one-sided border strips (`border-left: 4px`), zero raw Python array dumps.
- **Iconography:** Custom inline SVG vector iconography (`1.8px` geometric stroke) in `src/ui/design_system.py`.

## Three-Layer Token Architecture

### 1. Primitive & Semantic Color Tokens
| Token | Value | Role |
|---|---|---|
| `--bg-canvas` | `#F4F6F9` | Architectural drafting ground |
| `--bg-surface` | `#FFFFFF` | Specification plate surface |
| `--bg-elevated` | `#F8FAFC` | Recessed telemetry & matrix well |
| `--bg-shell` | `#0F172A` | Top Engineering Command Shell & Gherkin BDD Terminal |
| `--ink-primary` | `#0F172A` | Primary drafting ink (>15:1 contrast) |
| `--ink-secondary` | `#334155` | Specification prose (>8:1 contrast) |
| `--ink-muted` | `#475569` | Technical metadata & labels (≥4.6:1 contrast) |
| `--accent-cobalt` | `#1E3A8A` | Primary engineering action & active focus ring |
| `--fr-fg` / `--fr-bg` | `#0F766E` / `#F0FDFA` | Functional Requirement (FR) semantic badge |
| `--nfr-fg` / `--nfr-bg` | `#1D4ED8` / `#EFF6FF` | Non-Functional Requirement (NFR · ISO 25010) badge |
| `--warn-fg` / `--warn-bg` | `#92400E` / `#FFFBEB` | Ambiguity defect alert box (full `1px` border `#FDE68A`) |
| `--smart-fg` / `--smart-bg` | `#166534` / `#F0FDF4` | SMART verified specification card (full `1px` border `#BBF7D0`) |
| `--danger-fg` / `--danger-bg` | `#991B1B` / `#FEF2F2` | Inline vague term diagnostic chip |

### 2. Typography Scale
- **Primary UI & Specification Prose:** `'IBM Plex Sans'`, `-apple-system`, `sans-serif` (65–75ch max prose measure, `1.6` line-height).
- **Technical Identifiers, Telemetry, Gherkin BDD & Confusion Matrices:** `'JetBrains Mono'`, `monospace` with `font-variant-numeric: tabular-nums`.

### 3. Motion & Animation Thesis
- **Focal Authored Moment:** Live 6-Stage NLP Pipeline Execution Console (`STAGE 01 INGEST & SEGMENT` -> `STAGE 02 HYBRID CLASSIFIER` -> `STAGE 03 AMBIGUITY & SMART` -> `STAGE 04 GHERKIN BDD` -> `STAGE 05 UML 2.5 MODEL` -> `STAGE 06 IEEE 830 SRS`) with `@keyframes pulseRadar` active node ring and `@keyframes streamShimmer` progress wave.
- **State & Continuity:** `@keyframes slideReveal` (`cubic-bezier(0.16, 1, 0.3, 1)`) for specification plates and `@keyframes barGrow` for KPI & benchmark accuracy meters.
- **Accessibility:** Full `@media (prefers-reduced-motion: reduce)` path disabling spatial movement while preserving state color transitions.

### 4. Spatial Architecture (4 Zones)
- **Zone A (Top Command Shell):** Brand emblem + live system telemetry pills (`ENGINE`, `ROUTER τ`, `LOCALE`, `STD`).
- **Zone B (Collapsible Ingestion Studio):** Dual-column document dropzone, project identifier, 1-click E-commerce sample loader, and raw specification editor; automatically collapses upon analysis completion to prioritize the workbench.
- **Zone C (Pipeline Telemetry Console & KPI Ribbon):** 6-stage execution timing breakdown + 5 tabular-numeral KPI plates.
- **Zone D (4-Workspace Engineering Workbench):**
  - `01 · Ma trận Yêu cầu & Kiểm định SMART`: Filter/search bar, batch SMART normalizer, and 2-column specification + Human-in-the-Loop cards.
  - `02 · Agile User Stories & Gherkin BDD`: 3-cell Role-Goal-Benefit grid, dark Gherkin BDD terminals, and 3-column Ecosystem Sync Hub (Jira, GitHub Issues, Trello).
  - `03 · Mô hình Use Case & Hồ sơ SRS (IEEE 830)`: Dual-pane UML 2.5 diagram canvas and inline scrollable 6-chapter IEEE 830 document reader.
  - `04 · Kiểm chuẩn Mô hình (5-Fold Benchmark)`: 3-tier comparative matrix with animated metric bars and 2x2 HTML Confusion Matrix tables.
