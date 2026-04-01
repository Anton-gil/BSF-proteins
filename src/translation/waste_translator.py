"""
Waste Translator

Converts between farmer-friendly waste names and C:N ratios.
Uses the existing configs/waste_lookup.yaml database.
"""

import yaml
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class WasteType:
    """Information about a waste type."""
    name: str
    cn_ratio: float
    moisture_pct: float
    category: str
    availability: str
    notes: str = ""


class WasteTranslator:
    """
    Translates between waste names and C:N ratios.

    Usage:
        translator = WasteTranslator()

        # Get C:N for a waste
        cn = translator.get_cn_ratio("banana_peels")

        # Find wastes to achieve target C:N
        mix = translator.suggest_waste_mix(
            target_cn=18,
            available_wastes=["banana_peels", "rice_bran"]
        )
    """

    def __init__(self, config_path: str = "configs/waste_lookup.yaml"):
        """Load waste database from YAML config."""
        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        self.waste_types: Dict[str, WasteType] = {}

        for name, info in data.get('waste_types', {}).items():
            # Support both 'moisture_pct' and 'moisture_percent' key names
            moisture = info.get('moisture_pct', info.get('moisture_percent', 70))
            self.waste_types[name] = WasteType(
                name=name,
                cn_ratio=float(info.get('cn_ratio', 25)),
                moisture_pct=float(moisture),
                category=info.get('category', 'other'),
                availability=info.get('availability', 'common'),
                notes=info.get('notes', '')
            )

        # Human-readable display names
        self.display_names = {
            name: name.replace('_', ' ').title()
            for name in self.waste_types.keys()
        }

    # ------------------------------------------------------------------
    # Lookups
    # ------------------------------------------------------------------

    def get_cn_ratio(self, waste_name: str) -> Optional[float]:
        """Get C:N ratio for a waste type."""
        waste = self.waste_types.get(waste_name)
        return waste.cn_ratio if waste else None

    def get_moisture(self, waste_name: str) -> Optional[float]:
        """Get moisture percentage for a waste type."""
        waste = self.waste_types.get(waste_name)
        return waste.moisture_pct if waste else None

    def get_waste_info(self, waste_name: str) -> Optional[WasteType]:
        """Get full information about a waste type."""
        return self.waste_types.get(waste_name)

    def list_wastes(self, category: Optional[str] = None) -> List[str]:
        """
        List available waste types.

        Args:
            category: Filter by category (fruit, vegetable, grain, etc.)

        Returns:
            List of waste names
        """
        if category:
            return [
                name for name, waste in self.waste_types.items()
                if waste.category == category
            ]
        return list(self.waste_types.keys())

    def list_categories(self) -> List[str]:
        """List available waste categories."""
        return list(set(w.category for w in self.waste_types.values()))

    # ------------------------------------------------------------------
    # Mix calculations
    # ------------------------------------------------------------------

    def calculate_mix_cn(
        self,
        waste_amounts: Dict[str, float]
    ) -> Tuple[float, float]:
        """
        Calculate weighted C:N ratio and moisture for a waste mix.

        Args:
            waste_amounts: {waste_name: amount_kg}

        Returns:
            (weighted_cn_ratio, weighted_moisture_pct)
        """
        total_weight = sum(waste_amounts.values())

        if total_weight <= 0:
            return 25.0, 70.0

        weighted_cn = 0.0
        weighted_moisture = 0.0

        for waste_name, amount in waste_amounts.items():
            waste = self.waste_types.get(waste_name)
            if waste and amount > 0:
                frac = amount / total_weight
                weighted_cn += waste.cn_ratio * frac
                weighted_moisture += waste.moisture_pct * frac

        return weighted_cn, weighted_moisture

    def suggest_waste_mix(
        self,
        target_cn: float,
        available_wastes: List[str],
        total_amount_kg: float = 1.0
    ) -> Dict[str, float]:
        """
        Suggest a two-component waste mix to achieve a target C:N ratio.

        Picks the closest high-C:N and low-C:N waste and blends them
        proportionally to hit the target.

        Args:
            target_cn: Target C:N ratio
            available_wastes: Waste names the farmer has available
            total_amount_kg: Total feed weight needed

        Returns:
            {waste_name: amount_kg}
        """
        if not available_wastes:
            return {}

        # Collect valid wastes with known C:N
        waste_cn: Dict[str, float] = {}
        for name in available_wastes:
            cn = self.get_cn_ratio(name)
            if cn is not None:
                waste_cn[name] = cn

        if not waste_cn:
            return {}

        if len(waste_cn) == 1:
            name = list(waste_cn.keys())[0]
            return {name: total_amount_kg}

        # Split into high-carbon and low-carbon pools
        high_cn = [(n, c) for n, c in waste_cn.items() if c >= target_cn]
        low_cn  = [(n, c) for n, c in waste_cn.items() if c < target_cn]

        # If everything is on one side, just use the closest
        if not high_cn or not low_cn:
            closest = min(waste_cn.items(), key=lambda x: abs(x[1] - target_cn))
            return {closest[0]: total_amount_kg}

        # Pick the nearer representative from each side
        high_waste, high_val = min(high_cn, key=lambda x: x[1] - target_cn)
        low_waste,  low_val  = max(low_cn,  key=lambda x: target_cn - x[1])

        # Lever-rule: a = (target - low) / (high - low)
        if high_val == low_val:
            a = 0.5
        else:
            a = (target_cn - low_val) / (high_val - low_val)
            a = max(0.0, min(1.0, a))

        return {
            high_waste: round(a * total_amount_kg, 3),
            low_waste:  round((1.0 - a) * total_amount_kg, 3)
        }

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    def get_display_name(self, waste_name: str) -> str:
        """Return a human-readable display name."""
        return self.display_names.get(
            waste_name, waste_name.replace('_', ' ').title()
        )

    def format_mix_instructions(
        self,
        waste_amounts: Dict[str, float]
    ) -> str:
        """
        Format a waste mix as human-readable farmer instructions.

        Args:
            waste_amounts: {waste_name: amount_kg}

        Returns:
            Instruction string, e.g. "Mix and feed: 1.2 kg Banana Peels, 400 g Rice Bran"
        """
        if not waste_amounts:
            return "No feed recommended"

        parts = []
        for name, amount in waste_amounts.items():
            if amount > 0:
                display = self.get_display_name(name)
                if amount >= 1.0:
                    parts.append(f"{amount:.1f} kg {display}")
                else:
                    parts.append(f"{amount * 1000:.0f} g {display}")

        if len(parts) == 1:
            return f"Feed {parts[0]}"
        return f"Mix and feed: {', '.join(parts)}"
