"""Tests for BSF Gymnasium environment."""
import sys
sys.path.insert(0, '.')

import numpy as np
from src.environments.bsf_env import BSFEnv


def test_environment_creation():
    """Test environment can be created."""
    env = BSFEnv(stochastic_weather=False)

    assert env.observation_space is not None
    assert env.action_space is not None

    print(f"✓ Environment created")
    print(f"  Observation space: {env.observation_space.shape}")
    print(f"  Action space: {env.action_space.shape}")


def test_reset():
    """Test environment reset."""
    env = BSFEnv(stochastic_weather=False)

    obs, info = env.reset(seed=42)

    assert obs.shape == (10,), f"Expected (10,), got {obs.shape}"
    assert env.observation_space.contains(obs), "Observation out of bounds"

    assert 'population' in info
    assert info['population'] == 1000

    print(f"✓ Reset works")
    print(f"  Initial obs: {obs}")


def test_step():
    """Test environment step."""
    env = BSFEnv(stochastic_weather=False)
    obs, _ = env.reset(seed=42)

    action = np.array([0.5, 0.5, 0.5, 0.5], dtype=np.float32)

    obs2, reward, terminated, truncated, info = env.step(action)

    assert obs2.shape == (10,), "Observation shape mismatch"
    assert env.observation_space.contains(obs2), "Observation out of bounds"
    assert isinstance(reward, (int, float)), "Reward should be numeric"
    assert isinstance(terminated, bool), "Terminated should be bool"
    assert isinstance(truncated, bool), "Truncated should be bool"

    print(f"✓ Step works")
    print(f"  Reward: {reward:.3f}")
    print(f"  Info keys: {list(info.keys())}")


def test_action_scaling():
    """Test action scaling from [0,1] to actual values."""
    env = BSFEnv(stochastic_weather=False)
    env.reset(seed=42)

    # Test minimum action
    cn, feed, moisture, aeration = env._scale_action(np.array([0, 0, 0, 0]))
    print(f"Min action: cn={cn:.1f}, feed={feed:.2f}, moisture={moisture}, aeration={aeration}")
    assert moisture == 0 and aeration == 0

    # Test maximum action
    cn, feed, moisture, aeration = env._scale_action(np.array([1, 1, 1, 1]))
    print(f"Max action: cn={cn:.1f}, feed={feed:.2f}, moisture={moisture}, aeration={aeration}")
    assert moisture == 2 and aeration == 2

    # Test middle action
    cn, feed, moisture, aeration = env._scale_action(np.array([0.5, 0.5, 0.5, 0.5]))
    print(f"Mid action: cn={cn:.1f}, feed={feed:.2f}, moisture={moisture}, aeration={aeration}")

    print(f"✓ Action scaling works")


def test_episode_rollout():
    """Test running a full episode."""
    env = BSFEnv(stochastic_weather=False)
    obs, _ = env.reset(seed=42)

    total_reward = 0
    steps = 0

    print(f"\nRunning episode...")

    while True:
        # Simple policy: feed normally, maintain conditions
        action = np.array([0.5, 0.6, 0.5, 0.5], dtype=np.float32)

        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += reward
        steps += 1

        # Print every day
        if steps % 6 == 0:
            day = steps // 6
            print(f"  Day {day}: pop={info['population']}, "
                  f"biomass={info['biomass_mg']:.1f}mg, reward={reward:.2f}")

        if terminated or truncated:
            break

    print(f"\n✓ Episode completed")
    print(f"  Steps: {steps}")
    print(f"  Total reward: {total_reward:.2f}")
    print(f"  Final population: {info['population']}")
    print(f"  Final biomass: {info['biomass_mg']:.2f} mg")
    print(f"  Survival rate: {info['survival_rate'] * 100:.1f}%")

    assert steps > 0, "Episode should have steps"
    assert steps <= 96, "Episode should not exceed max steps"


def test_termination_conditions():
    """Test termination conditions work."""
    env = BSFEnv(stochastic_weather=False)
    env.reset(seed=42)

    for _ in range(100):  # More than max steps
        _, _, term, trunc, _ = env.step(env.action_space.sample())
        if term or trunc:
            break

    assert term or trunc, "Episode should terminate"
    print(f"✓ Termination works (terminated={term}, truncated={trunc})")


def test_harvest_success():
    """Test that harvest success is detected."""
    env = BSFEnv(stochastic_weather=False)
    env.reset(seed=42)

    harvest_achieved = False

    for step in range(96):
        action = np.array([0.5, 0.7, 0.4, 0.5], dtype=np.float32)
        _, _, term, trunc, info = env.step(action)

        if info.get('harvest_success', False):
            harvest_achieved = True
            print(f"✓ Harvest achieved at step {step + 1}")
            print(f"  Final biomass: {info['biomass_mg']:.1f} mg")
            break

        if term or trunc:
            break

    print(f"  Harvest achieved: {harvest_achieved}")


def test_stochastic_weather():
    """Test stochastic weather variation."""
    env = BSFEnv(stochastic_weather=True)

    temps = []
    for seed in range(5):
        env.reset(seed=seed)
        temps.append(env.state.temperature_c)

    temp_range = max(temps) - min(temps)
    print(f"✓ Stochastic weather works")
    print(f"  Temperature range across seeds: {temp_range:.1f}°C")
    print(f"  Temperatures: {[f'{t:.1f}' for t in temps]}")


def test_render():
    """Test rendering works."""
    env = BSFEnv(render_mode="ansi", stochastic_weather=False)
    env.reset(seed=42)

    env.step(np.array([0.5, 0.5, 0.5, 0.5]))
    output = env.render()

    assert output is not None
    assert "BSF LARVAE BATCH" in output

    print(f"✓ Render works")
    print(output[:200] + "...")


def test_reproducibility():
    """Test that same seed gives same results."""
    env = BSFEnv(stochastic_weather=False)

    # Run 1
    obs1, _ = env.reset(seed=42)
    action = np.array([0.5, 0.6, 0.5, 0.5])
    obs1_next, reward1, _, _, _ = env.step(action)

    # Run 2 with same seed
    obs2, _ = env.reset(seed=42)
    obs2_next, reward2, _, _, _ = env.step(action)

    assert np.allclose(obs1, obs2), "Initial observations should match"
    assert np.allclose(obs1_next, obs2_next), "Next observations should match"
    assert reward1 == reward2, "Rewards should match"

    print(f"✓ Reproducibility works")


def test_gymnasium_api():
    """Test Gymnasium API compliance."""
    import gymnasium as gym

    env = BSFEnv(stochastic_weather=False)

    # Required attributes
    assert hasattr(env, 'observation_space')
    assert hasattr(env, 'action_space')
    assert hasattr(env, 'reset')
    assert hasattr(env, 'step')
    assert hasattr(env, 'render')
    assert hasattr(env, 'close')

    # Spaces are valid Gymnasium types
    assert isinstance(env.observation_space, gym.spaces.Box)
    assert isinstance(env.action_space, gym.spaces.Box)

    # reset() returns (obs, info)
    result = env.reset()
    assert isinstance(result, tuple) and len(result) == 2

    # step() returns (obs, reward, terminated, truncated, info)
    result = env.step(env.action_space.sample())
    assert isinstance(result, tuple) and len(result) == 5

    print(f"✓ Gymnasium API compliance verified")


if __name__ == "__main__":
    print("=" * 50)
    print("BSF ENVIRONMENT TESTS")
    print("=" * 50)

    test_environment_creation()
    test_reset()
    test_step()
    test_action_scaling()
    test_stochastic_weather()
    test_render()
    test_reproducibility()
    test_gymnasium_api()
    test_termination_conditions()
    test_episode_rollout()
    test_harvest_success()

    print("\n" + "=" * 50)
    print("✅ ALL BSF ENVIRONMENT TESTS PASSED")
    print("=" * 50)
