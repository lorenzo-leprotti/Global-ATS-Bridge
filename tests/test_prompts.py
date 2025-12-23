#!/usr/bin/env python3
# test_prompts.py
# Tests the updated Mirror-Fidelity prompts with comprehensive metrics

import sys
import os

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import google.generativeai as genai
import json
import time
from prompts import BASE_INSTRUCTIONS, AGENT_PROMPTS
from metrics import run_all_metrics

# Configuration
TEST_CV_PATH = "../test_cvs/cv_portuguese_Patrícia_de_Nunes_20251221_224022.pdf"
VISA_STATUS = "F-1 OPT (Stem)"

# Initialize Gemini
def init_gemini():
    """Initialize Gemini API with key from secrets file."""
    try:
        # Try to read from .streamlit/secrets.toml
        secrets_path = "../.streamlit/secrets.toml"
        if os.path.exists(secrets_path):
            with open(secrets_path, 'r') as f:
                for line in f:
                    if line.startswith('GOOGLE_API_KEY'):
                        api_key = line.split('=')[1].strip().strip('"')
                        genai.configure(api_key=api_key)
                        print("✅ Gemini API initialized")
                        return

        # Fallback to environment variable
        api_key = os.getenv('GOOGLE_API_KEY')
        if api_key:
            genai.configure(api_key=api_key)
            print("✅ Gemini API initialized from env")
        else:
            print("❌ No API key found")
            exit(1)
    except Exception as e:
        print(f"❌ Failed to initialize Gemini: {e}")
        exit(1)

def extract_original_text(pdf_path):
    """Extract raw text from PDF for metrics baseline."""
    try:
        pdf_file = genai.upload_file(pdf_path)
        time.sleep(2)

        model = genai.GenerativeModel('gemini-3-flash-preview')
        extract_prompt = "Extract all text from this PDF exactly as written. Return only the raw text, no formatting."
        response = model.generate_content([extract_prompt, pdf_file])

        pdf_file.delete()
        return response.text
    except Exception as e:
        print(f"⚠️ Could not extract original text: {e}")
        return ""

def get_system_prompt(persona):
    """Generate system prompt with grading standards."""
    try:
        with open("../data/grading_standards.json", "r") as f:
            grading_rules = f.read()
    except FileNotFoundError:
        grading_rules = "{'Warning': 'No reference data found.'}"

    agent_data = AGENT_PROMPTS.get(persona, AGENT_PROMPTS["Hybrid_Auditor"])

    return f"""
{BASE_INSTRUCTIONS}

DETERMINISTIC GRADING RULES (REFERENCE ONLY):
{grading_rules}

STYLE RULES FOR THIS AGENT:
{agent_data['instructions']}
"""

def test_agent(pdf_path, persona, visa_status):
    """Test a single agent with the updated prompts."""
    print(f"\n{'='*60}")
    print(f"🤖 Testing Agent: {persona}")
    print(f"{'='*60}")

    try:
        # Upload PDF
        print("📤 Uploading PDF to Gemini...")
        gemini_file = genai.upload_file(pdf_path, mime_type="application/pdf")

        # Wait for processing
        timeout = 30
        start_time = time.time()
        while gemini_file.state.name == "PROCESSING":
            if time.time() - start_time > timeout:
                print(f"❌ Timeout after {timeout}s")
                return None
            time.sleep(1)
            gemini_file = genai.get_file(gemini_file.name)

        if gemini_file.state.name == "FAILED":
            print("❌ File processing failed")
            return None

        # Generate response
        print("🧠 Generating response with Gemini 3 Flash...")

        # Create generation config
        gen_config = genai.GenerationConfig(
            temperature=0.0,
            max_output_tokens=8192,
            response_mime_type="application/json"
        )

        model = genai.GenerativeModel(
            'gemini-3-flash-preview',
            generation_config=gen_config
        )

        prompt = get_system_prompt(persona)
        response = model.generate_content([prompt, f"USER VISA: {visa_status}", gemini_file])

        # Parse JSON
        raw_text = response.text
        print(f"\n📝 Raw response length: {len(raw_text)} characters")

        # Save raw response for debugging
        with open("debug_raw_response.txt", "w", encoding="utf-8") as f:
            f.write(raw_text)
        print("💾 Raw response saved to: debug_raw_response.txt")

        clean_text = raw_text.replace("```json", "").replace("```", "").strip()

        try:
            result_json = json.loads(clean_text)
            print("✅ Response generated successfully")
            return result_json
        except json.JSONDecodeError as json_err:
            print(f"❌ JSON Parse Error: {json_err}")
            print(f"📄 First 500 chars of cleaned text:")
            print(clean_text[:500])
            print(f"\n📄 Last 500 chars of cleaned text:")
            print(clean_text[-500:])
            return None

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def display_metrics_report(metrics_report):
    """Display comprehensive metrics report."""
    print(f"\n{'='*60}")
    print(f"📊 COMPREHENSIVE METRICS REPORT")
    print(f"{'='*60}\n")

    # Overall Score
    overall = metrics_report['overall_score']
    grade = metrics_report['grade']
    status = metrics_report['overall_status']

    print(f"🎯 OVERALL SCORE: {overall:.2f} / 1.00 ({grade}) {status}")
    print(f"\n{'─'*60}\n")

    # Individual Metrics
    metrics = metrics_report['metrics']

    print("1️⃣  BULLET COUNT PRESERVATION")
    bp = metrics['bullet_preservation']
    print(f"   Status: {bp['status']}")
    print(f"   Original bullets: {bp['original_count']}")
    print(f"   Output bullets: {bp['output_count']}")
    print(f"   Preservation ratio: {bp['preservation_ratio']:.2f}")
    print(f"   Score: {bp['score']:.2f}")

    print(f"\n2️⃣  JSON INTEGRITY")
    ji = metrics['json_integrity']
    print(f"   Status: {ji['status']}")
    print(f"   Total issues: {ji['total_issues']}")
    if ji['issues']:
        for issue in ji['issues'][:3]:
            print(f"   - {issue['issue']} at {issue['path']}")
    print(f"   Score: {ji['score']:.2f}")

    print(f"\n3️⃣  PHANTOM SECTION DETECTION")
    pd = metrics['phantom_detection']
    print(f"   Status: {pd['status']}")
    print(f"   Phantom sections found: {pd['count']}")
    if pd['phantom_sections']:
        for phantom in pd['phantom_sections']:
            print(f"   - {phantom['section']}: {phantom['issue']}")
    print(f"   Score: {pd['score']:.2f}")

    print(f"\n4️⃣  STRUCTURAL COMPLIANCE")
    sc = metrics['structural_compliance']
    print(f"   Status: {sc['status']}")
    print(f"   Expected order: {' → '.join(sc['expected_order'])}")
    print(f"   Actual order: {' → '.join(sc['actual_order'])}")
    print(f"   Compliant: {sc['compliant']}")
    print(f"   Score: {sc['score']:.2f}")

    print(f"\n5️⃣  TRANSLATION QUALITY")
    tq = metrics['translation_quality']
    print(f"   Status: {tq['status']}")
    print(f"   Quality score: {tq['quality_score']:.2f}")
    print(f"   Checks:")
    for check, passed in tq['checks'].items():
        print(f"   - {check}: {'✅' if passed else '❌'}")

    print(f"\n6️⃣  FIELD COVERAGE")
    fc = metrics['field_coverage']
    print(f"   Status: {fc['status']}")
    print(f"   Coverage ratio: {fc['coverage_ratio']:.2f}")
    print(f"   Present fields: {', '.join(fc['present_fields'])}")
    print(f"   Has work auth: {fc['has_work_auth']}")
    print(f"   Score: {fc['score']:.2f}")

    print(f"\n7️⃣  SECTION DENSITY")
    sd = metrics['section_density']
    print(f"   Status: {sd['status']}")
    print(f"   Avg bullets per entry: {sd['avg_bullets_per_entry']}")
    print(f"   Total entries: {sd['total_entries']}")
    print(f"   Total bullets: {sd['total_bullets']}")
    print(f"   Score: {sd['score']:.2f}")

    print(f"\n{'='*60}\n")

def main():
    """Main test execution."""
    print(f"\n🧪 PROMPT TESTING SUITE - Mirror-Fidelity Validation")
    print(f"{'='*60}")

    # Initialize
    init_gemini()

    # Verify test CV exists
    if not os.path.exists(TEST_CV_PATH):
        print(f"❌ Test CV not found: {TEST_CV_PATH}")
        exit(1)

    print(f"📄 Test CV: {TEST_CV_PATH}")
    print(f"🛂 Visa Status: {VISA_STATUS}")

    # Extract original text for metrics baseline
    print(f"\n📖 Extracting original text for baseline...")
    original_text = extract_original_text(TEST_CV_PATH)
    print(f"✅ Extracted {len(original_text)} characters")

    # Test Hybrid_Auditor (the one we updated)
    result_json = test_agent(TEST_CV_PATH, "Hybrid_Auditor", VISA_STATUS)

    if not result_json:
        print("❌ Test failed - no result generated")
        exit(1)

    # Save result for inspection
    output_path = "test_output_hybrid_auditor.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result_json, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Result saved to: {output_path}")

    # Run comprehensive metrics
    print(f"\n📊 Running comprehensive metrics analysis...")
    metrics_report = run_all_metrics(original_text, result_json)

    # Display results
    display_metrics_report(metrics_report)

    # Save metrics report
    metrics_output_path = "test_metrics_report.json"
    with open(metrics_output_path, 'w', encoding='utf-8') as f:
        json.dump(metrics_report, f, indent=2, ensure_ascii=False)
    print(f"💾 Metrics report saved to: {metrics_output_path}")

    # Final verdict
    print(f"\n{'='*60}")
    print(f"🏁 TEST COMPLETE")
    print(f"{'='*60}")

    if metrics_report['overall_score'] >= 0.85:
        print(f"✅ PASS - Prompts are performing well!")
        print(f"   Overall Score: {metrics_report['overall_score']:.2f} ({metrics_report['grade']})")
    elif metrics_report['overall_score'] >= 0.70:
        print(f"⚠️  MARGINAL - Some issues detected")
        print(f"   Overall Score: {metrics_report['overall_score']:.2f} ({metrics_report['grade']})")
        print(f"   Review the metrics report for details")
    else:
        print(f"❌ FAIL - Significant issues detected")
        print(f"   Overall Score: {metrics_report['overall_score']:.2f} ({metrics_report['grade']})")
        print(f"   Prompt tuning required")

    print(f"\n{'='*60}\n")

if __name__ == "__main__":
    main()
