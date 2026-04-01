#!/usr/bin/env python3
"""
BSF PPO Retraining Script — v2 (1M Steps)

What this does, explained simply:
  1. Backs up your current best model (so you can compare v1 vs v2)
  2. Creates the Gymnasium environment (the BSF farm simulation)
  3. Creates a larger PPO neural network with better hyperparameters
  4. Trains for 1,000,000 timesteps (each = one 4-hour BSF decision)
  5. Saves the new best model for evaluation

Why 1M steps?
  Each episode is 96 steps (16 days × 6 decisions/day).
  1M steps ≈ 10,416 full episodes for the agent to learn from.
  The previous run only managed ~1,041 full episodes — too few.

Usage:
    python scripts/retrain.py
"""

import sys
import shutil
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import (
    EvalCallback, CheckpointCallback, CallbackList, BaseCallback
)
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize

from src.environments.bsf_env import BSFEnv


# ── Progress Logger ────────────────────────────────────────────────────────
class ProgressCallback(BaseCallback):
    """
    Prints a human-readable training summary every LOG_EVERY steps.

    What it shows:
    - Steps completed out of 1,000,000
    - Average reward over the last 10 episodes
    - Average larva survival rate
    - Average final biomass
    """
    LOG_EVERY = 50_000

    def __init__(self):
        super().__init__()
        self.ep_rewards = []
        self.ep_survivals = []
        self.ep_biomasses = []
        self.last_log = 0

    def _on_step(self) -> bool:
        # Collect episode data when an episode finishes
        for info in self.locals.get("infos", []):
            ep = info.get("episode", {})
            if ep:
                self.ep_rewards.append(ep.get("r", 0))
                self.ep_survivals.append(info.get("survival_rate", 0) * 100)
                self.ep_biomasses.append(info.get("biomass_mg", 0))

        # Print summary every LOG_EVERY steps
        if self.n_calls - self.last_log >= self.LOG_EVERY and self.ep_rewards:
            pct = self.n_calls / 1_000_000 * 100
            recent_r   = np.mean(self.ep_rewards[-20:])
            recent_s   = np.mean(self.ep_survivals[-20:]) if self.ep_survivals else 0
            recent_b   = np.mean(self.ep_biomasses[-20:]) if self.ep_biomasses else 0
            total_eps  = len(self.ep_rewards)

            print(f"\n  [{pct:5.1f}%] Step {self.n_calls:,} / 1,000,000")
            print(f"         Episodes trained:  {total_eps}")
            print(f"         Avg reward (last 20 eps): {recent_r:+.2f}")
            print(f"         Avg survival rate:        {recent_s:.1f}%")
            print(f"         Avg final biomass:        {recent_b:.1f} mg")
            self.last_log = self.n_calls

        return True


# ── Environment factory ────────────────────────────────────────────────────
def make_env(rank: int, seed: int = 0):
    """
    Factory function for creating a single BSF environment.

    Why wrap in Monitor?
      SB3 needs the Monitor wrapper to automatically track episode
      statistics (reward, length) and log them for the callbacks.
    """
    def _init():
        env = BSFEnv(stochastic_weather=True)
        env = Monitor(env)
        return env
    return _init


# ── Main ─────────────────────────────────────────────────────────────────
def main():
    MODELS_DIR = Path("outputs/models")
    LOGS_DIR   = Path("outputs/logs")
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    print("\n" + "=" * 62)
    print("  BSF-RL-OPTIMIZER — PPO Retraining (v2, 1M Steps)")
    print("=" * 62)

    # ── Step 1: Back up old model ─────────────────────────────────────
    old_model = MODELS_DIR / "best_model.zip"
    if old_model.exists():
        backup = MODELS_DIR / "best_model_v1.zip"
        shutil.copy(old_model, backup)
        print(f"\n  [BACKUP] Old model saved to: {backup}")
    else:
        print("\n  [INFO] No existing model to back up.")

    # ── Step 2: Create vectorized training environment ────────────────
    # We use DummyVecEnv (single env) since we're CPU-bound.
    # VecNormalize scales observations and rewards to mean≈0, std≈1,
    # which dramatically helps PPO converge — it's like standardizing
    # input features in regular machine learning.
    print("\n  [SETUP] Creating training environment...")
    train_env = DummyVecEnv([make_env(0)])
    train_env = VecNormalize(
        train_env,
        norm_obs=True,       # Normalize observations (temperature, biomass, etc.)
        norm_reward=True,    # Normalize rewards to ~unit scale
        clip_obs=10.0,       # Clip extreme observations
        clip_reward=10.0,    # Clip extreme rewards
    )

    # Separate eval environment (not normalized by train stats, uses its own)
    eval_env = DummyVecEnv([make_env(99)])
    eval_env = VecNormalize(eval_env, norm_obs=True, norm_reward=False,
                            clip_obs=10.0)

    # ── Step 3: Create the PPO model ──────────────────────────────────
    # Policy hyperparameters are read from configs/training.yaml.
    # The neural network policy maps observations → actions.
    # Two heads: actor (π, what to do) and critic (V, how good is this state).
    print("  [SETUP] Creating PPO model with 128×128 network...")
    model = PPO(
        policy="MlpPolicy",
        env=train_env,
        learning_rate=1e-4,      # How fast to update weights (slow & stable)
        n_steps=4096,            # Steps collected before each update
        batch_size=256,          # Mini-batch size for gradient descent
        n_epochs=15,             # Times to reuse collected data per update
        gamma=0.995,             # Future reward discount (longer horizon)
        gae_lambda=0.95,         # Generalized Advantage Estimation parameter
        clip_range=0.2,          # Max policy change per update (PPO's core trick)
        ent_coef=0.005,          # Entropy bonus (encourages some exploration)
        vf_coef=0.5,             # Weight of value function loss
        max_grad_norm=0.5,       # Gradient clipping (prevents explosions)
        policy_kwargs={
            "net_arch": dict(pi=[128, 128], vf=[128, 128])
        },
        verbose=0,               # Suppress SB3's built-in output (we use our own)
    )

    total_params = sum(p.numel() for p in model.policy.parameters())
    print(f"  [SETUP] Policy network parameters: {total_params:,}")

    # ── Step 4: Set up callbacks ──────────────────────────────────────
    # Callbacks are functions called at specific training events.
    progress_cb = ProgressCallback()

    # EvalCallback runs 10 episodes every 20k steps and saves the best model.
    # "Best" = highest mean reward across those 10 eval episodes.
    eval_cb = EvalCallback(
        eval_env,
        best_model_save_path=str(MODELS_DIR),
        log_path=str(LOGS_DIR),
        eval_freq=20_000,
        n_eval_episodes=10,
        deterministic=True,
        render=False,
        verbose=0,
    )

    # CheckpointCallback saves a copy every 100k steps regardless of performance.
    checkpoint_cb = CheckpointCallback(
        save_freq=100_000,
        save_path=str(MODELS_DIR),
        name_prefix=f"bsf_ppo_v2_{ts}",
        verbose=0,
    )

    callbacks = CallbackList([progress_cb, eval_cb, checkpoint_cb])

    # ── Step 5: Train ─────────────────────────────────────────────────
    print(f"\n  [TRAIN] Starting 1,000,000-step training session...")
    print(f"          Progress updates every 50,000 steps")
    print(f"          Model auto-saved every 100,000 steps")
    print(f"          Best model saved at: {MODELS_DIR}/best_model.zip\n")
    print("-" * 62)

    model.learn(
        total_timesteps=1_000_000,
        callback=callbacks,
        progress_bar=True,       # tqdm progress bar in terminal
        reset_num_timesteps=True,
    )

    print("\n" + "-" * 62)
    print("  [DONE] Training complete!")

    # ── Step 6: Save final model ──────────────────────────────────────
    final_path = MODELS_DIR / f"bsf_ppo_v2_{ts}"
    model.save(str(final_path))
    train_env.save(str(MODELS_DIR / f"bsf_ppo_v2_{ts}_vecnormalize.pkl"))
    print(f"  [SAVE] Final model: {final_path}.zip")
    print(f"  [SAVE] VecNormalize stats saved alongside model")

    # ── Summary ───────────────────────────────────────────────────────
    if progress_cb.ep_rewards:
        last50 = progress_cb.ep_rewards[-50:]
        last50_b = progress_cb.ep_biomasses[-50:]
        last50_s = progress_cb.ep_survivals[-50:]
        print(f"\n  Final 50-episode averages:")
        print(f"    Reward:   {np.mean(last50):+.2f} ± {np.std(last50):.2f}")
        print(f"    Biomass:  {np.mean(last50_b):.1f} mg ± {np.std(last50_b):.1f}")
        print(f"    Survival: {np.mean(last50_s):.1f}%")

    print("\n  Next step: run  python results/run_real_evaluation.py")
    print("=" * 62 + "\n")


if __name__ == "__main__":
    main()
