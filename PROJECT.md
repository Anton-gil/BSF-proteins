# PROJECT.md — BSF-RL-Optimizer

**Complete technical reference for the BSF-RL-Optimizer project.**  
This document covers architecture, data flow, component responsibilities, known issues, and future roadmap.

---

## 1. Project Overview

BSF-RL-Optimizer is a full-stack AI system that helps smallholder farmers optimize Black Soldier Fly (BSF) larvae farming using Reinforcement Learning. It consists of:

- A **Gymnasium-based simulation environment** that models 16-day BSF larvae batches
- A **PPO agent** trained on 52,000+ simulated episodes to learn optimal feeding decisions
- A **FastAPI backend** that serves the trained model and persists batch data
- A **React frontend** that guides farmers through a conversational daily check-in flow

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   FRONTEND (React/Vite)                  │
│   Port: 5173                                            │
│                                                          │
│  Pages:  Landing · About · Dashboard · Report           │
│                                                          │
│  Dashboard Flow:                                         │
│    StartBatch → DailyCheckin (Day 0..15) → BatchHistory  │
│                                                          │
│  State: Zustand (batchStore) persisted to localStorage   │
│         activeBatch · currentDay · checkIns[]            │
└──────────────────────────┬──────────────────────────────┘
                           │  HTTP (Vite proxy /api → :8000)
                           ▼
┌─────────────────────────────────────────────────────────┐
│                   BACKEND (FastAPI)                      │
│   Port: 8000                                            │
│                                                          │
│  Data: backend/data/batches.json (JSON flat file)        │
│                                                          │
│  At startup loads:                                       │
│    · PPO model (outputs/models/best_model.zip)           │
│    · HeuristicPolicy (fallback if model missing)         │
└──────────────────────────┬──────────────────────────────┘
                           │  Python imports
                           ▼
┌─────────────────────────────────────────────────────────┐
│                   ML CORE (src/)                         │
│                                                          │
│  StateEstimator → 8-dim observation vector              │
│  BSFPPOAgent.predict() / HeuristicPolicy.predict()      │
│  RecommendationGenerator → plain-English schedule       │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Dashboard User Flow

The complete user journey through the dashboard:

```
/dashboard
    │
    ├─ (no active batch) ──► /dashboard/new
    │      StartBatch form
    │      Fill: larvae count, container size, start date, location
    │      Click "Start Batch →"
    │          POST /api/batches
    │          setActiveBatch() in Zustand store
    │          navigate('/dashboard/checkin')
    │
    └─ (active batch) ──► /dashboard/checkin
           DailyCheckin — Day N of 15
           Step 1: Select larvae status (healthy/deaths/sick)
           Step 2: Select waste types + quantities (kg)
           Step 3: AI processes via POST /api/checkin
           Step 4: View 3-slot daily schedule cards
           Click "Complete Check-in"
               POST /api/batches/{id}/checkin (saves to backend)
               completeDay() → increments currentDay in store
               ├─ Day < 15: "Day N Complete!" screen → reset form
               └─ Day ≥ 15: endBatch() → navigate('/dashboard/history')

/dashboard/history
    BatchHistory table
    Shows: all batches from GET /api/batches
    Columns: Batch ID · Start Date · Duration · Final Biomass · Policy · Status
    Expanded row: real check-in logs from batch.checkIns[]
    "Continue Check-in →" button for active batches
```

---

## 4. State Management

State lives in two places that must stay in sync:

### Zustand Store (`frontend/src/store/batchStore.js`)
Persisted to `localStorage` as `bsf-batch-store`. Survives page refresh.

| Key | Type | Description |
|-----|------|-------------|
| `activeBatch` | `Object \| null` | Currently running batch (full batch object from API) |
| `currentDay` | `number` | 0-indexed day counter (0–15) |
| `checkIns` | `Array` | Local copy of confirmed check-ins for current batch |
| `batches` | `Array` | Full batch list (synced from GET /api/batches) |
| `policy` | `string` | `'ppo'` or `'rule_based'` |
| `todaySchedule` | `Object \| null` | AI-generated schedule from last check-in |

### Backend JSON (`backend/data/batches.json`)
Persistent across backend restarts. Each batch object:

```json
{
  "id": "1775573045199",
  "larvaeCount": 10000,
  "containerSize": "standard",
  "startDate": "2026-04-07",
  "location": "chennai",
  "status": "active",
  "policy": "ppo",
  "createdAt": "2026-04-07T16:30:00.000Z",
  "currentDay": 3,
  "checkIns": [
    {
      "day": 0,
      "feed_kg": 15.0,
      "recommendation": "Feed 2kg Veg + 1kg Bakery",
      "confirmed_at": "2026-04-07T17:00:00Z"
    }
  ]
}
```

---

## 5. Backend API Reference

Base URL: `http://localhost:8000`

### Batches

| Method | Endpoint | Request Body | Response |
|--------|----------|-------------|----------|
| `GET` | `/api/batches` | — | `[Batch, ...]` |
| `POST` | `/api/batches` | `{larvaeCount, containerSize, startDate, location}` | `Batch` |
| `GET` | `/api/batches/{id}` | — | `Batch` |
| `POST` | `/api/batches/{id}/checkin` | `{day, feed_kg, recommendation, confirmed_at}` | `Batch` |
| `PATCH` | `/api/batches/{id}` | `{...any batch fields}` | `Batch` |

### AI

| Method | Endpoint | Request Body | Response |
|--------|----------|-------------|----------|
| `POST` | `/api/checkin` | `{batch_id, larvae_activity, mortality_estimate, substrate_condition, smell, waste_available, estimated_larvae_count, age_days}` | `{schedule, projection, feed_instruction, ...}` |
| `GET` | `/api/report` | — | `{strategies: [...], highlights: {...}}` |

### Settings

| Method | Endpoint | Response |
|--------|----------|----------|
| `GET` | `/api/settings` | `{policy: "ppo"}` |
| `POST` | `/api/settings/policy` | `{policy: "rule_based"}` |

---

## 6. ML Pipeline

### Observation Vector (8 dimensions)
The `StateEstimator` converts farmer inputs into this vector:

| Index | Feature | Range | Source |
|-------|---------|-------|--------|
| 0 | Larval age (days) | 0–16 | Batch start date |
| 1 | Biomass estimate (mg) | 0–200 | Growth model |
| 2 | Substrate level | 0–1 | State estimator |
| 3 | Temperature (°C) | 15–45 | Weather API |
| 4 | Humidity (%) | 0–100 | Weather API |
| 5 | C:N ratio | 0–40 | Waste selection |
| 6 | Moisture % | 0–1 | State estimator |
| 7 | Hours since last feed | 0–48 | Batch info |

### Action Vector (4 dimensions, continuous 0–1)
What the PPO agent outputs:

| Index | Action | Interpretation |
|-------|--------|---------------|
| 0 | Feed amount scale | 0 = no feed, 1 = max feed |
| 1 | C:N ratio target | 0 = carbon-heavy, 1 = nitrogen-heavy |
| 2 | Moisture action | 0 = dry out, 0.5 = no change, 1 = add water |
| 3 | Aeration level | 0 = low, 1 = high |

### Training Configuration (`configs/training.yaml`)
- Algorithm: PPO (Stable-Baselines3)
- Total steps: 5,000,000
- Parallel environments: 8 (DummyVecEnv)
- Network: MLP 128×128 (actor + critic)
- Normalization: VecNormalize (obs only)
- Checkpoint: saved at each evaluation when mean reward improves

---

## 7. Key Files

| File | Purpose |
|------|---------|
| `backend/main.py` | FastAPI app — all 8 API endpoints, model loading at startup |
| `frontend/src/store/batchStore.js` | Central state — batch lifecycle, day counter, check-ins |
| `frontend/src/pages/Dashboard/DailyCheckin.jsx` | Main farmer interaction — 4-step check-in flow |
| `frontend/src/pages/Dashboard/BatchHistory.jsx` | Batch list with real data, expandable rows, search |
| `frontend/src/pages/Dashboard/index.jsx` | Dashboard layout — sidebar with live batch status |
| `frontend/src/api/client.js` | Axios client — all API calls with mock fallbacks |
| `src/translation/state_estimator.py` | Converts farmer observations → 8-dim RL vector |
| `src/translation/recommendation.py` | Converts 4-dim RL action → human-readable schedule |
| `src/environments/bsf_env.py` | Core Gymnasium simulation — 96 steps, stochastic weather |
| `src/environments/reward.py` | Multi-component reward — biomass, mortality, feed waste |
| `results/summary_comparison.csv` | Ground-truth benchmark results (4 strategies × 20 episodes) |

---

## 8. Known Issues & Limitations

| Issue | Status | Notes |
|-------|--------|-------|
| PPO model takes ~3 min to load on backend startup | Known | Normal — loading VecNormalize + SB3 model |
| High mortality in AI batches (67.8% avg) | By design | Larvae mortality in simulation reflects biological reality; AI optimizes for survivors' biomass |
| `currentDay` is 0-indexed | By design | Day 0 = first check-in, Day 15 = 16th and final check-in |
| localStorage not cleared between test runs | Manual step | Clear `bsf-batch-store` in DevTools if testing fresh flow |
| Frontend only runs on localhost:5173 in backend CORS | Config | Update `allow_origins` in `backend/main.py` for deployment |
| No authentication | Prototype scope | Single-user local tool; no user accounts |

---

## 9. Running the Project

### Requirements
- Python 3.10+
- Node.js 18+
- `pip install -r requirements.txt`

### Start Commands

**Terminal 1 — Backend:**
```bash
# From project root
uvicorn backend.main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm install      # first time only
npm run dev
```

**Open:** http://localhost:5173

### First-Time Setup
```bash
# If testing fresh (clears old broken batches):
# 1. Delete backend/data/batches.json content → replace with []
# 2. In browser DevTools → Application → Local Storage → 
#    delete 'bsf-batch-store' entry
# 3. Refresh page
```

---

## 10. Future Roadmap

| Priority | Feature | Description |
|----------|---------|-------------|
| High | IoT sensor integration | Replace state estimator with real temperature/moisture sensors |
| High | User authentication | Multi-farm support with login |
| Medium | Curriculum learning | Gradually introduce weather variability during training |
| Medium | Mobile-responsive UI | Optimize Daily Check-in for smartphone use |
| Medium | Offline mode | Service worker + local model inference (ONNX) |
| Low | Multi-batch management | Allow multiple simultaneous active batches |
| Low | Export to PDF | Generate printable harvest report |
| Low | WhatsApp integration | Send daily check-in reminders via WhatsApp API |

---

## 11. Team & Roles

| Member | Contribution |
|--------|-------------|
| **Anton Gilchrist A** | RL environment design, PPO training pipeline, evaluation scripts |
| **Dev Arjun G** | Translation layer, recommendation engine, data pipeline |
| **Jabin Joseph M** | Frontend (React), Backend (FastAPI), dashboard flow, integration |
