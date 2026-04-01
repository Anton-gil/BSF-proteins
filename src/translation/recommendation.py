"""
Recommendation Generator

Converts RL action arrays into farmer-friendly daily recommendations:
feeding instructions, moisture actions, and aeration levels.
"""

import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from src.translation.waste_translator import WasteTranslator


@dataclass
class DailyRecommendation:
    """Complete daily recommendation for the farmer."""
    date: datetime
    feed_instruction: str
    feed_amounts: Dict[str, float]   # {waste_name: kg}
    target_cn: float
    moisture_action: str
    aeration_action: str
    notes: List[str]
    confidence: float               # 0–1


class RecommendationGenerator:
    """
    Translates RL actions → farmer instructions.

    Usage:
        gen = RecommendationGenerator()
        rec = gen.generate(
            action=np.array([0.5, 0.7, 0.3, 0.5]),
            available_wastes=["banana_peels", "rice_bran"],
            larvae_count=1000,
            age_days=7
        )
        print(gen.format_recommendation(rec))
    """

    # C:N action [0] maps linearly: 0 → CN=10, 1 → CN=30
    _CN_MIN, _CN_MAX = 10.0, 30.0

    _MOISTURE_ACTIONS = {
        0: ("No action needed",
            "Moisture level is fine."),
        1: ("Add water",
            "Substrate is getting dry — moisten gently."),
        2: ("Increase ventilation",
            "Substrate is too wet — open the container or add holes."),
    }

    _AERATION_LEVELS = {
        0: ("Low aeration",    "Keep the container mostly covered."),
        1: ("Normal aeration", "Standard airflow is fine."),
        2: ("High aeration",   "Open container widely or add ventilation holes."),
    }

    def __init__(
        self,
        waste_translator: Optional[WasteTranslator] = None,
        base_feed_rate_mg: float = 100.0   # mg per larva per day at peak
    ):
        self.waste_translator = waste_translator or WasteTranslator()
        self.base_feed_rate = base_feed_rate_mg

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _scale_action(self, action: np.ndarray) -> Tuple[float, float, int, int]:
        """
        Decode normalised [0,1]^4 action vector.

        Returns:
            (target_cn, feed_multiplier, moisture_idx, aeration_idx)
        """
        target_cn = self._CN_MIN + action[0] * (self._CN_MAX - self._CN_MIN)
        feed_mult = float(action[1]) * 2.0   # [0, 2]

        moist_idx = 0 if action[2] < 0.33 else (1 if action[2] < 0.67 else 2)
        aer_idx   = 0 if action[3] < 0.33 else (1 if action[3] < 0.67 else 2)

        return float(target_cn), float(feed_mult), int(moist_idx), int(aer_idx)

    def _age_multiplier(self, age_days: float) -> float:
        """Feeding rate multiplier by developmental phase."""
        if age_days <= 3:
            return 0.5     # Neonate
        elif age_days <= 7:
            return 1.0     # Exponential growth
        elif age_days <= 10:
            return 1.5     # Peak feeding
        else:
            return 0.5     # Pre-pupa

    def calculate_feed_amount(
        self,
        feed_multiplier: float,
        larvae_count: int,
        age_days: float
    ) -> float:
        """
        Compute total feed quantity in kg.

        Args:
            feed_multiplier: RL-derived multiplier in [0, 2]
            larvae_count: Current larvae population
            age_days: Larval age

        Returns:
            Feed amount in kg
        """
        age_mult  = self._age_multiplier(age_days)
        total_mg  = self.base_feed_rate * larvae_count * age_mult * feed_multiplier
        return total_mg / 1_000_000.0   # mg → kg

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def generate(
        self,
        action: np.ndarray,
        available_wastes: List[str],
        larvae_count: int,
        age_days: float,
        current_cn: Optional[float] = None
    ) -> DailyRecommendation:
        """
        Generate a daily recommendation from an RL action.

        Args:
            action: RL action [4] in [0, 1]
            available_wastes: Waste the farmer has on hand
            larvae_count: Estimated current population
            age_days: Larval age in days
            current_cn: Observed C:N ratio (boosts confidence if provided)

        Returns:
            DailyRecommendation dataclass
        """
        target_cn, feed_mult, moist_idx, aer_idx = self._scale_action(action)
        total_feed_kg = self.calculate_feed_amount(feed_mult, larvae_count, age_days)

        # Waste mix
        if total_feed_kg >= 0.01 and available_wastes:
            feed_amounts = self.waste_translator.suggest_waste_mix(
                target_cn=target_cn,
                available_wastes=available_wastes,
                total_amount_kg=total_feed_kg
            )
            feed_instruction = self.waste_translator.format_mix_instructions(feed_amounts)
        elif total_feed_kg < 0.01:
            feed_amounts = {}
            feed_instruction = "No feeding needed right now"
        else:
            feed_amounts = {}
            feed_instruction = "No waste types available — check settings"

        moisture_action, moisture_note = self._MOISTURE_ACTIONS[moist_idx]
        aeration_action, aeration_note = self._AERATION_LEVELS[aer_idx]

        # Context notes
        notes: List[str] = []
        if age_days < 3:
            notes.append("Young larvae — keep meals small.")
        elif age_days > 11:
            notes.append("Approaching pre-pupa stage — reduced appetite is normal.")
        if moist_idx == 1:
            notes.append(moisture_note)
        elif moist_idx == 2:
            notes.append(moisture_note)
        if aer_idx == 2:
            notes.append(aeration_note)

        # Confidence
        confidence = 0.65
        if current_cn is not None:
            confidence += 0.10
        if len(available_wastes) >= 2:
            confidence += 0.10
        if 3.0 <= age_days <= 10.0:
            confidence += 0.15   # Most predictable phase

        return DailyRecommendation(
            date=datetime.now(),
            feed_instruction=feed_instruction,
            feed_amounts=feed_amounts,
            target_cn=target_cn,
            moisture_action=moisture_action,
            aeration_action=aeration_action,
            notes=notes,
            confidence=float(min(1.0, confidence))
        )

    def format_recommendation(self, rec: DailyRecommendation) -> str:
        """Render a DailyRecommendation as a human-readable string."""
        lines = [
            f"Daily Recommendation — {rec.date.strftime('%Y-%m-%d %H:%M')}",
            "",
            f"FEEDING:   {rec.feed_instruction}",
            f"Target C:N ratio: {rec.target_cn:.0f}:1",
            "",
            f"MOISTURE:  {rec.moisture_action}",
            f"AERATION:  {rec.aeration_action}",
        ]
        if rec.notes:
            lines.append("")
            lines.append("NOTES:")
            for note in rec.notes:
                lines.append(f"  • {note}")
        lines += ["", f"Confidence: {rec.confidence * 100:.0f}%"]
        return "\n".join(lines)
