# medRAG — Manual Test Scenarios

## Structure

```
test_scenarios/
├── phase0_infra.json        Phase 0: health checks, MongoDB, Weaviate, RabbitMQ
├── phase1_auth.json         Phase 1: registration, login, JWT, gateway
├── phase2_ingestion.json    Phase 2: PDF upload → vectors in Weaviate
├── phase3_query.json        Phase 3: query pipeline, streaming, citations
├── phase4_rag_modes.json    Phase 4: vanilla / hyde / self_reflection / multi_agent / ...
└── phase5_admin_eval.json   Phase 5: admin CRUD, RAG metrics, CSV export
```

## How to read the JSONs

Each file has the following structure:

```json
{
  "phase": "...",
  "scenarios": [
    {
      "id": "0.1",
      "title": "Short title",
      "description": "What this test verifies and why",
      "preconditions": ["What must be true before starting"],
      "steps": [
        {
          "step": 1,
          "action": "What to do (human-readable)",
          "command": "curl ...",
          "expected_status": 200,
          "expected_response": { "example": "response" },
          "notes": "Additional remarks"
        }
      ],
      "expected_outcome": "What the final result of the scenario should be",
      "save_for_later": { "variable": "$.field.from.response" }
    }
  ]
}
```

## Variables

curl commands use `$VARIABLE` — replace with values from previous steps.
Key variables to carry between scenarios:

| Variable        | Source                                  |
|-----------------|-----------------------------------------|
| `$TOKEN`        | Response from POST /auth/login          |
| `$ADMIN_TOKEN`  | Response from POST /auth/login (admin)  |
| `$PROJECT_ID`   | Response from POST /admin/projects      |
| `$DOCUMENT_ID`  | Response from POST /ingest/.../documents|
