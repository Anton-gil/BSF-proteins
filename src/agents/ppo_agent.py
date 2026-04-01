"""
PPO Agent for BSF Environment

Wrapper around Stable-Baselines3 PPO with BSF-specific configurations.
"""

import os
import numpy as np
from pathlib import Path
from typing import Dict, Optional, Callable, Any
from datetime import datetime

from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import (
    BaseCallback,
    EvalCallback,
    CheckpointCallback,
    CallbackList
)
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
from stable_baselines3.common.evaluation import evaluate_policy
import yaml

from src.environments.bsf_env import BSFEnv


class BSFTrainingCallback(BaseCallback):
    """
    Custom callback for BSF-specific logging during training.

    Logs:
    - Episode rewards
    - Survival rates
    - Final biomass
    - Harvest success rate
    """

    def __init__(self, verbose: int = 0, log_freq: int = 1000):
        super().__init__(verbose)
        self.log_freq = log_freq
        self.episode_rewards = []
        self.episode_lengths = []
        self.survival_rates = []
        self.final_biomasses = []
        self.harvest_successes = []

    def _on_step(self) -> bool:
        # SB3 Monitor injects ep_info into info['episode'] with keys 'r', 'l', 't'
        # when an episode ends.  Our BSFEnv also sets info['episode'] with BSF-specific
        # keys (final_biomass_mg, final_survival_rate, etc.) on the *same* step.
        if self.locals.get('dones') is not None:
            for idx, done in enumerate(self.locals['dones']):
                if done:
                    info = self.locals['infos'][idx]
                    ep_info = info.get('episode', {})
                    if ep_info:
                        # 'r' is the Monitor key for episode reward
                        self.episode_rewards.append(ep_info.get('r', ep_info.get('total_reward', 0)))
                        self.episode_lengths.append(ep_info.get('l', ep_info.get('length', 0)))
                        self.survival_rates.append(ep_info.get('final_survival_rate', info.get('survival_rate', 1.0)))
                        self.final_biomasses.append(ep_info.get('final_biomass_mg', info.get('biomass_mg', 0)))
                        self.harvest_successes.append(1 if ep_info.get('harvest_success', False) else 0)

        # Log periodically
        if self.n_calls % self.log_freq == 0 and len(self.episode_rewards) > 0:
            recent_rewards = self.episode_rewards[-10:]
            recent_survival = self.survival_rates[-10:]
            recent_biomass = self.final_biomasses[-10:]
            recent_harvest = self.harvest_successes[-10:]

            if self.verbose > 0:
                print(f"\n--- Step {self.n_calls} ---")
                print(f"Episodes completed: {len(self.episode_rewards)}")
                print(f"Avg reward (last 10): {np.mean(recent_rewards):.2f}")
                print(f"Avg survival (last 10): {np.mean(recent_survival)*100:.1f}%")
                print(f"Avg biomass (last 10): {np.mean(recent_biomass):.1f} mg")
                print(f"Harvest rate (last 10): {np.mean(recent_harvest)*100:.0f}%")

        return True

    def get_metrics(self) -> Dict[str, float]:
        """Get summary metrics."""
        if len(self.episode_rewards) == 0:
            return {}

        return {
            'total_episodes': len(self.episode_rewards),
            'mean_reward': float(np.mean(self.episode_rewards)),
            'std_reward': float(np.std(self.episode_rewards)),
            'mean_survival': float(np.mean(self.survival_rates)),
            'mean_biomass': float(np.mean(self.final_biomasses)),
            'harvest_rate': float(np.mean(self.harvest_successes)),
            'best_reward': float(max(self.episode_rewards)),
            'best_biomass': float(max(self.final_biomasses))
        }


def create_bsf_env(
    stochastic_weather: bool = True,
    monitor_dir: Optional[str] = None
) -> BSFEnv:
    """
    Create a BSF environment with optional monitoring.

    Args:
        stochastic_weather: Whether to vary weather
        monitor_dir: Directory for Monitor logs

    Returns:
        Wrapped BSF environment
    """
    env = BSFEnv(stochastic_weather=stochastic_weather)

    if monitor_dir:
        os.makedirs(monitor_dir, exist_ok=True)
        env = Monitor(env, monitor_dir)

    return env


def create_vectorized_env(
    n_envs: int = 1,
    stochastic_weather: bool = True,
    normalize: bool = True,
    monitor_dir: Optional[str] = None
) -> DummyVecEnv:
    """
    Create a vectorized (optionally normalised) environment for training.

    Args:
        n_envs: Number of parallel environments
        stochastic_weather: Whether to vary weather
        normalize: Whether to normalise observations/rewards
        monitor_dir: Directory for Monitor logs

    Returns:
        DummyVecEnv (or VecNormalize wrapping it)
    """
    def make_env(rank: int):
        def _init():
            env = BSFEnv(stochastic_weather=stochastic_weather)
            # Monitor MUST be inside DummyVecEnv so SB3 receives ep_info
            # ('r', 'l') on episode completion.  A per-rank log file is
            # created when monitor_dir is provided; otherwise a tmp file
            # is used so SB3 still gets the epinfo it needs.
            log_path = os.path.join(monitor_dir, f"env_{rank}") if monitor_dir else None
            if monitor_dir:
                os.makedirs(monitor_dir, exist_ok=True)
            env = Monitor(env, log_path)
            return env
        return _init

    vec_env = DummyVecEnv([make_env(i) for i in range(n_envs)])

    if normalize:
        vec_env = VecNormalize(
            vec_env,
            norm_obs=True,
            norm_reward=True,
            clip_obs=10.0,
            clip_reward=10.0
        )

    return vec_env


class BSFPPOAgent:
    """
    PPO Agent wrapper for BSF environment.

    Handles:
    - Model creation with BSF-optimised hyperparameters
    - Training with callbacks
    - Evaluation
    - Saving/loading

    Usage:
        agent = BSFPPOAgent()
        agent.train(total_timesteps=100_000)
        agent.save("outputs/models/bsf_ppo")

        # Later:
        agent = BSFPPOAgent.load("outputs/models/bsf_ppo")
        action = agent.predict(observation)
    """

    def __init__(
        self,
        config_path: str = "configs/training.yaml",
        env: Optional[Any] = None,
        verbose: int = 1
    ):
        """
        Initialise PPO agent.

        Args:
            config_path: Path to training config
            env: Optional pre-created environment
            verbose: Verbosity level (0/1/2)
        """
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        self.verbose = verbose
        self.model: Optional[PPO] = None
        self.env = env
        self.training_callback: Optional[BSFTrainingCallback] = None

        # Ensure output directories exist
        self.paths = self.config['paths']
        os.makedirs(self.paths['model_save_dir'], exist_ok=True)
        os.makedirs(self.paths['log_dir'], exist_ok=True)

    # ------------------------------------------------------------------
    # Model creation
    # ------------------------------------------------------------------

    # sentinel so callers can distinguish "not passed" from "explicitly None"
    _UNSET = object()

    def create_model(
        self,
        env: Optional[Any] = None,
        tensorboard_log: Any = _UNSET
    ) -> PPO:
        """
        Create PPO model with configured hyperparameters.

        Args:
            env: Environment to train on (created automatically if None)
            tensorboard_log: TensorBoard log directory

        Returns:
            PPO model
        """
        if env is None:
            env = self.env
        if env is None:
            env = create_vectorized_env(
                n_envs=1,
                stochastic_weather=True,
                normalize=True,
                monitor_dir=self.paths['log_dir']
            )
            self.env = env

        ppo_cfg = self.config['ppo']
        pol_cfg = self.config['policy']

        model = PPO(
            policy=pol_cfg['type'],
            env=env,
            learning_rate=ppo_cfg['learning_rate'],
            n_steps=ppo_cfg['n_steps'],
            batch_size=ppo_cfg['batch_size'],
            n_epochs=ppo_cfg['n_epochs'],
            gamma=ppo_cfg['gamma'],
            gae_lambda=ppo_cfg['gae_lambda'],
            clip_range=ppo_cfg['clip_range'],
            ent_coef=ppo_cfg['ent_coef'],
            vf_coef=ppo_cfg['vf_coef'],
            max_grad_norm=ppo_cfg['max_grad_norm'],
            policy_kwargs={'net_arch': pol_cfg['net_arch']},
            tensorboard_log=(
                self.paths.get('tensorboard_dir')
                if tensorboard_log is BSFPPOAgent._UNSET
                else tensorboard_log      # None → disabled, str → custom path
            ),
            verbose=self.verbose
        )

        self.model = model
        return model

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def train(
        self,
        total_timesteps: Optional[int] = None,
        eval_env: Optional[Any] = None,
        save_best: bool = True,
        save_freq: Optional[int] = None,
        progress_bar: bool = True
    ) -> Dict[str, Any]:
        """
        Train the PPO agent.

        Args:
            total_timesteps: Total training steps (default from config)
            eval_env: Separate evaluation environment
            save_best: Save the best model found during eval
            save_freq: Checkpoint save frequency
            progress_bar: Show tqdm progress bar

        Returns:
            Dict of training metrics
        """
        if self.model is None:
            self.create_model()

        train_cfg = self.config['training']

        if total_timesteps is None:
            total_timesteps = train_cfg['total_timesteps']
        if save_freq is None:
            save_freq = train_cfg['save_freq']

        callbacks = []

        # BSF-specific logging callback
        self.training_callback = BSFTrainingCallback(
            verbose=self.verbose,
            log_freq=train_cfg['log_interval'] * 100
        )
        callbacks.append(self.training_callback)

        # Periodic checkpoint
        checkpoint_cb = CheckpointCallback(
            save_freq=max(1, save_freq // max(1, getattr(self.env, 'num_envs', 1))),
            save_path=self.paths['model_save_dir'],
            name_prefix="bsf_ppo"
        )
        callbacks.append(checkpoint_cb)

        # Evaluation + best-model saver
        if save_best:
            if eval_env is None:
                eval_env = create_vectorized_env(
                    n_envs=1,
                    stochastic_weather=True,
                    normalize=True
                )

            eval_cb = EvalCallback(
                eval_env,
                best_model_save_path=self.paths['model_save_dir'],
                log_path=self.paths['log_dir'],
                eval_freq=max(1, train_cfg['eval_freq'] // max(1, getattr(self.env, 'num_envs', 1))),
                n_eval_episodes=train_cfg['n_eval_episodes'],
                deterministic=True,
                render=False
            )
            callbacks.append(eval_cb)

        if self.verbose:
            print(f"\n{'='*50}")
            print(f"Starting PPO Training")
            print(f"Total timesteps: {total_timesteps:,}")
            print(f"{'='*50}\n")

        self.model.learn(
            total_timesteps=total_timesteps,
            callback=CallbackList(callbacks),
            progress_bar=progress_bar
        )

        metrics = self.training_callback.get_metrics()

        if self.verbose:
            print(f"\n{'='*50}")
            print("Training Complete!")
            print(f"{'='*50}")
            for k, v in metrics.items():
                print(f"  {k}: {v:.3f}" if isinstance(v, float) else f"  {k}: {v}")

        return metrics

    # ------------------------------------------------------------------
    # Prediction
    # ------------------------------------------------------------------

    def predict(
        self,
        observation: np.ndarray,
        deterministic: bool = True
    ) -> np.ndarray:
        """
        Predict action for an observation.

        Args:
            observation: State observation array
            deterministic: Use deterministic policy

        Returns:
            Action array (shape [4])
        """
        if self.model is None:
            raise RuntimeError("Model not trained. Call train() or load() first.")

        action, _ = self.model.predict(observation, deterministic=deterministic)
        return action

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def evaluate(
        self,
        n_episodes: int = 10,
        env: Optional[Any] = None,
        deterministic: bool = True
    ) -> Dict[str, float]:
        """
        Evaluate trained agent over multiple episodes.

        Args:
            n_episodes: Number of evaluation episodes
            env: Evaluation environment (created if None)
            deterministic: Use deterministic policy

        Returns:
            Dict of evaluation metrics
        """
        if self.model is None:
            raise RuntimeError("Model not trained. Call train() or load() first.")

        if env is None:
            env = BSFEnv(stochastic_weather=True)

        episode_rewards = []
        episode_lengths = []
        survival_rates = []
        final_biomasses = []
        harvest_successes = []
        info = {}

        for _ in range(n_episodes):
            obs, _ = env.reset()
            done = False
            total_reward = 0.0
            steps = 0

            while not done:
                action = self.predict(obs, deterministic=deterministic)
                obs, reward, terminated, truncated, info = env.step(action)
                total_reward += reward
                steps += 1
                done = terminated or truncated

            episode_rewards.append(total_reward)
            episode_lengths.append(steps)

            if 'episode' in info:
                survival_rates.append(info['episode']['final_survival_rate'])
                final_biomasses.append(info['episode']['final_biomass_mg'])
                harvest_successes.append(1 if info['episode']['harvest_success'] else 0)
            else:
                survival_rates.append(info.get('survival_rate', 0))
                final_biomasses.append(info.get('biomass_mg', 0))
                harvest_successes.append(0)

        return {
            'mean_reward': float(np.mean(episode_rewards)),
            'std_reward': float(np.std(episode_rewards)),
            'mean_length': float(np.mean(episode_lengths)),
            'mean_survival': float(np.mean(survival_rates)),
            'mean_biomass': float(np.mean(final_biomasses)),
            'harvest_rate': float(np.mean(harvest_successes)),
            'min_reward': float(min(episode_rewards)),
            'max_reward': float(max(episode_rewards))
        }

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: Optional[str] = None):
        """
        Save model (and VecNormalize stats) to disk.

        Args:
            path: Save path without extension
        """
        if self.model is None:
            raise RuntimeError("No model to save.")

        if path is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(self.paths['model_save_dir'], f"bsf_ppo_{ts}")

        self.model.save(path)

        if isinstance(self.env, VecNormalize):
            self.env.save(f"{path}_vecnormalize.pkl")

        if self.verbose:
            print(f"Model saved to: {path}")

    @classmethod
    def load(
        cls,
        path: str,
        env: Optional[Any] = None,
        config_path: str = "configs/training.yaml"
    ) -> 'BSFPPOAgent':
        """
        Load model from disk.

        Args:
            path: Model path (without .zip)
            env: Environment (created automatically if None)
            config_path: Config path

        Returns:
            Loaded BSFPPOAgent
        """
        agent = cls(config_path=config_path, verbose=1)

        if env is None:
            env = create_vectorized_env(n_envs=1, stochastic_weather=True, normalize=True)

        # Restore VecNormalize stats if available
        vecnorm_path = f"{path}_vecnormalize.pkl"
        if os.path.exists(vecnorm_path) and isinstance(env, VecNormalize):
            env = VecNormalize.load(vecnorm_path, env)

        agent.env = env
        agent.model = PPO.load(path, env=env)

        return agent


# ------------------------------------------------------------------
# Convenience helper
# ------------------------------------------------------------------

def quick_train(
    total_timesteps: int = 50_000,
    verbose: int = 1
) -> BSFPPOAgent:
    """
    Quick training helper for testing.

    Args:
        total_timesteps: Number of environment steps
        verbose: Verbosity level

    Returns:
        Trained agent
    """
    agent = BSFPPOAgent(verbose=verbose)
    agent.train(total_timesteps=total_timesteps)
    return agent
