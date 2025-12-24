#!/usr/bin/env python3
# enhanced_metrics.py
# Advanced metrics for RL training and fine-tuning optimization
# Integrates with existing metrics.py for comprehensive evaluation

import json
import re
from typing import Dict, List, Tuple
from collections import Counter
import numpy as np


# ============================================================================
# TIER 1: HARD CONSTRAINTS (Pass/Fail)
# ============================================================================

def check_hard_constraints(output_json: dict, raw_response: str) -> Dict:
    """
    Binary pass/fail checks that must succeed.
    If any fail, the entire output is considered invalid for RL training.

    Returns:
        dict with individual checks and overall pass/fail
    """
    checks = {
        "valid_json": True,  # Already checked if we got here
        "has_contact_info": bool(output_json.get("contact_info")),
        "has_sections": len(output_json.get("sections", [])) > 0,
        "no_truncation_markers": "..." not in raw_response and "etc." not in raw_response.lower(),
        "no_empty_sections": all(
            section.get("content") for section in output_json.get("sections", [])
        ),
        "correct_section_types": all(
            section.get("us_category") in ["Summary", "Experience", "Education", "Skills"]
            for section in output_json.get("sections", [])
        )
    }

    passed = all(checks.values())

    return {
        "checks": checks,
        "passed": passed,
        "fail_count": sum(1 for v in checks.values() if not v),
        "score": 1.0 if passed else 0.0
    }


# ============================================================================
# TIER 2: SEMANTIC FIDELITY METRICS (For RL Reward Signal)
# ============================================================================

def calculate_entity_preservation(original_text: str, output_json: dict) -> Dict:
    """
    Checks if critical entities (dates, numbers, emails, phones) are preserved.
    This is crucial for factual accuracy.
    """
    # Extract entities from original
    original_entities = {
        "dates": re.findall(r'\b\d{4}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b', original_text, re.IGNORECASE),
        "numbers": re.findall(r'\b\d+(?:[.,]\d+)?%?\b', original_text),
        "emails": re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', original_text),
        "phones": re.findall(r'\+?\d[\d\s\-\(\)]{7,}\d', original_text)
    }

    # Extract entities from output JSON
    output_text = json.dumps(output_json, ensure_ascii=False)
    output_entities = {
        "dates": re.findall(r'\b\d{4}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b', output_text, re.IGNORECASE),
        "numbers": re.findall(r'\b\d+(?:[.,]\d+)?%?\b', output_text),
        "emails": re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', output_text),
        "phones": re.findall(r'\+?\d[\d\s\-\(\)]{7,}\d', output_text)
    }

    # Calculate preservation ratios
    preservation = {}
    for entity_type in original_entities.keys():
        orig_count = len(set(original_entities[entity_type]))
        output_count = len(set(output_entities[entity_type]))

        if orig_count == 0:
            preservation[entity_type] = 1.0  # No entities to preserve
        else:
            # Check how many original entities appear in output
            preserved = sum(1 for e in set(original_entities[entity_type]) if e in output_text)
            preservation[entity_type] = preserved / orig_count

    overall_preservation = np.mean(list(preservation.values()))

    return {
        "entity_preservation": preservation,
        "original_entity_counts": {k: len(set(v)) for k, v in original_entities.items()},
        "output_entity_counts": {k: len(set(v)) for k, v in output_entities.items()},
        "overall_preservation": round(overall_preservation, 3),
        "status": "✅" if overall_preservation >= 0.90 else "⚠️" if overall_preservation >= 0.75 else "❌",
        "score": overall_preservation
    }


def calculate_information_density(original_text: str, output_json: dict) -> Dict:
    """
    Measures if the output maintains appropriate information density.
    Detects over-compression (data loss) or over-expansion (hallucination).
    """
    # Get word counts
    original_words = len(re.findall(r'\b\w+\b', original_text))
    output_text = json.dumps(output_json, ensure_ascii=False)
    output_words = len(re.findall(r'\b\w+\b', output_text))

    # Calculate density ratio (should be close to 1.0 for good extraction)
    density_ratio = output_words / original_words if original_words > 0 else 0

    # Per-section density analysis
    section_densities = []
    for section in output_json.get('sections', []):
        category = section.get('us_category')
        content = section.get('content', [])

        if category in ['Experience', 'Education']:
            for entry in content:
                if isinstance(entry, dict):
                    bullets = entry.get('bullets', [])
                    if bullets:
                        avg_words = np.mean([len(re.findall(r'\b\w+\b', b)) for b in bullets])
                        section_densities.append(avg_words)

    avg_bullet_words = np.mean(section_densities) if section_densities else 0

    # Healthy range: 0.7-1.3 (accounting for translation variance)
    is_healthy = 0.7 <= density_ratio <= 1.3

    # Score: Penalize extreme compression or expansion
    if 0.85 <= density_ratio <= 1.15:
        score = 1.0
    elif 0.7 <= density_ratio <= 1.3:
        score = 0.8
    else:
        score = max(0, 1 - abs(1 - density_ratio))

    return {
        "original_words": original_words,
        "output_words": output_words,
        "density_ratio": round(density_ratio, 3),
        "avg_bullet_words": round(avg_bullet_words, 1),
        "is_healthy": is_healthy,
        "status": "✅" if is_healthy else "⚠️",
        "score": score
    }


def calculate_action_verb_quality(output_json: dict) -> Dict:
    """
    Measures use of strong, professional CV action verbs.
    Important for US recruiter expectations.
    """
    # Strong action verbs (past tense for completed work)
    strong_verbs = {
        "led", "managed", "developed", "implemented", "created", "designed",
        "built", "optimized", "improved", "increased", "reduced", "launched",
        "established", "coordinated", "analyzed", "architected", "engineered",
        "delivered", "drove", "executed", "spearheaded", "streamlined",
        "automated", "orchestrated", "pioneered", "transformed", "scaled"
    }

    # Weak/passive verbs to avoid
    weak_verbs = {
        "helped", "assisted", "involved", "participated", "responsible",
        "worked", "tasked", "utilized", "used", "did"
    }

    # Extract all bullets
    all_bullets = []
    for section in output_json.get('sections', []):
        if section.get('us_category') == 'Experience':
            for entry in section.get('content', []):
                if isinstance(entry, dict):
                    all_bullets.extend(entry.get('bullets', []))

    if not all_bullets:
        return {
            "total_bullets": 0,
            "strong_verb_count": 0,
            "weak_verb_count": 0,
            "score": 0.5,
            "status": "⚠️"
        }

    # Count verb usage
    strong_count = sum(1 for bullet in all_bullets if any(verb in bullet.lower() for verb in strong_verbs))
    weak_count = sum(1 for bullet in all_bullets if any(verb in bullet.lower() for verb in weak_verbs))

    strong_ratio = strong_count / len(all_bullets)
    weak_ratio = weak_count / len(all_bullets)

    # Score: Reward strong verbs, penalize weak verbs
    score = min(1.0, strong_ratio * 1.2 - weak_ratio * 0.5)

    return {
        "total_bullets": len(all_bullets),
        "strong_verb_count": strong_count,
        "weak_verb_count": weak_count,
        "strong_ratio": round(strong_ratio, 3),
        "weak_ratio": round(weak_ratio, 3),
        "status": "✅" if strong_ratio >= 0.6 else "⚠️" if strong_ratio >= 0.3 else "❌",
        "score": max(0, score)
    }


def calculate_ats_compliance_score(output_json: dict) -> Dict:
    """
    Measures ATS-friendliness of the output.
    Checks for proper structure, keywords, and formatting.
    """
    checks = {
        "has_contact_name": bool(output_json.get("contact_info", {}).get("name")),
        "has_contact_email": bool(output_json.get("contact_info", {}).get("email")),
        "has_contact_phone": bool(output_json.get("contact_info", {}).get("phone")),
        "has_work_auth": bool(output_json.get("work_authorization")),
        "has_experience_section": any(s.get("us_category") == "Experience" for s in output_json.get("sections", [])),
        "has_education_section": any(s.get("us_category") == "Education" for s in output_json.get("sections", [])),
        "proper_section_order": [s.get("us_category") for s in output_json.get("sections", [])][:2] == ["Summary", "Experience"] or [s.get("us_category") for s in output_json.get("sections", [])][:1] == ["Experience"],
        "no_special_chars_in_contact": not any(c in str(output_json.get("contact_info", {})) for c in ['<', '>', '{', '}']),
        "bullets_are_strings": all(
            isinstance(bullet, str)
            for section in output_json.get("sections", [])
            if section.get("us_category") in ["Experience", "Education"]
            for entry in section.get("content", [])
            if isinstance(entry, dict)
            for bullet in entry.get("bullets", [])
        )
    }

    score = sum(checks.values()) / len(checks)

    return {
        "checks": checks,
        "compliance_score": round(score, 3),
        "status": "✅" if score >= 0.9 else "⚠️" if score >= 0.7 else "❌",
        "score": score
    }


# ============================================================================
# TIER 3: RL REWARD CALCULATION
# ============================================================================

def calculate_rl_reward(original_text: str, output_json: dict, raw_response: str,
                        base_metrics: dict) -> Dict:
    """
    Comprehensive reward function for RL training.
    Combines all metrics into a single differentiable reward signal.

    Args:
        original_text: Raw text from PDF
        output_json: Parsed JSON output
        raw_response: Raw model response (for truncation checks)
        base_metrics: Output from metrics.run_all_metrics()

    Returns:
        dict with reward breakdown and final reward value
    """
    # Run all enhanced metrics
    hard_constraints = check_hard_constraints(output_json, raw_response)
    entity_preservation = calculate_entity_preservation(original_text, output_json)
    information_density = calculate_information_density(original_text, output_json)
    action_verb_quality = calculate_action_verb_quality(output_json)
    ats_compliance = calculate_ats_compliance_score(output_json)

    # If hard constraints fail, return 0 reward
    if not hard_constraints["passed"]:
        return {
            "reward": 0.0,
            "reason": "Hard constraints failed",
            "failed_checks": [k for k, v in hard_constraints["checks"].items() if not v],
            "breakdown": {},
            "grade": "F",
            "enhanced_metrics": {
                "entity_preservation": entity_preservation,
                "information_density": information_density,
                "action_verb_quality": action_verb_quality,
                "ats_compliance": ats_compliance
            },
            "hard_constraints": hard_constraints
        }

    # Weighted reward calculation
    weights = {
        # Base metrics (from existing metrics.py) - 60% weight
        "base_overall": 0.60,

        # Enhanced semantic metrics - 25% weight
        "entity_preservation": 0.08,
        "information_density": 0.07,
        "action_verb_quality": 0.05,

        # ATS compliance - 15% weight
        "ats_compliance": 0.15
    }

    component_scores = {
        "base_overall": base_metrics["overall_score"],
        "entity_preservation": entity_preservation["score"],
        "information_density": information_density["score"],
        "action_verb_quality": action_verb_quality["score"],
        "ats_compliance": ats_compliance["score"]
    }

    # Calculate weighted reward
    reward = sum(component_scores[k] * weights[k] for k in weights.keys())

    # Bonus rewards for excellence
    if reward >= 0.95:
        reward += 0.05  # Perfection bonus
    elif reward >= 0.90:
        reward += 0.02  # Excellence bonus

    # Cap at 1.0
    reward = min(1.0, reward)

    return {
        "reward": round(reward, 4),
        "grade": _get_reward_grade(reward),
        "component_scores": component_scores,
        "weights": weights,
        "weighted_contributions": {k: round(component_scores[k] * weights[k], 4) for k in weights.keys()},
        "enhanced_metrics": {
            "entity_preservation": entity_preservation,
            "information_density": information_density,
            "action_verb_quality": action_verb_quality,
            "ats_compliance": ats_compliance
        },
        "hard_constraints": hard_constraints
    }


def _get_reward_grade(reward: float) -> str:
    """Convert reward to letter grade."""
    if reward >= 0.97: return "A+"
    elif reward >= 0.93: return "A"
    elif reward >= 0.90: return "A-"
    elif reward >= 0.87: return "B+"
    elif reward >= 0.83: return "B"
    elif reward >= 0.80: return "B-"
    elif reward >= 0.75: return "C+"
    elif reward >= 0.70: return "C"
    elif reward >= 0.60: return "D"
    else: return "F"


# ============================================================================
# BULK EVALUATION UTILITIES
# ============================================================================

def calculate_bulk_statistics(rewards_list: List[Dict]) -> Dict:
    """
    Calculate aggregate statistics for bulk evaluation sessions.

    Args:
        rewards_list: List of reward dicts from calculate_rl_reward()

    Returns:
        dict with mean, median, std, min, max, and distribution
    """
    if not rewards_list:
        return {
            "count": 0,
            "mean_reward": 0.0,
            "median_reward": 0.0,
            "std_reward": 0.0,
            "min_reward": 0.0,
            "max_reward": 0.0,
            "grade_distribution": {},
            "component_averages": {},
            "passing_rate": 0.0
        }

    rewards = [r["reward"] for r in rewards_list]

    # Grade distribution
    grades = [r["grade"] for r in rewards_list]
    grade_counts = Counter(grades)

    # Component-wise averages (only for rewards with component_scores)
    component_averages = {}
    valid_rewards = [r for r in rewards_list if "component_scores" in r]

    if valid_rewards:
        # Get all component keys from the first valid reward
        all_components = valid_rewards[0]["component_scores"].keys()
        for component in all_components:
            scores = [r["component_scores"][component] for r in valid_rewards]
            component_averages[component] = round(np.mean(scores), 4) if scores else 0.0

    return {
        "count": len(rewards),
        "mean_reward": round(np.mean(rewards), 4),
        "median_reward": round(np.median(rewards), 4),
        "std_reward": round(np.std(rewards), 4),
        "min_reward": round(min(rewards), 4),
        "max_reward": round(max(rewards), 4),
        "grade_distribution": dict(grade_counts),
        "component_averages": component_averages,
        "passing_rate": round(sum(1 for r in rewards if r >= 0.80) / len(rewards), 3)
    }


# ============================================================================
# COMPARISON UTILITIES
# ============================================================================

def compare_model_outputs(baseline_result: dict, improved_result: dict) -> Dict:
    """
    Compare two model outputs (e.g., baseline vs RL-trained).

    Args:
        baseline_result: Result dict from calculate_rl_reward for baseline model
        improved_result: Result dict from calculate_rl_reward for improved model

    Returns:
        dict with comparison metrics and statistical significance
    """
    baseline_reward = baseline_result["reward"]
    improved_reward = improved_result["reward"]

    improvement = improved_reward - baseline_reward
    improvement_pct = (improvement / baseline_reward * 100) if baseline_reward > 0 else 0

    # Component-wise comparison
    component_improvements = {}
    for component in baseline_result["component_scores"].keys():
        baseline_score = baseline_result["component_scores"][component]
        improved_score = improved_result["component_scores"][component]
        delta = improved_score - baseline_score
        component_improvements[component] = {
            "baseline": round(baseline_score, 4),
            "improved": round(improved_score, 4),
            "delta": round(delta, 4),
            "improvement_pct": round((delta / baseline_score * 100) if baseline_score > 0 else 0, 2)
        }

    return {
        "baseline_reward": baseline_reward,
        "improved_reward": improved_reward,
        "absolute_improvement": round(improvement, 4),
        "relative_improvement_pct": round(improvement_pct, 2),
        "component_improvements": component_improvements,
        "verdict": "🎉 IMPROVED" if improvement > 0.01 else "➡️ NEUTRAL" if improvement > -0.01 else "⚠️ DEGRADED"
    }


if __name__ == "__main__":
    print("Enhanced Metrics System for RL Training")
    print("=" * 60)
    print("\nThis module provides advanced metrics for:")
    print("1. Hard constraint checking (pass/fail)")
    print("2. Semantic fidelity scoring")
    print("3. RL reward calculation")
    print("4. Bulk evaluation statistics")
    print("5. Model comparison")
    print("\nImport and use with your existing metrics.py module.")
