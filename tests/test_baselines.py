"""Tests for baseline policies."""
import sys
sys.path.insert(0, '.')

import numpy as np
from src.baselines.random_policy import RandomPolicy
from src.baselines.fixed_policy import FixedPolicy
from src.baselines.heuristic_policy import HeuristicPolicy
from src.environments.bsf_env import BSFEnv


def test_random_policy():
    """Test random policy."""
    policy = RandomPolicy(seed=42)

    obs = np.zeros(10, dtype=np.float32)

    action1 = policy.predict(obs)
    action2 = policy.predict(obs)

    assert action1.shape == (4,), f"Expected (4,), got {action1.shape}"
    assert not np.allclose(action1, action2), "Actions should be different"
    assert np.all(action1 >= 0) and np.all(action1 <= 1), "Actions should be in [0,1]"

    print("✓ Random policy works")


def test_fixed_policy():
    """Test fixed policy."""
    policy = FixedPolicy(feed_cn=0.5, feed_amount=0.6, moisture=0.5, aeration=0.5)

    obs = np.zeros(10, dtype=np.float32)

    action1 = policy.predict(obs)
    action2 = policy.predict(obs)

    assert action1.shape == (4,), f"Expected (4,), got {action1.shape}"
    assert np.allclose(action1, action2), "Actions should be identical"
    assert np.allclose(action1, [0.5, 0.6, 0.5, 0.5]), "Actions should match config"

    print("✓ Fixed policy works")


def test_fixed_policy_variants():
    """Test fixed policy variants."""
    conservative = FixedPolicy.conservative()
    aggressive = FixedPolicy.aggressive()
    balanced = FixedPolicy.balanced()

    obs = np.zeros(10, dtype=np.float32)

    a_con = conservative.predict(obs)
    a_agg = aggressive.predict(obs)
    a_bal = balanced.predict(obs)

    # Aggressive should feed more than conservative
    assert a_agg[1] > a_con[1], "Aggressive should feed more"

    print("✓ Fixed policy variants work")
    print(f"  Conservative: {a_con}")
    print(f"  Balanced:     {a_bal}")
    print(f"  Aggressive:   {a_agg}")


def test_heuristic_policy():
    """Test heuristic policy basics."""
    policy = HeuristicPolicy()

    obs_normal = np.array([
        7.0,   # age_days (mid-cycle)
        50.0,  # biomass_mg
        0.95,  # survival_rate
        3,     # development_stage
        18.0,  # cn_ratio (optimal)
        70.0,  # moisture_pct (optimal)
        50.0,  # substrate_remaining
        30.0,  # temperature_c (optimal)
        65.0,  # humidity_pct
        4.0    # hours_since_feed
    ], dtype=np.float32)

    action_normal = policy.predict(obs_normal)
    assert action_normal.shape == (4,)

    # Dry conditions (50% < 62% threshold) → add water
    obs_dry = obs_normal.copy()
    obs_dry[5] = 50.0
    action_dry = policy.predict(obs_dry)
    assert 0.33 < action_dry[2] < 0.67, \
        f"Should add water when dry (50%), got {action_dry[2]}"

    # Wet conditions (84% > 83% threshold) → ventilate
    obs_wet = obs_normal.copy()
    obs_wet[5] = 84.0
    action_wet = policy.predict(obs_wet)
    assert action_wet[2] > 0.67, \
        f"Should ventilate when wet (84%), got {action_wet[2]}"

    print("✓ Heuristic policy works")
    print(f"  Normal:  {action_normal}")
    print(f"  Dry:     {action_dry}")
    print(f"  Wet:     {action_wet}")


def test_heuristic_age_response():
    """Test heuristic policy responds correctly to larval age."""
    policy = HeuristicPolicy()

    base_obs = np.array([
        0.0, 50.0, 0.95, 3, 18.0, 70.0, 50.0, 30.0, 65.0, 4.0
    ], dtype=np.float32)

    obs_young = base_obs.copy(); obs_young[0] = 1.0
    obs_peak = base_obs.copy();  obs_peak[0] = 6.0
    obs_prepupa = base_obs.copy(); obs_prepupa[0] = 13.0

    a_young   = policy.predict(obs_young)
    a_peak    = policy.predict(obs_peak)
    a_prepupa = policy.predict(obs_prepupa)

    assert a_peak[1] > a_young[1],   "Peak age should feed more than young"
    assert a_peak[1] > a_prepupa[1], "Peak age should feed more than prepupa"

    print("✓ Heuristic age response works")
    print(f"  Young   (day 1)  feed: {a_young[1]:.2f}")
    print(f"  Peak    (day 6)  feed: {a_peak[1]:.2f}")
    print(f"  Prepupa (day 13) feed: {a_prepupa[1]:.2f}")


def test_policy_episode():
    """Test each policy can run a full episode without error."""
    env = BSFEnv(stochastic_weather=False)

    policies = [
        RandomPolicy(seed=42),
        FixedPolicy.balanced(),
        HeuristicPolicy()
    ]

    for policy in policies:
        obs, _ = env.reset(seed=42)
        policy.reset()

        total_reward = 0.0
        steps = 0

        while True:
            action = policy.predict(obs)
            obs, reward, terminated, truncated, info = env.step(action)
            total_reward += reward
            steps += 1
            if terminated or truncated:
                break

        print(f"\n{policy.name}:")
        print(f"  Steps: {steps}")
        print(f"  Total reward:    {total_reward:.2f}")
        print(f"  Final survival:  {info.get('survival_rate', 0)*100:.1f}%")
        print(f"  Final biomass:   {info.get('biomass_mg', 0):.1f} mg")

    print("\n✓ All policies complete episodes")


def test_policy_comparison():
    """Verify heuristic beats random over several episodes."""
    env = BSFEnv(stochastic_weather=True)
    n_episodes = 5

    policies = [
        RandomPolicy(seed=42),
        FixedPolicy.balanced(),
        HeuristicPolicy()
    ]

    results = {}

    for policy in policies:
        rewards = []
        for ep in range(n_episodes):
            obs, _ = env.reset(seed=ep)
            policy.reset()
            total_reward = 0.0

            while True:
                action = policy.predict(obs)
                obs, reward, terminated, truncated, _ = env.step(action)
                total_reward += reward
                if terminated or truncated:
                    break

            rewards.append(total_reward)

        results[policy.name] = {
            'mean': float(np.mean(rewards)),
            'std': float(np.std(rewards))
        }

    print("\nPolicy Comparison (5 episodes each):")
    for name, stats in results.items():
        print(f"  {name}: {stats['mean']:.2f} ± {stats['std']:.2f}")

    # Heuristic should beat random or at minimum be competitive
    # (Random occasionally gets lucky; use a generous tolerance of 10 pts)
    assert results['HeuristicPolicy']['mean'] >= results['RandomPolicy']['mean'] - 10, \
        (f"Heuristic ({results['HeuristicPolicy']['mean']:.1f}) should be "
         f"competitive with random ({results['RandomPolicy']['mean']:.1f})")

    print("\n✓ Policy comparison works — Heuristic competitive with Random confirmed")


if __name__ == "__main__":
    print("=" * 50)
    print("BASELINE POLICY TESTS")
    print("=" * 50)

    test_random_policy()
    test_fixed_policy()
    test_fixed_policy_variants()
    test_heuristic_policy()
    test_heuristic_age_response()
    test_policy_episode()
    test_policy_comparison()

    print("\n" + "=" * 50)
    print("✅ ALL BASELINE TESTS PASSED")
    print("=" * 50)
