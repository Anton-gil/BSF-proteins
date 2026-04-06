# 🪲 BSF-RL-Optimizer

**Black Soldier Fly Larvae Feed Optimization using Reinforcement Learning**

> **Team:** Anton Gilchrist A, Dev Arjun G, Jabin Joseph M
> **Domain:** Agri-Tech / Sustainable Food Systems

---

## What Is This?

Black Soldier Fly (BSF) larvae are one of the most efficient bio-converters of organic waste into high-protein animal feed. A farmer raises a batch of larvae over 16 days by making daily decisions about:

- 🥬 **How much to feed** (organic waste substrate)
- ⚖️ **What feed type** (carbon-heavy or nitrogen-heavy waste → affects C:N ratio)
- 💧 **Moisture control** (add water or ventilate)
- 🌀 **Aeration level** (manage temperature & oxygen)

Bad decisions = larvae die or grow poorly. Good decisions = dense, healthy biomass.

**This project trains a Reinforcement Learning (PPO) agent** to learn optimal feeding strategies by simulating thousands of virtual BSF batches — and compares it against expert rule-based farming practices.

---

## How It Works

```
  Real Farm Inputs          AI Brain (PPO Agent)         Farmer Output
  ─────────────────         ──────────────────────       ──────────────
  Temperature (°C)    ──►   Neural Network               Feed amount
  Humidity (%)        ──►   (trained on 52,083           Feed type
  Larval age (days)   ──►    simulated episodes)    ──►  Water/ventilate
  Biomass estimate    ──►                                Aeration level
  Substrate level     ──►
  C:N ratio           ──►
```

Every 4 hours (96 decision points over 16 days), the agent observes the farm state and outputs 4 actions. It was trained using **Proximal Policy Optimization (PPO)** via Stable-Baselines3 in a custom Gymnasium environment with stochastic weather simulation, using **8 parallel environments** for fast rollout collection.

### The 4 Strategies Compared

| Strategy | Description |
|----------|-------------|
| 🤖 **PPO Agent** | Our trained RL agent — learns by trial and error across 52,000+ episodes |
| 📚 **Rule-Based** | Expert heuristic derived from published BSF biology research (Eawag handbook). Represents an *ideal scientist-farmer with sensors* |
| 🎲 **Random** | Completely random actions — lower bound reference |
| 😴 **Do-Nothing** | Never feeds. Represents complete neglect |

---

## Results (5M Training Steps, 20 Episodes Each)

| Strategy | Avg Biomass | Max Biomass | Avg Reward | Feed Used | Mortality |
|----------|-------------|-------------|------------|-----------|-----------|
| 🤖 PPO Agent | **148.2 mg** | 153.1 mg | **+89.1** | **508 g** | **67.8%** |
| 📚 Rule-Based | 134.0 mg | **153.2 mg** | +63.1 | 737 g | 79.0% |
| 🎲 Random | 128.3 mg | 151.6 mg | +52.7 | 744 g | 81.5% |
| 😴 Do-Nothing | 1.96 mg | 2.4 mg | -162.9 | 0 g | 100% |

### Key Findings

- **🏆 Best Overall Performance:** The AI **outperforms the expert heuristic on every metric** — higher biomass, less feed, lower mortality, and greater consistency
- **🥬 Biomass Leader:** 148.2mg average vs 134.0mg for Rule-Based — **+10.6% more biomass**
- **💰 Feed Efficiency:** The AI uses **31% less feed** than the rule-based heuristic (508g vs 737g per batch) — a direct cost saving for farmers
- **🛡️ Lowest Mortality:** 67.8% mortality vs 79.0% — the AI keeps **more larvae alive**
- **📏 Most Consistent:** Std dev of 9.6 vs 18.6 — the AI is **twice as consistent** as the expert
- **🧪 Important context:** Our "Rule-Based" heuristic is an *idealized* expert farmer with perfect sensor data. Real smallholder farmers without sensors likely perform much worse

---

## Scientific References

The environment parameters, growth curves, and heuristic thresholds are based on:

1. **Dortmans, B., Diener, S., Verstappen, B., Zurbrügg, C. (2017).** *Black Soldier Fly Biowaste Processing - A Step-by-Step Guide.* Eawag: Swiss Federal Institute of Aquatic Science and Technology.
   - Source of moisture thresholds (60–80%), temperature ranges, and feeding guidelines used in our heuristic rules.

2. **Tomberlin, J. K., Adler, P. H., & Myers, H. M. (2009).** Development of the black soldier fly (Diptera: Stratiomyidae) in relation to temperature. *Environmental Entomology*, 38(3), 930–934.
   - Source of thermal tolerance curves used in our growth and mortality models.

3. **Oonincx, D. G., van Broekhoven, S., van Huis, A., & van Loon, J. J. (2015).** Feed conversion, survival and development, and composition of four insect species on diets composed of food by-products. *PLoS One*, 10(12), e0144601.
   - Source of age-phase feeding rates (neonates → exponential → pre-pupa) used in our heuristic.

4. **Lalander, C., Diener, S., Magri, M. E., Zurbrügg, C., Lindström, A., & Vinnerås, B. (2019).** Faecal sludge and solid waste mixed for optimization of black soldier fly larvae treatment. *Science of The Total Environment*, 650, 151–157.
   - Source of optimal C:N ratio range (14–18:1) used in feed composition rules.

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Train the model (5M steps, ~10 min with 8 parallel envs)
python scripts/retrain.py

# 3. Run evaluation (generates CSVs + 6 comparison graphs)
python results/run_real_evaluation.py
python results/generate_comparison_graphs.py

# 4. Launch the farmer dashboard
streamlit run dashboard/app.py
```

---

## Project Structure

```
bsf-rl-optimizer/
├── configs/
│   └── training.yaml        # PPO hyperparameters & reward weights
├── src/
│   ├── environments/
│   │   ├── bsf_env.py       # Gymnasium environment (96-step BSF simulation)
│   │   ├── growth_model.py  # Biomass growth based on feed & temperature
│   │   ├── mortality_model.py # Larval death rate model
│   │   └── reward.py        # Multi-component reward function
│   ├── agents/
│   │   └── ppo_agent.py     # PPO agent wrapper (Stable-Baselines3)
│   ├── baselines/
│   │   ├── heuristic_policy.py  # Expert rule-based policy
│   │   ├── random_policy.py     # Random baseline
│   │   └── fixed_policy.py      # Do-nothing baseline
│   ├── translation/
│   │   ├── waste_translator.py  # Maps farmer waste types → C:N ratios
│   │   ├── weather_client.py    # Live/simulated weather data
│   │   ├── state_estimator.py   # Farmer observations → RL state vector
│   │   └── recommendation.py   # RL action → plain-English advice
│   └── data/                # SQLite persistence layer
├── dashboard/
│   └── app.py               # Streamlit farmer UI (Daily check-in + AI Report)
├── scripts/
│   ├── retrain.py           # 5M-step retraining script (v4, 8 parallel envs)
│   └── train.py             # Original training script
├── results/
│   ├── run_real_evaluation.py       # Evaluates all 4 strategies
│   ├── generate_comparison_graphs.py # Generates 6 publication-quality graphs
│   ├── summary_comparison.csv       # Aggregate results
│   └── episode_comparison.csv       # Per-episode results (80 rows)
├── outputs/
│   └── models/
│       ├── best_model.zip           # Best performing checkpoint
│       └── best_model_v1.zip        # Pre-retraining backup
└── tests/                   # Unit tests for env, reward, translation
```

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| RL Algorithm | PPO — Stable-Baselines3 |
| Environment | Custom Gymnasium env |
| Neural Network | 128×128 MLP (actor-critic) |
| Dashboard | Streamlit |
| Config | YAML |
| Logging | TensorBoard |
| Language | Python 3.10+ |
