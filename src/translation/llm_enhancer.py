"""
LLM Enhancer
============
Uses a local Ollama model to generate contextually appropriate,
empathetic coach messages based on farmer observations and RL recommendations.

Requirements:
    - Ollama installed and running: https://ollama.ai
    - Model pulled: `ollama pull llama3.2:1b`  (or phi3:mini for better quality)

Graceful fallback: if Ollama is not running, returns None and the caller
falls back to the structured recommendation as-is.
"""

import logging
import urllib.request
import urllib.error
import json
from typing import Dict, List, Optional

logger = logging.getLogger("bsf-llm")

# Ollama local endpoint — no API key needed
OLLAMA_URL = "http://localhost:11434/api/generate"

# Recommended lightweight models (in preference order):
#   llama3.2:1b  — fastest (~1.3 GB),  good enough for coaching text
#   phi3:mini    — better quality (~2.2 GB), still fast
#   gemma2:2b   — balanced (~1.6 GB)
DEFAULT_MODEL = "llama3.2:1b"


# ─── Severity helpers ────────────────────────────────────────────────────────

_MORTALITY_SEVERITY = {
    "none": 0,
    "few":  1,
    "some": 2,
    "many": 3,
}

_ACTIVITY_CONCERN = {
    "very_active": 0,
    "normal":      1,
    "sluggish":    2,
}

_SUBSTRATE_CONCERN = {
    "good":   0,
    "dry":    1,
    "wet":    1,
    "soggy":  2,
}

_SMELL_CONCERN = {
    "normal":   0,
    "sour":     1,
    "ammonia":  2,
}


def _overall_severity(
    mortality: str,
    activity: str,
    substrate: str,
    smell: str,
) -> int:
    """0=good, 1=mild concern, 2=serious concern."""
    score = (
        _MORTALITY_SEVERITY.get(mortality, 0)
        + _ACTIVITY_CONCERN.get(activity, 0)
        + _SUBSTRATE_CONCERN.get(substrate, 0)
        + _SMELL_CONCERN.get(smell, 0)
    )
    if score == 0:
        return 0
    elif score <= 2:
        return 1
    else:
        return 2


# ─── Prompt builder ──────────────────────────────────────────────────────────

def _build_prompt(
    mortality: str,
    activity: str,
    substrate: str,
    smell: str,
    age_days: float,
    feed_instruction: str,
    moisture_action: str,
    aeration_action: str,
    notes: List[str],
    confidence: float,
    trajectory: str,
    available_wastes: List[str],
) -> str:
    severity = _overall_severity(mortality, activity, substrate, smell)

    tone_guide = {
        0: "The farmer's batch looks healthy. Be warm, encouraging, and brief.",
        1: "There are some mild concerns. Be calm, practical, and supportive — not alarming.",
        2: "There are serious concerns. Be empathetic, direct, and clear about what needs to happen. Do NOT open with 'great' or any positive filler.",
    }[severity]

    waste_list = ", ".join(available_wastes) if available_wastes else "unspecified"
    notes_str  = " | ".join(notes) if notes else "none"

    prompt = f"""You are an expert BSF (Black Soldier Fly) farming coach. A farmer just checked in on their larvae batch.

FARMER OBSERVATIONS:
- Larvae activity: {activity}
- Visible mortality: {mortality}
- Substrate condition: {substrate}
- Smell: {smell}
- Larvae age: {age_days:.0f} days
- Available waste: {waste_list}

RL SYSTEM RECOMMENDATION:
- Feeding: {feed_instruction}
- Moisture: {moisture_action}
- Aeration: {aeration_action}
- Growth trajectory: {trajectory}
- Confidence: {int(confidence * 100)}%
- Notes: {notes_str}

TONE GUIDE: {tone_guide}

Write a short coach message (3-5 sentences) for the farmer. Be specific to their situation. Use plain language — no jargon. Do not start with "Great!" or similar empty openers if there are concerns. Do not repeat the raw numbers or percentages.

Coach message:"""

    return prompt


# ─── Ollama caller ───────────────────────────────────────────────────────────

def _call_ollama(prompt: str, model: str = DEFAULT_MODEL, timeout: int = 30) -> Optional[str]:
    """
    Call Ollama's local REST API.  Returns the generated text or None on failure.
    Uses urllib to avoid requiring the `requests` package.
    """
    payload = json.dumps({
        "model":  model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "num_predict": 200,   # max tokens — keep response short
            "top_p": 0.9,
        },
    }).encode("utf-8")

    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            text = body.get("response", "").strip()
            return text if text else None
    except urllib.error.URLError as e:
        logger.warning("Ollama not reachable (%s) — skipping LLM enhancement.", e.reason)
        return None
    except Exception as e:
        logger.warning("LLM call failed: %s — skipping LLM enhancement.", e)
        return None


# ─── Public interface ─────────────────────────────────────────────────────────

class LLMEnhancer:
    """
    Wraps the local Ollama LLM to produce contextual coach messages.

    Usage:
        enhancer = LLMEnhancer()
        msg = enhancer.enhance(
            mortality="few", activity="sluggish", substrate="good", smell="normal",
            age_days=5.0,
            feed_instruction="Feed 60% vegetable mix + 40% coffee grounds",
            moisture_action="No action needed",
            aeration_action="Normal aeration",
            notes=["Young larvae — keep meals small."],
            confidence=0.75,
            trajectory="On Track",
            available_wastes=["Vegetable Scraps", "Coffee Grounds"],
        )
        # msg is a string, or None if Ollama is unavailable
    """

    def __init__(self, model: str = DEFAULT_MODEL):
        self.model = model
        self._available: Optional[bool] = None   # lazy check

    def _check_available(self) -> bool:
        """Ping Ollama once to see if it's up."""
        if self._available is not None:
            return self._available
        try:
            req = urllib.request.Request(
                "http://localhost:11434/api/tags",
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                # Check if our model is pulled
                model_names = [m.get("name", "") for m in body.get("models", [])]
                has_model = any(self.model in name for name in model_names)
                if not has_model:
                    logger.warning(
                        "Model '%s' not found in Ollama. Run: ollama pull %s",
                        self.model, self.model,
                    )
                self._available = True   # Ollama is up; model check is just a warning
                return True
        except Exception:
            self._available = False
            logger.info("Ollama not running — LLM enhancement disabled.")
            return False

    def enhance(
        self,
        mortality: str,
        activity: str,
        substrate: str,
        smell: str,
        age_days: float,
        feed_instruction: str,
        moisture_action: str,
        aeration_action: str,
        notes: List[str],
        confidence: float,
        trajectory: str,
        available_wastes: List[str],
    ) -> Optional[str]:
        """
        Generate a contextual coach message.

        Returns:
            A natural-language coaching string, or None if Ollama is unavailable.
        """
        if not self._check_available():
            return None

        prompt = _build_prompt(
            mortality=mortality,
            activity=activity,
            substrate=substrate,
            smell=smell,
            age_days=age_days,
            feed_instruction=feed_instruction,
            moisture_action=moisture_action,
            aeration_action=aeration_action,
            notes=notes,
            confidence=confidence,
            trajectory=trajectory,
            available_wastes=available_wastes,
        )

        return _call_ollama(prompt, model=self.model)
