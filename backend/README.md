# Backend engineering guide

Nuxtron runs as a **modular monolith with separately deployed workers**. Start here rather than reading every file in alphabetical order.

## 1. First files to read

1. `fastapi/app/main.py`: the supported ASGI entry point.
2. `fastapi/app/bootstrap/application.py`: application construction.
3. `fastapi/app/bootstrap/lifespan.py`: startup and shutdown.
4. `fastapi/app/router_registration.py`: compatibility/API composition catalog.
5. The domain folder for the feature you are changing.

Django is a separate service under `django/`, not another FastAPI entry point. Its domain applications live under `django/apps/`, settings under `django/config/`, and tests under `django/tests/`.

## 2. Canonical domain map

| Feature | Implementation owner |
|---|---|
| Authentication, verified organizations, token validation, security audit, connection-pinned connector egress | `fastapi/app/domains/identity/` |
| AI policy and gateway | `fastapi/app/domains/ai/` |
| Workflow definitions, execution, approvals, remediation | `fastapi/app/domains/workflows/` |
| Search/provider automation | `fastapi/app/domains/search/` |
| SEO Platform commands and performance analysis | `fastapi/app/domains/seo/platform/` |
| SEO analysis services | `fastapi/app/domains/seo/services/` |
| AI crawler enablement | `fastapi/app/domains/search/crawlers/` |
| Visibility/search analytics | `fastapi/app/domains/search/visibility/` |
| Social Workspace publishing, accounts, brand profiles | `fastapi/app/domains/social/` |
| Smart Inbox | `fastapi/app/domains/social/inbox/` |
| CRM commands | `fastapi/app/domains/crm/` |
| Assistant/IRA commands and governance | `fastapi/app/domains/assistant/` |
| Meetings/email assistants | `fastapi/app/domains/meetings/` |
| Content generation, campaigns, storage, media jobs | `fastapi/app/domains/content/` |
| Billing checkout compatibility adapter | `fastapi/app/domains/billing/` |
| Webhooks, provider helpers, social platform connections, CMS | `fastapi/app/domains/integrations/` |
| Notification delivery and email campaigns | `fastapi/app/domains/notifications/` |
| Ads and growth commands | `fastapi/app/domains/marketing/` |
| Platform intelligence | `fastapi/app/domains/intelligence/platform/` |
| Autonomous workforce | `fastapi/app/domains/automation/workforce/` |

Existing specialized packages such as `answer_engine/`, `intelligence/`, `governance/`, `llm/`, `vault/`, and `tasks/` are retained. A package is not unnecessary merely because it predates the domain layout.

## 3. How a request travels

```text
HTTP request
  -> authentication dependency (verified organization)
  -> domains/<feature>/api/<group>.py (HTTP adapter)
  -> domains/<feature>/operations/<use-case>.py (business orchestration)
  -> service/provider or repository adapter
  -> database / queue / provider
```

- `api/`: small route groups; parses HTTP parameters and delegates. Do not add SQL or provider clients here.
- `operations/`: use cases and policy decisions. Cross-use-case calls go to operations, never back through HTTP handlers.
- `services/`: reusable provider, analysis, normalization, and policy logic.
- `schemas.py`: request/response validation; must not import runtime composition.
- `constants.py`: vocabulary and configuration data; must not import services. Executable provider registries have a separate module.
- `runtime.py`: explicit application-instance dependencies and shared state. Do not replace it with an untyped `globals()` dictionary.
- `repository.py` / `persistence.py`: database access. A database outage is not an empty successful result in production.
- `bootstrap.py`: builds runtime and registers HTTP groups. This is the only place to wire the whole domain together.

Not every domain needs every file. Avoid empty layers or one-file-per-function fragmentation merely to match a diagram.

## 4. Ownership rules

1. Keep ORM declarations in their existing single owner (`app/models.py` and existing model modules) until a deliberate migration changes ownership. Never copy a mapped class into two packages.
2. Pass explicit runtime/context dependencies. Bind runtime when passing a callable to a thread pool or worker.
3. Do not use another router's private helper as a new service contract.
4. A compatibility alias under `routers/`, `services/`, or the app root redirects to one canonical module. Do not add implementation there.
5. Modular files do **not** isolate operating-system failures. Separate worker deployments, timeouts, queues, and bulkheads provide runtime isolation.
6. Mutable Python lists remain local state, not durable storage. Existing development adapters must not be described as Kubernetes-safe production repositories.
7. Tenant-configured Slack/generic webhooks, crawler page checks, snippet-deployment webhooks, and the backend-to-SSR-provider hop use `identity/secure_egress.py`; call `resolve_outbound_target` and `outbound_request` together so DNS validation is pinned to the actual connection. Use `safe_outbound_get` for public page fetches with its redirect/response bounds. `validate_outbound_url` is only a compatibility preflight, not a safe transport. The external SSR provider must independently pin page targets and authenticate callers; other provider clients still need a separate SSRF review.

The media `DELETE /media/raw-input` path requires configured MinIO credentials and a signer, binds the object key to the authenticated tenant, and reports success only after storage acknowledges the signed DELETE. Missing storage returns 503; a failed delete returns a sanitized 502. Do not restore memory/log-only success behavior. Configured privileged-IP allowlists also reject requests whose peer address is missing.

Google Meet/Teams recording start, status, and artifact lookup are not implemented by the current calendar adapters. Recording start returns 503 rather than reporting a fabricated success; enable it only after provider-side recording APIs, explicit participant consent, and verified meeting-scoped artifact ownership are available.

## 5. Database and migrations

- Alembic revisions: `fastapi/alembic/versions/`.
- Historical SQL assets under `fastapi/sql/` and `fastapi/app/migrations/` are retained because runtime and release tooling still reference them.
- New production schema changes belong in reviewed migrations, not HTTP-time `CREATE TABLE` statements.
- Organization context must be set transaction-locally. RLS must be verified on PostgreSQL using a non-bypass application role; text assertions or SQLite tests are not proof.

## 6. Development validation

From the repository root, using the project's prepared Python environment:

```bash
ENVIRONMENT=development backend/fastapi/.venv312/bin/python -m pytest -q --no-cov backend/fastapi/app/tests
ENVIRONMENT=development backend/fastapi/.venv312/bin/python -m pytest -q backend/fastapi/app/tests
backend/fastapi/.venv312/bin/python -m ruff check backend/fastapi/app/domains --select F821,F822,F823
backend/fastapi/.venv312/bin/python -m compileall -q backend/fastapi/app
```

Run these commands from the repository root. The second command includes the repository coverage gate using `backend/fastapi/pyproject.toml`. Coverage measures the application filesystem path, so both supported Python import namespaces are counted and test files are excluded. Do not report a focused or `--no-cov` test pass as a coverage pass.

Django requires its declared dependencies in a separate environment. For local-only tests set `DJANGO_ENV=development`, `DJANGO_DEBUG=1`, a disposable `DJANGO_SECRET_KEY`, and `PYTHONPATH=backend/django`. Never copy those test defaults into production deployment.

## 7. Safe cleanup and compatibility retirement

Do not delete migrations, credentials, uploaded media, databases, dependency environments, or files referenced by release commands merely to make the tree prettier. Keep generated refactor/validation tools under repository `.work/`, not `app/`.

Compatibility aliases should be removed together only after repository-wide import checks, route/OpenAPI contract tests, deployment-entrypoint checks, and a documented migration window. See `../docs/BACKEND-COMPATIBILITY-INVENTORY.md`.

## 8. Current limits

The modularization does not complete the full production redesign. Some domains still have process-local business state, remaining large legacy modules, provider-dependent or unsupported capabilities, and unverified production infrastructure. SOC 2 / ISO 27001 certification, a million-user capacity claim, and complete feature operation require external deployment and operational evidence. See the current readiness report and restructuring plan for release blockers.

## 9. Compatibility review and important naming examples

The local tracking record `BACKEND-MOD-001` and the 2026-11-10 review date are documented in `../docs/BACKEND-COMPATIBILITY-INVENTORY.md`. Compatibility review is not automatic deletion: deployment paths and maintained consumers must migrate first.

Good starting points for provider work:

- Platform OAuth: `fastapi/app/domains/integrations/platforms/services/oauth.py`.
- Platform provider clients: `fastapi/app/domains/integrations/platforms/services/clients.py`.
- Legacy platform file persistence: `fastapi/app/domains/integrations/platforms/services/local_repository.py` (not Kubernetes-ready durable truth).
- Assistant reasoning support: `fastapi/app/domains/assistant/services/reasoning_support.py`.
- Workforce mission execution: `fastapi/app/domains/automation/workforce/services/mission_execution.py`.
- Media processing: `fastapi/app/domains/content/media/services/processing.py`.
- Platform observability: `fastapi/app/domains/intelligence/platform/services/observability.py`.

Media validation token signing refuses a missing/short/known-development `FASTAPI_SECRET` in production. Generate and store a high-entropy secret; never copy the development default into a deployment.

For verification evidence and the remaining acceptance backlog, read `../docs/BACKEND-MODULARIZATION-VALIDATION-2026-10-10.md`. A modular monolith improves locality and testing; it does not guarantee a process cannot fail or that incomplete features become functional automatically.


## 10. Current capability and verification status — 2026-10-13

Media job create/read/retry/progress/output and provider-dispatch routes return typed `501` in every environment until a tenant-scoped durable repository, queue/worker, and artifact-completion path are implemented. The provider catalog's `configured` flag means only that deployment credentials exist; it does **not** mean processing is available. The legacy media job-record helper also fails closed. Raw-input deletion is a separate path and must continue to require durable audit and a successful signed storage DELETE.

All 17 Client Portal client/report/template/schedule/share-link routes return typed JSON `501`; no sample metrics, generated reports, or HTML success should be reintroduced as a substitute for durable customer data and verified analytics.

The latest full local FastAPI suite passed `7,125` tests with `26` skipped and `78.85%` source-only coverage (the repository gate remains `39%`). This is not a production deployment test. Production NO-GO blockers include global tenant/RLS proof, durable distributed work and remaining feature implementation, live Auth0/DB/Redis/Celery/storage/provider verification, AWS/Kubernetes deployment and network policy, backup/restore/chaos, authenticated DAST, and representative load evidence. No Kubernetes/Helm/Terraform/EKS manifest was found in the tracked repository inventory, and no Docker image or cloud deployment was built in this verification. Do not claim `10,000` concurrent users, complete product functionality, SOC 2/ISO 27001 certification, or absolute security. See `../docs/BACKEND-MODULARIZATION-VALIDATION-2026-10-10.md` and `../docs/BACKEND-SECURITY-READINESS-2026-10-09.md` for evidence and release gates.
