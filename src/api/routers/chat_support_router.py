from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import time
import json
import hashlib
import redis
from src.agents.data_synthesizer.scdg import SCDG
from src.core.knowledge_base import KnowledgeBase
from src.ml.inference import CreditRiskModel

router = APIRouter(prefix="/chat", tags=["chat_support"])

r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
DEMO_NAMES_KEY = "demo:names"

def _seed_names_if_needed():
    if not r.exists(DEMO_NAMES_KEY):
        names: List[str] = []
        gen = SCDG(seed="demo-names")
        for i in range(500):
            profile = gen.generate_profile({"age": 25 + (i % 30), "territory": "ECCU"})
            names.append(profile.identity.full_name)
        for n in names:
            r.rpush(DEMO_NAMES_KEY, n)

@router.get("/suggestions")
async def suggestions(prefix: str = "", limit: int = 10):
    _seed_names_if_needed()
    all_names = r.lrange(DEMO_NAMES_KEY, 0, -1)
    prefix_lower = prefix.strip().lower()
    filtered = [n for n in all_names if n.lower().startswith(prefix_lower)]
    return {"items": filtered[:max(1, min(limit, 50))]}

class IdentityRequest(BaseModel):
    name: str
    surname: str

@router.post("/identity")
async def identity(req: IdentityRequest):
    full_name = f"{req.name.strip()} {req.surname.strip()}".strip()
    token = hashlib.sha256(full_name.encode()).hexdigest()
    return {"full_name": full_name, "token": token}

def _progress_events(full_name: str):
    kb = KnowledgeBase()
    model = CreditRiskModel()
    gen = SCDG(seed=f"chat-{full_name}")
    steps = [
        ("database_lookup", 10),
        ("feature_assembly", 30),
        ("classification", 60),
        ("model_inference", 85),
        ("aggregation", 100)
    ]
    try:
        kb_results = kb.search("credit policy", top_k=3)
    except Exception:
        kb_results = []
    for step, pct in steps:
        if step == "feature_assembly":
            profile = gen.generate_profile({"age": 30, "territory": "ECCU"})
        elif step == "model_inference":
            pred = model.predict(profile)
        d = {"step": step, "progress": pct}
        if step == "database_lookup":
            d["kb_hits"] = len(kb_results)
        if step == "model_inference":
            d["probability_good"] = pred.get("probability_good", 0.5)
        yield f"data: {json.dumps(d)}\n\n"
        time.sleep(0.4)

@router.get("/progress/stream")
async def progress_stream(full_name: str):
    return StreamingResponse(_progress_events(full_name), media_type="text/event-stream")
