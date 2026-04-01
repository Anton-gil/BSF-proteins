#!/usr/bin/env python3
"""
BSF PPO Continue-Training Script — Parallel (4 envs)

Resumes from best_model.zip and trains for 2,000,000 MORE steps
using 4 parallel environments via SubprocVecEnv.

WHY 4 PARALLEL ENVIRONMENTS?
─────────────────────────────
Normal training (1 env):
  Step → get 1 experience → repeat 4096 times → 1 update

4 parallel envs:
  Step → get 4 experiences simultaneously (one per CPU core)
  1024 steps × 4 envs = 4096 experiences per update (same total)
  But wall-clock time is ~3-4x less because all 4 farms run at once.

The model doesn't "know" 4 envs were used — it just sees
4096 diverse experiences per update instead of 4096 sequential ones.
The VecNormalize stats update correctly across all 4 envs.

CONTINUITY:
  We load the VecNormalize stats from the previous 1M-step run.
  The normalization mean/std continues to update from where it left off.
  The model weights continue improving from the previous best checkpoint.

Usage:
    python scripts/continue_training.py
"""

import sys
import glob
import shutil
from pathlib import Path
from datetime import datetime

# Must be at top level for SubprocVecEnv on Windows
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import (
    EvalCallback, CheckpointCallback, CallbackList, BaseCallback
)
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import (
    DummyVecEnv, SubprocVecEnv, VecNormalize
)

from src.environments.bsf_env import BSFEnv

MODELS_DIR  = Path("outputs/models")
LOGS_DIR    = Path("outputs/logs")
N_ENVS      = 4          # Number of parallel farm simulations
N_STEPS     = 1024       # Steps per env per update → 4×1024 = 4096 total (same as before)
EXTRA_STEPS = 2_000_000  # Additional steps to train


class ProgressCallback(BaseCallback):
    """Print a readable progress summary every LOG_EVERY steps."""
    LOG_EVERY = 50_000

    def __init__(self):
        super().__init__()
        self.ep_rewards   = []
        self.ep_biomasses = []
        self.ep_survivals = []
        self.last_log     = 0

    def _on_step(self) -> bool:
        for info in self.locals.get("infos", []):
            ep = info.get("episode", {})
            if ep:
                self.ep_rewards.append(ep.get("r", 0))
                self.ep_biomasses.append(info.get("biomass_mg", 0))
                self.ep_survivals.append(info.get("survival_rate", 0) * 100)

        if self.n_calls - self.last_log >= self.LOG_EVERY and self.ep_rewards:
            pct      = self.n_calls / EXTRA_STEPS * 100
            recent_r = np.mean(self.ep_rewards[-30:])
            recent_b = np.mean(self.ep_biomasses[-30:]) if self.ep_biomasses else 0
            recent_s = np.mean(self.ep_survivals[-30:]) if self.ep_survivals else 0
            print(f"\n  [{pct:5.1f}%] Step {self.n_calls:,} / {EXTRA_STEPS:,}")
            print(f"         Avg reward   (last 30 eps): {recent_r:+.2f}")
            print(f"         Avg survival:               {recent_s:.1f}%")
            print(f"         Avg biomass:                {recent_b:.1f} mg")
            self.last_log = self.n_calls
        return True


def make_env_fn(rank: int):
    """Factory: returns a function that creates one BSFEnv (for SubprocVecEnv)."""
    def _init():
        env = BSFEnv(stochastic_weather=True)
        env = Monitor(env)
        return env
    return _init


def main():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    print("\n" + "=" * 65)
    print(f"  BSF-RL-OPTIMIZER — Continue Training (+2M Steps, {N_ENVS} envs)")
    print("=" * 65)

    model_path    = MODELS_DIR / "best_model"
    vecnorm_files = sorted(glob.glob(str(MODELS_DIR / "*vecnormalize*.pkl")))
    vecnorm_path  = vecnorm_files[-1] if vecnorm_files else None

    print(f"\n  [LOAD] Model:        {model_path}.zip")
    print(f"  [LOAD] VecNormalize: {Path(vecnorm_path).name if vecnorm_path else 'NOT FOUND — will start fresh'}")
    print(f"  [SETUP] {N_ENVS} parallel environments (SubprocVecEnv)")
    print(f"  [SETUP] {N_STEPS} steps/env/update × {N_ENVS} envs = {N_STEPS*N_ENVS} total per update\n")

    # ── Build parallel training environments ──────────────────────────────
    # DummyVecEnv runs N_ENVS farms in a tight sequential loop — no subprocess
    # spawn overhead (which is very slow on Windows with SubprocVecEnv).
    # The benefit is 4x more diverse experience per update cycle:
    # each batch of 4096 steps comes from 4 different farm runs with
    # different weather seeds, rather than one farm sequentially.
    train_vec = DummyVecEnv([make_env_fn(i) for i in range(N_ENVS)])
    print(f"  [OK] DummyVecEnv with {N_ENVS} environments active")


    # Load or create VecNormalize with the previous run's statistics
    if vecnorm_path:
        train_norm = VecNormalize.load(vecnorm_path, train_vec)
        train_norm.training    = True   # Keep updating stats
        train_norm.norm_reward = True
    else:
        train_norm = VecNormalize(
            train_vec, norm_obs=True, norm_reward=True,
            clip_obs=10.0, clip_reward=10.0
        )

    # ── Build single eval environment ─────────────────────────────────────
    eval_vec = DummyVecEnv([make_env_fn(99)])
    if vecnorm_path:
        eval_norm = VecNormalize.load(vecnorm_path, eval_vec)
        eval_norm.training    = False
        eval_norm.norm_reward = False
    else:
        eval_norm = VecNormalize(eval_vec, norm_obs=True, norm_reward=False, clip_obs=10.0)

    # ── Load model from last checkpoint ───────────────────────────────────
    # n_steps is adjusted to 1024 so that 4 envs × 1024 = 4096 total
    # (same effective rollout size as the single-env run's 4096)
    model = PPO.load(str(model_path), env=train_norm)
    model.n_steps    = N_STEPS          # Override for 4-env efficiency
    model.batch_size = 512              # Larger batch (more data per update)
    model._setup_model()                # Rebuild internal buffers for new n_steps
    print(f"  [OK] Model loaded. n_steps={N_STEPS}, batch={model.batch_size}")

    # ── Callbacks ─────────────────────────────────────────────────────────
    progress_cb = ProgressCallback()

    eval_cb = EvalCallback(
        eval_norm,
        best_model_save_path=str(MODELS_DIR),
        log_path=str(LOGS_DIR),
        eval_freq=20_000,
        n_eval_episodes=10,
        deterministic=True,
        render=False,
        verbose=0,
    )

    checkpoint_cb = CheckpointCallback(
        save_freq=100_000,
        save_path=str(MODELS_DIR),
        name_prefix=f"bsf_ppo_v3_{ts}",
        verbose=0,
    )

    print(f"\n  [TRAIN] Training for {EXTRA_STEPS:,} more steps...")
    print(f"          Progress every 50,000 steps | Checkpoints every 100,000")
    print(f"          Effective throughput: ~{N_ENVS}x faster than single env")
    print("-" * 65)

    model.learn(
        total_timesteps=EXTRA_STEPS,
        callback=CallbackList([progress_cb, eval_cb, checkpoint_cb]),
        progress_bar=True,
        reset_num_timesteps=False,  # Preserve step counter from v1+v2 runs
    )

    print("\n" + "-" * 65)
    print("  [DONE] Training complete!")

    # ── Save ──────────────────────────────────────────────────────────────
    final_path = MODELS_DIR / f"bsf_ppo_v3_{ts}"
    model.save(str(final_path))

    # Save VecNormalize — both timestamped and as the "canonical" file
    # the dashboard and evaluation scripts will pick up automatically
    train_norm.save(str(MODELS_DIR / f"bsf_ppo_v3_{ts}_vecnormalize.pkl"))
    train_norm.save(str(MODELS_DIR / "bsf_ppo_v3_latest_vecnormalize.pkl"))

    if progress_cb.ep_rewards:
        last50_r = progress_cb.ep_rewards[-50:]
        last50_b = progress_cb.ep_biomasses[-50:]
        print(f"\n  Final 50-episode averages (across all {N_ENVS} envs):")
        print(f"    Reward:  {np.mean(last50_r):+.2f} ± {np.std(last50_r):.2f}")
        print(f"    Biomass: {np.mean(last50_b):.1f} mg ± {np.std(last50_b):.1f}")

    print(f"\n  [SAVE] {final_path}.zip")
    print(f"  [SAVE] bsf_ppo_v3_latest_vecnormalize.pkl")
    print("\n  Next: python results/run_real_evaluation.py")
    print("=" * 65 + "\n")


# SubprocVecEnv on Windows REQUIRES the main guard — without this
# each subprocess would re-import and try to spawn more subprocesses
# causing an infinite fork bomb.
if __name__ == "__main__":
    main()
