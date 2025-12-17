
import os
import sys
from typing import Dict, Any, Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add project root to sys.path
sys.path.append(os.getcwd())

from shared.brightdata import BrightDataClient
from shared.llm import LLM
from basic_agent.agent import run_basic_agent
from web_discovery_agent.agent import run_web_discovery_agent

app = FastAPI(title="AI Research Agent GUI")

# Enable CORS for dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class ResearchRequest(BaseModel):
    params: str  # The query (named params to match basic agent args conceptually, or just query)
    mode: str = "basic"  # "basic" or "discovery"

class ResearchResponse(BaseModel):
    answer: str
    sources: list
    logs: Optional[str] = None

# Init shared resources (lazy loaded in endpoints or global)
# We regenerate them per request or reuse. Reusing is better for connection pooling.
# But we need to handle .env changes. For now, we load once.
from dotenv import load_dotenv
load_dotenv()

# Helper to serialize SourceDoc
def serialize_source(doc):
    return {
        "title": doc.title,
        "url": doc.url,
        "snippet": doc.snippet,
        "source_type": doc.source_type,
        "meta": doc.meta
    }

@app.post("/api/research")
async def research(req: ResearchRequest):
    try:
        # Re-load env to catch any runtime updates
        load_dotenv(override=True)
        
        # Clients
        client = BrightDataClient(api_key=os.getenv("BRIGHTDATA_API_KEY"))
        serp_zone = os.getenv("BRIGHTDATA_SERP_ZONE")
        llm = LLM.from_env()

        if req.mode == "discovery":
            print(f"Running Web Discovery Agent for: {req.params}")
            run, answer_md = run_web_discovery_agent(
                question=req.params,
                client=client,
                serp_zone=serp_zone,
                llm=llm,
                out_dir=Path("outputs") 
            )
            sources = [serialize_source(d) for d in run.docs]
            return {"answer": answer_md, "sources": sources}
            
        else:
            print(f"Running Basic Agent for: {req.params}")
            # Fix argument: 'zone' -> 'serp_zone'
            run, answer_md = run_basic_agent(
                question=req.params,
                client=client,
                serp_zone=serp_zone,
                llm=llm,
                out_dir=Path("outputs")
            )
            sources = [serialize_source(d) for d in run.docs]
            return {"answer": answer_md, "sources": sources}

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return HTMLResponse("<h1>Lemon Agent Backend is Running 🍋</h1><p>API is ready at /api/research</p>")

@app.get("/api/history")
async def get_history():
    """List all past runs from the outputs directory."""
    history = []
    base_dir = Path("outputs")
    if not base_dir.exists():
        print(f"History: {base_dir} does not exist")
        return {"history": []}
    
    # Iterate over agent types (basic_agent, web_discovery_agent)
    for agent_dir in base_dir.iterdir():
        if agent_dir.is_dir():
            agent_type = agent_dir.name
            for run_dir in agent_dir.iterdir():
                if run_dir.is_dir():
                    meta = {}
                    try:
                        sources_file = run_dir / "sources.json"
                        if sources_file.exists():
                            import json
                            data = json.loads(sources_file.read_text(encoding="utf-8"))
                            meta["question"] = data.get("question", "Unknown Question")
                            meta["created_at"] = data.get("created_at_iso")
                        else:
                             print(f"History: Skipping {run_dir}, no sources.json")
                    except Exception as e:
                        print(f"History: Error reading {run_dir}: {e}")
                    
                    history.append({
                        "id": run_dir.name,
                        "agent": agent_type,
                        "path": str(run_dir),
                        "question": meta.get("question", run_dir.name),
                        "timestamp": meta.get("created_at", "")
                    })
    
    # Sort by timestamp desc
    history.sort(key=lambda x: x["timestamp"], reverse=True)
    print(f"History: Found {len(history)} items")
    return {"history": history}

@app.delete("/api/history/{agent}/{run_id}")
async def delete_history(agent: str, run_id: str):
    import shutil
    target = Path("outputs") / agent / run_id
    if target.exists() and target.is_dir():
        try:
            shutil.rmtree(target)
            return {"status": "deleted", "id": run_id}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    raise HTTPException(status_code=404, detail="Run not found")

if __name__ == "__main__":
    import uvicorn
    print("\nStarting AI Research Agent Backend on http://localhost:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)
