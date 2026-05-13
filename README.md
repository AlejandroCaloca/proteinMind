# proteinMind

ProteinMind is a multi-agent system that continuously ingests scientific literature, extracts structured design constraints, and applies them toward designing novel protein tools with a long-term architecture that can eventually target custom nuclease/effector domains for gene editing.

## 1) Technical architecture and agent protocol

### Agent layers
- **Layer 1: Librarian Agent**: literature retrieval + structured constraint extraction.
- **Layer 2: Designer Agent**: translates constraints into ColabFold / RFdiffusion-ready inputs and flags incompatible constraints.
- **Layer 3: Memory & Synthesis Agent**: persistent knowledge graph with evidence tracking, conflict reconciliation, and uncertainty surfacing.

### Communication protocol (JSON envelope)
All agent-to-agent messages should use a shared envelope:

```json
{
  "message_id": "uuid",
  "sender": "librarian|designer|memory",
  "receiver": "librarian|designer|memory|ui",
  "message_type": "constraint_object|design_request|design_result|conflict_report|memory_update",
  "timestamp": "ISO-8601",
  "payload": {},
  "trace": {
    "query": "luciferase active site",
    "source_papers": ["PMID:...", "bioRxiv:..."],
    "version": "v1"
  }
}
```

### Librarian output contract (`constraint_object`)
- `query`, `generated_at`, `papers_analyzed`
- `constraints`: typed entries grouped by:
  - `active_site_contacts`
  - `geometry`
  - `ligand_binding`
  - `beneficial_mutations`
  - `deleterious_mutations`
  - `codon_context`
  - `validation`
- `conflicts`: explicit contradiction/gap items

## 2) NemoClaw / NeMo Guardrails + NVIDIA mapping

- **Orchestration**: NemoClaw multi-agent graph (Librarian → Designer → Memory).
- **Guarded actions + schema checks**: NeMo Guardrails rails enforcing JSON schema per message type.
- **Extraction model serving**: NVIDIA NIM endpoints or local NeMo-hosted LLM for paper-to-constraint extraction.
- **Vector retrieval**: NVIDIA NeMo Retriever (or FAISS-backed index on GPU where available) for paper chunk lookup.
- **Knowledge graph persistence**: graph DB layer (e.g., Neo4j) with evidence edge metadata, orchestrated by Memory agent.
- **Designer compute path**: ColabFold/RFdiffusion input generation + optional GPU execution on DGX Spark.

## 3) Realistic 24-hour build scope

- [ ] **Hour 0–2**: Scaffold repo, schemas, protocol envelope, mock providers.
- [ ] **Hour 2–8**: Librarian MVP (PubMed/bioRxiv ingestion, extraction, JSON output).
- [ ] **Hour 8–14**: Designer MVP (constraint translation + conflict surfacing).
- [ ] **Hour 14–18**: Memory MVP (graph persistence + contradiction flagging).
- [ ] **Hour 18–22**: Minimal UI + demo flow for one protein target.
- [ ] **Hour 22–24**: Hardening, prompt tuning, final demo script.

## 4) Librarian Agent prototype (implemented)

This repository now includes a production-oriented Librarian foundation in `proteinmind/librarian.py` with:
- provider abstraction for PubMed/bioRxiv clients
- extraction schema + typed constraints
- deterministic conflict detection (same mutation labeled both beneficial and deleterious)
- JSON-serializable `constraint_object` output for downstream agents

Run tests:

```bash
python -m unittest discover -s tests -v
```
