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


def rule_based_analysis(logs: str):
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
            "prevention": "Add clearer CI checks, dependency validation, and automated alerts.",
        },
        "analysis_mode": "rule-based",
    }


def ai_analysis(logs: str):
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
                "content": "You are an expert DevOps incident analyst. Analyze CI/CD logs and return concise, practical incident analysis.",
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
            "suggested_fix": "Paste CI/CD logs before running analysis.",
            "postmortem": {
                "title": "No Incident Detected",
                "impact": "No impact.",
                "root_cause": "No logs were submitted.",
                "resolution": "Submit logs for analysis.",
                "prevention": "N/A",
            },
            "analysis_mode": "empty",
        }

    if client:
        try:
            return ai_analysis(logs)
        except Exception as e:
            fallback = rule_based_analysis(logs)
            fallback["analysis_mode"] = "fallback"
            fallback["ai_error"] = str(e)
            return fallback

    return rule_based_analysis(logs)