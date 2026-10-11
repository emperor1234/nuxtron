# Brand management context

This pilot keeps the `/api/v1/brands` contract unchanged while separating business rules from FastAPI and storage.

- `public.py` is the only supported import surface for other contexts.
- `service.py` names every tenant-scoped operation. A tenant ID is required before any lookup or mutation.
- `ports.py` describes the small atomic repository boundary used by the service.
- `memory_repository.py` adapts the canonical `memory_stores.brand_hub_brands` object and its shared lock.
- `api/` contains the ten historical endpoints split into focused route groups.
- `wiring.py` creates the service and router. The application bootstrap registers that router explicitly.

Production mutations still fail with `503` because the historical brand feature has no durable repository. Reads retain their existing process-local behavior. The compatibility modules under `routers/brand_hub.py` and `brand_hub/core.py` should not be used by new code.
