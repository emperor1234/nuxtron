# Nuxtron Rebuild (Modern Stack)

This repository has been migrated to a modern multi-service architecture:

- Frontend: Next.js 16.2.4 (`frontend/`)
- Backend API + Admin: Django 6.0.4 (`backend/django/`)
- Service Layer: FastAPI (`backend/fastapi/`)
- Database: PostgreSQL

## Why this stack

- Django handles heavy backend logic, mature ORM, auth, and admin UI.
- FastAPI handles high-speed async API/microservice workloads (AI/ML-ready).
- Next.js provides a scalable, component-driven frontend for long-term growth.

## PostgreSQL-Only Policy Scope

The maintained platform is PostgreSQL-only. CI enforces this policy for the primary runtime and deployment surfaces:

- services/**
- frontend/app/**
- deploy/*.ps1, deploy/*.bat, deploy/*.sh, deploy/*.md, deploy/*.json, deploy/*.yml, deploy/*.yaml
- README.md

Intentional exclusions:

- Archived reference material under docs/archive/non-runtime-db-references/**
- Generated and vendor trees (for example frontend/.next/, frontend/node_modules/, and other ignored artifacts)

Policy guard:

- scripts/security/check-postgres-only.sh (executed in CI)

## Supabase + pgvector + Vault

For the recommended production architecture and schema patterns, see:

- SUPABASE_PGVECTOR_VAULT_GUIDE.md

Apply SQL migrations (including pgvector baseline) with:

```bash
npm run db:migrate:fastapi:sql
```

## Quick Start

## 1. Docker (recommended)

```bash
docker compose up --build
```

Production profile (strict, no fallback secrets):

```bash
docker compose -f docker-compose.production.yml config
docker compose -f docker-compose.production.yml -f docker-compose.production.edge.yml config
docker compose -f docker-compose.production.yml -f docker-compose.production.edge.yml up --build -d
```

The production profile intentionally requires secret/env injection and does not expose `NEXT_PUBLIC_FASTAPI_API_KEY`.

Endpoints:

- Frontend: http://localhost:3000
- Django API health: http://localhost:8000/api/health/
- Django admin: http://localhost:8000/admin/
- FastAPI health: http://localhost:8001/healthz
- Redis: localhost:6379
- Local integration mock: http://localhost:4010

The default core compose stack now also includes:

- Redis for cache-backed FastAPI bridge endpoints
- a WireMock-backed local integration mock for Twilio, Slack, and Resend URL override testing

## 2. Local without Docker

Frontend:

```bash
npm --prefix frontend install
npm run dev:frontend
```

Frontend + FastAPI (single command, stable mode):

```bash
npm install
npm run dev:local:stable
```

Frontend + FastAPI (single command, reload mode for active API development):

```bash
npm run dev:local
```

Quick local health check (frontend + FastAPI):

```bash
npm run check:local:health
```

If FastAPI port is intentionally unavailable and you only want the frontend:

```bash
npm run dev:local:stable:frontend-only
```

Django:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r backend/django/requirements.txt
python backend/django/manage.py migrate
python backend/django/manage.py runserver 0.0.0.0:8000
```

Django requires PostgreSQL 18.3. Set `POSTGRES_HOST`, `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD` before running migrations.

FastAPI:

```bash
pip install -r backend/fastapi/requirements.txt
uvicorn backend.fastapi.app.main:app --host 0.0.0.0 --port 8001 --reload --reload-dir backend/fastapi/app --reload-exclude backend/fastapi/app/*_smoke.py --reload-exclude backend/fastapi/app/selftest.py
```

If your environment is noisy with file-watcher reloads during local work, run FastAPI without reload:

```bash
npm run dev:fastapi:stable
```

FastAPI business endpoints now require:

- `X-API-Key`: must match `FASTAPI_API_KEY`
- `X-Tenant-Id`: tenant identifier for data isolation

Bridge provider overrides supported for local infrastructure testing:

- `TWILIO_API_BASE_URL`
- `SLACK_API_BASE_URL`
- `RESEND_API_BASE_URL`

When running through Docker Compose, these may point at the bundled `integration-mock` service while you supply dummy credentials for local smoke testing.

## Local Provider Mock Stack

The default compose stack includes a WireMock provider simulator on `http://localhost:4010` with canned responses for:

- Twilio SMS: `/twilio/2010-04-01/Accounts/:sid/Messages.json`
- Twilio voice: `/twilio/2010-04-01/Accounts/:sid/Calls.json`
- Slack Web API: `/slack/api/chat.postMessage`
- Slack webhook: `/slack/webhook`
- Resend email: `/resend/emails`

Useful commands:

```bash
npm run docker:mocks:config
npm run docker:mocks:up
npm run docker:mocks:down
```

## Frontend Smoke Tests

Playwright smoke coverage is available for the Dashboard and key Studio bridge actions using a local mock FastAPI server started automatically by the test runner.

```bash
npm run check:frontend:smoke
```

## SonarCloud Scan (Local)

Run SonarCloud with explicit org/project settings:

```bash
npm run scan:sonar:cloud
```

Required environment variable:

- `SONAR_TOKEN`

Optional overrides:

- `SONAR_PROJECT_KEY` (default: `nuxtron`)
- `SONAR_ORGANIZATION` (default: `nux-tron`)
- `SONAR_HOST_URL` (default: `https://sonarcloud.io`)

## SonarQube Community (Free Self-Hosted Alternative)

Bring up a local SonarQube Community + PostgreSQL stack:

```bash
npm run docker:sonarqube:config
npm run docker:sonarqube:up
```

Bootstrap first-run local setup (admin password rotation, project creation, token generation, and user-level token persistence):

```bash
npm run docker:sonarqube:bootstrap
```

If you need to display the generated token in the console, run the script directly with `-ShowToken`:

```bash
powershell -ExecutionPolicy Bypass -File deploy/bootstrap-sonarqube-local.ps1 -PersistUserEnv -ShowToken
```

Service URL:

- `http://localhost:9005`

Optional logs:

```bash
npm run docker:sonarqube:logs
```

Run a local scan against self-hosted SonarQube:

```bash
npm run scan:sonarqube:local
```

Optional environment variables:

- `SONARQUBE_TOKEN` (recommended)
- `SONARQUBE_HOST_URL` (default: `http://localhost:9005`)
- `SONARQUBE_PROJECT_KEY` (default: `nuxtron-local`)

Notes:

- The bootstrap command persists both `SONARQUBE_TOKEN` and `SONAR_TOKEN` to your user environment.
- Open a new terminal after bootstrap so the persisted variables are available.
- For security, bootstrap hides token values by default unless `-ShowToken` is provided.
- After first bootstrap rotates the admin password, reruns should provide `-CurrentPassword` (or set `SONARQUBE_ADMIN_PASSWORD`).

Stop the self-hosted stack:

```bash
npm run docker:sonarqube:down
```

## DR Drill Evidence (Local)

Generate a timestamped disaster recovery drill report artifact:

```bash
npm run dr:drill:record
```

Example with local health verification and key metadata:

```bash
powershell -ExecutionPolicy Bypass -File deploy/record-dr-drill.ps1 -CheckLocalHealth -DrillEnvironment staging -Scenario "Postgres restore rehearsal" -ChangeRef "CHG-2026-04-21"
```

Output:

- `docs/reports/disaster-recovery-drill-YYYY-MM-DD-HHMMSS.md`

## Production Preflight (Recommended Before Push)

Run a full local quality gate to catch build, API, test, and compose profile issues before opening a PR:

```bash
npm run check:platform:preflight
```

This command runs:

- release gate
- Django system checks
- FastAPI selftest
- frontend smoke tests
- compose config validation for core/mocks, OSS add-ons, PostHog, and edge security profiles

## God-Level Quality Gate (Default)

Run the unified full-stack quality gate locally:

```bash
npm run quality:god
```

Strict mode (fails on missing optional scanners/assistants and stricter environment assumptions):

```bash
npm run quality:god:strict
```

This gate is designed to cover platform depth across frontend, backend, security, quality, and testing with these tools/check families:

- SonarQube / SonarCloud
- CodeQL
- Semgrep
- Ruff
- Pyright
- Mypy
- Refurb
- Biome (optional)
- Nx checks when nx workspace is configured (optional)
- PyTest coverage gate
- Vitest
- Playwright
- Trivy
- OSV-style dependency checks (`pip-audit` + `npm audit`)
- Gitleaks
- ZAP baseline via CI workflow
- Codemod engine readiness (`jscodeshift`)
- AutoGen import readiness
- TabbyML / StarCoder2 / CodeGeeX endpoint health checks when configured

Environment variables for AI assistant endpoint checks:

- `TABBYML_HEALTH_URL`
- `STARCODER2_HEALTH_URL`
- `CODEGEEX_HEALTH_URL`

CI workflow:

- `.github/workflows/god-quality.yml`

## CI and Security Workflow Model

To avoid duplicate checks and reduce CI noise, workflows are split by purpose:

- `.github/workflows/ci.yml` is the canonical PR/push quality gate and requires `default-stack`.
- `.github/workflows/security.yml` runs scheduled/manual deep security scanning (CodeQL, Trivy, secrets).
- `.github/workflows/security-scan.yml` is manual deep DAST/IaC/license scanning only.
- `.github/workflows/platform-quality.yml` runs scheduled/manual extended quality checks.

## Production Full Gate (End-To-End)

Run the complete local production readiness gate that chains frontend, backend, database/config, Playwright, load testing (k6 when available), and SonarQube quality checks:

```bash
npm run check:production:full
```

This command runs:

- `npm run check:platform:preflight`
- `npm run check:frontend:smoke`
- `npm run check:fastapi:load` (uses `k6` automatically when installed and scripts are available)
- `npm run scan:sonarqube:local`
- unresolved SonarQube issue enforcement (`0` required)

## Scheduled Fallback Pressure Monitoring

Daily monitoring workflow is available at:

- `.github/workflows/fallback-pressure-monitor.yml`

Behavior:

- runs every day at 05:00 UTC and on manual dispatch
- executes fallback pressure guard + trend comparison
- uploads snapshot and trend report artifacts per run for historical analysis
- retains fallback monitoring artifacts for 30 days (`retention-days: 30`)

## Monthly Baseline Refresh

Monthly baseline candidate workflow:

- `.github/workflows/fallback-pressure-baseline-refresh.yml`

Behavior:

- runs on day 1 of each month at 06:00 UTC and on manual dispatch
- generates a new baseline candidate from current synthetic fallback snapshot
- uploads baseline candidate, snapshot, and trend report artifacts

Adoption process:

- review the uploaded `fallback-pressure-baseline-candidate` artifact
- if approved, replace `backend/fastapi/app/fallback_pressure_baseline.json` in a follow-up commit

### Fallback Pressure Incident Runbook

Use this runbook when fallback pressure trend warnings persist for 3 or more consecutive daily runs:

1. Confirm signal quality:
   - Inspect latest `fallback-pressure-snapshot` and `fallback-pressure-trend-report` artifacts.
   - Verify warnings are not caused by intentional baseline drift.
2. Identify stressed buffer(s):
   - Read `fallback_buffers.hot_buffers` and `fallback_buffers.utilization_ratio` from `/ops/platform/status`.
   - Correlate with provider config status in `integrations` to detect dependency outages.
3. Mitigate quickly:
   - Restore external provider credentials/connectivity (Redis, Meilisearch, Twilio, Slack, Resend, Algolia).
   - Temporarily reduce fallback load by throttling non-critical jobs.
4. Stabilize baseline governance:
   - If behavior is the new accepted normal, review monthly baseline candidate artifacts.
   - Open a follow-up PR to update `backend/fastapi/app/fallback_pressure_baseline.json` only after review.
5. Close incident:
   - Ensure daily monitor returns to stable trend output.
   - Link incident notes in the PR that made the mitigation/baseline decision.

Security additions now implemented:

- Bcrypt + salt default password hashing (`PASSWORD_HASH_ALGO=bcrypt`)
- Argon2id alternative (`PASSWORD_HASH_ALGO=argon2id`)
- Pepper support from environment or Vault
- Application-Level Encryption (ALE) for sensitive social content fields
- Supabase-ready RLS SQL policies for multi-tenant isolation
- HashiCorp Vault integration for pepper/encryption-key retrieval
- Rate-limit protection on sensitive FastAPI security/email endpoints

Studio UI:

- http://localhost:3000/studio
- Uses `NEXT_PUBLIC_FASTAPI_URL`, `NEXT_PUBLIC_FASTAPI_API_KEY`, and `NEXT_PUBLIC_DEFAULT_TENANT_ID`

Social scheduler persistence:

- Uses PostgreSQL table `social_scheduled_posts` when DB is configured
- Falls back to in-memory storage only if DB is unavailable in local/dev environments

## Secure SendGrid-like Stack

Additional secure stack compose template is included in:

- `docker-compose.secure-stack.yml`

It includes:

- `listmonk` as campaign/email engine
- `postal` as SMTP delivery layer
- dedicated PostgreSQL instance for secure email services
- `clamav` antivirus daemon

Commands:

```bash
npm run docker:secure:up
npm run docker:secure:down
```

## OSS Add-ons Stack (Free/Open Source)

Optional OSS bundle for rapid expansion:

- `docker-compose.oss-addons.yml`

Commands:

```bash
npm run docker:oss:config
npm run docker:oss:up
npm run docker:oss:down
```

Included in this add-ons stack:

- Listmonk
- Truemail
- CrowdSec
- Netdata
- Keycloak
- Authelia
- n8n
- GrowthBook
- Strapi
- Directus
- Meilisearch
- OpenSearch
- PostGraphile
- Drone CI + Drone runner
- Rasa
- MLflow
- Apache Airflow
- Apache Superset
- Plausible
- Matomo
- ToolJet
- Budibase
- PocketBase

Full status matrix (wired vs cataloged):

- `deploy/oss/stack-catalog.json`

## Open-Source AI Generation Stack (Image + Video + Voice + Text)

Dedicated AI model stack compose profile:

- `docker-compose.ai-open-source.yml`

Commands:

```bash
npm run docker:ai:config
npm run docker:ai:up
npm run docker:ai:pull-models
npm run docker:ai:down
```

Included runtime coverage:

- Image: SDXL, ControlNet, Real-ESRGAN, GFPGAN, LaMa, SAM (via ComfyUI workflows/models)
- Video: Stable Video Diffusion + FFmpeg-based pipeline support (RIFE/FILM via workflow nodes)
- Voice: Whisper V3/WhisperX + OpenVoice/Bark/RVC worker endpoints for local TTS routing
- Text: Llama 3, Mixtral, Qwen 2, Phi-3 (via Ollama)

More details:

- `deploy/ai/README.md`

Clarity analytics:

- Microsoft Clarity auto-loads when `NEXT_PUBLIC_CLARITY_PROJECT_ID` is set.

## PostHog Self-Host Profile

Dedicated PostHog compose profile:

- `docker-compose.posthog.yml`

Commands:

```bash
npm run docker:posthog:config
npm run docker:posthog:up
npm run docker:posthog:down
```

This profile brings up:

- PostHog app
- Postgres
- Redis

Note: the optional PostHog compose profile currently runs in PostgreSQL-only mode for this repo.

## Edge Security Stack (ModSecurity + Let's Encrypt)

Edge stack template:

- `docker-compose.edge-security.yml`

Commands:

```bash
npm run docker:edge:config
npm run docker:edge:up
npm run docker:edge:down
```

This profile includes:

- Nginx + OWASP ModSecurity CRS WAF container
- Certbot for Let's Encrypt certificate bootstrap

Config files:

- `deploy/security/nginx/default.conf`
- `deploy/security/nginx/modsecurity.conf`

## CRM / Affiliate Bridge APIs

FastAPI now includes bridge endpoints:

- `POST /integrations/suitecrm/upsert-lead`
- `POST /integrations/refferq/register-referral`

Behavior:

- Attempts provider delivery when integration env vars are configured.
- Falls back to queued mode if provider credentials are absent/unreachable.

## Analytics Event Bridge API

FastAPI includes a PostHog bridge endpoint:

- `POST /analytics/posthog/capture`
- `POST /analytics/matomo/track`
- `POST /analytics/plausible/track`

Behavior:

- Attempts direct capture to PostHog when `POSTHOG_URL` and `POSTHOG_PROJECT_API_KEY` are configured.
- Falls back to queued mode if PostHog is unconfigured/unreachable.
- Attempts Matomo track calls when `MATOMO_URL` and `MATOMO_SITE_ID` are configured.
- Attempts Plausible event calls when `PLAUSIBLE_API_URL` and `PLAUSIBLE_SITE_DOMAIN` are configured.
- All analytics bridges safely queue on provider failure/unavailability.

## Automation + Feature Flag APIs

FastAPI now includes platform orchestration endpoints:

- `POST /integrations/n8n/trigger-webhook`
- `POST /flags/growthbook/evaluate`
- `GET /ops/platform/status`
- `GET /ops/platform/metrics-summary`

Behavior:

- n8n trigger attempts webhook delivery when `N8N_WEBHOOK_URL` is configured, otherwise queues safely.
- GrowthBook evaluation attempts API fetch via `GROWTHBOOK_API_URL` and `GROWTHBOOK_CLIENT_KEY`, with deterministic local fallback when unavailable.
- Ops status returns tenant-scoped integration readiness and queue telemetry.
- Metrics summary exposes tenant-scoped queue totals and in-memory rate limiter telemetry.

## Supabase Security SQL

Run these in Supabase SQL editor:

- `sql/supabase-rls.sql`
- `sql/supabase-secure-sendgrid-stack.sql`
- `sql/fastapi-email-module.sql`

These scripts include:

- RLS tenant isolation policies (contacts, campaigns, API keys, analytics)
- pgsodium extension baseline
- Supabase Vault secret examples

Email module behavior:

- `/email/campaigns/{id}/send-test` attempts provider delivery through Listmonk, Postal, or SES SMTP when configured.
- If provider credentials are missing/unavailable in local/dev, it safely falls back to queued mode.

## Linux Security Tooling

Linux hardening/audit script is provided:

- `deploy/security/linux-hardening-audit.sh`

Tools covered by the script:

- ClamAV
- Linux Malware Detect (Maldet/LMD)
- Rkhunter
- Chkrootkit
- Lynis
- Fail2ban

Run on Linux host as root:

```bash
sudo bash deploy/security/linux-hardening-audit.sh
```

## Migration Note

Previous runtime artifacts from the pre-migration architecture have been removed.
The repository now runs on Next.js, Django, FastAPI, and PostgreSQL.

## IRA Auto-Update Flow

IRA can now manage sandbox-first updates through `deploy/ira-update-manager.ps1`.

Behavior:

- Checks the configured Git branch for upstream updates.
- Creates or refreshes a dedicated sandbox worktree.
- Runs the release gate in sandbox first.
- Promotes to the main platform only if sandbox validation passes.
- Runs the release gate again after promotion.
- Reverts to the previous Git revision automatically if promotion validation fails.
- Writes an audit log to `deploy/ira-update.log` and state to `deploy/ira-update-state.json`.

Commands:

```bash
npm run ira:update:check
npm run ira:update:run
npm run ira:update:watch
npm run ira:update:register
```

Configuration lives in `deploy/ira-update-config.json`.

For a 24/7 Windows host, `npm run ira:update:register` installs a scheduled task that starts the IRA watch loop automatically at logon.

---

## 📚 Production-Grade Release & Deployment Documentation

Complete production-ready release management with machine-enforced gates, operational runbooks, and developer guides.

### Quick Navigation

**For Developers** 👨‍💻  
[**DEVELOPER_QUICKSTART.md**](DEVELOPER_QUICKSTART.md) - 60-second workflow: feature branch → PR → merge → deploy

**For DevOps / Release Managers** 🚀  
[**PRODUCTION_RELEASE_RUNBOOK.md**](PRODUCTION_RELEASE_RUNBOOK.md) - Phase-by-phase procedures, checklists, and emergency procedures

**For Architects / Technical Leads** 🏗️  
[**PRODUCTION_ARCHITECTURE_SUMMARY.md**](PRODUCTION_ARCHITECTURE_SUMMARY.md) - Complete system architecture, component stack, and operational guarantees

**For Navigation** 🗺️  
[**PRODUCTION_DOCUMENTATION_INDEX.md**](PRODUCTION_DOCUMENTATION_INDEX.md) - Full index of all documentation and setup instructions

**⚠️ Important: Feature Parity Audit** 📋  
[**HOOTSUITE_FEATURE_PARITY_AUDIT.md**](HOOTSUITE_FEATURE_PARITY_AUDIT.md) - Honest assessment of implemented features vs Hootsuite requirements

**✅ Latest Hootsuite Verification Artifacts**
- [**HOOTSUITE_E2E_STATUS_CHART_2026-05-24.md**](HOOTSUITE_E2E_STATUS_CHART_2026-05-24.md) - Backend slice status chart and end-to-end verification summary
- [**HOOTSUITE_FRONTEND_E2E_STATUS_CHART_2026-05-24.md**](HOOTSUITE_FRONTEND_E2E_STATUS_CHART_2026-05-24.md) - Frontend parity status chart for Hootsuite command center pages
- [**docs/reports/hootsuite_e2e_verification_20260524.json**](docs/reports/hootsuite_e2e_verification_20260524.json) - Machine-readable backend verification evidence
- [**docs/reports/hootsuite_frontend_parity_20260524.json**](docs/reports/hootsuite_frontend_parity_20260524.json) - Machine-readable frontend parity verification evidence

### Key Features

#### Smart Inbox - Production-Grade Delivery
- ✅ DLQ with retry/backoff (configurable via env vars)
- ✅ Replay-pending history with per-operator metrics
- ✅ Performance analytics with p50/p95 latency tracking
- ✅ Anomaly detection (6 types, environment-tunable thresholds)
- ✅ Runbook catalog (mapped to alert codes)
- ✅ Go-live gate endpoint

See: [backend/fastapi/app/routers/smart_inbox.py](backend/fastapi/app/routers/smart_inbox.py)

#### Social Media - Vendor Governance
- ✅ Credential rotation (atomic with audit trail)
- ✅ Credential revocation (immediate disconnect)
- ✅ Credential status (real-time metadata)
- ✅ Contract matrix (per-platform readiness)
- ✅ Live-check gating (optional real-time validation)
- ✅ Unified platform go-live gate

See: [backend/fastapi/app/routers/social_media_router.py](backend/fastapi/app/routers/social_media_router.py)

#### CI/CD Automation
- ✅ Local gate validation script
- ✅ Staging environment gate workflow
- ✅ Release promotion gate (master gate with all checks)
- ✅ Branch protection enforcement (programmatic setup + automation)
- ✅ Fail-closed verdict artifact

See: [.github/workflows/release-promotion-gate.yml](.github/workflows/release-promotion-gate.yml), [scripts/ci/check_go_live_gate.py](scripts/ci/check_go_live_gate.py)

#### Branch Protection & Enforcement
- ✅ Mandatory release gate (promotion-verdict required)
- ✅ Required PR reviews (1+ approval)
- ✅ Mandatory branch freshness checks
- ✅ Admin bypass disabled (even admins cannot force-merge)
- ✅ Programmatic setup and verification

See: [.github/branch-protection-rules.md](.github/branch-protection-rules.md), [scripts/ci/enforce_branch_protection.py](scripts/ci/enforce_branch_protection.py)

### Operational Guarantees

```
✅ No production release without passing release gate
✅ No merge without peer review (1+ approval required)
✅ No merge with outdated branch (must be current with main)
✅ No admin bypass (enforce_admins: true prevents workarounds)
✅ No force pushes (linear history maintained)
✅ No message loss (Smart Inbox DLQ persists indefinitely)
✅ No vendor downtime (unified gate checks all platforms)
✅ Full audit trail (all decisions logged in artifacts)
```

### Complete Release Flow

```
Feature branch → Commit → Push PR
    ↓
GitHub Actions (parallel):
  • staging-go-live-gate (deployed environment validation)
  • smart-inbox-reliability (DLQ/replay/metrics tests)
  • social-governance (credential/contract tests)
  • promotion-verdict (aggregates results, master gate)
    ↓
All 4 gates must pass ✅
    ↓
Code review: 1+ approval required
    ↓
Merge to main (branch protection enforces all checks)
    ↓
Production deployment → Health checks → Done! 🎉
```

### Setup Instructions

**For Developers**:
1. Read [DEVELOPER_QUICKSTART.md](DEVELOPER_QUICKSTART.md) (5 min)
2. Create a test PR and watch gates run
3. Done!

**For DevOps**:
1. Run branch protection setup:
   ```bash
   python scripts/ci/enforce_branch_protection.py \
     --owner nux-tron \
     --repo nuxtron \
     --token $GITHUB_TOKEN
   ```
2. Verify configuration
3. Follow [PRODUCTION_RELEASE_RUNBOOK.md](PRODUCTION_RELEASE_RUNBOOK.md)

**For Operations**:
1. Configure monitoring dashboards for:
   - Smart Inbox metrics: `/inbox/delivery-failures/metrics`
   - Social vendor governance: `/social/ops/go-live-gate`
2. Set up alerting for anomaly thresholds
3. Create runbooks from [PRODUCTION_RELEASE_RUNBOOK.md](PRODUCTION_RELEASE_RUNBOOK.md)

### Test Coverage

- ✅ Smart Inbox test suite: 6/6 tests passing
- ✅ Social media test suite: 5/5 tests passing
- ✅ CI/CD validation: Local + staging + release gates verified
- ✅ Branch protection: Script and automation tested

### Related Files

- Documentation: [PRODUCTION_DOCUMENTATION_INDEX.md](PRODUCTION_DOCUMENTATION_INDEX.md)
- Session summary: [SESSION_COMPLETE_BRANCH_PROTECTION_PHASE.md](SESSION_COMPLETE_BRANCH_PROTECTION_PHASE.md)
- Implementation details: [PRODUCTION_ARCHITECTURE_SUMMARY.md](PRODUCTION_ARCHITECTURE_SUMMARY.md)
