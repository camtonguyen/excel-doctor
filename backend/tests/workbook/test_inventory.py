from pathlib import Path

import yaml

from backend.workbook.inventory import get_inventory

FIXTURES_DIR = Path(__file__).parent.parent.parent.parent / "fixtures"
META_PATH = Path(__file__).parent.parent / "fixtures_meta.yaml"

def load_meta() -> dict:
    with open(META_PATH, "r") as f:
        return yaml.safe_load(f)["fixtures"]

def test_inventory_matches_metadata():
    meta = load_meta()
    for filename, data in meta.items():
        fixture_path = FIXTURES_DIR / filename
        if not fixture_path.exists():
            continue
            
        expected_inventory = data.get("inventory", {})
        
        # Act
        actual_inventory = get_inventory(fixture_path)
        
        # Assert each expected key
        for key, expected_value in expected_inventory.items():
            if key == "requires_tier_a":
                assert actual_inventory.requires_tier_a == expected_value, f"Fixture {filename}: requires_tier_a mismatch"
            else:
                actual_value = getattr(actual_inventory, key)
                assert actual_value == expected_value, f"Fixture {filename}: {key} mismatch. Expected {expected_value}, got {actual_value}"
