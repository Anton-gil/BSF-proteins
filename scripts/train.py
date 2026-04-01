#!/usr/bin/env python3
"""
Training script for BSF-RL-OPTIMIZER.

Usage:
    python scripts/train.py                      # Default training (from config)
    python scripts/train.py --timesteps 100000   # Custom timesteps
    python scripts/train.py --quick              # Quick test run (10 000 steps)
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

# Ensure project root is on sys.path regardless of working directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.ppo_agent import BSFPPOAgent, create_vectorized_env
from src.environments.bsf_env import BSFEnv


def parse_args():
    parser = argparse.ArgumentParser(description="Train BSF-RL-OPTIMIZER")

    parser.add_argument(
        '--timesteps', '-t',
        type=int,
        default=None,
        help='Total training timesteps (default: from config)'
    )
    parser.add_argument(
        '--quick', '-q',
        action='store_true',
        help='Quick test run (10 000 steps)'
    )
    parser.add_argument(
        '--n-envs',
        type=int,
        default=4,
        help='Number of parallel environments'
    )
    parser.add_argument(
        '--no-tensorboard',
        action='store_true',
        help='Disable TensorBoard logging'
    )
    parser.add_argument(
        '--eval-episodes',
        type=int,
        default=10,
        help='Number of evaluation episodes after training'
    )
    parser.add_argument(
        '--save-name',
        type=str,
        default=None,
        help='Custom save name for model'
    )
    parser.add_argument(
        '--verbose', '-v',
        type=int,
        default=1,
        help='Verbosity level (0, 1, 2)'
    )

    return parser.parse_args()


def main():
    args = parse_args()

    print("\n" + "=" * 60)
    print("  BSF-RL-OPTIMIZER Training")
    print("=" * 60)

    if args.quick:
        timesteps = 10_000
        print("  Mode: Quick test run (10 000 steps)")
    elif args.timesteps:
        timesteps = args.timesteps
        print(f"  Mode: Custom ({timesteps:,} steps)")
    else:
        timesteps = None  # Use config default
        print("  Mode: Full training (from config)")

    print(f"  Parallel envs: {args.n_envs}")
    print("=" * 60 + "\n")

    # Training environment
    env = create_vectorized_env(
        n_envs=args.n_envs,
        stochastic_weather=True,
        normalize=True,
        monitor_dir="outputs/logs/train"
    )

    # Agent
    agent = BSFPPOAgent(verbose=args.verbose)

    tensorboard_log = None if args.no_tensorboard else "outputs/logs/tensorboard"
    agent.create_model(env=env, tensorboard_log=tensorboard_log)

    print("Starting training...")
    start_time = datetime.now()

    metrics = agent.train(
        total_timesteps=timesteps,
        save_best=True,
        progress_bar=True
    )

    duration = datetime.now() - start_time
    print(f"\nTraining completed in {duration}")

    # Save final model
    if args.save_name:
        save_path = f"outputs/models/{args.save_name}"
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = f"outputs/models/bsf_ppo_final_{ts}"

    agent.save(save_path)

    # Final evaluation
    print(f"\n{'='*60}")
    print("  Final Evaluation")
    print("=" * 60)

    eval_env = BSFEnv(stochastic_weather=True)
    eval_metrics = agent.evaluate(
        n_episodes=args.eval_episodes,
        env=eval_env,
        deterministic=True
    )

    print(f"\nEvaluation Results ({args.eval_episodes} episodes):")
    print(f"  Mean reward:   {eval_metrics['mean_reward']:.2f} ± {eval_metrics['std_reward']:.2f}")
    print(f"  Mean survival: {eval_metrics['mean_survival']*100:.1f}%")
    print(f"  Mean biomass:  {eval_metrics['mean_biomass']:.1f} mg")
    print(f"  Harvest rate:  {eval_metrics['harvest_rate']*100:.0f}%")

    print(f"\n{'='*60}")
    print(f"  Model saved to: {save_path}")
    print("=" * 60 + "\n")

    return agent


if __name__ == "__main__":
    main()
