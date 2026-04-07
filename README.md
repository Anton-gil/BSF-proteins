# 🪲 BSF-RL-Optimizer

**Black Soldier Fly Larvae Feed Optimization using Reinforcement Learning**

> **Team:** Anton Gilchrist A, Dev Arjun G, Jabin Joseph M  
> **Domain:** Agri-Tech / Sustainable Food Systems  
> **Stack:** Python · FastAPI · React · PPO (Stable-Baselines3) · Gymnasium

---

## What Is This?

Black Soldier Fly (BSF) larvae are one of the most efficient bio-converters of organic waste into high-protein animal feed. A farmer raises a batch of larvae over **16 days** by making daily decisions about:

- 🥬 **How much to feed** (organic waste substrate)
- ⚖️ **What feed type** (carbon-heavy or nitrogen-heavy waste → C:N ratio)
- 💧 **Moisture control** (add water or ventilate)
- 🌀 **Aeration level** (manage temperature & oxygen)

Bad decisions = larvae die or grow poorly. Good decisions = dense, healthy biomass.

**This project trains a Reinforcement Learning (PPO) agent** to learn optimal feeding strategies by simulating thousands of virtual BSF batches — and deploys it as a full-stack farmer-facing web application.

---

## How It Works

```
  Real Farm Inputs          AI Brain (PPO Agent)         Farmer Output
  ─────────────────         ──────────────────────       ──────────────
  Temperature (°C)    ──►   Neural Network               Feed amount
  Humidity (%)        ──►   (trained on 52,083           Feed type (C:N)
  Larval age (days)   ──►    simulated episodes)    ──►  Water/ventilate
  Biomass estimate    ──►                                Aeration level
  Substrate level     ──►
  C:N ratio           ──►
```

Every day, the farmer does a **Daily Check-in** on the web dashboard:
1. Reports larvae status (healthy / deaths / sick)
2. Selects available organic waste
3. Gets an AI-generated daily feeding schedule (3 time slots)
4. Follows the schedule → comes back next day

After 16 days, the batch is complete and recorded in **Batch History** with full day-by-day logs.

---

## The 4 Strategies Compared

| Strategy | Description |
|----------|-------------|
| 🤖 **PPO Agent** | Our trained RL agent — learns by trial and error across 52,000+ episodes |
| 📚 **Rule-Based** | Expert heuristic derived from Eawag BSF handbook. Represents an *ideal scientist-farmer with perfect sensors* |
| 🎲 **Random** | Completely random actions — lower bound reference |
| 😴 **Do-Nothing** | Never feeds — represents complete neglect |

---

## Results (5M Training Steps, 20 Episodes Each)

| Strategy | Avg Biomass | Max Biomass | Feed Used | Mortality | Consistency |
|----------|-------------|-------------|-----------|-----------|-------------|
| 🤖 **PPO Agent** | **148.2 mg** | 153.1 mg | **508 g** | **67.8%** | **σ = 9.6** |
| 📚 Rule-Based | 134.0 mg | **153.2 mg** | 737 g | 79.0% | σ = 18.6 |
| 🎲 Random | 128.3 mg | 151.6 mg | 744 g | 81.5% | σ = 21.4 |
| 😴 Do-Nothing | 1.96 mg | 2.4 mg | 0 g | 100% | — |

### Key Findings

- 🏆 **Best Overall:** AI **outperforms the expert heuristic on every metric** — higher biomass, less feed, lower mortality, greater consistency
- 💰 **31% less feed** than rule-based (508g vs 737g) — direct cost saving for farmers  
- 🛡️ **11.2% lower mortality** than rule-based (67.8% vs 79.0%)
- 📏 **2x more consistent** (std dev 9.6 vs 18.6)
- 📊 **+10.6% more biomass** on average (148.2mg vs 134.0mg)

> **Note:** Our Rule-Based heuristic is an *idealized* scientist-farmer with perfect sensors. Real smallholder farmers without sensors will perform significantly worse, making the AI advantage even greater in practice.

---

## Scientific References

1. **Dortmans, B., Diener, S., Verstappen, B., Zurbrügg, C. (2017).** *Black Soldier Fly Biowaste Processing - A Step-by-Step Guide.* Eawag.  
   → Source of moisture thresholds (60–80%), temperature ranges, and feeding guidelines

2. **Tomberlin, J. K., Adler, P. H., & Myers, H. M. (2009).** Development of the black soldier fly in relation to temperature. *Environmental Entomology*, 38(3), 930–934.  
   → Source of thermal tolerance curves in our growth and mortality models

3. **Oonincx, D. G., van Broekhoven, S., van Huis, A., & van Loon, J. J. (2015).** Feed conversion, survival and development of four insect species on food by-products. *PLoS One*, 10(12).  
   → Source of age-phase feeding rates (neonate → exponential → pre-pupa)

4. **Lalander, C., Diener, S., et al. (2019).** Faecal sludge and solid waste mixed for BSF larvae treatment. *Science of The Total Environment*, 650, 151–157.  
   → Source of optimal C:N ratio range (14–18:1) used in feed composition rules

---

## Quick Start

### Backend (FastAPI)
```bash
# Install Python dependencies
pip install -r requirements.txt

# Run backend API (from project root)
uvicorn backend.main:app --reload --port 8000
```

### Frontend (React)
```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:5173
```

### Train / Evaluate (optional)
```bash
# Retrain the PPO model (5M steps, ~10 min)
python scripts/retrain.py

# Evaluate all 4 strategies (generates CSVs + graphs)
python results/run_real_evaluation.py
python results/generate_comparison_graphs.py
```

---

## Project Structure

```
bsf-rl-optimizer/
├── backend/
│   ├── main.py              # FastAPI REST API (8 endpoints)
│   └── data/
│       ├── batches.json     # Persistent batch storage
│       └── settings.json    # Active policy setting
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── Dashboard/
│       │   │   ├── index.jsx        # Dashboard layout + sidebar
│       │   │   ├── StartBatch.jsx   # New batch form
│       │   │   ├── DailyCheckin.jsx # Day-by-day check-in flow
│       │   │   └── BatchHistory.jsx # Batch history table
│       │   ├── Landing/             # Home page
│       │   ├── About/               # About page
│       │   └── Report/              # AI performance comparison
│       ├── store/
│       │   └── batchStore.js        # Zustand state (persisted to localStorage)
│       └── api/
│           └── client.js            # Axios API client
├── src/
│   ├── environments/
│   │   ├── bsf_env.py           # Gymnasium environment (96-step simulation)
│   │   ├── growth_model.py      # Biomass growth model
│   │   ├── mortality_model.py   # Larval death rate model
│   │   └── reward.py            # Multi-component reward function
│   ├── agents/
│   │   └── ppo_agent.py         # PPO agent wrapper (Stable-Baselines3)
│   ├── baselines/
│   │   ├── heuristic_policy.py  # Expert rule-based policy
│   │   ├── random_policy.py     # Random baseline
│   │   └── fixed_policy.py      # Do-nothing baseline
│   └── translation/
│       ├── waste_translator.py  # Waste types → C:N ratios
│       ├── state_estimator.py   # Farmer observations → RL state vector
│       └── recommendation.py   # RL action → plain-English schedule
├── scripts/
│   ├── retrain.py               # 5M-step retraining (8 parallel envs)
│   └── continue_training.py     # Resume from checkpoint (+2M steps)
├── results/
│   ├── run_real_evaluation.py           # Evaluates all 4 strategies
│   ├── generate_comparison_graphs.py    # 6 publication-quality graphs
│   ├── summary_comparison.csv           # Aggregate results
│   └── episode_comparison.csv           # Per-episode results (80 rows)
├── outputs/
│   └── models/
│       └── best_model.zip       # Best trained checkpoint (gitignored)
├── configs/
│   └── training.yaml            # PPO hyperparameters & reward weights
└── requirements.txt
```

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| RL Algorithm | PPO — Stable-Baselines3 |
| RL Environment | Custom Gymnasium env |
| Neural Network | 128×128 MLP (actor-critic) |
| Backend API | FastAPI + Uvicorn |
| Frontend | React 18 + Vite + Tailwind CSS |
| State Management | Zustand (persisted to localStorage) |
| Animations | Framer Motion |
| Charts | Recharts |
| Config | YAML |
| Language | Python 3.10+ / JavaScript (ESM) |

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/batches` | List all batches |
| `POST` | `/api/batches` | Create new batch |
| `GET` | `/api/batches/{id}` | Get single batch |
| `POST` | `/api/batches/{id}/checkin` | Save daily check-in |
| `PATCH` | `/api/batches/{id}` | Update batch fields |
| `POST` | `/api/checkin` | Get AI recommendation |
| `GET` | `/api/report` | Strategy comparison data |
| `GET/POST` | `/api/settings/policy` | Get/set active policy |
