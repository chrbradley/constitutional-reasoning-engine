LAYER 1: Fact Establishment

This layer establishes the factual foundation for constitutional reasoning.

Phase 1 (Current):
- Facts are loaded directly from scenario JSON (no API call)
- Each file contains: established facts, ambiguous elements, and key questions
- Field "skipped": true indicates facts were not generated via API

Phase 2+ (Future):
- Facts will be established via real-time grounding mechanisms
- Will test: RAG, citations, provenance, confidence intervals
- Field "skipped": false and "source": "gpt-4o" indicates API-generated facts

File format: {scenario_id}_{constitution_id}_{model_id}.json
