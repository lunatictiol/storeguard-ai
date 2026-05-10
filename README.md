# StoreGuard AI

An autonomous multi-agent system that monitors a mock e-commerce store, detects operational anomalies, investigates root causes using a local LLM, and delivers actionable triage reports to Discord — fully automated, zero human intervention required.

Built as a portfolio project demonstrating real-world AI automation engineering skills across LangGraph, FastAPI, n8n, and Discord webhook integration.

---

## What it does

StoreGuard AI polls a product catalogue every 5 minutes and runs three anomaly detection rules:

- **Low demand** — flags products with suspiciously low review counts, signalling poor visibility or dead stock risk
- **Poor rating** — identifies products rated below 2.5 that are still actively listed
- **Price anomaly** — detects products whose price deviates more than 70% from their category average

When an anomaly is detected, a LangGraph agent classifies it, reasons through the root cause, and posts a formatted severity-coded embed to a Discord channel.

---

## Architecture

```
Fake Store API (fakestoreapi.com)
        ↓  HTTP poll every 5 min
   n8n (anomaly detection rules)
        ↓  POST list[AnomalyEvent]
   FastAPI /analyze endpoint
        ↓  invoke per anomaly
   LangGraph agent (Ollama / llama3)
        ↓  POST embed
   Discord webhook
```

### Components

| Layer | Tool | Role |
|---|---|---|
| Data source | Fake Store API | Mock product catalogue — orders, products, inventory |
| Orchestration | n8n | Schedule trigger, anomaly rules, HTTP POST to FastAPI |
| API layer | FastAPI + Pydantic | Receives and validates anomaly payloads |
| Agent brain | LangGraph + Ollama | Multi-node reasoning chain — classify, root cause, recommend |
| Notification | Discord webhook | Formatted severity-coded embed alerts |
| Containerisation | Docker Compose | Runs n8n and FastAPI together |

---

## Project structure

```
storeguard-ai/
├── agent/
│   ├── main.py              # FastAPI app — /analyze endpoint
│   ├── models.py            # Pydantic models matching n8n payload
│   ├── agent.py             # LangGraph agent — analyze + notify nodes
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .dockerignore
├── n8n/
│   └── workflow.json        # Exported n8n workflow (without credentials)
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Ollama](https://ollama.com/) installed and running locally
- A Discord server with a webhook URL

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/your-username/storeguard-ai.git
cd storeguard-ai
```

### 2. Pull the LLM model

```bash
ollama pull llama3
```

Confirm Ollama is running:

```bash
curl http://localhost:11434/api/tags
```

### 3. Configure environment variables

Copy the example env file and fill in your values:

```bash
cp .env.example .env
```

`.env`:
```
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/your/url
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=llama3
```

### 4. Start the stack

```bash
docker compose up --build
```

This starts:
- FastAPI agent on `http://localhost:8000`
- n8n on `http://localhost:5679`

### 5. Import the n8n workflow

- Open `http://localhost:5679`
- Go to **Workflows → Import from file**
- Select `n8n/workflow.json`
- Open the workflow and update the HTTP Request node URL if needed
- Toggle the workflow **Active**

---

## How the n8n workflow works

The workflow runs on a 5-minute schedule and executes three detection rules in sequence:

**Rule 1 — Low demand**
```javascript
const products = $input.all().map(item => item.json);
const lowDemand = products.filter(p => p.rating.count < 150);
```
Flags products with fewer than 150 ratings. Severity is `critical` if count is below 80, `warning` otherwise.

**Rule 2 — Poor rating**
```javascript
const poorRated = products.filter(p => p.rating.rate < 2.5);
```
Flags any product rated below 2.5. Severity is `critical` if below 2.0.

**Rule 3 — Price anomaly**
```javascript
const deviation = Math.abs(p.price - avg) / avg;
if (deviation > 0.7) { outliers.push(p); }
```
Groups products by category, calculates average price, and flags any product deviating more than 70% from the category mean.

All three rules output a consistent payload shape and are merged before being POSTed to FastAPI as a single `list[AnomalyEvent]`.

---

## API reference

### `POST /analyze`

Accepts a list of anomaly events and runs the LangGraph agent for each.

**Request body:**
```json
[
  {
    "anomaly_type": "poor_rating",
    "severity": "critical",
    "triggered_at": "2026-05-10T14:13:59.937Z",
    "affected_count": 3,
    "products": [
      {
        "id": 4,
        "title": "Mens Casual Slim Fit",
        "category": "men's clothing",
        "price": 15.99,
        "rating": 2.1,
        "review_count": 430
      }
    ]
  }
]
```

**Response:**
```json
{
  "status": "processed",
  "processed": 1,
  "reports": [
    {
      "anomaly_type": "poor_rating",
      "severity": "critical",
      "report": "Three products across men's clothing, jewelery, and electronics categories show ratings below 2.5..."
    }
  ]
}
```

**Empty payload response:**
```json
{
  "status": "no_anomalies",
  "processed": 0
}
```

### `GET /health`

```json
{ "status": "ok" }
```

Interactive API docs available at `http://localhost:8000/docs`.

---

## Discord alerts

Alerts are posted as embeds with severity-coded colors:

| Severity | Color | Trigger |
|---|---|---|
| Critical | Red | Rating < 2.0 or demand count < 80 |
| Warning | Yellow | Rating 2.0–2.5 or demand count 80–150 or price anomaly |
| Info | Green | Informational detections |

Each embed includes the anomaly type, severity, affected item count, LLM-generated root cause analysis, and actionable recommendations.

---

## LangGraph agent

The agent runs a two-node graph per anomaly:

```
analyze_anomaly → notify_discord → END
```

**analyze_anomaly** — sends the anomaly data to a local Ollama LLM with a structured prompt asking for impact analysis and 1–2 recommendations. Strips any follow-up questions from the response.

**notify_discord** — formats the analysis as a Discord embed and POSTs it to the configured webhook URL.

---

## Development

Hot reload is enabled — save any `.py` file inside `agent/` and uvicorn restarts automatically:

```
INFO:  StatReload detected changes in 'agent.py'. Reloading...
```

To run FastAPI outside Docker for faster iteration:

```bash
cd agent
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

---

## Environment variables

| Variable | Description | Default |
|---|---|---|
| `DISCORD_WEBHOOK_URL` | Discord channel webhook URL | required |
| `OLLAMA_BASE_URL` | Ollama API base URL | `http://localhost:11434` |
| `OLLAMA_MODEL` | Ollama model name | `llama3` |

---

## Tech stack

- **FastAPI** — async Python API framework
- **Pydantic** — request validation and data modelling
- **LangGraph** — multi-node agent graph orchestration
- **LangChain Ollama** — local LLM integration
- **Ollama + llama3** — free local LLM, no API key required
- **n8n** — no-code workflow automation and scheduling
- **Docker Compose** — container orchestration
- **Discord Webhooks** — alert delivery

---

## Roadmap

- [ ] Add a Grafana dashboard for anomaly trend visualisation
- [ ] Expand anomaly rules to cover order spike detection via `/carts` endpoint
- [ ] Add a Slack notification channel as an alternative to Discord
- [ ] Persist anomaly reports to SQLite for historical analysis
- [ ] Containerise Ollama alongside the stack

