# metrics.py
# Comprehensive CV Extraction Quality Metrics

import json
import re
from collections import Counter

# === METRIC 1: BULLET COUNT PRESERVATION ===
def calculate_bullet_preservation_score(original_text, output_json):
    """
    Verifies 1:1 bullet mapping between source CV and output JSON.
    Directly tests mirror-translation fidelity.

    Returns:
        dict with original_count, output_count, preservation_ratio, status
    """
    # Extract bullet-like patterns from original text
    # Matches: • bullet, - bullet, * bullet, or numbered lists
    original_bullets = re.findall(r'(?:^|\n)[\s]*[•\-\*\d+\.]\s*(.+)', original_text, re.MULTILINE)

    # Count bullets in output JSON
    output_bullets = []
    for section in output_json.get('sections', []):
        if section.get('us_category') in ['Experience', 'Education']:
            for entry in section.get('content', []):
                if isinstance(entry, dict):
                    output_bullets.extend(entry.get('bullets', []))

    preservation_ratio = len(output_bullets) / len(original_bullets) if original_bullets else 1.0

    return {
        "original_count": len(original_bullets),
        "output_count": len(output_bullets),
        "preservation_ratio": round(preservation_ratio, 2),
        "status": "✅" if 0.85 <= preservation_ratio <= 1.15 else "❌",  # Allow 15% variance
        "score": min(1.0, preservation_ratio) if preservation_ratio <= 1.0 else max(0, 2 - preservation_ratio)
    }

# === METRIC 2: JSON INTEGRITY SCORE ===
def calculate_json_integrity_score(output_json):
    """
    Checks for JSON string integrity issues.
    Detects physical newlines, malformed arrays, empty strings.

    Returns:
        dict with total_issues, issues list, status
    """
    issues = []

    def check_value(value, path="root"):
        if isinstance(value, str):
            # Check for physical newlines (not escaped)
            if '\n' in value and '\\n' not in repr(value):
                issues.append({"path": path, "issue": "Unescaped newline in string", "sample": value[:50]})

            # Check for empty strings where content expected
            if value.strip() == "" and "bullets" in path:
                issues.append({"path": path, "issue": "Empty string in bullets"})

        elif isinstance(value, list):
            # Check for empty lists where content expected
            if len(value) == 0 and ("content" in path or "bullets" in path):
                issues.append({"path": path, "issue": "Empty array"})

            for i, item in enumerate(value):
                check_value(item, f"{path}[{i}]")

        elif isinstance(value, dict):
            for k, v in value.items():
                check_value(v, f"{path}.{k}")

    check_value(output_json)

    return {
        "total_issues": len(issues),
        "issues": issues[:10],  # Limit to first 10 for display
        "status": "✅" if len(issues) == 0 else "❌",
        "score": max(0, 1 - (len(issues) * 0.1))  # -0.1 per issue
    }

# === METRIC 3: PHANTOM SECTION DETECTION ===
def detect_phantom_sections(output_json):
    """
    Detects sections that are empty but not omitted.
    Tests the conditional section logic from prompts.

    Returns:
        dict with phantom_sections list, count, status
    """
    phantoms = []

    for section in output_json.get('sections', []):
        content = section.get('content', [])
        category = section.get('us_category', 'Unknown')

        # Check for empty content
        if not content:
            phantoms.append({"section": category, "issue": "Empty content array"})
        elif content == [] or content == [''] or content == [[]]:
            phantoms.append({"section": category, "issue": "Null/empty placeholder"})

        # Check for empty objects in Experience/Education
        elif isinstance(content, list):
            for idx, entry in enumerate(content):
                if isinstance(entry, dict):
                    if not entry.get('bullets', []) and category in ['Experience', 'Education']:
                        phantoms.append({"section": f"{category}[{idx}]", "issue": "Empty bullets array"})

    return {
        "phantom_sections": phantoms,
        "count": len(phantoms),
        "status": "✅" if len(phantoms) == 0 else "❌",
        "score": max(0, 1 - (len(phantoms) * 0.2))  # -0.2 per phantom
    }

# === METRIC 4: STRUCTURAL COMPLIANCE SCORE ===
def calculate_structural_compliance(output_json):
    """
    Checks if sections follow the mandatory US resume order:
    Summary → Experience → Education → Skills

    Returns:
        dict with expected, actual, compliant, status
    """
    expected_order = ["Summary", "Experience", "Education", "Skills"]
    actual_order = [s.get('us_category') for s in output_json.get('sections', [])]

    # Filter to only categories that exist in both
    present_categories = [cat for cat in expected_order if cat in actual_order]
    actual_filtered = [cat for cat in actual_order if cat in expected_order]

    is_compliant = present_categories == actual_filtered

    # Calculate order score (partial credit for partially correct order)
    if not present_categories:
        order_score = 1.0  # No applicable sections
    else:
        # Count how many adjacent pairs are in correct order
        correct_pairs = 0
        total_pairs = len(present_categories) - 1
        for i in range(total_pairs):
            if actual_filtered[i] == present_categories[i]:
                correct_pairs += 1
        order_score = correct_pairs / total_pairs if total_pairs > 0 else 1.0

    return {
        "expected_order": expected_order,
        "actual_order": actual_order,
        "present_categories": present_categories,
        "compliant": is_compliant,
        "status": "✅" if is_compliant else "❌",
        "score": 1.0 if is_compliant else order_score
    }

# === METRIC 5: TRANSLATION QUALITY SCORE ===
def calculate_translation_quality(original_text, output_json):
    """
    Heuristic checks for translation quality.
    Ensures professional English without untranslated content.

    Returns:
        dict with checks, quality_score, status
    """
    # Extract English text from output
    english_text = json.dumps(output_json, ensure_ascii=False).lower()

    # Professional CV action verbs
    action_verbs = ['led', 'managed', 'developed', 'implemented', 'created',
                   'designed', 'built', 'optimized', 'improved', 'increased',
                   'reduced', 'launched', 'established', 'coordinated', 'analyzed']

    # Common untranslated words (PT/IT/FR/ES)
    untranslated_markers = [
        'esperienze', 'istruzione', 'competenze',  # Italian
        'resumo', 'experiência', 'formação', 'habilidades',  # Portuguese
        'expérience', 'formation', 'compétences',  # French
        'experiencia', 'educación', 'habilidades'  # Spanish
    ]

    checks = {
        "has_action_verbs": any(verb in english_text for verb in action_verbs),
        "no_untranslated": not any(marker in english_text for marker in untranslated_markers),
        "has_bullets": "bullets" in english_text and len(re.findall(r'"bullets":\s*\[', english_text)) > 0,
        "no_placeholder_text": "lorem ipsum" not in english_text and "todo" not in english_text
    }

    quality_score = sum(checks.values()) / len(checks)

    return {
        "checks": checks,
        "quality_score": round(quality_score, 2),
        "status": "✅" if quality_score >= 0.75 else "❌",
        "score": quality_score
    }

# === METRIC 6: FIELD COVERAGE RATE ===
def calculate_field_coverage(output_json):
    """
    Checks completeness of contact_info and core fields.
    Ensures no critical data was lost during extraction.

    Returns:
        dict with expected_fields, present_fields, coverage_ratio, status
    """
    contact = output_json.get('contact_info', {})
    expected_fields = ['name', 'email', 'phone', 'location']

    present_fields = [field for field in expected_fields if contact.get(field) and contact.get(field).strip()]
    coverage = len(present_fields) / len(expected_fields)

    # Check for work authorization
    has_visa = bool(output_json.get('work_authorization'))

    # Check for at least one section
    has_sections = len(output_json.get('sections', [])) > 0

    return {
        "expected_fields": expected_fields,
        "present_fields": present_fields,
        "coverage_ratio": round(coverage, 2),
        "has_work_auth": has_visa,
        "has_sections": has_sections,
        "status": "✅" if coverage >= 0.75 and has_sections else "❌",
        "score": coverage
    }

# === METRIC 7: SECTION DENSITY (NEW) ===
def calculate_section_density(output_json):
    """
    Measures average bullets per work experience entry.
    Low density = possible summarization/data loss.

    Returns:
        dict with avg_bullets_per_entry, total_entries, status
    """
    total_bullets = 0
    total_entries = 0

    for section in output_json.get('sections', []):
        if section.get('us_category') == 'Experience':
            for entry in section.get('content', []):
                if isinstance(entry, dict):
                    total_entries += 1
                    total_bullets += len(entry.get('bullets', []))

    avg_density = total_bullets / total_entries if total_entries > 0 else 0

    # Typical CV has 3-6 bullets per job
    is_healthy = 2 <= avg_density <= 8

    return {
        "total_bullets": total_bullets,
        "total_entries": total_entries,
        "avg_bullets_per_entry": round(avg_density, 1),
        "status": "✅" if is_healthy else "⚠️",
        "score": min(1.0, avg_density / 4.0)  # Optimal = 4 bullets
    }

# === METRIC 8: COMPLETENESS CHECK (ANTI-TRUNCATION) ===
def calculate_completeness_check(output_json):
    """
    Detects truncated or incomplete text (ellipses, etc., shorthand).
    Directly tests the Anti-Lazy policy from prompts.

    Returns:
        dict with truncation_issues, total_truncated, status
    """
    truncation_issues = []

    def check_text(text, location):
        """Helper to check a single text string for truncation markers."""
        if not isinstance(text, str):
            return

        issues = []

        # Check for ellipses
        if "..." in text:
            issues.append("Contains ellipses (...)")

        # Check for etc.
        if re.search(r'\betc\.?\b', text, re.IGNORECASE):
            issues.append("Contains 'etc.'")

        # Check for shorthand phrases
        shorthand_patterns = [
            r'\bsame as above\b',
            r'\bsee above\b',
            r'\band more\b',
            r'\bso on\b',
            r'\bto be continued\b'
        ]
        for pattern in shorthand_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                issues.append(f"Contains shorthand: '{pattern}'")

        # Check for suspiciously short bullets (< 10 chars for experience/education)
        if len(text.strip()) < 10 and "experience" in location.lower():
            issues.append(f"Suspiciously short ({len(text)} chars)")

        if issues:
            truncation_issues.append({
                "location": location,
                "text": text[:100],  # First 100 chars for display
                "issues": issues
            })

    # Scan all sections
    for section in output_json.get('sections', []):
        category = section.get('us_category', 'Unknown')
        content = section.get('content', [])

        if category in ['Experience', 'Education']:
            # Check bullets in structured content
            if isinstance(content, list):
                for idx, entry in enumerate(content):
                    if isinstance(entry, dict):
                        # Check header/subheader
                        check_text(entry.get('header', ''), f"{category}[{idx}].header")
                        check_text(entry.get('subheader', ''), f"{category}[{idx}].subheader")

                        # Check bullets
                        bullets = entry.get('bullets', [])
                        for bullet_idx, bullet in enumerate(bullets):
                            check_text(bullet, f"{category}[{idx}].bullets[{bullet_idx}]")

        elif category in ['Summary', 'Skills']:
            # Check simple string arrays
            if isinstance(content, list):
                for idx, item in enumerate(content):
                    check_text(item, f"{category}[{idx}]")

    total_truncated = len(truncation_issues)
    is_complete = total_truncated == 0

    return {
        "truncation_issues": truncation_issues[:10],  # Limit to first 10 for display
        "total_truncated": total_truncated,
        "status": "✅" if is_complete else "❌",
        "score": max(0, 1 - (total_truncated * 0.1))  # -0.1 per truncation
    }

# === AGGREGATE METRICS RUNNER ===
def run_all_metrics(original_text, output_json):
    """
    Runs all metrics and returns comprehensive report.

    Args:
        original_text: Raw text extracted from source PDF
        output_json: Parsed JSON output from agent

    Returns:
        dict with individual metrics and overall quality score
    """
    metrics = {
        "bullet_preservation": calculate_bullet_preservation_score(original_text, output_json),
        "json_integrity": calculate_json_integrity_score(output_json),
        "phantom_detection": detect_phantom_sections(output_json),
        "structural_compliance": calculate_structural_compliance(output_json),
        "translation_quality": calculate_translation_quality(original_text, output_json),
        "field_coverage": calculate_field_coverage(output_json),
        "section_density": calculate_section_density(output_json),
        "completeness_check": calculate_completeness_check(output_json)
    }

    # Calculate weighted overall score
    weights = {
        "bullet_preservation": 0.20,  # Critical
        "json_integrity": 0.10,
        "phantom_detection": 0.08,
        "structural_compliance": 0.12,
        "translation_quality": 0.15,
        "field_coverage": 0.10,
        "section_density": 0.05,
        "completeness_check": 0.20  # CRITICAL - Anti-truncation
    }

    overall_score = sum(metrics[key]["score"] * weights[key] for key in weights.keys())

    return {
        "metrics": metrics,
        "overall_score": round(overall_score, 2),
        "overall_status": "✅" if overall_score >= 0.85 else ("⚠️" if overall_score >= 0.70 else "❌"),
        "grade": get_letter_grade(overall_score)
    }

def get_letter_grade(score):
    """Converts numeric score to letter grade."""
    if score >= 0.95: return "A+"
    elif score >= 0.90: return "A"
    elif score >= 0.85: return "A-"
    elif score >= 0.80: return "B+"
    elif score >= 0.75: return "B"
    elif score >= 0.70: return "B-"
    elif score >= 0.65: return "C+"
    elif score >= 0.60: return "C"
    else: return "F"
