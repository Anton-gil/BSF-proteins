"""
BSF-RL-Optimizer  —  FastAPI REST API
======================================
Run from project root:
    uvicorn backend.main:app --reload --port 8000
"""

import sys
import os

# Make src/ importable when running from the backend/ subdirectory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import csv
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bsf-api")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent          # project root
BACKEND_DATA_DIR = Path(__file__).resolve().parent / "data"
BATCHES_FILE = BACKEND_DATA_DIR / "batches.json"
SETTINGS_FILE = BACKEND_DATA_DIR / "settings.json"
MODEL_PATH = BASE_DIR / "outputs" / "models" / "best_model"
RESULTS_CSV = BASE_DIR / "results" / "summary_comparison.csv"

BACKEND_DATA_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# JSON persistence helpers
# ---------------------------------------------------------------------------

def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save_json(path: Path, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


# Ensure persistence files exist
if not BATCHES_FILE.exists():
    _save_json(BATCHES_FILE, [])
if not SETTINGS_FILE.exists():
    _save_json(SETTINGS_FILE, {"policy": "ppo"})

# ---------------------------------------------------------------------------
# Load ML models at startup
# ---------------------------------------------------------------------------
ppo_agent = None
heuristic_policy = None
llm_enhancer = None

try:
    from src.agents.ppo_agent import BSFPPOAgent
    model_zip = Path(str(MODEL_PATH) + ".zip")
    if model_zip.exists():
        logger.info("Loading PPO model from %s …", model_zip)
        ppo_agent = BSFPPOAgent.load(str(MODEL_PATH))
        logger.info("PPO model loaded successfully.")
    else:
        logger.warning(
            "PPO model file not found at %s — ppo_agent will be None. "
            "Falling back to heuristic policy for all requests.",
            model_zip,
        )
except Exception as exc:
    logger.warning("Could not load PPO model: %s — continuing without it.", exc)

try:
    from src.baselines.heuristic_policy import HeuristicPolicy
    heuristic_policy = HeuristicPolicy()
    logger.info("HeuristicPolicy loaded.")
except Exception as exc:
    logger.error("Could not load HeuristicPolicy: %s", exc)

try:
    from src.translation.llm_enhancer import LLMEnhancer
    llm_enhancer = LLMEnhancer()
    logger.info("LLMEnhancer initialised (Ollama backend). Will activate on first request if Ollama is running.")
except Exception as exc:
    logger.warning("Could not initialise LLMEnhancer: %s", exc)

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="BSF-RL-Optimizer API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

CONTAINER_SIZE_CM2 = {
    "small": 1200.0,       # 40×30 cm
    "standard": 2400.0,    # 60×40 cm
    "industrial": 4800.0,  # 80×60 cm
}

class NewBatchRequest(BaseModel):
    larvaeCount: int
    containerSize: str     # "small" | "standard" | "industrial"
    startDate: str
    location: str


class CheckInRequest(BaseModel):
    batch_id: str
    larvae_activity: str        # sluggish | normal | very_active
    mortality_estimate: str     # none | few | some | many
    substrate_condition: str    # dry | good | wet | soggy
    smell: str                  # normal | ammonia | sour
    waste_available: Dict[str, float]   # {"Vegetable Scraps": 5.0, …}
    estimated_larvae_count: int
    age_days: float


class PolicyUpdateRequest(BaseModel):
    policy: str   # "ppo" | "rule_based"


# ---------------------------------------------------------------------------
# Helper: fallback schedule (used when check-in logic fails)
# ---------------------------------------------------------------------------

def _fallback_schedule(batch_id: str) -> Dict:
    return {
        "feed_instruction": "Feed 50% vegetable mix",
        "feed_amounts": {"Vegetable Scraps": 0.05},
        "target_cn": 20.0,
        "moisture_action": "No action needed",
        "aeration_action": "Normal aeration",
        "notes": ["Using fallback schedule — check server logs for details."],
        "confidence": 0.5,
        "schedule": [
            {"time": "08:00 AM", "mix": "Feed 50% vegetable mix", "h2o": "No action needed"},
            {"time": "02:00 PM", "mix": "Feed 50% vegetable mix", "h2o": "Monitor substrate"},
            {"time": "06:00 PM", "mix": "No evening feed", "h2o": "Normal aeration"},
        ],
        "projection": {"expected": 160.0, "trajectory": "Normal"},
    }


# ---------------------------------------------------------------------------
# GET /api/batches
# ---------------------------------------------------------------------------

@app.get("/api/batches")
def get_batches() -> List[Dict]:
    """Return all tracked batches."""
    return _load_json(BATCHES_FILE, [])


# ---------------------------------------------------------------------------
# POST /api/batches
# ---------------------------------------------------------------------------

@app.post("/api/batches", status_code=201)
def create_batch(req: NewBatchRequest) -> Dict:
    """Create a new larvae batch."""
    settings = _load_json(SETTINGS_FILE, {"policy": "ppo"})
    batches: List[Dict] = _load_json(BATCHES_FILE, [])

    new_batch = {
        "id": str(int(time.time() * 1000)),
        "larvaeCount": req.larvaeCount,
        "containerSize": req.containerSize,
        "startDate": req.startDate,
        "location": req.location,
        "status": "active",
        "policy": settings.get("policy", "ppo"),
        "createdAt": datetime.utcnow().isoformat(),
    }

    batches.append(new_batch)
    _save_json(BATCHES_FILE, batches)
    return new_batch


# ---------------------------------------------------------------------------
# GET /api/batches/{batch_id}
# ---------------------------------------------------------------------------

@app.get("/api/batches/{batch_id}")
def get_batch(batch_id: str) -> Dict:
    """Return a single batch by ID."""
    batches: List[Dict] = _load_json(BATCHES_FILE, [])
    for batch in batches:
        if batch.get("id") == batch_id:
            return batch
    raise HTTPException(status_code=404, detail=f"Batch '{batch_id}' not found.")


# ---------------------------------------------------------------------------
# POST /api/checkin
# ---------------------------------------------------------------------------

@app.post("/api/checkin")
def checkin(req: CheckInRequest) -> Dict:
    """
    Process a farmer check-in observation and return a daily recommendation.
    Falls back to a mock schedule on any error.
    """
    try:
        from src.translation.state_estimator import StateEstimator, BatchInfo, FarmerObservation
        from src.translation.recommendation import RecommendationGenerator

        # --- Look up batch ---
        batches: List[Dict] = _load_json(BATCHES_FILE, [])
        batch_data: Optional[Dict] = None
        for b in batches:
            if b.get("id") == req.batch_id:
                batch_data = b
                break

        # Build BatchInfo
        if batch_data:
            try:
                start_dt = datetime.fromisoformat(batch_data["startDate"])
            except Exception:
                start_dt = datetime.utcnow()
            batch_info = BatchInfo(
                start_date=start_dt,
                initial_count=batch_data.get("larvaeCount", req.estimated_larvae_count),
                estimated_count=req.estimated_larvae_count,
                container_area_cm2=CONTAINER_SIZE_CM2.get(batch_data.get("containerSize", "standard"), 2400.0),
            )
        else:
            # Batch not found — construct from check-in data
            batch_info = BatchInfo(
                start_date=datetime.utcnow(),
                initial_count=req.estimated_larvae_count,
                estimated_count=req.estimated_larvae_count,
            )

        # Build FarmerObservation
        farmer_obs = FarmerObservation(
            larvae_activity=req.larvae_activity,
            mortality_estimate=req.mortality_estimate,
            substrate_condition=req.substrate_condition,
            smell=req.smell,
        )

        # Estimate RL observation vector
        # Bug fix: pass actual waste_available so C:N is estimated correctly
        obs = StateEstimator().estimate_state(
            batch_info=batch_info,
            farmer_obs=farmer_obs,
            recent_waste=req.waste_available,  # was {} — now uses farmer's actual selection
        )

        # Choose policy
        settings = _load_json(SETTINGS_FILE, {"policy": "ppo"})
        policy_name = settings.get("policy", "ppo")

        if policy_name == "ppo" and ppo_agent is not None:
            # Bug fix: PPO was trained with VecNormalize — must normalize obs before predict
            try:
                from stable_baselines3.common.vec_env import VecNormalize
                if isinstance(ppo_agent.env, VecNormalize):
                    obs_norm = ppo_agent.env.normalize_obs(obs.reshape(1, -1))[0]
                else:
                    obs_norm = obs
            except Exception:
                obs_norm = obs  # fallback: use raw obs
            action, _ = ppo_agent.model.predict(obs_norm, deterministic=True)
        else:
            if heuristic_policy is not None:
                action = heuristic_policy.predict(obs)
            else:
                # Last-resort: neutral action
                action = np.array([0.5, 0.5, 0.15, 0.5], dtype=np.float32)

        # Generate recommendation
        # waste_available has form {id: kg} — pass keys for waste mix selection
        rec = RecommendationGenerator().generate(
            action=action,
            available_wastes=list(req.waste_available.keys()),
            larvae_count=req.estimated_larvae_count,
            age_days=req.age_days,
        )

        # Bug fix: split feed across AM/PM (60%/40%), evening = moisture/aeration only
        total_kg = sum(rec.feed_amounts.values()) if rec.feed_amounts else 0.0
        am_amounts = {k: round(v * 0.6, 3) for k, v in rec.feed_amounts.items()}
        pm_amounts = {k: round(v * 0.4, 3) for k, v in rec.feed_amounts.items()}

        from src.translation.waste_translator import WasteTranslator
        _wt = WasteTranslator()
        am_instruction = _wt.format_mix_instructions(am_amounts) if am_amounts else "No morning feed"
        pm_instruction = _wt.format_mix_instructions(pm_amounts) if pm_amounts else "No afternoon feed"

        # Bug fix: projection uses logistic growth curve instead of CN * 8
        # Logistic: K=150mg, r=0.5, t0=7 days
        K, r, t0 = 150.0, 0.5, 7.0
        days_remaining = max(0.0, 16.0 - req.age_days)
        expected_biomass_at_harvest = K / (1.0 + np.exp(-r * (16.0 - t0)))
        # Adjust for confidence (lower confidence → more conservative estimate)
        expected_biomass_at_harvest = round(expected_biomass_at_harvest * (0.7 + 0.3 * rec.confidence), 1)

        # Determine trajectory from current biomass vs ideal curve
        ideal_now = K / (1.0 + np.exp(-r * (req.age_days - t0)))
        current_biomass = float(obs[1])   # obs[1] = biomass_mg from state estimator
        if current_biomass >= ideal_now * 0.95:
            trajectory = "On Track 🟢"
        elif current_biomass >= ideal_now * 0.75:
            trajectory = "Slightly Behind 🟡"
        else:
            trajectory = "Needs Attention 🔴"

        # LLM coach message — context-aware, empathetic natural language
        coach_message: Optional[str] = None
        if llm_enhancer is not None:
            try:
                coach_message = llm_enhancer.enhance(
                    mortality=req.mortality_estimate,
                    activity=req.larvae_activity,
                    substrate=req.substrate_condition,
                    smell=req.smell,
                    age_days=req.age_days,
                    feed_instruction=rec.feed_instruction,
                    moisture_action=rec.moisture_action,
                    aeration_action=rec.aeration_action,
                    notes=rec.notes,
                    confidence=rec.confidence,
                    trajectory=trajectory,
                    available_wastes=list(req.waste_available.keys()),
                )
            except Exception as llm_exc:
                logger.warning("LLM enhancement failed: %s", llm_exc)

        return {
            "feed_instruction": rec.feed_instruction,
            "feed_amounts": rec.feed_amounts,
            "target_cn": rec.target_cn,
            "moisture_action": rec.moisture_action,
            "aeration_action": rec.aeration_action,
            "notes": rec.notes,
            "confidence": rec.confidence,
            "coach_message": coach_message,   # None if Ollama not running
            "schedule": [
                {
                    "time": "08:00 AM",
                    "mix": am_instruction,
                    "h2o": rec.moisture_action,
                },
                {
                    "time": "02:00 PM",
                    "mix": pm_instruction,
                    "h2o": "Monitor substrate moisture",
                },
                {
                    "time": "06:00 PM",
                    "mix": "No evening feed — larvae rest phase",
                    "h2o": rec.aeration_action,
                },
            ],
            "projection": {
                "expected": expected_biomass_at_harvest,
                "trajectory": trajectory,
            },
        }

    except Exception as exc:
        logger.error("Check-in failed for batch %s: %s", req.batch_id, exc, exc_info=True)
        return _fallback_schedule(req.batch_id)


# ---------------------------------------------------------------------------
# POST /api/batches/{batch_id}/checkin  — save a confirmed daily check-in
# ---------------------------------------------------------------------------

class CheckInSaveRequest(BaseModel):
    day: int
    feed_kg: float
    recommendation: str
    confirmed_at: str


@app.post("/api/batches/{batch_id}/checkin")
def save_daily_checkin(batch_id: str, req: CheckInSaveRequest) -> Dict:
    """Persist a confirmed daily check-in to the batch record."""
    batches: List[Dict] = _load_json(BATCHES_FILE, [])
    for batch in batches:
        if batch.get("id") == batch_id:
            if "checkIns" not in batch:
                batch["checkIns"] = []
            batch["checkIns"].append(req.dict())
            batch["currentDay"] = req.day + 1
            # Mark completed when final day done (day 15 = 16th day, 0-indexed)
            if req.day >= 15:
                batch["status"] = "completed"
                batch["duration"] = 16
            _save_json(BATCHES_FILE, batches)
            logger.info("Saved check-in day %d for batch %s", req.day, batch_id)
            return batch
    raise HTTPException(status_code=404, detail=f"Batch '{batch_id}' not found.")


# ---------------------------------------------------------------------------
# PATCH /api/batches/{batch_id}  — partial update
# ---------------------------------------------------------------------------

@app.patch("/api/batches/{batch_id}")
def patch_batch(batch_id: str, updates: Dict) -> Dict:
    """Partial update of a batch record (status, currentDay, etc.)."""
    batches: List[Dict] = _load_json(BATCHES_FILE, [])
    for batch in batches:
        if batch.get("id") == batch_id:
            batch.update(updates)
            _save_json(BATCHES_FILE, batches)
            logger.info("Patched batch %s: %s", batch_id, list(updates.keys()))
            return batch
    raise HTTPException(status_code=404, detail=f"Batch '{batch_id}' not found.")



@app.get("/api/report")
def get_report() -> Dict:
    """Return strategy comparison data from results/summary_comparison.csv."""
    strategies = []
    try:
        with open(RESULTS_CSV, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                strategies.append(
                    {
                        "name": row["strategy"],
                        "avg_biomass": float(row["avg_biomass"]),
                        "std_biomass": float(row["std_biomass"]),
                        "max_biomass": float(row["max_biomass"]),
                        "avg_reward": float(row["avg_reward"]),
                        "avg_feed_g": float(row["avg_feed_g"]),
                        "avg_mortality": float(row["avg_mortality"]),
                    }
                )
    except Exception as exc:
        logger.error("Could not read results CSV: %s", exc)
        # Fallback values — exact copy of results/summary_comparison.csv
        strategies = [
            {"name": "PPO Agent",  "avg_biomass": 110.45, "std_biomass": 37.57, "max_biomass": 151.67, "avg_reward":   30.22, "avg_feed_g": 196.28, "avg_mortality": 82.03},
            {"name": "Rule-Based", "avg_biomass": 134.04, "std_biomass": 18.65, "max_biomass": 153.25, "avg_reward":   63.07, "avg_feed_g": 737.17, "avg_mortality": 78.95},
            {"name": "Random",     "avg_biomass": 128.34, "std_biomass": 21.38, "max_biomass": 151.63, "avg_reward":   52.66, "avg_feed_g": 744.67, "avg_mortality": 81.52},
            {"name": "Do-Nothing", "avg_biomass":   1.96, "std_biomass":  0.28, "max_biomass":   2.44, "avg_reward": -162.88, "avg_feed_g":   0.00, "avg_mortality": 99.99},
        ]

    # Compute highlights from actual strategy data (not hardcoded)
    ppo  = next((s for s in strategies if s["name"] == "PPO Agent"),  None)
    rule = next((s for s in strategies if s["name"] == "Rule-Based"), None)
    highlights = {}
    if ppo and rule and rule["avg_feed_g"] > 0:
        highlights = {
            "feed_savings_pct":        round((rule["avg_feed_g"] - ppo["avg_feed_g"]) / rule["avg_feed_g"] * 100, 1),
            "biomass_advantage_mg":    round(ppo["avg_biomass"] - rule["avg_biomass"], 2),
            "mortality_change_pct":    round(rule["avg_mortality"] - ppo["avg_mortality"], 2),
        }

    return {
        "strategies": strategies,
        "highlights": highlights,
    }


# ---------------------------------------------------------------------------
# DELETE /api/batches/history  — wipe all completed + abandoned batches
# ---------------------------------------------------------------------------

@app.delete("/api/batches/history")
def clear_batch_history() -> Dict:
    """Delete all completed and abandoned (no check-ins) batches. Keeps any batch that has check-ins in progress."""
    batches: List[Dict] = _load_json(BATCHES_FILE, [])
    kept = [b for b in batches if b.get("status") == "active" and b.get("checkIns")]
    removed = len(batches) - len(kept)
    _save_json(BATCHES_FILE, kept)
    logger.info("Cleared batch history: removed %d, kept %d", removed, len(kept))
    return {"removed": removed, "kept": len(kept)}


# ---------------------------------------------------------------------------
# GET /api/settings
# ---------------------------------------------------------------------------

@app.get("/api/settings")
def get_settings() -> Dict:
    """Return current policy settings."""
    return _load_json(SETTINGS_FILE, {"policy": "ppo"})


# ---------------------------------------------------------------------------
# POST /api/settings/policy
# ---------------------------------------------------------------------------

@app.post("/api/settings/policy")
def update_policy(req: PolicyUpdateRequest) -> Dict:
    """Update the active inference policy."""
    if req.policy not in ("ppo", "rule_based"):
        raise HTTPException(
            status_code=422,
            detail="policy must be 'ppo' or 'rule_based'",
        )
    settings = {"policy": req.policy}
    _save_json(SETTINGS_FILE, settings)
    logger.info("Policy updated to: %s", req.policy)
    return settings
