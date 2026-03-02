from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import time
import json
import hashlib
import redis
import random
import asyncio
from src.agents.data_synthesizer.scdg import SCDG
from src.core.knowledge_base import KnowledgeBase
from src.ml.inference import CreditRiskModel
from src.api.routers.admin_config_router import _get_flag

router = APIRouter(prefix="/chat", tags=["chat_support"])

# Initialize Redis with fallback
try:
    r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
    r.ping()
except redis.ConnectionError:
    # Fallback mock if Redis is down
    class MockRedis:
        def __init__(self): self.store = {}
        def get(self, k): return self.store.get(k)
        def set(self, k, v): self.store[k] = v
        def setex(self, k, t, v): self.store[k] = v
        def exists(self, k): return k in self.store
        def rpush(self, k, *v): 
            l = self.store.get(k, [])
            if not isinstance(l, list): l = []
            l.extend(v)
            self.store[k] = l
        def lrange(self, k, s, e):
            l = self.store.get(k, [])
            if e == -1: return l[s:]
            return l[s:e+1]
    r = MockRedis()

DEMO_NAMES_KEY = "demo:names"
CARIBBEAN_TERRITORIES = {
    "AG": "Antigua and Barbuda",
    "AI": "Anguilla",
    "DM": "Dominica",
    "GD": "Grenada",
    "MS": "Montserrat",
    "KN": "Saint Kitts and Nevis",
    "LC": "Saint Lucia",
    "VC": "Saint Vincent and the Grenadines"
}

def _seed_names_if_needed():
    if not r.exists(DEMO_NAMES_KEY):
        names: List[str] = []
        gen = SCDG(seed="demo-names")
        for i in range(50): 
            profile = gen.generate_profile({"age": 25 + (i % 30), "territory": "ECCU"})
            names.append(profile.identity.full_name)
        for n in names:
            r.rpush(DEMO_NAMES_KEY, n)

@router.get("/suggestions")
async def suggestions(prefix: str = "", limit: int = 10):
    """
    Returns suggestions.
    If prefix is provided, returns autocomplete suggestions (names).
    If no prefix, returns full starter prompts for "Need help getting started?".
    """
    if not _get_flag():
        return {"items": []}
    
    # If no prefix, return rich starter suggestions
    if not prefix:
        STARTER_KEY = "demo:starters"
        starters = r.get(STARTER_KEY)
        if not starters:
            gen = SCDG(seed=str(time.time()))
            items = []
            # Generate 3 valid Caribbean profiles
            territories = list(CARIBBEAN_TERRITORIES.keys())
            for _ in range(3):
                t_code = random.choice(territories)
                age = random.randint(22, 55)
                # Ensure we generate a profile for this specific territory to get a valid name
                p = gen.generate_profile({"age": age, "territory": t_code})
                
                t_name = CARIBBEAN_TERRITORIES.get(t_code, t_code)
                full_name = p.identity.full_name
                
                items.append({
                    "label": f"{full_name} ({t_name})",
                    "text": f"My name is {full_name}, I am {age} years old from {t_name}."
                })
            r.setex(STARTER_KEY, 300, json.dumps(items)) # Cache for 5 mins
            return {"items": items}
        else:
            return {"items": json.loads(starters)}

    # Existing autocomplete logic
    _seed_names_if_needed()
    all_names = r.lrange(DEMO_NAMES_KEY, 0, -1)
    prefix_lower = prefix.strip().lower()
    filtered = [n for n in all_names if n.lower().startswith(prefix_lower)]
    return {"items": filtered[:max(1, min(limit, 50))]}

async def _progress_generator(full_name: str):
    """
    Generator that simulates the backend processing steps and emits SSE events.
    """
    # Simulate processing time and steps
    steps = [
        ("database_lookup", 10, 0.5),
        ("feature_assembly", 30, 0.8),
        ("classification", 60, 1.0),
        ("model_inference", 85, 0.7),
        ("aggregation", 100, 0.5)
    ]
    
    for step_name, progress, delay in steps:
        meta = {}
        # Simulate check
        if step_name == "database_lookup":
            meta["status"] = "checked"
        
        data = {
            "step": step_name,
            "progress": progress,
            **meta
        }
        yield f"data: {json.dumps(data)}\n\n"
        await asyncio.sleep(delay)

@router.get("/progress/stream")
async def progress_stream(full_name: str):
    return StreamingResponse(_progress_generator(full_name), media_type="text/event-stream")

class IdentityRequest(BaseModel):
    name: str
    surname: str

@router.post("/identity")
async def identity(req: IdentityRequest):
    full_name = f"{req.name.strip()} {req.surname.strip()}".strip()
    token = hashlib.sha256(full_name.encode()).hexdigest()
    return {"full_name": full_name, "token": token}
