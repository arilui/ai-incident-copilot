# AI Incident CoPilot

A full-stack tool that analyzes CI/CD pipeline logs, identifies likely failures, classifies severity, and drafts a postmortem.

It uses a **hybrid, cost-aware design**: deterministic rules handle common, recognizable failures for free, and a language model is called only for logs that are complex, ambiguous, large, or high-risk.

**Live demo:** _add your Vercel URL here_

---

## How It Works

```text
Pipeline logs
     ↓
Extract error lines + detect pipeline stage (rules)
     ↓
Routing: is this log complex?
  (tracebacks, production, infra keywords, >2,500 chars, ≥4 errors, unknown stage)
     ↓                                   ↓
   No → rule-based analysis           Yes → GPT-4.1-mini with a strict JSON schema
        (free, instant)                       ↓
                                       On API failure or rate limit → rule-based fallback
     ↓
Severity, stage, top errors, suggested fix, postmortem
```

Every response reports which path was used (`analysis_mode`) and why (`ai_reason`), so the routing decision is visible in the UI.

### Design decisions

- **Rules first.** Most CI failures (a missing module, a failed test, a bad API key) match known patterns. Handling them without an LLM call keeps cost and latency near zero.
- **Structured output.** The model must return JSON that matches a schema, so the frontend can render it without parsing free text.
- **Graceful degradation.** If the OpenAI call fails or the per-IP AI quota is used up, the user still gets the rule-based analysis instead of an error.

---

## Tech Stack

**Frontend:** Next.js, React, TypeScript, Tailwind CSS, lucide-react

**Backend:** FastAPI, OpenAI API (`gpt-4.1-mini`, structured outputs)

---

## Running Locally

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
```

Create `backend/.env` (optional; without a key, every log uses rule-based analysis):

```env
OPENAI_API_KEY=your_openai_api_key
```

Start the API:

```bash
python -m uvicorn app:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The app runs at `http://localhost:3000` and calls the API at `NEXT_PUBLIC_API_URL`, which defaults to `http://127.0.0.1:8000`.

---

## Deploying to Vercel

The backend and frontend deploy as two Vercel projects from this one repository.

1. **Backend project.** Import this repo in Vercel, set **Root Directory** to `backend`, and add these environment variables:
   - `OPENAI_API_KEY`
   - `ALLOWED_ORIGINS`: the frontend URL, for example `https://ai-incident-copilot.vercel.app`
2. **Frontend project.** Import the repo again, set **Root Directory** to `frontend`, and add:
   - `NEXT_PUBLIC_API_URL`: the backend URL
3. **Cap spending.** Set a monthly budget limit in your OpenAI account. The per-IP AI quota (`AI_RATE_LIMIT`, default 5 calls per minute) is tracked per server instance, so the budget is the real cost cap.

Logs are limited to 200,000 characters per request.
