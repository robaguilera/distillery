# Distillery

A local-first personal knowledge management skill for condensing video (and eventually other media) into structured, searchable knowledge. Currently a Claude Code skill; designed to grow into a native desktop app.

## Language

**Distillation**:
A structured summary of a single media item — includes an executive summary, key points, and timestamped topics.
_Avoid_: Report, summary, note

**Canonical Extraction**:
The structured JSON payload produced from a media item — the source of truth that all views render from.
_Avoid_: Raw data, parsed output, summary JSON

**View**:
A named HTML template that renders a Canonical Extraction into a specific layout and content shape suited to a use case.
_Avoid_: Template, layout, format, theme

**Default View**:
The standard View — video player left, prose summary right, timestamped outline. What distillery produces today.

**Study Guide View**:
A View optimised for retention — hierarchical outline, key concepts defined, structured for review.

**Executive Brief View**:
A View optimised for fast signal extraction — 2-paragraph summary and 5 bullets, nothing else.

**Batch**:
A Distillation covering multiple media items processed together, with a synthesis section that finds themes across them.
_Avoid_: Multi-video, playlist summary, group

**Synthesis**:
The cross-item analysis produced by a Batch — themes, contradictions, and narrative threads that emerge across multiple media items.
_Avoid_: Combined summary, group summary

**Knowledge Base**:
The persistent store of all Canonical Extractions and their metadata — the foundation for tagging, search, and cross-document analysis. Currently `manifest.json`; intended to become SQLite.
_Avoid_: Database, library, archive, vault

**Ingestion**:
The process of fetching, extracting, and storing a media item into the Knowledge Base.
_Avoid_: Processing, parsing, importing

## Relationships

- **Ingestion** produces one **Canonical Extraction**
- A **Canonical Extraction** can be rendered into one or more **Views**
- A **Batch** contains multiple **Canonical Extractions** and produces one **Synthesis**
- The **Knowledge Base** stores all **Canonical Extractions** and their metadata

## Example dialogue

> **Dev:** "Should the flashcard layout re-run the LLM to get flashcard-friendly content?"
> **Domain expert:** "Not yet — for now every View renders from the same Canonical Extraction. View-specific re-extraction is a future stage."

> **Dev:** "When a user processes a playlist, is that a Batch?"
> **Domain expert:** "Yes — multiple videos processed together with a Synthesis across them is a Batch. A single video is just a Distillation."

## Flagged ambiguities

- "Summary" was used loosely to mean both the executive summary section within a Distillation and the entire Distillation itself — resolved: use **Distillation** for the whole artifact, **executive summary** only for the specific section within it.
- "Template" was used to mean both a View and an HTML file — resolved: **View** is the concept, the HTML file is the implementation detail.
