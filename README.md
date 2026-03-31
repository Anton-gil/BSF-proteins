# BSF-RL-Optimizer

**Black Soldier Fly Larvae Feed Optimization using Reinforcement Learning**

> Team: Anton Gilchrist A, Dev Arjun G, Jabin Joseph M  
> Domain: Agri-Tech / Sustainable Food Systems

## Overview

A simulation-based RL prototype that helps BSF farmers optimize their feeding strategies. The RL agent learns optimal feeding patterns in a simulated environment, then provides daily actionable recommendations through a Streamlit dashboard.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run config validation
python tests/test_configs.py

# Train the model (Phase 3)
python scripts/train.py

# Launch dashboard (Phase 7)
streamlit run dashboard/app.py
```

## Project Structure

```
bsf-rl-optimizer/
├── configs/          # YAML configuration files
├── src/              # Source code
│   ├── environments/ # Gymnasium environment + growth/mortality models
│   ├── agents/       # PPO agent wrapper
│   ├── baselines/    # Fixed and random policy baselines
│   ├── translation/  # Waste→C:N, weather, recommendations
│   ├── data/         # SQLite persistence layer
│   └── utils/        # Metrics and visualization helpers
├── dashboard/        # Streamlit farmer-facing UI
├── scripts/          # Training and evaluation entry points
├── tests/            # Unit tests
├── data/             # Persistent storage
└── outputs/          # Trained models and logs
```

## Tech Stack

- **RL**: PPO via Stable-Baselines3 + Gymnasium
- **Backend**: Python, NumPy, Pandas
- **Dashboard**: Streamlit
- **Config**: YAML
- **Logging**: TensorBoard
