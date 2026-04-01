"""Tests for BSF reward function."""
import sys
sys.path.insert(0, '.')

from src.environments.reward import (
    RewardCalculator,
    RewardComponents,
    RewardShaper,
    calculate_batch_score
)
import numpy as np


def test_biomass_reward():
    """Test biomass reward calculation."""
    calc = RewardCalculator()

    # Positive growth
    r_grow = calc.biomass_reward(prev_biomass_mg=50, curr_biomass_mg=53, timestep_hours=4)
    assert r_grow > 0, f"Growth should give positive reward, got {r_grow}"

    # No growth
    r_none = calc.biomass_reward(prev_biomass_mg=50, curr_biomass_mg=50, timestep_hours=4)
    assert r_none == 0, f"No growth should give zero reward, got {r_none}"

    # Weight loss
    r_loss = calc.biomass_reward(prev_biomass_mg=50, curr_biomass_mg=48, timestep_hours=4)
    assert r_loss < 0, f"Weight loss should give negative reward, got {r_loss}"

    print(f"✓ Biomass reward tests passed")
    print(f"  +3mg: {r_grow:.3f}, 0mg: {r_none:.3f}, -2mg: {r_loss:.3f}")


def test_survival_reward():
    """Test survival reward calculation."""
    calc = RewardCalculator()

    # No deaths
    r_perfect = calc.survival_reward(
        prev_population=1000, curr_population=1000, initial_population=1000
    )
    assert r_perfect >= 0, f"No deaths should give positive/zero reward, got {r_perfect}"

    # Some deaths (1%)
    r_some = calc.survival_reward(
        prev_population=1000, curr_population=990, initial_population=1000
    )
    assert r_some < r_perfect, f"Deaths should reduce reward"

    # Heavy deaths (10%)
    r_heavy = calc.survival_reward(
        prev_population=1000, curr_population=900, initial_population=1000
    )
    assert r_heavy < r_some, f"More deaths should give worse reward"
    assert r_heavy < 0, f"10% deaths should be negative, got {r_heavy}"

    print(f"✓ Survival reward tests passed")
    print(f"  0% deaths: {r_perfect:.3f}, 1%: {r_some:.3f}, 10%: {r_heavy:.3f}")


def test_feed_efficiency_reward():
    """Test feed efficiency reward."""
    calc = RewardCalculator()

    # Good efficiency (low waste, good FCR)
    r_good = calc.feed_efficiency_reward(
        feed_given_g=100, feed_consumed_g=90,
        biomass_gain_mg=3, population=1000
    )

    # Wasteful (high waste)
    r_waste = calc.feed_efficiency_reward(
        feed_given_g=100, feed_consumed_g=30,
        biomass_gain_mg=1, population=1000
    )

    # No feed
    r_none = calc.feed_efficiency_reward(
        feed_given_g=0, feed_consumed_g=0,
        biomass_gain_mg=0, population=1000
    )

    assert r_good > r_waste, "Good efficiency should beat wasteful"
    assert r_waste < 0, "High waste should be negative"

    print(f"✓ Feed efficiency reward tests passed")
    print(f"  Good: {r_good:.3f}, Wasteful: {r_waste:.3f}, None: {r_none:.3f}")


def test_resource_cost():
    """Test resource cost penalty."""
    calc = RewardCalculator()

    # No resources
    r_none = calc.resource_cost_penalty(water_used_ml=0, aeration_level=0)
    assert r_none == 0 or r_none >= -0.01, "No resources should be ~0"

    # Some resources
    r_some = calc.resource_cost_penalty(water_used_ml=50, aeration_level=1)
    assert r_some < 0, "Resource use should be negative"

    # Heavy resources
    r_heavy = calc.resource_cost_penalty(water_used_ml=200, aeration_level=2)
    assert r_heavy < r_some, "More resources should cost more"

    print(f"✓ Resource cost tests passed")
    print(f"  None: {r_none:.3f}, Some: {r_some:.3f}, Heavy: {r_heavy:.3f}")


def test_terminal_reward():
    """Test terminal bonus calculation."""
    calc = RewardCalculator()

    # Great outcome (target reached, high survival)
    r_great = calc.terminal_reward(
        final_biomass_mg=160,  # Above target
        final_population=950,
        initial_population=1000,
        days_elapsed=14,
        target_days=14
    )

    # Okay outcome
    r_okay = calc.terminal_reward(
        final_biomass_mg=120,
        final_population=850,
        initial_population=1000,
        days_elapsed=14,
        target_days=14
    )

    # Poor outcome
    r_poor = calc.terminal_reward(
        final_biomass_mg=60,
        final_population=500,
        initial_population=1000,
        days_elapsed=16,  # Took too long
        target_days=14
    )

    assert r_great > r_okay > r_poor, "Better outcomes should give higher rewards"
    assert r_great > 0, "Great outcome should be positive"

    print(f"✓ Terminal reward tests passed")
    print(f"  Great: {r_great:.2f}, Okay: {r_okay:.2f}, Poor: {r_poor:.2f}")


def test_full_reward_calculation():
    """Test complete reward calculation."""
    calc = RewardCalculator()

    # Good timestep
    reward_good, comp_good = calc.calculate_reward(
        prev_biomass_mg=50,
        curr_biomass_mg=53,
        prev_population=1000,
        curr_population=999,
        initial_population=1000,
        feed_given_g=100,
        feed_consumed_g=85,
        water_used_ml=20,
        aeration_level=1,
        timestep_hours=4,
        is_terminal=False
    )

    # Bad timestep
    reward_bad, comp_bad = calc.calculate_reward(
        prev_biomass_mg=50,
        curr_biomass_mg=49,
        prev_population=1000,
        curr_population=950,
        initial_population=1000,
        feed_given_g=200,
        feed_consumed_g=50,
        water_used_ml=100,
        aeration_level=2,
        timestep_hours=4,
        is_terminal=False
    )

    assert reward_good > reward_bad, "Good timestep should beat bad"

    print(f"\n✓ Full reward calculation tests passed")
    print(f"\nGood timestep breakdown:")
    print(f"  Biomass: {comp_good.biomass_reward:.3f}")
    print(f"  Survival: {comp_good.survival_reward:.3f}")
    print(f"  Feed eff: {comp_good.feed_efficiency_reward:.3f}")
    print(f"  Resource: {comp_good.resource_cost:.3f}")
    print(f"  TOTAL: {comp_good.total_reward:.3f}")

    print(f"\nBad timestep breakdown:")
    print(f"  Biomass: {comp_bad.biomass_reward:.3f}")
    print(f"  Survival: {comp_bad.survival_reward:.3f}")
    print(f"  Feed eff: {comp_bad.feed_efficiency_reward:.3f}")
    print(f"  Resource: {comp_bad.resource_cost:.3f}")
    print(f"  TOTAL: {comp_bad.total_reward:.3f}")


def test_terminal_episode():
    """Test reward with terminal bonus."""
    calc = RewardCalculator()

    # Successful harvest
    reward_success, comp = calc.calculate_reward(
        prev_biomass_mg=145,
        curr_biomass_mg=150,
        prev_population=920,
        curr_population=920,
        initial_population=1000,
        feed_given_g=80,
        feed_consumed_g=75,
        water_used_ml=10,
        aeration_level=1,
        timestep_hours=4,
        is_terminal=True,
        days_elapsed=14
    )

    assert comp.terminal_bonus > 0, "Successful harvest should have positive terminal bonus"
    assert reward_success > 2, f"Total should be significant, got {reward_success}"

    print(f"\n✓ Terminal episode test passed")
    print(f"  Terminal bonus: {comp.terminal_bonus:.2f}")
    print(f"  Total reward: {reward_success:.2f}")


def test_reward_shaper():
    """Test reward shaping."""
    shaper = RewardShaper(gamma=0.99)

    # Improving state
    shaping_pos = shaper.shaping_reward(
        prev_biomass=50, curr_biomass=55,
        prev_survival=0.95, curr_survival=0.95
    )

    # Declining state
    shaping_neg = shaper.shaping_reward(
        prev_biomass=55, curr_biomass=50,
        prev_survival=0.95, curr_survival=0.90
    )

    assert shaping_pos > 0, "Improving should give positive shaping"
    assert shaping_neg < 0, "Declining should give negative shaping"

    print(f"\n✓ Reward shaper tests passed")
    print(f"  Improving: {shaping_pos:.3f}, Declining: {shaping_neg:.3f}")


def test_batch_score():
    """Test batch scoring metrics."""
    # Good batch
    score_good = calculate_batch_score(
        final_biomass_mg=150,
        final_population=900,
        initial_population=1000,
        total_feed_kg=2.0,
        days_elapsed=14
    )

    # Poor batch
    score_poor = calculate_batch_score(
        final_biomass_mg=80,
        final_population=500,
        initial_population=1000,
        total_feed_kg=3.0,
        days_elapsed=18
    )

    print(f"\n✓ Batch score tests passed")
    print(f"\nGood batch:")
    for k, v in score_good.items():
        print(f"  {k}: {v:.3f}")

    print(f"\nPoor batch:")
    for k, v in score_poor.items():
        print(f"  {k}: {v:.3f}")

    assert score_good['composite_score'] > score_poor['composite_score']


def test_reward_scale():
    """Verify rewards are in reasonable range for PPO."""
    calc = RewardCalculator()

    rewards = []

    # Sample various conditions
    for _ in range(100):
        biomass_delta = np.random.uniform(-2, 5)
        death_rate = np.random.uniform(0, 0.05)

        reward, _ = calc.calculate_reward(
            prev_biomass_mg=50,
            curr_biomass_mg=50 + biomass_delta,
            prev_population=1000,
            curr_population=int(1000 * (1 - death_rate)),
            initial_population=1000,
            feed_given_g=np.random.uniform(50, 150),
            feed_consumed_g=np.random.uniform(30, 100),
            water_used_ml=np.random.uniform(0, 50),
            aeration_level=np.random.randint(0, 3),
            timestep_hours=4,
            is_terminal=False
        )
        rewards.append(reward)

    rewards = np.array(rewards)

    print(f"\n✓ Reward scale test passed")
    print(f"  Mean: {rewards.mean():.3f}")
    print(f"  Std: {rewards.std():.3f}")
    print(f"  Min: {rewards.min():.3f}")
    print(f"  Max: {rewards.max():.3f}")

    # Rewards should be reasonable for PPO (roughly -20 to +20 range)
    assert -20 < rewards.min() < 20, "Rewards should be bounded"
    assert -20 < rewards.max() < 20, "Rewards should be bounded"


if __name__ == "__main__":
    print("=" * 50)
    print("REWARD FUNCTION TESTS")
    print("=" * 50)

    test_biomass_reward()
    test_survival_reward()
    test_feed_efficiency_reward()
    test_resource_cost()
    test_terminal_reward()
    test_full_reward_calculation()
    test_terminal_episode()
    test_reward_shaper()
    test_batch_score()
    test_reward_scale()

    print("\n" + "=" * 50)
    print("✅ ALL REWARD FUNCTION TESTS PASSED")
    print("=" * 50)
