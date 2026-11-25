# ClinicalGraph 2.0 — Vercel-Only Free Deployment Guide

This guide explains how to deploy **all of ClinicalGraph 2.0** on **Vercel Hobby (free tier)** using **two separate Vercel projects** connected to your existing **Neo4j AuraDB** and **Groq** cloud services:

1. **ClinicalGraph API (`clinicalgraph-api`):** Python FastAPI backend deployed from the repository root (`pyproject.toml` `[tool.vercel] entrypoint = "backend.main:app"`).
2. **ClinicalGraph Web (`clinicalgraph-web`):** Next.js 15 App Router frontend deployed from `apps/web`.

> **Optional Render Fallback:** [render.yaml](../render.yaml) is retained in the repository as an optional fallback if you later decide to host the Python API on Render instead of Vercel.

---

## Why the Previous Vercel Deployment Failed (`PYTHON_ENTRYPOINT_NOT_FOUND`)

The original repository placed a Streamlit Python app at the root without a Next.js workspace or a `pyproject.toml` entrypoint. When Vercel connected to the repository root, it detected `requirements.txt` and attempted to build a Python serverless function, failing with `PYTHON_ENTRYPOINT_NOT_FOUND`.

**How ClinicalGraph 2.0 resolves this cleanly across two Vercel projects:**
- **Backend project (Root Directory = `.`):** [pyproject.toml](../pyproject.toml) declares `[tool.vercel] entrypoint = "backend.main:app"` and specifies lean FastAPI/Neo4j/OpenAI dependencies (excluding `streamlit`, `plotly`, `pandas`, `numpy`, and `pytest`). Root [.vercelignore](../.vercelignore) excludes `apps/`, `frontend/`, `tests/`, `data/`, `docs/`, and `.venv/` so the Python serverless bundle stays compact.
- **Frontend project (Root Directory = `apps/web`):** Vercel detects `apps/web/package.json` (`next`) cleanly with zero Python files inside `apps/web/`. [apps/web/.vercelignore](../apps/web/.vercelignore) overrides root `.vercelignore` for the frontend project.
- **Server-to-Server Auth:** Next.js Route Handlers (`apps/web/app/api/*`) forward requests over HTTPS to `BACKEND_URL` with `X-Backend-Token: <BACKEND_API_TOKEN>`. No credentials ever reach the browser.

---

## Architecture Overview

```text
Browser ──HTTPS──▶ Vercel Project 2: clinicalgraph-web (apps/web, Next.js 15)
                        │  Server-side Route Handlers (/api/*)
                        │  Injects X-Backend-Token + enforces DEMO_ACCESS_CODE
                        ▼  HTTPS
                   Vercel Project 1: clinicalgraph-api (root, FastAPI + Fluid Compute)
                        │  Reuses src/graph/retrieval.py & src/rag/engine.py
                        ▼
              Neo4j AuraDB  +  Groq API (openai/gpt-oss-120b)
```

---

## Private GitHub Organization Compatibility (Important)

The repository `hospital-graph-rag-team/hospital-graph-rag` is a **private repository owned by a GitHub Organization**.

On **Vercel Hobby (free)**:
- **Git Integration Restriction:** Vercel Hobby does **not** support connecting or importing private repositories owned by GitHub Organizations directly in the Vercel Dashboard.
- **CLI Deployment (`vercel` CLI):** You can deploy from your local working directory using the Vercel CLI under your personal Hobby account **if** the commit author matches your personal Vercel Hobby account email (`Abel Alexander <abelalexander84@gmail.com>`) and your account/CLI link is permitted without connecting the GitHub Organization integration.
- **If CLI deployment is still blocked by organization repository checks on your account:** Do **not** make the private repository public, purchase Vercel Pro, or create unauthorized mirrors. The legitimate no-cost alternatives are:
  1. Transferring/hosting the project under a personal GitHub repository owned by the Hobby account owner (with team permission), or
  2. Deploying via an authorized team member's Vercel Pro account if available.

---

## Step 1: Deploy Backend Project (`clinicalgraph-api`) via Vercel CLI

Run from the **repository root**:

```bash
# 1. Install and authenticate Vercel CLI (one-time)
npm i -g vercel
vercel login

# 2. Link this root directory to a new Vercel project (do NOT link to apps/web)
#    When prompted:
#      Set up and deploy? N (configure env vars first)
#      Which scope? Your personal Hobby account
#      Link to existing project? N
#      Project name: clinicalgraph-api
#      Directory in which your code is located: ./
vercel link

# 3. Set server-side environment variables (Production & Preview)
vercel env add NEO4J_URI production
vercel env add NEO4J_USERNAME production
vercel env add NEO4J_PASSWORD production
vercel env add GROQ_API_KEY production
vercel env add BACKEND_API_TOKEN production
vercel env add ENVIRONMENT production        # enter: production
vercel env add CORS_ORIGINS production       # enter: https://<your-frontend-domain>.vercel.app

# 4. Deploy preview first, then production once verified
vercel
# After testing preview URL:
vercel --prod
```

Verify the backend health endpoint:
```bash
curl https://<your-api-domain>.vercel.app/health
```
Expected response: `"status": "ok"`, `"neo4j_connected": true`, `"groq_configured": true`, `"auth_enabled": true`.

---

## Step 2: Deploy Frontend Project (`clinicalgraph-web`) via Vercel CLI

Run inside **`apps/web`** (keep this completely separate from the root `.vercel` link):

```bash
cd apps/web

# 1. Link apps/web as a second Vercel project
#    Project name: clinicalgraph-web
#    Directory in which your code is located: ./
#    Framework Preset: Next.js (auto-detected)
vercel link

# 2. Set server-side environment variables (NEVER prefix with NEXT_PUBLIC_)
vercel env add BACKEND_URL production         # https://<your-api-domain>.vercel.app
vercel env add BACKEND_API_TOKEN production   # exact same token set on clinicalgraph-api
vercel env add DEMO_ACCESS_CODE production    # recommended demo passcode

# 3. Deploy preview first, then production
vercel
# After testing preview URL:
vercel --prod
```

*(Note: After `clinicalgraph-web` gets its final HTTPS URL, update `CORS_ORIGINS` on `clinicalgraph-api` if needed and redeploy `clinicalgraph-api`.)*

---

## Step 3: Exact Project & Environment Variable Reference

### Project 1 — `clinicalgraph-api` (FastAPI Backend)
- **Root Directory:** `.` (repository root)
- **Entrypoint:** `backend.main:app` (declared in [pyproject.toml](../pyproject.toml))
- **Python Runtime:** `3.12` (`requires-python = ">=3.12,<3.13"`)
- **Dependencies Source:** `pyproject.toml` (lean API runtime; excludes Streamlit/Plotly/Pandas/Pytest)
- **Excluded via `.vercelignore`:** `apps/`, `frontend/`, `tests/`, `data/`, `docs/`, `scratch/`, `.venv/`, `src/data_generation/`

| Environment Variable | Required | Description |
| --- | --- | --- |
| `NEO4J_URI` | Yes | Existing Neo4j AuraDB connection URI |
| `NEO4J_USERNAME` | Yes | Neo4j AuraDB username |
| `NEO4J_PASSWORD` | Yes | Neo4j AuraDB password |
| `GROQ_API_KEY` | Yes | Groq API key for `openai/gpt-oss-120b` |
| `BACKEND_API_TOKEN` | Yes (Prod) | Shared secret required via `X-Backend-Token` header; production fails closed (`503`) if omitted |
| `ENVIRONMENT` | Recommended | Set to `production` (also auto-detected via `VERCEL_ENV=production`) |
| `CORS_ORIGINS` | Recommended | Comma-separated allowed frontend HTTPS origin(s) |
| `CHAT_RATE_LIMIT_PER_MINUTE` | Optional | Default `20` (per serverless isolate) |
| `API_RATE_LIMIT_PER_MINUTE` | Optional | Default `180` (per serverless isolate) |

### Project 2 — `clinicalgraph-web` (Next.js Frontend)
- **Framework Preset:** `Next.js`
- **Root Directory:** `apps/web`
- **Install / Build / Output:** `npm install` / `npm run build` / `.next` (defaults)
- **Chat Route Timeout:** `export const maxDuration = 60;` in [apps/web/app/api/chat/route.ts](../apps/web/app/api/chat/route.ts)

| Environment Variable | Required | Description |
| --- | --- | --- |
| `BACKEND_URL` | Yes | HTTPS URL of the deployed `clinicalgraph-api` Vercel project |
| `BACKEND_API_TOKEN` | Yes | Exact matching shared secret forwarded server-side |
| `DEMO_ACCESS_CODE` | Recommended | Enables the UI passcode modal + HttpOnly `cg_demo_access` cookie on all `/api/*` data/AI routes |

---

## Step 4: Vercel Hobby & Serverless Limitations

1. **Per-Instance In-Memory Rate Limiting:** `api_rate_limiter` and `chat_rate_limiter` in [backend/security.py](../backend/security.py) store sliding-window timestamps in memory per warm serverless isolate. Under concurrent scaling across multiple isolates, limits are enforced per instance rather than globally. Keep `DEMO_ACCESS_CODE` enabled on public previews to guard Groq quota without paid Redis.
2. **Fluid Compute & Timeouts:** Vercel Fluid Compute supports up to 300s duration and 2 GB memory on Hobby. `/api/chat` explicitly sets `maxDuration = 60` with a 50s proxy timeout and 45s backend `asyncio.wait_for` timeout so slow Groq calls fail cleanly rather than hanging.
3. **Cold Starts & Warm Neo4j Drivers:** Cold starts instantiate the Neo4j driver lazily on first request. If an idle warm isolate encounters a stale Neo4j socket, `check_neo4j_connectivity` resets the driver cleanly for the next request.
4. **Hobby Usage Quotas:** Subject to Vercel Hobby monthly bandwidth, Active CPU, and invocation caps (suitable for academic demos, not high-traffic production workloads).

---

## Step 5: Verification & Troubleshooting

- **Unauthorized / `401` on `/api/patients` or `/api/chat`:** Expected when `DEMO_ACCESS_CODE` is set and the `cg_demo_access` cookie is missing, or when `BACKEND_API_TOKEN` differs between the two Vercel projects.
- **`503` from backend:** `ENVIRONMENT=production` (or `VERCEL_ENV=production`) is active without `BACKEND_API_TOKEN` configured.
- **`504` Timeout on AI Assistant:** Retrying once usually succeeds after a cold start; check Groq quota if persistent.
- **Optional Render Fallback:** If you prefer deploying the backend on Render in the future, [render.yaml](../render.yaml) remains ready with `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`.
