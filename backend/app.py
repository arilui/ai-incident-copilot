from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import re

app = FastAPI(title="AI Incident Copilot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class LogRequest(BaseModel):
    logs: str

@app.get("/")
def root():
    return {"message": "AI Incident Copilot API is running"}

@app.post("/analyze")
def analyze_logs(request: LogRequest):
    logs = request.logs

    errors = re.findall(r".*(error|failed|failure|exception|traceback).*", logs, re.IGNORECASE)

    severity = "low"
    if len(errors) >= 5:
        severity = "high"
    elif len(errors) >= 2:
        severity = "medium"

    likely_stage = "unknown"
    lower_logs = logs.lower()

    if "npm" in lower_logs or "node_modules" in lower_logs:
        likely_stage = "frontend build"
    elif "pytest" in lower_logs or "test failed" in lower_logs:
        likely_stage = "testing"
    elif "docker" in lower_logs:
        likely_stage = "containerization"
    elif "deploy" in lower_logs:
        likely_stage = "deployment"

    return {
        "summary": "The pipeline appears to have failed due to one or more errors in the logs.",
        "severity": severity,
        "likely_stage": likely_stage,
        "error_count": len(errors),
        "top_errors": errors[:5],
        "suggested_fix": "Review the top error messages, reproduce locally, and verify dependencies, environment variables, and build commands.",
        "postmortem": {
            "title": f"{likely_stage.title()} Failure",
            "impact": "Build or deployment was blocked.",
            "root_cause": errors[0] if errors else "Root cause could not be determined from logs.",
            "resolution": "Fix the failing command or configuration, then rerun the pipeline.",
            "prevention": "Add clearer CI checks, dependency validation, and automated alerts."
        }
    }