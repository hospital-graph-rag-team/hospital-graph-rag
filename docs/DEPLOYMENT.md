# ClinicalGraph 2.0 — Cloud Deployment Guide

This guide covers deploying **ClinicalGraph 2.0** cleanly across **Render** (FastAPI backend) and **Vercel** (Next.js frontend), connected to your existing **Neo4j AuraDB** and **Groq** cloud services.

---

## Why the Previous Vercel Deployment Failed (`PYTHON_ENTRYPOINT_NOT_FOUND`)

The original repository placed a Streamlit Python app at the root without a Next.js workspace. When Vercel connected to the repository root, it detected `requirements.txt` and attempted to build a Python serverless function, failing with `PYTHON_ENTRYPOINT_NOT_FOUND`.

**How ClinicalGraph 2.0 fixes this:**
- The Next.js frontend lives strictly inside `apps/web/` (pure Node.js / TypeScript, zero Python files).
- Vercel is configured with **Root Directory = `apps/web`** and **Framework Preset = Next.js**.
- The Python FastAPI backend runs independently on **Render** from the repository root so it can import `src/` and access Neo4j AuraDB and Groq securely.
- The Next.js server-side Route Handlers (`apps/web/app/api/*`) act as a secure server-to-server proxy using `BACKEND_URL` and `BACKEND_API_TOKEN`, so credentials never touch the browser.

---

## Step 1: Deploy the FastAPI Backend on Render

1. Sign in to [Render](https://render.com) and click **New +** → **Web Service** (or **Blueprint** using `render.yaml`).
2. Connect the GitHub repository: `hospital-graph-rag-team/hospital-graph-rag`.
3. Configure these exact settings:
   - **Service Type:** Web Service
   - **Branch:** `feat/clinicalgraph-v2` (for initial testing; later `main` after merge)
   - **Root Directory:** *(leave blank — repository root)*
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path:** `/health`
   - **Instance Type:** Free (for academic demonstration)
4. Add the following **Environment Variables** in Render:

| Variable | Value / Placeholder | Notes |
| --- | --- | --- |
| `PYTHON_VERSION` | `3.12.10` | Matches local `.venv` Python 3.12 |
| `ENVIRONMENT` | `production` | Enables fail-closed backend token enforcement |
| `NEO4J_URI` | `neo4j+s://<instance>.databases.neo4j.io` | Existing Neo4j AuraDB URI |
| `NEO4J_USERNAME` | `<your-neo4j-username>` | Existing AuraDB username |
| `NEO4J_PASSWORD` | `<your-neo4j-password>` | Existing AuraDB password |
| `GROQ_API_KEY` | `<your-groq-api-key>` | Existing Groq API key |
| `BACKEND_API_TOKEN` | `<generate-long-random-hex-token>` | Shared secret between Vercel & Render (e.g., `openssl rand -hex 32`) |
| `CORS_ORIGINS` | `https://<your-vercel-domain>.vercel.app` | Comma-separated allowed frontend origins |
| `CHAT_RATE_LIMIT_PER_MINUTE` | `20` | Protects Groq quota |
| `API_RATE_LIMIT_PER_MINUTE` | `180` | Protects Neo4j read endpoints |

5. Deploy and verify `https://<your-render-service>.onrender.com/health` returns `"status": "ok"` and `"neo4j_connected": true`.

### Render Free-Tier Limitations
- Render free web services spin down after **15 minutes of inactivity**. The first request after idle sleep can take **30–50 seconds** (cold start).
- The Next.js proxy routes use 25s (GET) and 50s (POST `/api/chat`) timeouts and display a clear retry prompt if a cold start exceeds the timeout.

---

## Step 2: Deploy the Next.js Frontend on Vercel

1. Sign in to [Vercel](https://vercel.com) and click **Add New...** → **Project**.
2. Import `hospital-graph-rag-team/hospital-graph-rag`.
   > **Organization Repository Note:** Vercel's Hobby (free) plan restricts importing repositories owned by GitHub Organizations. If your repository is under a GitHub Organization (`hospital-graph-rag-team`), you will either need Vercel Pro team access, deploy via a personal GitHub fork connected to your Hobby account, or deploy via the Vercel CLI (`vercel --prod` / `vercel` preview from `apps/web`) where permitted. Do not make a private repository public without team approval.
3. Configure these exact settings:
   - **Framework Preset:** `Next.js`
   - **Root Directory:** `apps/web`
   - **Install Command:** `npm install` (default)
   - **Build Command:** `npm run build` (default)
   - **Output Directory:** `.next` (Next.js default)
   - **Deployment Branch:** `feat/clinicalgraph-v2` (preview deployment first)
4. Add these **Server-Side Environment Variables** in Vercel (do **NOT** prefix any with `NEXT_PUBLIC_`):

| Variable | Value / Placeholder | Notes |
| --- | --- | --- |
| `BACKEND_URL` | `https://<your-render-service>.onrender.com` | HTTPS URL of your Render FastAPI service |
| `BACKEND_API_TOKEN` | `<exact-same-token-as-render>` | Must match Render `BACKEND_API_TOKEN` |
| `DEMO_ACCESS_CODE` | `<optional-passcode>` | Optional lightweight UI gate for public preview links |

5. Trigger a **Preview Deployment** and verify:
   - `/` (Overview Dashboard) loads live Neo4j stats (50 patients, 10 doctors, 146 visits, 364 nodes, 826 relationships).
   - Direct refresh on `/patients`, `/graph`, `/assistant`, and `/analytics` works cleanly without 404s.
   - Browser DevTools Network tab calls `/api/...` on the Vercel origin (zero `localhost` URLs, zero exposed secrets).

---

## Step 3: Post-Deploy Checklist & Troubleshooting

- **401 Unauthorized on `/api/*`:** Verify `BACKEND_API_TOKEN` matches identically between Render and Vercel.
- **503 Backend authentication is not configured:** `ENVIRONMENT=production` requires `BACKEND_API_TOKEN` to be set on Render.
- **502 / 504 Timeout on first load:** Render free tier is waking up; wait 15–30 seconds and click **Retry**.
- **CORS Error:** Only browser-to-Render direct calls would hit CORS (the Next.js server proxy avoids CORS for normal usage), but ensure `CORS_ORIGINS` includes your exact Vercel preview/production HTTPS origin.
