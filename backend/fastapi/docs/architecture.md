# Backend modular architecture

## Goal and package shape

The migration replaces the flat application incrementally. It does not change HTTP behavior. Each business capability becomes a bounded context:

```text
app/
├── main.py                       # process/bootstrap entry point
├── composition.py               # transitional global composition
├── router_registration.py       # transitional legacy router wiring
├── shared/                       # small, context-neutral primitives only
└── contexts/
    └── <context_name>/
        ├── README.md
        ├── public.py             # the only module other contexts may import
        ├── bootstrap.py          # dependency wiring and router export
        ├── domain/               # entities, value objects, policies
        ├── application/          # use cases and abstract ports
        ├── infrastructure/       # database and external-service adapters
        └── api/                  # FastAPI router and transport schemas
```

Create a context only for a cohesive business capability, not for a technical category. For example, `billing`, `identity`, and `content_generation` are contexts; `helpers` and `services` are not.

## Dependency direction

Dependencies point inward:

```text
api ───────┐
           ├──> application ──> domain
infrastructure ────────────────> domain
bootstrap ─> api + application + infrastructure
```

- `domain` is pure Python and imports no FastAPI, database driver/ORM, or HTTP client.
- `application` coordinates use cases and defines ports. It has the same framework restrictions.
- `infrastructure` implements application ports and owns SQLAlchemy, psycopg, and outbound HTTP details.
- `api` translates HTTP input/output and calls application use cases. Business rules do not live in routers.
- `bootstrap.py` constructs adapters and handlers and exports a router. The root composition layer includes it; context code does not call `include_router`.
- A context may import another context only through that context's `public.py`.

The AST checks in `app/tests/test_architecture_boundaries.py` enforce these rules as soon as `app/contexts/` contains code. They intentionally pass before the first context exists while still guarding router composition and legacy size ratchets.

`include_router` is receiver-agnostic and permitted only at explicitly reviewed paths. The current transition allowlist is `composition.py`, `legacy_main.py`, `router_registration.py`, `main_social.py`, and the legacy nested-router aggregator `routers/ops.py`. A filename such as `bootstrap.py`, `application.py`, or `main_new.py` does not grant permission. New context routers are exported to `composition.py`; removing a transitional caller must shrink this allowlist.

## Naming and public contracts

- Use lowercase `snake_case` for contexts, modules, commands, and queries.
- Name use cases with an action and object, such as `CreateCampaign` or `GetInvoice`.
- Name ports by responsibility, such as `InvoiceRepository` or `PaymentGateway`; adapters describe the technology, such as `PostgresInvoiceRepository`.
- Keep transport models in `api/schemas.py`; domain objects must not inherit from Pydantic or ORM classes.
- `public.py` re-exports the smallest stable set of types and application operations needed by other contexts. It must not expose infrastructure or router internals. Both `app.contexts.<name>` and `backend.fastapi.app.contexts.<name>` imports are checked; package-level imports such as `from app.contexts import billing` are prohibited.
- Private implementation modules and symbols may change freely. Cross-context consumers depend only on the public contract.

## Compatibility shims

Migration is route-by-route. Existing imports and call sites remain valid until their consumers move. A compatibility shim:

1. keeps the old module path and callable signature;
2. delegates immediately to the new context public API;
3. contains no new business logic;
4. has a removal condition documented beside it; and
5. preserves status codes, headers, payload schemas, operation IDs, and authentication behavior.

Do not duplicate writes between legacy and modular implementations. Select one implementation behind the shim and prove parity with characterization tests.

## File and router limits

These limits apply to every new or migrated context module:

- ordinary module: 300-line target and 500-line absolute hard limit;
- router/API module: 250 lines and no more than eight HTTP endpoints;
- bootstrap/wiring module: 150 lines.

Router/API limits cover every Python file below a context's `api/` package plus context-level `api.py`, `router.py`, and `routes.py`; nested helper names do not bypass them. Endpoint counting recognizes decorators on router-like names and variables assigned from `APIRouter`/`FastAPI`, counts each declared method in `api_route(methods=[...])`, and ignores unrelated decorators such as cache `.get()`. A simple uppercase module constant assigned an immutable tuple of method strings is resolved safely. Any dynamic or otherwise indeterminate `api_route` method expression is an explicit architecture violation; counting never guesses. Router and wiring limits are strict.

An ordinary module at or below 300 lines passes. A 301–500-line module passes only when its exact relative path appears in `TEMPORARY_SIZE_RATCHETS` with a non-empty split reason and a ceiling no higher than 500. The check requires the ceiling to equal the file's current line count, so an exception cannot reserve growth headroom. Lower the ceiling immediately whenever the file shrinks, and never increase it. Any migrated context module above 500 lines fails even if a temporary ratchet is present. Split by responsibility before using an exception.

Existing hotspots are not forced into arbitrary splits: `legacy_main.py`, `router_registration.py`, and `composition.py` have explicit ceilings in the architecture test and may only shrink. Lower a ceiling whenever a migration removes lines; never raise one to make CI pass.

## Contract and TDD workflow

Every migration uses red-green-refactor:

1. Add or strengthen a characterization/unit test for the behavior being moved.
2. Run the smallest focused command and capture the expected failure.
3. Implement the minimum code that makes that test pass.
4. Run the focused test again, then architecture and route-contract tests.
5. Run application smoke tests, lint, and type checking for changed production modules.
6. Refactor only while tests remain green.

The checked-in route manifest records every OpenAPI HTTP method, path, operation ID, and stable hashes of selected request and response schemas. Local `$ref` targets are resolved before hashing, and OpenAPI 3.1 `$ref` sibling keywords are merged so changing a sibling changes the relevant hash.

Schema generation fails loudly unless the route's complete HTTP method set, path, operation ID, exception type, and normalized detail match `KNOWN_SCHEMA_FAILURES` exactly. The sole current allowance requires the method set to be exactly `{POST}` for `/content/generate/async`; adding another method does not inherit the allowance. Its Pydantic detail normalization requires all three stable markers: `ForwardRef('content_request_model')`, `is not fully defined`, and `/class-not-fully-defined`. The manifest records the exact normalized identity `content_request_model:is-not-fully-defined:class-not-fully-defined`. Do not broaden the allowance or add one without documenting and scheduling the production fix.

Run:

```bash
PYTHONPATH=. backend/fastapi/.venv312/bin/pytest \
  backend/fastapi/app/tests/test_route_contract.py \
  backend/fastapi/app/tests/test_architecture_boundaries.py --no-cov
```

If an intentional, reviewed API change occurs, regenerate the baseline explicitly:

```bash
PYTHONPATH=. backend/fastapi/.venv312/bin/python \
  -m backend.fastapi.app.tests.contracts.route_manifest --write
```

Never regenerate merely to silence a failure. Review the method, path, operation-ID, and schema-hash difference first.

## Migration sequence

1. Choose one cohesive route group and capture its current behavior.
2. Create the context from `docs/context-readme-template.md`.
3. Move pure rules and types into `domain`.
4. Move orchestration into `application`; define ports for persistence and remote calls.
5. Implement those ports in `infrastructure`.
6. Add a thin `api` router that preserves the existing HTTP contract.
7. Wire dependencies and export the router in `bootstrap.py`; register that router in root `composition.py`.
8. Replace the old implementation with a compatibility shim.
9. Run contract, architecture, smoke, lint, and type checks.
10. Remove the shim only after all consumers migrate, then lower the relevant legacy ratchet.

## Finding and changing a feature

For a new developer:

1. Search the route path to find its `api/router.py` handler.
2. Follow the single application use-case call from that handler.
3. Read the context `README.md` for ownership, public API, dependencies, and tests.
4. Find business decisions in `domain`; find database or remote-service details in `infrastructure`.
5. Start the change with a focused failing test in the same layer.
6. Keep imports inside the dependency direction and use another context's `public.py` when collaboration is required.
7. Run the focused test, architecture/contract checks, and the application smoke suite before requesting review.

If the feature has not migrated, begin at its existing router, trace dependencies, and migrate a narrow vertical slice rather than creating another flat helper.
