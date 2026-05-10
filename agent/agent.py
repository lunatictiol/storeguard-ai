import os
import json
import requests
from typing import TypedDict
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langchain_ollama import ChatOllama
from models import AnomalyEvent

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
llm = ChatOllama(
    model=os.getenv("OLLAMA_MODEL", "llama3"),
    temperature=0,
    base_url=ollama_base_url
)

SEVERITY_COLORS = {
    "critical": 15158332,
    "warning":  16776960,
    "info":     3066993,
}

class AgentState(TypedDict):
    event: AnomalyEvent
    analysis_report: str

def analyze_anomaly(state: AgentState):
    event = state["event"]
    data_str = json.dumps(event.model_dump(), default=str, indent=2)
    prompt = f"""
You are an expert e-commerce data analyst. Analyze the following anomaly event and provide a concise summary report.

Anomaly Data:
{data_str}

Please explain the potential impact of this anomaly and suggest 1-2 actionable recommendations.
"""
    response = llm.invoke(prompt)
    content = response.content

    # Strip the follow-up question if present
    if "---" in content:
        content = content.split("---")[0].strip()

    return {"analysis_report": content}
def notify_discord(state: AgentState):
    event = state["event"]
    report = state["analysis_report"]

    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("No Discord webhook URL set — skipping")
        return state

    embed = {
        "title": f"Anomaly detected — {event.anomaly_type.replace('_', ' ').title()}",
        "description": report,
        "color": SEVERITY_COLORS.get(event.severity, 3066993),
        "fields": [
            {"name": "Severity",       "value": event.severity,             "inline": True},
            {"name": "Affected items", "value": str(event.affected_count),  "inline": True},
        ],
        "footer": {"text": "StoreGuard AI"}
    }

    try:
        requests.post(webhook_url, json={"embeds": [embed]})
    except Exception as e:
        print(f"Discord notification failed: {e}")

    return state

workflow = StateGraph(AgentState)
workflow.add_node("analyze", analyze_anomaly)
workflow.add_node("notify", notify_discord)
workflow.set_entry_point("analyze")
workflow.add_edge("analyze", "notify")
workflow.add_edge("notify", END)

app_graph = workflow.compile()

def run_agent(event: AnomalyEvent):
    result = app_graph.invoke({"event": event})
    return {
        "anomaly_type": event.anomaly_type,
        "severity": event.severity,
        "report": result.get("analysis_report")
    }