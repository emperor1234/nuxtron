# Connecting an AI provider and keeping data across restarts

## AI provider

Set one of these on the backend service and restart it:

| Variable | Used for |
| --- | --- |
| `OPENAI_API_KEY` | Content, ads, copywriter, SEO tools (preferred when both are set) |
| `ANTHROPIC_API_KEY` | Same, when no OpenAI key is set |
| `OPENAI_MODEL`, `ANTHROPIC_MODEL`, `SEO_HOSTED_MODEL` | Optional model overrides |
| `OPENAI_BASE_URL`, `ANTHROPIC_BASE_URL` | Optional: an OpenAI/Anthropic-compatible gateway |
| `SEO_LLM_PROVIDER=ollama` | Force the local Ollama model instead of a hosted one |

Without a key, generators answer `503 AI_MODEL_UNAVAILABLE`; they never return
canned text. `GET /integrations/tools` shows which providers are configured.
`app/tests/test_ai_provider_round_trip.py` runs the success path over real HTTP
against a local OpenAI-compatible server.

## Persistence

* Records the ORM owns (CRM, billing, approvals, workflows) live in Postgres.
* Everything else that used to sit in process memory is snapshotted by
  `app/process_store_persistence.py` into the `process_store_snapshots` table
  (migration `4c6e8a2b5d37`) and restored on start. Without a database it uses
  a JSON file (`NUXTRON_STATE_PATH`).
* Run **one** backend worker (`WEB_CONCURRENCY=1`, the default). Snapshots are
  per process, so several workers would overwrite each other.
* Stores holding tokens, credentials or OAuth state are never snapshotted.
* Set `NUXTRON_PERSIST_STORES=0` to turn snapshots off.
