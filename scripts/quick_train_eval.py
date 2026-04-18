#!/usr/bin/env python3
"""
Quick Train + Evaluate
Trains PPO for 1M steps (4 parallel envs) then evaluates vs all baselines.
Expected runtime: 8-15 minutes on Mac M-series.
"""

import sys, csv, time, glob
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))   # project root on sys.path

import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv, DummyVecEnv, VecNormalize
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.callbacks import (
    EvalCallback, CallbackList, BaseCallback
)

from src.environments.bsf_env import BSFEnv
from src.baselines.base_policy  import BasePolicy
from src.baselines.heuristic_policy import HeuristicPolicy
from src.baselines.random_policy    import RandomPolicy

# ── Do-Nothing policy (inline, same as run_real_evaluation.py) ─────────────
class DoNothingPolicy(BasePolicy):
    """Never feeds — serves as lower-bound baseline."""
    def __init__(self):
        super().__init__(name="Do-Nothing")
    def predict(self, obs):
        return np.zeros(4, dtype=np.float32)

# ── Config ─────────────────────────────────────────────────────────────────
MODELS_DIR  = Path("outputs/models")
RESULTS_DIR = Path("results")
SEED        = 42
N_EPISODES  = 20
TOTAL_STEPS = 1_000_000   # 1M steps ≈ 8-15 min


# ── Progress callback ───────────────────────────────────────────────────────
class ProgressCallback(BaseCallback):
    LOG_EVERY = 100_000

    def __init__(self):
        super().__init__()
        self.ep_rewards   = []
        self.ep_biomasses = []
        self.ep_survivals = []
        self.last_log     = 0
        self.start_time   = time.time()

    def _on_step(self) -> bool:
        for info in self.locals.get("infos", []):
            if "episode" in info:
                self.ep_rewards.append(info["episode"]["r"])
            if "biomass_mg" in info:
                self.ep_biomasses.append(info["biomass_mg"])
            if "survival_rate" in info:
                self.ep_survivals.append(info["survival_rate"] * 100)

        if self.n_calls - self.last_log >= self.LOG_EVERY and self.ep_rewards:
            elapsed  = time.time() - self.start_time
            pct      = self.n_calls / TOTAL_STEPS * 100
            recent_r = np.mean(self.ep_rewards[-20:])
            recent_b = np.mean(self.ep_biomasses[-20:]) if self.ep_biomasses else 0.0
            recent_s = np.mean(self.ep_survivals[-20:]) if self.ep_survivals else 0.0
            steps_left = TOTAL_STEPS - self.n_calls
            eta = steps_left / (self.n_calls / elapsed) if elapsed > 0 else 0
            print(f"  [{pct:5.1f}%] Step {self.n_calls:,}/{TOTAL_STEPS:,} | "
                  f"reward={recent_r:+.1f} | biomass={recent_b:.1f}mg | "
                  f"survival={recent_s:.1f}% | eta ~{eta/60:.0f}min")
            self.last_log = self.n_calls
        return True


# ── Environment factory ─────────────────────────────────────────────────────
def make_env(rank=0):
    def _init():
        env = BSFEnv(stochastic_weather=True)
        return Monitor(env)
    return _init


# ── Evaluation helpers ──────────────────────────────────────────────────────
def evaluate_baseline(policy, n_episodes):
    results = []
    for ep in range(n_episodes):
        env       = BSFEnv(stochastic_weather=True)
        obs, _    = env.reset(seed=ep + SEED)
        done      = False
        total_reward = 0.0
        steps     = 0
        info      = {}
        while not done:
            action = policy.predict(obs)
            obs, reward, terminated, truncated, info = env.step(action)
            total_reward += reward
            steps += 1
            done  = terminated or truncated
        ep_info = info.get("episode", {})
        bm   = ep_info.get("final_biomass_mg", info.get("biomass_mg",   0.0))
        surv = ep_info.get("final_survival_rate", info.get("survival_rate", 0.0))
        feed = ep_info.get("total_feed_kg", info.get("total_feed_kg",   0.0)) * 1000.0
        results.append({
            "strategy":         policy.name,
            "episode":          ep + 1,
            "final_biomass_mg": round(bm,   2),
            "total_reward":     round(total_reward, 2),
            "total_feed_g":     round(feed, 2),
            "mortality_pct":    round((1 - surv) * 100, 2),
            "survival_pct":     round(surv * 100,       2),
            "steps":            steps,
        })
    return results


def evaluate_ppo(model, vec_norm, n_episodes):
    vec_norm.training    = False
    vec_norm.norm_reward = False
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
        ep_info = info.get("episode", {})
        bm   = ep_info.get("final_biomass_mg", info.get("biomass_mg",   0.0))
        surv = ep_info.get("final_survival_rate", info.get("survival_rate", 0.0))
        feed = ep_info.get("total_feed_kg", info.get("total_feed_kg",   0.0)) * 1000.0
        results.append({
            "strategy":         "PPO Agent",
            "episode":          ep + 1,
            "final_biomass_mg": round(bm,   2),
            "total_reward":     round(total_reward, 2),
            "total_feed_g":     round(feed, 2),
            "mortality_pct":    round((1 - surv) * 100, 2),
            "survival_pct":     round(surv * 100,       2),
            "steps":            steps,
        })
    return results


def compute_summary(all_results):
    groups = defaultdict(list)
    for r in all_results:
        groups[r["strategy"]].append(r)
    rows = []
    for strat, episodes in groups.items():
        bms   = [e["final_biomass_mg"] for e in episodes]
        rews  = [e["total_reward"]     for e in episodes]
        feeds = [e["total_feed_g"]     for e in episodes]
        morts = [e["mortality_pct"]    for e in episodes]
        rows.append({
            "strategy":      strat,
            "avg_biomass":   round(np.mean(bms),   2),
            "std_biomass":   round(np.std(bms),    2),
            "max_biomass":   round(np.max(bms),    2),
            "avg_reward":    round(np.mean(rews),  2),
            "avg_feed_g":    round(np.mean(feeds), 2),
            "avg_mortality": round(np.mean(morts), 2),
        })
    return rows


def save_csvs(all_results, summary_rows):
    ep_fields = ["strategy","episode","final_biomass_mg","total_reward",
                 "total_feed_g","mortality_pct","survival_pct","steps"]
    with open(RESULTS_DIR / "episode_comparison.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ep_fields)
        w.writeheader()
        w.writerows(all_results)

    sm_fields = ["strategy","avg_biomass","std_biomass","max_biomass",
                 "avg_reward","avg_feed_g","avg_mortality"]
    with open(RESULTS_DIR / "summary_comparison.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=sm_fields)
        w.writeheader()
        w.writerows(summary_rows)


# ── Main ────────────────────────────────────────────────────────────────────
def main():
    np.random.seed(SEED)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    print("\n" + "=" * 65)
    print("  BSF Quick Train + Eval — 1M Steps → 20 Episodes per Strategy")
    print("=" * 65)

    # ────────────────────────── TRAIN ──────────────────────────────────
    N_ENVS = 4
    print(f"\n[TRAIN] {TOTAL_STEPS:,}-step PPO with {N_ENVS} parallel envs…")

    train_env = SubprocVecEnv([make_env(i) for i in range(N_ENVS)])
    train_env = VecNormalize(
        train_env, norm_obs=True, norm_reward=True,
        clip_obs=10.0, clip_reward=10.0
    )

    eval_env = DummyVecEnv([make_env(99)])
    eval_env = VecNormalize(eval_env, norm_obs=True, norm_reward=False, clip_obs=10.0)

    model = PPO(
        policy="MlpPolicy",
        env=train_env,
        learning_rate=3e-4,
        n_steps=2048,
        batch_size=256,
        n_epochs=10,
        gamma=0.995,
        gae_lambda=0.95,
        clip_range=0.2,
        ent_coef=0.01,
        vf_coef=0.5,
        max_grad_norm=0.5,
        policy_kwargs={"net_arch": dict(pi=[128, 128], vf=[128, 128])},
        verbose=0,
    )

    vecnorm_path = str(MODELS_DIR / "best_model_vecnormalize.pkl")

    progress_cb = ProgressCallback()
    eval_cb = EvalCallback(
        eval_env,
        best_model_save_path=str(MODELS_DIR),
        log_path=str(MODELS_DIR),
        eval_freq=50_000,
        n_eval_episodes=10,
        deterministic=True,
        render=False,
        verbose=0,
    )

    model.learn(
        total_timesteps=TOTAL_STEPS,
        callback=CallbackList([progress_cb, eval_cb]),
        progress_bar=False,
        reset_num_timesteps=True,
    )

    train_env.save(vecnorm_path)
    train_elapsed = (time.time() - t0) / 60
    print(f"\n[TRAIN] Done in {train_elapsed:.1f} min  →  best_model.zip saved")

    if progress_cb.ep_biomasses:
        last20_b = np.mean(progress_cb.ep_biomasses[-20:])
        last20_r = np.mean(progress_cb.ep_rewards[-20:])
        last20_s = np.mean(progress_cb.ep_survivals[-20:])
        print(f"        Final 20-ep: biomass={last20_b:.1f}mg | reward={last20_r:+.1f} | survival={last20_s:.1f}%")

    # ────────────────────────── EVALUATE ───────────────────────────────
    print(f"\n[EVAL] {N_EPISODES} episodes per strategy (deterministic)…")
    all_results = []

    # PPO Agent
    best_path    = str(MODELS_DIR / "best_model")
    vec_env_ppo  = DummyVecEnv([make_env(0)])
    vec_norm_ppo = VecNormalize.load(vecnorm_path, vec_env_ppo)
    ppo_model    = PPO.load(best_path, env=vec_norm_ppo)
    ppo_results  = evaluate_ppo(ppo_model, vec_norm_ppo, N_EPISODES)
    all_results.extend(ppo_results)
    bm_ppo = np.mean([r["final_biomass_mg"] for r in ppo_results])
    print(f"  ✓ PPO Agent    → avg_biomass={bm_ppo:.1f} mg")

    # Baselines
    for label, policy in [
        ("Rule-Based", HeuristicPolicy()),
        ("Random",     RandomPolicy(seed=SEED)),
        ("Do-Nothing", DoNothingPolicy()),
    ]:
        policy.name = label
        res = evaluate_baseline(policy, N_EPISODES)
        all_results.extend(res)
        bm = np.mean([r["final_biomass_mg"] for r in res])
        print(f"  ✓ {label:<12} → avg_biomass={bm:.1f} mg")

    # ────────────────────────── SAVE ───────────────────────────────────
    summary_rows = compute_summary(all_results)
    save_csvs(all_results, summary_rows)

    # Sort by avg_biomass descending for display
    summary_rows.sort(key=lambda r: r["avg_biomass"], reverse=True)

    print("\n" + "=" * 72)
    print(f"  {'Rank':<6} {'Strategy':<14} {'Avg Biomass':>12} {'Max Biomass':>12} {'Avg Reward':>12} {'Std Dev':>9}")
    print("  " + "-" * 66)
    for rank, r in enumerate(summary_rows, 1):
        tag = " ← BEST 🏆" if rank == 1 else ""
        print(f"  #{rank:<5} {r['strategy']:<14} {r['avg_biomass']:>10.1f} mg "
              f"{r['max_biomass']:>10.1f} mg {r['avg_reward']:>10.1f}  "
              f"σ={r['std_biomass']:>5.1f}{tag}")
    print("=" * 72)

    total_min = (time.time() - t0) / 60
    print(f"\n  Total time: {total_min:.1f} min")
    print("  CSVs updated → backend will reload automatically (--reload)")
    print("\n[DONE]\n")


if __name__ == "__main__":
    main()
