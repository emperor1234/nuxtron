# `<context_name>` context

## Purpose

State the business capability this context owns in two or three sentences. List what is explicitly outside its boundary.

## Public API

List the symbols exported by `public.py`, their consumers, and compatibility guarantees.

- `<CommandOrQuery>` — `<what it does>`
- `<PublicType>` — `<why another context needs it>`

Other contexts must import only from `app.contexts.<context_name>.public`.

## Package map

```text
<context_name>/
├── README.md
├── public.py
├── bootstrap.py
├── domain/
├── application/
├── infrastructure/
└── api/
```

- `domain`: `<entities, value objects, rules>`
- `application`: `<use cases and ports>`
- `infrastructure`: `<database and remote adapters>`
- `api`: `<routes and transport schemas>`
- `bootstrap.py`: `<wiring and router export>`

## Dependencies

### Inbound

- `<consumer>` uses `<public symbol>`

### Outbound

- `<context>.public` — `<reason>`
- `<application port>` implemented by `<adapter>`

Do not list direct imports of another context's internal modules; those are prohibited.

## HTTP contract

- `<METHOD> <path>` — operation ID `<operation_id>`

Record authentication, status codes, headers, and compatibility-shim locations. The global route manifest remains the source of truth for exact OpenAPI compatibility.

## Data ownership

List tables, queues, caches, and external resources owned by this context. Describe transaction boundaries and idempotency expectations.

## Tests and local workflow

Focused tests:

```bash
PYTHONPATH=. backend/fastapi/.venv312/bin/pytest <test paths> --no-cov
```

Also run `app/tests/test_architecture_boundaries.py`, `app/tests/test_route_contract.py`, application smoke tests, Ruff, and mypy for changed production modules.

## Migration status

- Legacy source: `<module/symbol>`
- Compatibility shim: `<module/symbol or none>`
- Migrated slices: `<list>`
- Remaining work: `<list>`
- Shim removal condition: `<measurable condition>`
- Temporary size ratchet: `<exact relative path, current ceiling, split reason, or none>`

Ordinary modules target 300 lines and may use a documented, non-increasing temporary ratchet only from 301–500 lines. Its ceiling must equal the file's current line count—no growth headroom—and must be lowered when the file shrinks. Every file under `api/`, plus context-level `api.py`, `router.py`, and `routes.py`, has a strict 250-line/eight-endpoint limit. Multi-method `api_route` declarations count each HTTP method; use a literal method collection or a simple uppercase immutable tuple constant because dynamic method expressions fail architecture validation. Context-level bootstrap/wiring has a strict 150-line limit. No context module may exceed 500 lines.

## Change guide

Explain where a junior developer should start for:

- changing a business rule;
- changing a use case;
- changing persistence or an external integration;
- changing an HTTP transport detail without changing the public API.

Keep this section current whenever package ownership changes.
