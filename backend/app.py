from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI
import os
import re
import json

load_dotenv()

app = FastAPI(title="AI Incident Copilot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None


class LogRequest(BaseModel):
    logs: str


def extract_errors(logs: str):
    error_lines = []

    for line in logs.splitlines():
        lower = line.lower()

        if any(
            keyword in lower
            for keyword in [
                "error",
                "failed",
                "failure",
                "exception",
                "traceback",
                "fatal",
                "timeout",
                "unauthorized",
                "permission denied",
            ]
        ):
            error_lines.append(line.strip())

    return error_lines


def detect_stage(logs: str):
    lower_logs = logs.lower()

    if "npm" in lower_logs or "next build" in lower_logs or "node_modules" in lower_logs:
        return "frontend build"

    if "pytest" in lower_logs or "test failed" in lower_logs:
        return "testing"

    if "docker" in lower_logs or "image build" in lower_logs:
        return "containerization"

    if "deploy" in lower_logs or "deployment" in lower_logs:
        return "deployment"

    if "database" in lower_logs or "migration" in lower_logs:
        return "database"

    if (
        "auth" in lower_logs
        or "unauthorized" in lower_logs
        or "api key" in lower_logs
    ):
        return "authentication/configuration"

    return "unknown"


def estimate_severity(errors, logs: str):
    lower_logs = logs.lower()

    if (
        "production" in lower_logs
        and ("deployment aborted" in lower_logs or "outage" in lower_logs)
    ):
        return "critical"

    if len(errors) >= 5:
        return "high"

    if len(errors) >= 2:
        return "medium"

    return "low"


def should_use_ai(logs: str, errors, likely_stage: str):
    lower_logs = logs.lower()
    log_length = len(logs)

    if not client:
        return False

    if len(errors) == 0:
        return False

    complex_keywords = [
        "traceback",
        "exception",
        "timeout",
        "unauthorized",
        "permission denied",
        "database",
        "migration",
        "kubernetes",
        "helm",
        "terraform",
        "production",
        "rollback",
        "multi-service",
        "rate limit",
        "memory exceeded",
        "segmentation fault",
    ]

    has_complex_keyword = any(
        keyword in lower_logs for keyword in complex_keywords
    )

    docker_failure = (
        "docker" in lower_logs
        and any(
            word in lower_logs
            for word in ["error", "failed", "failure", "fatal"]
        )
    )

    if log_length > 2500:
        return True

    if len(errors) >= 4:
        return True

    if likely_stage == "unknown" and len(errors) > 0:
        return True

    if has_complex_keyword or docker_failure:
        return True

    return False


def rule_based_analysis(logs: str):
    errors = extract_errors(logs)
    likely_stage = detect_stage(logs)
    severity = estimate_severity(errors, logs)

    if not errors:
        return {
            "summary": "No clear failure was detected in the logs.",
            "severity": "low",
            "likely_stage": likely_stage,
            "error_count": 0,
            "top_errors": [],
            "suggested_fix": "Review warnings if needed, but the pipeline does not appear to have failed.",
            "postmortem": {
                "title": "No Incident Detected",
                "impact": "No user or deployment impact detected.",
                "root_cause": "No explicit error patterns were found.",
                "resolution": "No immediate action required.",
                "prevention": "Continue monitoring pipeline warnings and build health.",
            },
            "analysis_mode": "rule-based",
            "ai_used": False,
            "ai_reason": "No clear failure detected.",
        }

    first_error = errors[0]

    suggested_fix = (
        "Review the top error messages, reproduce locally, "
        "and verify dependencies, environment variables, and build commands."
    )

    lower_logs = logs.lower()

    if "cannot find module" in lower_logs or "module not found" in lower_logs:
        suggested_fix = (
            "Install the missing package, verify it exists in package.json, "
            "then rerun npm install and rebuild the application."
        )

    elif "api key" in lower_logs or "unauthorized" in lower_logs:
        suggested_fix = (
            "Verify API keys, secrets, and environment variables are correctly configured."
        )

    elif "docker" in lower_logs:
        suggested_fix = (
            "Inspect Dockerfile dependency installation, image build steps, "
            "and pinned package versions."
        )

    elif "pytest" in lower_logs or "test failed" in lower_logs:
        suggested_fix = (
            "Run failing tests locally and inspect assertion failures or fixture configuration."
        )

    return {
        "summary": f"The pipeline failed during the {likely_stage} stage.",
        "severity": severity,
        "likely_stage": likely_stage,
        "error_count": len(errors),
        "top_errors": errors[:5],
        "suggested_fix": suggested_fix,
        "postmortem": {
            "title": f"{likely_stage.title()} Failure",
            "impact": "The pipeline was blocked before successful completion.",
            "root_cause": first_error,
            "resolution": suggested_fix,
            "prevention": (
                "Add stronger validation, automated checks, "
                "and dependency verification in CI."
            ),
        },
        "analysis_mode": "rule-based",
        "ai_used": False,
        "ai_reason": "Log matched deterministic failure patterns.",
    }


def ai_analysis(logs: str, routing_reason: str):
    schema = {
        "name": "incident_analysis",
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "summary": {"type": "string"},
                "severity": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "critical"],
                },
                "likely_stage": {"type": "string"},
                "error_count": {"type": "integer"},
                "top_errors": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "suggested_fix": {"type": "string"},
                "postmortem": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "title": {"type": "string"},
                        "impact": {"type": "string"},
                        "root_cause": {"type": "string"},
                        "resolution": {"type": "string"},
                        "prevention": {"type": "string"},
                    },
                    "required": [
                        "title",
                        "impact",
                        "root_cause",
                        "resolution",
                        "prevention",
                    ],
                },
            },
            "required": [
                "summary",
                "severity",
                "likely_stage",
                "error_count",
                "top_errors",
                "suggested_fix",
                "postmortem",
            ],
        },
    }

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert DevOps incident analyst. "
                    "Analyze CI/CD logs and provide concise, practical incident analysis."
                ),
            },
            {
                "role": "user",
                "content": f"Analyze these CI/CD logs:\n\n{logs[:12000]}",
            },
        ],
        response_format={
            "type": "json_schema",
            "json_schema": schema,
        },
    )

    data = json.loads(response.choices[0].message.content)

    data["analysis_mode"] = "openai"
    data["ai_used"] = True
    data["ai_reason"] = routing_reason

    return data


@app.get("/")
def root():
    return {"message": "AI Incident Copilot API is running"}


@app.post("/analyze")
def analyze_logs(request: LogRequest):
    logs = request.logs

    if not logs.strip():
        return {
            "summary": "No logs were provided.",
            "severity": "low",
            "likely_stage": "unknown",
            "error_count": 0,
            "top_errors": [],
            "suggested_fix": "Paste or upload CI/CD logs before running analysis.",
            "postmortem": {
                "title": "No Incident Detected",
                "impact": "No impact.",
                "root_cause": "No logs were submitted.",
                "resolution": "Submit logs for analysis.",
                "prevention": "N/A",
            },
            "analysis_mode": "empty",
            "ai_used": False,
            "ai_reason": "No logs submitted.",
        }

    errors = extract_errors(logs)
    likely_stage = detect_stage(logs)

    use_ai = should_use_ai(logs, errors, likely_stage)

    if use_ai:
        routing_reason = (
            "AI selected because the logs appear complex, ambiguous, "
            "large, or high-risk."
        )

        try:
            return ai_analysis(logs, routing_reason)

        except Exception as e:
            fallback = rule_based_analysis(logs)

            fallback["analysis_mode"] = "fallback"
            fallback["ai_used"] = False
            fallback["ai_reason"] = (
                f"AI analysis failed and fallback mode was used: {str(e)}"
            )

            return fallback

    return rule_based_analysis(logs)