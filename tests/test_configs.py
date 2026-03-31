"""Test that all config files load correctly."""
import yaml
from pathlib import Path

def test_configs_load():
    """Verify all YAML configs load without error."""
    config_dir = Path("configs")
    
    configs = ["environment.yaml", "training.yaml", "waste_lookup.yaml"]
    
    for config_name in configs:
        config_path = config_dir / config_name
        assert config_path.exists(), f"Missing: {config_path}"
        
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        assert data is not None, f"Empty config: {config_name}"
        print(f"✓ {config_name} loaded successfully")
        print(f"  Keys: {list(data.keys())[:5]}...")
    
    print("\n✅ All configs valid!")

def test_environment_params():
    """Verify environment.yaml has required parameters."""
    with open("configs/environment.yaml", "r", encoding="utf-8") as f:
        env = yaml.safe_load(f)
    
    # Check critical sections exist
    required_sections = [
        "larvae", "growth", "temperature", "moisture", 
        "cn_ratio", "feeding", "mortality", "simulation",
        "state_bounds", "action_bounds"
    ]
    
    for section in required_sections:
        assert section in env, f"Missing section: {section}"
        print(f"✓ {section} section present")
    
    # Check specific critical values
    assert env["temperature"]["optimal_min_c"] == 27
    assert env["temperature"]["optimal_max_c"] == 32
    assert env["cn_ratio"]["optimal_min"] == 14
    assert env["cn_ratio"]["optimal_max"] == 18
    
    print("\n✅ Environment params validated!")

def test_waste_lookup():
    """Verify waste_lookup.yaml has required waste types."""
    with open("configs/waste_lookup.yaml", "r", encoding="utf-8") as f:
        waste = yaml.safe_load(f)
    
    assert "waste_types" in waste, "Missing waste_types"
    
    # Check some common wastes exist
    common_wastes = ["banana_peels", "rice_bran", "kitchen_waste_mixed"]
    for w in common_wastes:
        assert w in waste["waste_types"], f"Missing waste: {w}"
        assert "cn_ratio" in waste["waste_types"][w]
        print(f"✓ {w}: C:N = {waste['waste_types'][w]['cn_ratio']}")
    
    print(f"\n✅ {len(waste['waste_types'])} waste types loaded!")

if __name__ == "__main__":
    test_configs_load()
    print("\n" + "="*50 + "\n")
    test_environment_params()
    print("\n" + "="*50 + "\n")
    test_waste_lookup()
