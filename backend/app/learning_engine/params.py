"""Parameter validation and defaults for learning algorithms."""

import hashlib
import json
from typing import Any


def normalize_params(params: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize parameters to canonical form for checksum computation.
    
    Sorts keys, converts to stable JSON representation.
    """
    return json.loads(json.dumps(params, sort_keys=True))


def compute_checksum(params: dict[str, Any]) -> str:
    """
    Compute SHA256 checksum of normalized parameters.
    
    Args:
        params: Parameter dictionary
    
    Returns:
        Hex digest of SHA256 hash
    """
    normalized = normalize_params(params)
    params_str = json.dumps(normalized, sort_keys=True)
    return hashlib.sha256(params_str.encode()).hexdigest()


def get_default_params(algo_key: str) -> dict[str, Any]:
    """
    Get default parameters for an algorithm.
    
    Args:
        algo_key: Algorithm key (e.g., "mastery")
    
    Returns:
        Default parameter dictionary
    """
    defaults = {
        "mastery": {
            "lookback_days": 90,
            "min_attempts": 5,
            "recency_buckets": [
                {"days": 7, "weight": 0.50},
                {"days": 30, "weight": 0.30},
                {"days": 90, "weight": 0.20},
            ],
            "difficulty_weights": {
                "easy": 0.90,
                "medium": 1.00,
                "hard": 1.10,
            },
            "use_difficulty": False,
        },
        "revision": {
            "horizon_days": 7,
            "min_attempts": 5,
            "mastery_bands": [
                {"name": "weak", "max": 0.39},
                {"name": "medium", "max": 0.69},
                {"name": "strong", "max": 0.84},
                {"name": "mastered", "max": 1.00},
            ],
            "spacing_days": {
                "weak": 1,
                "medium": 2,
                "strong": 5,
                "mastered": 12,
            },
            "question_counts": {
                "weak": [15, 20],
                "medium": [10, 15],
                "strong": [5, 10],
                "mastered": [5, 5],
            },
            "priority_weights": {
                "mastery_inverse": 70,
                "recency": 2,
                "low_data_bonus": 10,
            },
        },
        "difficulty": {
            "window_size": 100,
            "min_attempts": 10,
        },
        "adaptive": {
            "exploration_rate": 0.2,
            "target_accuracy": 0.75,
        },
        "mistakes": {
            "min_frequency": 3,
            "lookback_days": 90,
        },
    }
    return defaults.get(algo_key, {})


def validate_params(algo_key: str, params: dict[str, Any]) -> tuple[bool, str | None]:
    """
    Validate parameters for an algorithm.
    
    Args:
        algo_key: Algorithm key
        params: Parameter dictionary to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Basic validation - can be extended per algorithm
    if not isinstance(params, dict):
        return False, "Parameters must be a dictionary"
    
    # Algorithm-specific validation
    if algo_key == "mastery":
        if "lookback_days" in params and params["lookback_days"] < 1:
            return False, "mastery.lookback_days must be >= 1"
        if "min_attempts" in params and params["min_attempts"] < 1:
            return False, "mastery.min_attempts must be >= 1"
        if "recency_buckets" in params:
            if not isinstance(params["recency_buckets"], list):
                return False, "mastery.recency_buckets must be a list"
            for bucket in params["recency_buckets"]:
                if not isinstance(bucket, dict) or "days" not in bucket or "weight" not in bucket:
                    return False, "mastery.recency_buckets items must have 'days' and 'weight'"
                if bucket["days"] < 1:
                    return False, "mastery.recency_buckets.days must be >= 1"
                if not (0 <= bucket["weight"] <= 1):
                    return False, "mastery.recency_buckets.weight must be between 0 and 1"
    elif algo_key == "revision":
        if "horizon_days" in params and params["horizon_days"] < 1:
            return False, "revision.horizon_days must be >= 1"
        if "min_attempts" in params and params["min_attempts"] < 1:
            return False, "revision.min_attempts must be >= 1"
        if "mastery_bands" in params:
            if not isinstance(params["mastery_bands"], list):
                return False, "revision.mastery_bands must be a list"
            for band in params["mastery_bands"]:
                if not isinstance(band, dict) or "name" not in band or "max" not in band:
                    return False, "revision.mastery_bands items must have 'name' and 'max'"
        if "spacing_days" in params:
            if not isinstance(params["spacing_days"], dict):
                return False, "revision.spacing_days must be a dictionary"
        if "question_counts" in params:
            if not isinstance(params["question_counts"], dict):
                return False, "revision.question_counts must be a dictionary"
    elif algo_key == "difficulty":
        if "min_attempts" in params and params["min_attempts"] < 1:
            return False, "difficulty.min_attempts must be >= 1"
    elif algo_key == "adaptive":
        if "exploration_rate" in params and not (0 <= params["exploration_rate"] <= 1):
            return False, "adaptive.exploration_rate must be between 0 and 1"
    elif algo_key == "mistakes":
        if "min_frequency" in params and params["min_frequency"] < 1:
            return False, "mistakes.min_frequency must be >= 1"
    
    return True, None
