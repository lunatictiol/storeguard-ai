import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

import uvicorn
from fastapi import FastAPI, HTTPException
from typing import List
from models import AnomalyEvent
from agent import run_agent

app = FastAPI()

@app.post("/analyze")
def analyze_anomalies(payload: List[AnomalyEvent]):
    print("analyze hit")
    if not payload:
        raise HTTPException(status_code=400, detail="Empty payload")
    
    reports = []
    for event in payload:
        report = run_agent(event)
        reports.append(report)
        
    return {"status": "success", "reports": reports}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
