"""Tests for PPO agent."""
import sys
sys.path.insert(0, '.')

import os
import numpy as np
import tempfile
from pathlib import Path

from src.agents.ppo_agent import (
    BSFPPOAgent,
    BSFTrainingCallback,
    create_bsf_env,
    create_vectorized_env,
    quick_train
)
from src.environments.bsf_env import BSFEnv


def test_env_creation():
    """Test environment creation utilities."""
    env = create_bsf_env(stochastic_weather=False)
    assert env is not None
    print("✓ Single environment created")

    vec_env = create_vectorized_env(n_envs=2, stochastic_weather=False, normalize=True)
    assert vec_env is not None
    print("✓ Vectorized environment created")


def test_agent_creation():
    """Test agent initialization."""
    agent = BSFPPOAgent(verbose=0)
    assert agent is not None
    assert agent.model is None  # Not created yet
    print("✓ Agent created")


def test_model_creation():
    """Test model creation."""
    agent = BSFPPOAgent(verbose=0)

    env = create_vectorized_env(n_envs=1, stochastic_weather=False, normalize=True)
    model = agent.create_model(env=env, tensorboard_log=None)

    assert model is not None
    assert agent.model is not None
    print("✓ Model created")
    print(f"  Policy: {type(model.policy).__name__}")


def test_quick_training():
    """Test quick training run."""
    print("\nRunning quick training (5000 steps)...")

    agent = BSFPPOAgent(verbose=0)
    env = create_vectorized_env(n_envs=1, stochastic_weather=False, normalize=True)
    agent.create_model(env=env, tensorboard_log=None)

    metrics = agent.train(
        total_timesteps=5000,
        save_best=False,
        progress_bar=False
    )

    # May be empty if no episodes completed in 5000 steps; just check it ran
    assert isinstance(metrics, dict)
    print("✓ Quick training completed")
    print(f"  Episodes: {metrics.get('total_episodes', 0)}")


def test_prediction():
    """Test action prediction."""
    agent = BSFPPOAgent(verbose=0)
    env = create_vectorized_env(n_envs=1, stochastic_weather=False, normalize=True)
    agent.create_model(env=env, tensorboard_log=None)

    # Train briefly so the model is usable
    agent.train(total_timesteps=1000, save_best=False, progress_bar=False)

    test_env = BSFEnv(stochastic_weather=False)
    obs, _ = test_env.reset()

    action = agent.predict(obs, deterministic=True)

    assert action.shape == (4,), f"Expected shape (4,), got {action.shape}"
    assert test_env.action_space.contains(action), "Action out of bounds"

    print("✓ Prediction works")
    print(f"  Sample action: {action}")


def test_evaluation():
    """Test agent evaluation."""
    agent = BSFPPOAgent(verbose=0)
    env = create_vectorized_env(n_envs=1, stochastic_weather=False, normalize=True)
    agent.create_model(env=env, tensorboard_log=None)

    agent.train(total_timesteps=2000, save_best=False, progress_bar=False)

    eval_env = BSFEnv(stochastic_weather=False)
    metrics = agent.evaluate(n_episodes=2, env=eval_env, deterministic=True)

    assert 'mean_reward' in metrics
    assert 'mean_survival' in metrics
    assert 'mean_biomass' in metrics

    print("✓ Evaluation works")
    print(f"  Mean reward: {metrics['mean_reward']:.2f}")
    print(f"  Mean survival: {metrics['mean_survival']*100:.1f}%")


def test_save_load():
    """Test model save/load."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Train and save
        agent = BSFPPOAgent(verbose=0)
        agent.config['paths']['model_save_dir'] = tmpdir
        agent.config['paths']['log_dir'] = tmpdir

        env = create_vectorized_env(n_envs=1, stochastic_weather=False, normalize=True)
        agent.create_model(env=env, tensorboard_log=None)
        agent.train(total_timesteps=1000, save_best=False, progress_bar=False)

        save_path = os.path.join(tmpdir, "test_model")
        agent.save(save_path)

        assert os.path.exists(save_path + ".zip"), "Model .zip not created"

        # Load and predict
        loaded_agent = BSFPPOAgent.load(save_path)
        assert loaded_agent.model is not None

        test_env = BSFEnv(stochastic_weather=False)
        obs, _ = test_env.reset()
        action = loaded_agent.predict(obs)

        assert action.shape == (4,)
        print("✓ Save/load works")


def test_training_callback():
    """Test custom training callback metrics."""
    callback = BSFTrainingCallback(verbose=0)

    # Inject fake episode data
    callback.episode_rewards = [10.0, 15.0, 12.0, 18.0, 20.0]
    callback.survival_rates = [0.90, 0.85, 0.88, 0.92, 0.95]
    callback.final_biomasses = [100.0, 110.0, 105.0, 120.0, 130.0]
    callback.harvest_successes = [0, 1, 0, 1, 1]

    metrics = callback.get_metrics()

    assert metrics['total_episodes'] == 5
    assert metrics['mean_reward'] == 15.0
    assert metrics['harvest_rate'] == 0.6

    print("✓ Training callback works")
    print(f"  Metrics: {metrics}")


def test_episode_rollout_with_agent():
    """Test full episode rollout with a briefly-trained agent."""
    agent = BSFPPOAgent(verbose=0)
    env = create_vectorized_env(n_envs=1, stochastic_weather=False, normalize=True)
    agent.create_model(env=env, tensorboard_log=None)
    agent.train(total_timesteps=3000, save_best=False, progress_bar=False)

    test_env = BSFEnv(stochastic_weather=False)
    obs, _ = test_env.reset(seed=42)

    total_reward = 0.0
    steps = 0

    while True:
        action = agent.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, info = test_env.step(action)
        total_reward += reward
        steps += 1
        if terminated or truncated:
            break

    print(f"\n✓ Episode rollout completed")
    print(f"  Steps: {steps}")
    print(f"  Total reward: {total_reward:.2f}")
    print(f"  Final survival: {info.get('survival_rate', 0)*100:.1f}%")
    print(f"  Final biomass:  {info.get('biomass_mg', 0):.1f} mg")


if __name__ == "__main__":
    print("=" * 50)
    print("PPO AGENT TESTS")
    print("=" * 50)

    test_env_creation()
    test_agent_creation()
    test_model_creation()
    test_training_callback()
    test_quick_training()
    test_prediction()
    test_evaluation()
    test_save_load()
    test_episode_rollout_with_agent()

    print("\n" + "=" * 50)
    print("✅ ALL PPO AGENT TESTS PASSED")
    print("=" * 50)
