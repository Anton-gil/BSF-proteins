#!/usr/bin/env python3
"""
BSF Real Evaluation Script (v2)

Evaluates all 4 strategies over 20 episodes each using real BSFEnv simulation.

KEY FIX: PPO was trained with VecNormalize (observations normalized to
mean~0, std~1). We MUST use the same normalization at evaluation time,
otherwise the model receives inputs it has never seen --> garbage output.

Think of it like this: if you train a model to recognize temperatures in
Celsius, then test it with Fahrenheit values it will fail, not because
it's a bad model, but because the input format doesn't match.
"""

import sys
import glob
import csv
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
from stable_baselines3.common.monitor import Monitor

from src.environments.bsf_env import BSFEnv
from src.baselines.base_policy import BasePolicy
from src.baselines.random_policy import RandomPolicy
from src.baselines.heuristic_policy import HeuristicPolicy

RESULTS_DIR = Path(__file__).parent
MODELS_DIR  = Path("outputs/models")
N_EPISODES  = 20
SEED        = 42


# ── Do-Nothing policy ──────────────────────────────────────────────────────
class DoNothingPolicy(BasePolicy):
    """Never feed. Represents worst-case neglect — the lower bound."""
    def __init__(self):
        super().__init__(name="Do-Nothing")

    def predict(self, observation, deterministic=True):
        self.total_steps += 1
        # action[1] = 0.0 → below 0.1 threshold in env._scale_action → no feed
        return np.array([0.5, 0.0, 0.15, 0.5], dtype=np.float32)

    def reset(self):
        self.episode_count += 1


# ── Evaluate a simple (non-PPO) baseline ──────────────────────────────────
def evaluate_baseline(policy: BasePolicy, n_episodes: int):
    """
    Run n_episodes on a raw BSFEnv (no normalization needed for baselines
    since they use hand-coded rules or random actions, not a neural network).
    """
    env = BSFEnv(stochastic_weather=True)
    results = []

    for ep in range(n_episodes):
        obs, _ = env.reset(seed=ep + SEED)
        policy.reset()
        done = False
        total_reward = 0.0
        steps = 0
        info = {}

        while not done:
            action = policy.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)
            total_reward += reward
            steps += 1
            done = terminated or truncated

        ep_info      = info.get('episode', {})
        final_bm     = ep_info.get('final_biomass_mg', info.get('biomass_mg', 0.0))
        final_surv   = ep_info.get('final_survival_rate', info.get('survival_rate', 0.0))
        total_feed_g = ep_info.get('total_feed_kg', info.get('total_feed_kg', 0.0)) * 1000.0

        results.append({
            'strategy':         policy.name,
            'episode':          ep + 1,
            'final_biomass_mg': round(final_bm, 2),
            'total_reward':     round(total_reward, 2),
            'total_feed_g':     round(total_feed_g, 2),
            'mortality_pct':    round((1.0 - final_surv) * 100.0, 2),
            'survival_pct':     round(final_surv * 100.0, 2),
            'steps':            steps,
        })

    return results


# ── Evaluate PPO with its VecNormalize wrapper ────────────────────────────
def evaluate_ppo(model: PPO, vec_norm: VecNormalize, n_episodes: int):
    """
    Evaluate PPO correctly using the VecNormalize wrapper from training.

    Why different from baselines?
    The neural network was trained on NORMALIZED observations (each input
    feature rescaled to mean~0, std~1). If we feed it raw values it will
    generate incorrect actions. We load the saved normalization stats and
    apply them here with training=False (stats frozen -- no updates).
    """
    vec_norm.training    = False  # Freeze normalization stats
    vec_norm.norm_reward = False  # Don't normalize rewards at eval time

    results = []

    for ep in range(n_episodes):
        obs      = vec_norm.reset()
        done     = False
        total_reward = 0.0
        steps    = 0
        info     = {}

        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, dones, infos = vec_norm.step(action)
            total_reward += float(reward[0])
            steps += 1
            done  = bool(dones[0])
            info  = infos[0] if infos else {}

        ep_info      = info.get('episode', {})
        final_bm     = ep_info.get('final_biomass_mg', info.get('biomass_mg', 0.0))
        final_surv   = ep_info.get('final_survival_rate', info.get('survival_rate', 0.0))
        total_feed_g = ep_info.get('total_feed_kg', info.get('total_feed_kg', 0.0)) * 1000.0

        results.append({
            'strategy':         'PPO Agent',
            'episode':          ep + 1,
            'final_biomass_mg': round(final_bm, 2),
            'total_reward':     round(total_reward, 2),
            'total_feed_g':     round(total_feed_g, 2),
            'mortality_pct':    round((1.0 - final_surv) * 100.0, 2),
            'survival_pct':     round(final_surv * 100.0, 2),
            'steps':            steps,
        })

    return results


# ── CSV helpers ───────────────────────────────────────────────────────────
def save_episode_csv(all_results, path):
    fieldnames = ['strategy', 'episode', 'final_biomass_mg', 'total_reward',
                  'total_feed_g', 'mortality_pct', 'survival_pct', 'steps']
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in all_results:
            writer.writerow(row)


def compute_summary(all_results):
    groups = defaultdict(list)
    for r in all_results:
        groups[r['strategy']].append(r)

    rows = []
    for strat, episodes in groups.items():
        biomasses = [e['final_biomass_mg'] for e in episodes]
        rewards   = [e['total_reward']     for e in episodes]
        feeds     = [e['total_feed_g']     for e in episodes]
        morts     = [e['mortality_pct']    for e in episodes]
        rows.append({
            'strategy':      strat,
            'avg_biomass':   round(np.mean(biomasses), 2),
            'std_biomass':   round(np.std(biomasses),  2),
            'max_biomass':   round(np.max(biomasses),  2),
            'avg_reward':    round(np.mean(rewards),   2),
            'avg_feed_g':    round(np.mean(feeds),     2),
            'avg_mortality': round(np.mean(morts),     2),
        })
    return rows


def save_summary_csv(summary_rows, path):
    fieldnames = ['strategy', 'avg_biomass', 'std_biomass', 'max_biomass',
                  'avg_reward', 'avg_feed_g', 'avg_mortality']
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in summary_rows:
            writer.writerow(row)


# ── Main ──────────────────────────────────────────────────────────────────
def main():
    np.random.seed(SEED)

    print("\n" + "=" * 65)
    print("  BSF Real Evaluation (v2) -- 4 Strategies x 20 Episodes")
    print("=" * 65)

    all_results = []

    # ── 1) PPO Agent (with VecNormalize) ──────────────────────────────
    model_path    = MODELS_DIR / "best_model"
    vecnorm_files = sorted(glob.glob(str(MODELS_DIR / "*vecnormalize*.pkl")))

    print(f"\n[1/4] PPO Agent")
    print(f"      Model:        {model_path}.zip")

    if vecnorm_files:
        vecnorm_path = vecnorm_files[-1]
        print(f"      VecNormalize: {Path(vecnorm_path).name}")
    else:
        vecnorm_path = None
        print("      VecNormalize: NOT FOUND")

    try:
        def make_raw_env():
            env = BSFEnv(stochastic_weather=True)
            return Monitor(env)

        vec_env = DummyVecEnv([make_raw_env])

        if vecnorm_path:
            vec_norm = VecNormalize.load(vecnorm_path, vec_env)
        else:
            vec_norm = VecNormalize(vec_env, norm_obs=True, norm_reward=False)

        model = PPO.load(str(model_path), env=vec_norm)
        print("      Status:       Loaded OK")

        ppo_results = evaluate_ppo(model, vec_norm, N_EPISODES)
        all_results.extend(ppo_results)

        bm = np.mean([r['final_biomass_mg'] for r in ppo_results])
        rw = np.mean([r['total_reward']     for r in ppo_results])
        mt = np.mean([r['mortality_pct']    for r in ppo_results])
        print(f"      avg_biomass={bm:.1f} mg  avg_reward={rw:.1f}  avg_mortality={mt:.1f}%")

    except Exception as exc:
        print(f"      ERROR: {exc}")
        print("      Skipping PPO evaluation.")

    # ── 2-4) Baselines ────────────────────────────────────────────────
    baselines = [
        ("Rule-Based", HeuristicPolicy()),
        ("Random",     RandomPolicy(seed=SEED)),
        ("Do-Nothing", DoNothingPolicy()),
    ]
    for idx, (label, policy) in enumerate(baselines, 2):
        policy.name = label
        print(f"\n[{idx}/4] {label}")
        results = evaluate_baseline(policy, N_EPISODES)
        all_results.extend(results)

        bm = np.mean([r['final_biomass_mg'] for r in results])
        rw = np.mean([r['total_reward']     for r in results])
        mt = np.mean([r['mortality_pct']    for r in results])
        print(f"      avg_biomass={bm:.1f} mg  avg_reward={rw:.1f}  avg_mortality={mt:.1f}%")

    # ── Save CSVs ─────────────────────────────────────────────────────
    episode_csv = RESULTS_DIR / "episode_comparison.csv"
    save_episode_csv(all_results, episode_csv)

    summary_rows = compute_summary(all_results)
    summary_csv  = RESULTS_DIR / "summary_comparison.csv"
    save_summary_csv(summary_rows, summary_csv)

    print("\n\n" + "=" * 95)
    print(f"{'Strategy':<15} {'Avg Biomass':>12} {'Std Biomass':>12} {'Max Biomass':>12}"
          f" {'Avg Reward':>12} {'Avg Feed(g)':>12} {'Avg Mort%':>10}")
    print("-" * 95)
    for row in summary_rows:
        print(f"{row['strategy']:<15} {row['avg_biomass']:>12.2f} {row['std_biomass']:>12.2f}"
              f" {row['max_biomass']:>12.2f} {row['avg_reward']:>12.2f}"
              f" {row['avg_feed_g']:>12.2f} {row['avg_mortality']:>10.2f}")
    print("=" * 95)

    print(f"\n  Saved: {episode_csv}")
    print(f"  Saved: {summary_csv}")
    print("\n[OK] Evaluation complete.\n")


if __name__ == "__main__":
    main()
