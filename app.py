import streamlit as st
import google.generativeai as genai
import json
import io
import tempfile
import os
import time
import base64
import concurrent.futures
from collections import Counter
import re
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
from reportlab.lib import colors
import prompts  # Prompt library for agent personas
import metrics  # Comprehensive quality metrics
import enhanced_metrics  # RL reward system and advanced metrics

# --- CONFIGURATION ---
st.set_page_config(page_title="Global ATS Bridge (V3 Tournament - Gemini 3 Flash)", layout="wide")

# --- RETRY HELPER ---
def retry_with_backoff(func, max_retries=3):
    """Retries a function with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise  # Give up after last attempt
            wait_time = 2 ** attempt  # 1s, 2s, 4s
            time.sleep(wait_time)

# --- FIDELITY CHECKSUM ---
def verify_fidelity(original_pdf_path, optimized_json):
    """
    Checksum to ensure no data loss during AI reordering.
    Checks if original professional keywords exist in the new JSON.

    Args:
        original_pdf_path: Path to original PDF file
        optimized_json: Transformed JSON output from agent

    Returns:
        dict with is_safe, loss_percentage, flagged_words
    """
    # 1. Extract text from original PDF using Gemini
    try:
        pdf_file = genai.upload_file(original_pdf_path)
        time.sleep(1)  # Wait for file processing

        # Simple extraction prompt
        extraction_model = genai.GenerativeModel('gemini-3-flash-preview')
        extract_prompt = "Extract all text from this PDF exactly as written. Return only the raw text, no formatting."
        response = extraction_model.generate_content([extract_prompt, pdf_file])
        original_text = response.text

        # Cleanup
        pdf_file.delete()
    except Exception as e:
        # If extraction fails, skip validation
        return {
            "is_safe": True,
            "loss_percentage": 0.0,
            "flagged_words": [],
            "error": f"Could not extract original text: {str(e)}"
        }

    # 2. Normalize and extract tokens (excluding common stop words)
    def get_tokens(text):
        words = re.findall(r'\w+', str(text).lower())
        # Filter out very short words/numbers to focus on "Experience" keywords
        stop_words = {'the', 'and', 'for', 'with', 'from', 'this', 'that', 'have', 'has', 'was', 'were', 'been'}
        return [w for w in words if len(w) > 3 and w not in stop_words]

    original_tokens = Counter(get_tokens(original_text))
    optimized_tokens = Counter(get_tokens(optimized_json))

    # 3. Compare intersection
    missing_tokens = []
    for word, count in original_tokens.items():
        if optimized_tokens[word] < count:
            missing_tokens.append(word)

    # 4. Calculate "Loss Ratio"
    # We allow some loss for formatting/stop words, but >10% is a red flag
    loss_ratio = len(missing_tokens) / len(original_tokens) if original_tokens else 0

    return {
        "is_safe": loss_ratio < 0.10,
        "loss_percentage": round(loss_ratio * 100, 2),
        "flagged_words": missing_tokens[:5]  # Show first 5 missing for debugging
    }

# Initialize Gemini
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
except Exception:
    st.error("🚨 API Key missing! Check .streamlit/secrets.toml")
    st.stop()

# --- 1. THE LOGGER (FLYWHEEL) ---
def save_training_data(original_filename, selected_variant, final_json, validation_report=None, session_id=None, processing_mode="single", comprehensive_metrics=None):
    """Saves the user's preference to a local JSONL file for future fine-tuning."""
    log_entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "session_id": session_id if session_id else time.strftime("%Y%m%d_%H%M%S"),  # Unique session identifier
        "processing_mode": processing_mode,  # "single" or "bulk"
        "filename": original_filename,
        "selected_variant": selected_variant,
        "final_json": final_json,
        "validation_report": validation_report if validation_report else {"valid": True, "invalid_gpas_found": []},
        "comprehensive_metrics": comprehensive_metrics if comprehensive_metrics else {}
    }
    with open("data/training_data.jsonl", "a") as f:
        f.write(json.dumps(log_entry) + "\n")

# --- 2A. PDF PREVIEW HELPER ---
def display_pdf(pdf_bytes, height=1000):
    """Displays a PDF inline using base64 encoding in an iframe."""
    base64_pdf = base64.b64encode(pdf_bytes.getvalue()).decode('utf-8')
    pdf_display = f'''
        <iframe
            src="data:application/pdf;base64,{base64_pdf}"
            width="100%"
            height="{height}"
            type="application/pdf"
            style="border: 2px solid #444; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        </iframe>
    '''
    st.markdown(pdf_display, unsafe_allow_html=True)

# --- 2A2. COMPREHENSIVE METRICS DISPLAY HELPER ---
def display_comprehensive_metrics(metrics_report, agent_name):
    """Displays comprehensive quality metrics in an expandable panel."""
    if not metrics_report or "error" in metrics_report:
        st.warning(f"⚠️ Metrics unavailable for {agent_name}")
        if "error" in metrics_report:
            st.caption(f"Error: {metrics_report.get('error', 'Unknown')}")
        return

    # Overall score header
    overall = metrics_report.get('overall_score', 0)
    grade = metrics_report.get('grade', 'F')
    status = metrics_report.get('overall_status', '❌')

    # RL Reward (Prominently displayed)
    rl_reward = metrics_report.get('rl_reward', {})
    rl_score = rl_reward.get('reward', overall)
    rl_grade = rl_reward.get('grade', grade)

    # Display RL Reward as primary metric (collapsed by default, expandable for details)
    st.metric(
        label=f"🎯 RL Reward Score ({agent_name})",
        value=f"{rl_score:.3f}",
        delta=f"Grade: {rl_grade}",
        help="Comprehensive score for RL training: combines base metrics (60%), semantic fidelity (25%), and ATS compliance (15%)"
    )

    with st.expander(f"📊 Detailed Metrics Breakdown: Base {overall:.2f} ({grade}) {status}", expanded=False):
        # Create metrics grid
        col1, col2, col3, col4 = st.columns(4)

        metrics_data = metrics_report.get('metrics', {})

        # Row 1: Core metrics
        with col1:
            bp = metrics_data.get('bullet_preservation', {})
            st.metric(
                "Bullet Preservation",
                f"{bp.get('preservation_ratio', 0):.0%}",
                delta=None,
                help=f"Original: {bp.get('original_count', 0)} → Output: {bp.get('output_count', 0)}"
            )
            st.caption(f"{bp.get('status', '❌')} Score: {bp.get('score', 0):.2f}")

        with col2:
            ji = metrics_data.get('json_integrity', {})
            st.metric(
                "JSON Integrity",
                f"{ji.get('total_issues', 0)} issues",
                delta=None,
                help="Checks for malformed JSON strings and line breaks"
            )
            st.caption(f"{ji.get('status', '❌')} Score: {ji.get('score', 0):.2f}")

        with col3:
            pd = metrics_data.get('phantom_detection', {})
            st.metric(
                "Phantom Sections",
                f"{pd.get('count', 0)} found",
                delta=None,
                help="Empty sections that should be omitted"
            )
            st.caption(f"{pd.get('status', '❌')} Score: {pd.get('score', 0):.2f}")

        with col4:
            sc = metrics_data.get('structural_compliance', {})
            st.metric(
                "Structure",
                "Compliant" if sc.get('compliant', False) else "Non-Compliant",
                delta=None,
                help="Summary → Experience → Education → Skills"
            )
            st.caption(f"{sc.get('status', '❌')} Score: {sc.get('score', 0):.2f}")

        # Row 2: Quality metrics
        col5, col6, col7, col8 = st.columns(4)

        with col5:
            tq = metrics_data.get('translation_quality', {})
            st.metric(
                "Translation Quality",
                f"{tq.get('quality_score', 0):.0%}",
                delta=None,
                help="Checks for professional English & untranslated text"
            )
            st.caption(f"{tq.get('status', '❌')} Score: {tq.get('score', 0):.2f}")

        with col6:
            fc = metrics_data.get('field_coverage', {})
            st.metric(
                "Field Coverage",
                f"{fc.get('coverage_ratio', 0):.0%}",
                delta=None,
                help=f"Present: {', '.join(fc.get('present_fields', []))}"
            )
            st.caption(f"{fc.get('status', '❌')} Score: {fc.get('score', 0):.2f}")

        with col7:
            sd = metrics_data.get('section_density', {})
            st.metric(
                "Avg Bullets/Entry",
                f"{sd.get('avg_bullets_per_entry', 0):.1f}",
                delta=None,
                help=f"{sd.get('total_bullets', 0)} bullets across {sd.get('total_entries', 0)} entries"
            )
            st.caption(f"{sd.get('status', '❌')} Score: {sd.get('score', 0):.2f}")

        with col8:
            cc = metrics_data.get('completeness_check', {})
            st.metric(
                "Completeness",
                f"{cc.get('total_truncated', 0)} truncations",
                delta=None,
                help="Detects ellipses (...), 'etc.', and other truncation markers"
            )
            st.caption(f"{cc.get('status', '❌')} Score: {cc.get('score', 0):.2f}")

        # Row 3: Overall grade
        st.markdown("---")
        col_overall = st.columns([1, 1, 1])[1]
        with col_overall:
            st.metric(
                "Overall Grade",
                grade,
                delta=None,
                help=f"Weighted score: {overall:.2f}"
            )
            st.caption(f"{status} Composite")

        # Detailed issues if any
        if ji.get('issues'):
            st.markdown("**JSON Integrity Issues:**")
            for issue in ji.get('issues', [])[:5]:
                st.text(f"  • {issue.get('issue', 'Unknown')} at {issue.get('path', 'Unknown')}")

        if pd.get('phantom_sections'):
            st.markdown("**Phantom Sections Found:**")
            for phantom in pd.get('phantom_sections', [])[:5]:
                st.text(f"  • {phantom.get('section', 'Unknown')}: {phantom.get('issue', 'Unknown')}")

        # Completeness check issues
        cc = metrics_data.get('completeness_check', {})
        if cc.get('truncation_issues'):
            st.markdown("**🚨 Truncation Issues Found (Anti-Lazy Policy Violation):**")
            for issue in cc.get('truncation_issues', [])[:5]:
                st.error(f"**{issue.get('location', 'Unknown')}**")
                st.text(f"  Text: {issue.get('text', 'N/A')}")
                st.text(f"  Issues: {', '.join(issue.get('issues', []))}")
                st.markdown("---")

    # Enhanced Metrics Display (inside a sub-expander)
    if rl_reward and "enhanced_metrics" in rl_reward:
        with st.expander("🔬 Enhanced RL Metrics (Advanced)", expanded=False):
            enhanced = rl_reward.get("enhanced_metrics", {})

            col_e1, col_e2, col_e3, col_e4 = st.columns(4)

            with col_e1:
                entity_pres = enhanced.get("entity_preservation", {})
                st.metric(
                    "Entity Preservation",
                    f"{entity_pres.get('overall_preservation', 0):.0%}",
                    help="Preservation of dates, numbers, emails, phones"
                )
                st.caption(f"{entity_pres.get('status', '❌')} Score: {entity_pres.get('score', 0):.2f}")

            with col_e2:
                info_density = enhanced.get("information_density", {})
                st.metric(
                    "Information Density",
                    f"{info_density.get('density_ratio', 0):.2f}x",
                    help="Ratio of output words to input words (ideal: 0.85-1.15)"
                )
                st.caption(f"{info_density.get('status', '❌')} Score: {info_density.get('score', 0):.2f}")

            with col_e3:
                action_verbs = enhanced.get("action_verb_quality", {})
                st.metric(
                    "Action Verb Quality",
                    f"{action_verbs.get('strong_ratio', 0):.0%}",
                    help=f"Strong: {action_verbs.get('strong_verb_count', 0)}, Weak: {action_verbs.get('weak_verb_count', 0)}"
                )
                st.caption(f"{action_verbs.get('status', '❌')} Score: {action_verbs.get('score', 0):.2f}")

            with col_e4:
                ats = enhanced.get("ats_compliance", {})
                st.metric(
                    "ATS Compliance",
                    f"{ats.get('compliance_score', 0):.0%}",
                    help="ATS-friendliness checks"
                )
                st.caption(f"{ats.get('status', '❌')} Score: {ats.get('score', 0):.2f}")

            # Component Contributions
            st.markdown("---")
            st.markdown("**RL Reward Component Contributions:**")
            contributions = rl_reward.get("weighted_contributions", {})
            for component, value in contributions.items():
                weight = rl_reward.get("weights", {}).get(component, 0)
                st.text(f"  • {component}: {value:.4f} (weight: {weight:.0%})")

            # Hard Constraints
            hard_constraints = rl_reward.get("hard_constraints", {})
            if not hard_constraints.get("passed", True):
                st.error(f"❌ Hard Constraints Failed: {hard_constraints.get('fail_count', 0)} checks failed")
                failed = [k for k, v in hard_constraints.get("checks", {}).items() if not v]
                st.text(f"Failed checks: {', '.join(failed)}")

# --- 2B. THE HANDS: DYNAMIC PDF GENERATOR ---
def generate_dynamic_pdf(data):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=LETTER)
    width, height = LETTER
    
    # Metadata
    contact = data.get("contact_info", {})
    name = contact.get("name", "Candidate").upper()
    c.setTitle(f"Resume - {name}")

    # Helper: Draw Divider Line
    def draw_line(y):
        c.setStrokeColor(colors.black)
        c.setLineWidth(0.5)
        c.line(50, y, width - 50, y)
        return y - 15

    # Tracker
    y = height - 50

    # HEADER
    info_line = f"{contact.get('location', '')} | {contact.get('email', '')} | {contact.get('phone', '')}"
    
    c.setFont("Times-Bold", 16)
    c.drawCentredString(width / 2, y, name)
    y -= 20
    
    c.setFont("Times-Roman", 10)
    c.drawCentredString(width / 2, y, info_line)
    if contact.get("linkedin"):
        y -= 12
        c.drawCentredString(width / 2, y, contact.get("linkedin"))
    y -= 15

    # WORK AUTHORIZATION
    visa = data.get("work_authorization", "Unknown Status")
    c.setFont("Times-Bold", 10)
    c.drawCentredString(width / 2, y, f"WORK AUTHORIZATION: {visa}")
    y -= 25

    # DYNAMIC SECTIONS LOOP
    # We iterate through whatever sections the AI found
    sections = data.get("sections", [])
    
    for section in sections:
        # Page Break Check
        if y < 100:
            c.showPage()
            y = height - 50
        
        # Section Header
        category = section.get("us_category", "Other").upper()
        c.setFont("Times-Bold", 12)
        c.drawString(50, y, category)
        y -= 5
        y = draw_line(y)

        # Content Handling
        content = section.get("content", [])
        
        # Scenario A: Content is a list of strings (Skills)
        if isinstance(content, list) and all(isinstance(i, str) for i in content):
            c.setFont("Times-Roman", 10)
            text_block = ", ".join(content)
            # Simple wrapping
            start = 0
            while start < len(text_block):
                end = start + 100
                line = text_block[start:end]
                c.drawString(50, y, line)
                y -= 12
                start = end
            y -= 10

        # Scenario B: Content is a list of objects (Experience/Education)
        elif isinstance(content, list):
            for entry in content:
                if not isinstance(entry, dict): continue # Skip bad data
                
                # Header Line (Company / University)
                header = entry.get("header", "")
                subheader = entry.get("subheader", "") # Role / Degree
                date = entry.get("date", "")
                
                c.setFont("Times-Bold", 10)
                c.drawString(50, y, header)
                c.drawRightString(width - 50, y, date)
                y -= 12
                
                if subheader:
                    c.setFont("Times-Roman", 10) # Italic simulation? Just Roman for MVP
                    c.drawString(50, y, subheader)
                    y -= 12
                
                # Bullets
                bullets = entry.get("bullets", [])
                c.setFont("Times-Roman", 10)
                for bullet in bullets:
                    # Clean bullet
                    bullet_text = f"• {bullet}"
                    if len(bullet_text) > 95: bullet_text = bullet_text[:95] + "..."
                    c.drawString(65, y, bullet_text)
                    y -= 12
                y -= 8 # Spacing between entries
            y -= 10 # Spacing between sections

    c.save()
    buffer.seek(0)
    return buffer

# --- 3. THE BRAIN: PROMPT FACTORY ---
def get_system_prompt(persona):
    """Generate system prompt using centralized prompt library with injected grading standards."""

    # 1. Load the "Golden Rules" from your JSON
    try:
        with open("data/grading_standards.json", "r") as f:
            grading_rules = f.read()
    except FileNotFoundError:
        grading_rules = "{'Warning': 'No reference data found.'}"

    # 2. Get the specific Agent instructions
    agent_data = prompts.AGENT_PROMPTS.get(persona, prompts.AGENT_PROMPTS["Strategist"])

    # 3. Stitch them together for the model
    return f"""
{prompts.BASE_INSTRUCTIONS}

DETERMINISTIC GRADING RULES (REFERENCE ONLY):
{grading_rules}

STYLE RULES FOR THIS AGENT:
{agent_data['instructions']}
"""

# --- 3B. VALIDATION ENGINE ---
def validate_gpa_conversions(agent_results):
    """
    Validates that all GPA conversions match the deterministic grading standards.
    Returns validation report with flagged anomalies.
    """
    # Load grading standards
    try:
        with open("data/grading_standards.json", "r") as f:
            standards = json.load(f)
    except FileNotFoundError:
        return {"error": "data/grading_standards.json not found", "valid": False}

    # Extract valid GPA values from standards
    valid_gpas = set()
    for country, data in standards.get("Standards", {}).items():
        for grade_range, gpa_value in data.get("mapping", {}).items():
            # Handle both numeric and string GPA values
            if isinstance(gpa_value, (int, float)):
                valid_gpas.add(str(float(gpa_value)))
            elif isinstance(gpa_value, str):
                # Handle ranges like "3.5-4.0" or "3.5+"
                if "-" in gpa_value:
                    parts = gpa_value.split("-")
                    valid_gpas.add(parts[0].strip())
                    valid_gpas.add(parts[1].strip())
                elif "+" in gpa_value:
                    valid_gpas.add(gpa_value.replace("+", "").strip())
                else:
                    valid_gpas.add(gpa_value.strip())

    # Validation report
    report = {
        "total_agents": len(agent_results),
        "agents_checked": 0,
        "invalid_gpas_found": [],
        "valid": True
    }

    # Check each agent's output
    for agent_name, data in agent_results.items():
        if "error" in data:
            continue

        report["agents_checked"] += 1

        # Check education sections for GPA mentions
        for section in data.get("sections", []):
            if section.get("us_category") in ["Education"]:
                content = section.get("content", [])

                # Handle both list of objects and single objects
                if isinstance(content, list):
                    for entry in content:
                        if isinstance(entry, dict):
                            # Check in subheader (degree line) and bullets
                            text_to_check = f"{entry.get('subheader', '')} {entry.get('header', '')} {' '.join(entry.get('bullets', []))}"

                            # Extract GPA mentions using regex
                            import re
                            gpa_pattern = r'GPA[:\s]+([0-9.]+)'
                            matches = re.findall(gpa_pattern, text_to_check, re.IGNORECASE)

                            for gpa_value in matches:
                                # Normalize to one decimal place for comparison
                                normalized_gpa = f"{float(gpa_value):.1f}"

                                # Check if this GPA is in our valid set
                                if normalized_gpa not in valid_gpas and gpa_value not in valid_gpas:
                                    report["invalid_gpas_found"].append({
                                        "agent": agent_name,
                                        "gpa": gpa_value,
                                        "context": text_to_check[:100]
                                    })
                                    report["valid"] = False

    return report

# --- 4. THE PARALLEL ENGINE ---
def run_agent(file_path, persona, visa_status):
    """Runs a single Gemini agent with a specific persona, fidelity check, and comprehensive metrics."""
    try:
        # 1. Upload and WAIT for processing (Crucial Step)
        gemini_file = genai.upload_file(file_path, mime_type="application/pdf")

        # Loop until the file is ready with timeout protection
        timeout = 30  # seconds
        start_time = time.time()
        while gemini_file.state.name == "PROCESSING":
            if time.time() - start_time > timeout:
                return persona, {"error": f"File processing timeout after {timeout}s"}, None, None
            time.sleep(1)
            gemini_file = genai.get_file(gemini_file.name)

        if gemini_file.state.name == "FAILED":
            return persona, {"error": "File processing failed on Google side."}, None, None

        # 2. Generate with retry logic
        # Create generation config for deterministic output
        gen_config = genai.GenerationConfig(
            temperature=0.0,  # Maximum determinism, no creativity
            max_output_tokens=8192,  # Allow long CVs without truncation
            response_mime_type="application/json"
        )

        model = genai.GenerativeModel(
            'gemini-3-flash-preview',
            generation_config=gen_config
        )
        prompt = get_system_prompt(persona)

        response = retry_with_backoff(
            lambda: model.generate_content([prompt, f"USER VISA: {visa_status}", gemini_file])
        )

        # 3. Clean and Parse JSON (Fixes the "Empty" issue)
        raw_text = response.text
        # Sometimes the model returns markdown code blocks, which breaks json.loads
        clean_text = raw_text.replace("```json", "").replace("```", "").strip()
        result_json = json.loads(clean_text)

        # 4. Run Fidelity Check (Legacy metric)
        fidelity_report = verify_fidelity(file_path, result_json)

        # 5. Extract original text for comprehensive metrics
        try:
            extract_model = genai.GenerativeModel('gemini-3-flash-preview')
            extract_prompt = "Extract all text from this PDF exactly as written. Return only the raw text, no formatting."
            extract_file = genai.upload_file(file_path, mime_type="application/pdf")
            time.sleep(1)
            extract_response = extract_model.generate_content([extract_prompt, extract_file])
            original_text = extract_response.text
            extract_file.delete()

            # 6. Run Comprehensive Metrics
            comprehensive_metrics = metrics.run_all_metrics(original_text, result_json)

            # 7. Calculate RL Reward (Enhanced Metrics)
            rl_reward = enhanced_metrics.calculate_rl_reward(
                original_text,
                result_json,
                raw_text,
                comprehensive_metrics
            )
            comprehensive_metrics["rl_reward"] = rl_reward
        except Exception as metrics_error:
            # If metrics fail, continue with empty report
            comprehensive_metrics = {
                "error": str(metrics_error),
                "overall_score": 0.0,
                "overall_status": "❌",
                "grade": "F",
                "rl_reward": {
                    "reward": 0.0,
                    "grade": "F",
                    "reason": str(metrics_error)
                }
            }

        return persona, result_json, fidelity_report, comprehensive_metrics

    except Exception as e:
        # This will now show up in your Debug panel if something breaks
        return persona, {"error": str(e)}, None, None

# --- 5. ADMIN DASHBOARD ---
def run_admin_dashboard():
    st.header("📊 Training Data Control Tower")

    file_path = "data/training_data.jsonl"

    # 1. Check if data exists
    if not os.path.exists(file_path):
        st.warning("No training data found yet. Go to the App and vote for some resumes!")
        return

    # 2. Load Data
    data = []
    with open(file_path, "r") as f:
        for line in f:
            try:
                data.append(json.loads(line))
            except:
                continue

    if not data:
        st.warning("No training data found yet!")
        return

    # 3. High-Level Metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📊 Total Samples", len(data))

    # Calculate favorite personas
    personas = [d['selected_variant'] for d in data]
    from collections import Counter
    persona_counts = Counter(personas)
    fav_persona = persona_counts.most_common(1)[0][0]
    col2.metric("🏆 Winningest Agent", fav_persona)

    # Unique files
    unique_files = len(set(d['filename'] for d in data))
    col3.metric("📄 Unique CVs", unique_files)

    last_active = data[-1]['timestamp']
    col4.metric("🕐 Last Activity", last_active.split()[1])  # Show time only

    st.divider()

    # 3.2 RL REWARD STATISTICS (BULK SESSION AVERAGES) - DISPLAYED FIRST
    st.subheader("🎯 RL Reward Statistics (Bulk Average)")

    # Extract all RL rewards from training data
    all_rl_rewards = []
    for d in data:
        comp_metrics = d.get('comprehensive_metrics', {})
        rl_reward = comp_metrics.get('rl_reward', {})
        if rl_reward and 'reward' in rl_reward:
            all_rl_rewards.append(rl_reward)

    if all_rl_rewards:
        # Calculate bulk statistics using enhanced_metrics
        bulk_stats = enhanced_metrics.calculate_bulk_statistics(all_rl_rewards)

        # Display prominently at the top
        col_bulk1, col_bulk2, col_bulk3, col_bulk4, col_bulk5 = st.columns(5)

        with col_bulk1:
            st.metric(
                "📊 Mean RL Reward",
                f"{bulk_stats['mean_reward']:.3f}",
                delta=f"±{bulk_stats['std_reward']:.3f}",
                help="Average reward across all processed CVs"
            )

        with col_bulk2:
            st.metric(
                "📈 Median Reward",
                f"{bulk_stats['median_reward']:.3f}",
                help="Middle value of all rewards"
            )

        with col_bulk3:
            st.metric(
                "⬆️ Max Reward",
                f"{bulk_stats['max_reward']:.3f}",
                help="Best score achieved"
            )

        with col_bulk4:
            st.metric(
                "⬇️ Min Reward",
                f"{bulk_stats['min_reward']:.3f}",
                help="Lowest score in dataset"
            )

        with col_bulk5:
            st.metric(
                "✅ Passing Rate",
                f"{bulk_stats['passing_rate']:.0%}",
                help="Percentage of CVs scoring >= 0.80"
            )

        # Grade distribution chart
        st.markdown("**Grade Distribution:**")
        grade_dist = bulk_stats['grade_distribution']
        grade_order = ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'D', 'F']
        for grade in grade_order:
            count = grade_dist.get(grade, 0)
            if count > 0:
                percentage = (count / bulk_stats['count']) * 100
                st.progress(percentage / 100, text=f"{grade}: {count} CVs ({percentage:.1f}%)")

        # Component-wise averages in an expander
        with st.expander("📊 Component-wise Averages (RL Breakdown)", expanded=False):
            comp_avgs = bulk_stats.get('component_averages', {})
            st.markdown("**Average scores for each RL component:**")
            for component, avg_score in comp_avgs.items():
                st.text(f"  • {component}: {avg_score:.4f}")
    else:
        st.info("No RL reward data available yet. Process some CVs to see statistics!")

    st.divider()

    # 3.5 TOURNAMENT SESSIONS (GROUPED VIEW)
    st.subheader("🎯 Tournament Sessions")

    # Group data by session_id
    from collections import defaultdict
    sessions = defaultdict(list)
    for d in data:
        session_id = d.get('session_id', 'unknown')
        sessions[session_id].append(d)

    # Display sessions in reverse chronological order
    session_list = sorted(sessions.items(), key=lambda x: x[0], reverse=True)

    if len(session_list) > 0:
        st.markdown(f"**Total Sessions:** {len(session_list)}")

        # Session selector
        selected_session = st.selectbox(
            "Select a tournament session to view:",
            options=range(len(session_list)),
            format_func=lambda i: f"Session #{i+1}: {session_list[i][0]} ({len(session_list[i][1])} CVs, {session_list[i][1][0].get('processing_mode', 'unknown')} mode)"
        )

        if selected_session is not None:
            session_id, session_data = session_list[selected_session]

            # Session details
            col_sess1, col_sess2, col_sess3, col_sess4 = st.columns(4)
            with col_sess1:
                st.metric("Session ID", session_id)
            with col_sess2:
                st.metric("CVs Processed", len(session_data))
            with col_sess3:
                processing_mode = session_data[0].get('processing_mode', 'unknown')
                st.metric("Mode", processing_mode.capitalize())
            with col_sess4:
                timestamp = session_data[0].get('timestamp', 'Unknown')
                st.metric("Date/Time", timestamp)

            # Session-specific agent wins
            session_agents = [d['selected_variant'] for d in session_data]
            session_agent_counts = Counter(session_agents)

            st.markdown("**Agent Performance in This Session:**")
            for agent, count in session_agent_counts.most_common():
                percentage = (count / len(session_data)) * 100
                st.progress(percentage / 100, text=f"{agent}: {count}/{len(session_data)} wins ({percentage:.1f}%)")

            # Session CV list
            st.markdown("**CVs in This Session:**")
            session_table = []
            for idx, d in enumerate(session_data):
                session_table.append({
                    "Index": idx + 1,
                    "Filename": d['filename'],
                    "Winner": d['selected_variant'],
                    "Candidate": d['final_json'].get('contact_info', {}).get('name', 'N/A'),
                    "Valid GPA": "✅" if d.get('validation_report', {}).get('valid', True) else "❌"
                })
            st.dataframe(session_table, use_container_width=True, height=300)

    st.divider()

    # 3.6 VALIDATION METRICS
    st.subheader("🛡️ GPA Validation Analytics")

    # Analyze validation data across all samples
    total_validations = 0
    total_invalid_gpas = 0
    agent_failure_counts = {"Conservative": 0, "Strategist": 0, "Hybrid_Auditor": 0}
    invalid_gpa_values = []

    for d in data:
        val_report = d.get('validation_report', {})
        if val_report:
            total_validations += 1
            invalid_gpas = val_report.get('invalid_gpas_found', [])
            total_invalid_gpas += len(invalid_gpas)

            for issue in invalid_gpas:
                agent = issue.get('agent', 'Unknown')
                if agent in agent_failure_counts:
                    agent_failure_counts[agent] += 1
                invalid_gpa_values.append(issue.get('gpa', 'Unknown'))

    # Display validation metrics
    col_val1, col_val2, col_val3 = st.columns(3)
    col_val1.metric("✅ Total Validations", total_validations)
    col_val2.metric("❌ Invalid GPAs Found", total_invalid_gpas)

    if total_validations > 0:
        validation_accuracy = ((total_validations - len([d for d in data if not d.get('validation_report', {}).get('valid', True)])) / total_validations) * 100
        col_val3.metric("📊 Validation Pass Rate", f"{validation_accuracy:.1f}%")
    else:
        col_val3.metric("📊 Validation Pass Rate", "N/A")

    # Agent failure breakdown
    if total_invalid_gpas > 0:
        st.markdown("**Agent Validation Failures:**")
        col_agent1, col_agent2, col_agent3 = st.columns(3)

        with col_agent1:
            st.metric("Conservative", agent_failure_counts["Conservative"])
        with col_agent2:
            st.metric("Strategist", agent_failure_counts["Strategist"])
        with col_agent3:
            st.metric("Hybrid_Auditor", agent_failure_counts["Hybrid_Auditor"])

        # Most common invalid GPAs
        if invalid_gpa_values:
            from collections import Counter
            common_invalid = Counter(invalid_gpa_values).most_common(5)
            st.markdown("**Most Common Invalid GPAs (Hallucinations):**")
            for gpa, count in common_invalid:
                st.text(f"  • GPA {gpa}: {count} occurrence(s)")
    else:
        st.success("🎉 Perfect record! No invalid GPAs detected across all tournaments.")

    st.divider()

    # 3.7 COMPREHENSIVE METRICS ANALYTICS
    st.subheader("📈 Comprehensive Quality Metrics Analytics")

    # Analyze comprehensive metrics across all samples
    samples_with_metrics = [d for d in data if d.get('comprehensive_metrics')]

    if len(samples_with_metrics) > 0:
        st.markdown(f"**Samples with Metrics:** {len(samples_with_metrics)}/{len(data)}")

        # Calculate average metrics by agent
        agent_metrics = {"Conservative": [], "Strategist": [], "Hybrid_Auditor": []}

        for d in samples_with_metrics:
            agent = d.get('selected_variant', 'Unknown')
            metrics_data = d.get('comprehensive_metrics', {})

            if agent in agent_metrics and metrics_data.get('overall_score'):
                agent_metrics[agent].append(metrics_data)

        # Display metrics comparison
        col_metrics1, col_metrics2, col_metrics3 = st.columns(3)

        for idx, (agent, metrics_list) in enumerate(agent_metrics.items()):
            col = [col_metrics1, col_metrics2, col_metrics3][idx]

            with col:
                st.markdown(f"**{agent}**")

                if len(metrics_list) > 0:
                    # Calculate averages
                    avg_overall = sum(m.get('overall_score', 0) for m in metrics_list) / len(metrics_list)
                    avg_grade = metrics.get_letter_grade(avg_overall)  # Using the metrics module function

                    st.metric("Avg Overall Score", f"{avg_overall:.2f} ({avg_grade})")

                    # Extract individual metric averages
                    avg_bullet_preservation = 0
                    avg_json_integrity = 0
                    avg_translation_quality = 0

                    for m in metrics_list:
                        m_data = m.get('metrics', {})
                        avg_bullet_preservation += m_data.get('bullet_preservation', {}).get('score', 0)
                        avg_json_integrity += m_data.get('json_integrity', {}).get('score', 0)
                        avg_translation_quality += m_data.get('translation_quality', {}).get('score', 0)

                    if len(metrics_list) > 0:
                        avg_bullet_preservation /= len(metrics_list)
                        avg_json_integrity /= len(metrics_list)
                        avg_translation_quality /= len(metrics_list)

                    st.progress(avg_bullet_preservation, text=f"Bullet Preservation: {avg_bullet_preservation:.2f}")
                    st.progress(avg_json_integrity, text=f"JSON Integrity: {avg_json_integrity:.2f}")
                    st.progress(avg_translation_quality, text=f"Translation Quality: {avg_translation_quality:.2f}")
                    st.caption(f"Based on {len(metrics_list)} samples")
                else:
                    st.info("No metrics data for this agent yet")

        # Metrics trends over time
        st.markdown("**Quality Metrics Trends**")

        if len(samples_with_metrics) >= 3:
            # Show last 10 samples
            recent_samples = samples_with_metrics[-10:]

            # Prepare data for trend visualization
            timestamps = []
            overall_scores = []
            agent_names = []

            for d in recent_samples:
                timestamps.append(d.get('timestamp', 'Unknown'))
                metrics_data = d.get('comprehensive_metrics', {})
                overall_scores.append(metrics_data.get('overall_score', 0))
                agent_names.append(d.get('selected_variant', 'Unknown'))

            # Display as table with color coding
            trend_data = []
            for i in range(len(recent_samples)):
                score = overall_scores[i]
                grade = metrics.get_letter_grade(score)
                status = "✅" if score >= 0.85 else ("⚠️" if score >= 0.70 else "❌")

                trend_data.append({
                    "Sample": i + 1,
                    "Timestamp": timestamps[i],
                    "Agent": agent_names[i],
                    "Score": f"{score:.2f}",
                    "Grade": grade,
                    "Status": status
                })

            st.dataframe(trend_data, use_container_width=True, height=300)

            # Show average score over time
            if len(overall_scores) > 0:
                avg_recent_score = sum(overall_scores) / len(overall_scores)
                st.metric(
                    "Average Score (Last 10 Samples)",
                    f"{avg_recent_score:.2f}",
                    delta=f"{(overall_scores[-1] - overall_scores[0]):.2f}" if len(overall_scores) > 1 else None,
                    help="Trend from oldest to newest in this window"
                )
        else:
            st.info("Collect at least 3 samples to see trends")

    else:
        st.info("📊 No comprehensive metrics data available yet. Metrics will appear after processing CVs with the updated system.")

    st.divider()

    # 4. BIAS DETECTION ANALYTICS
    st.subheader("🔍 Bias Detection Dashboard")

    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.markdown("**Agent Win Distribution**")
        for agent, count in persona_counts.most_common():
            percentage = (count / len(data)) * 100
            st.progress(percentage / 100, text=f"{agent}: {count} wins ({percentage:.1f}%)")

    with col_chart2:
        st.markdown("**File Pattern Analysis**")
        # Group by filename to detect biases
        file_winners = {}
        for d in data:
            fname = d['filename']
            if fname not in file_winners:
                file_winners[fname] = []
            file_winners[fname].append(d['selected_variant'])

        # Show files with consistent winner (potential bias indicator)
        st.markdown("*Files with consistent winner:*")
        for fname, winners in file_winners.items():
            if len(winners) > 1:
                winner_counts = Counter(winners)
                dominant = winner_counts.most_common(1)[0]
                if dominant[1] == len(winners):  # All same winner
                    st.warning(f"⚠️ `{fname}`: Always {dominant[0]}")

    st.divider()

    # 5. The Dataset (Enhanced Table View)
    st.subheader("🗄️ Training History")

    # Create enhanced display data
    display_data = []
    for i, d in enumerate(data):
        display_data.append({
            "Index": i + 1,
            "Timestamp": d['timestamp'],
            "Original File": d['filename'],
            "Winner": d['selected_variant'],
            "Contact Name": d['final_json'].get('contact_info', {}).get('name', 'N/A')
        })

    st.dataframe(display_data, use_container_width=True, height=300)

    st.divider()

    # 6. PDF ARCHIVE VIEWER
    st.subheader("📂 Winning Resume Archive")

    selected_index = st.selectbox(
        "Select a sample to view:",
        options=range(len(data)),
        format_func=lambda i: f"#{i+1} - {data[i]['filename']} → {data[i]['selected_variant']} ({data[i]['timestamp']})"
    )

    if selected_index is not None:
        record = data[selected_index]

        col_info, col_preview = st.columns([1, 2])

        with col_info:
            st.markdown("**Sample Details:**")
            st.json({
                "Index": selected_index + 1,
                "Timestamp": record['timestamp'],
                "Original File": record['filename'],
                "Winning Agent": record['selected_variant'],
                "Candidate": record['final_json'].get('contact_info', {}).get('name', 'N/A')
            })

        with col_preview:
            st.markdown(f"**Winning Resume PDF ({record['selected_variant']})**")
            # Generate the winning PDF
            winning_pdf = generate_dynamic_pdf(record['final_json'])
            display_pdf(winning_pdf, height=600)

    st.divider()

    # 7. DATA MANAGEMENT CONTROLS
    st.subheader("🛠️ Training Data Management")

    col_mgmt1, col_mgmt2 = st.columns(2)

    with col_mgmt1:
        st.markdown("**Export Dataset**")
        jsonl_str = "\n".join([json.dumps(d) for d in data])
        st.download_button(
            label="💾 Download Full Dataset (.jsonl)",
            data=jsonl_str,
            file_name="full_training_data.jsonl",
            mime="application/json",
            use_container_width=True,
            type="primary"
        )

    with col_mgmt2:
        st.markdown("**Delete Data**")
        if st.button("🗑️ Clear All Training Data", use_container_width=True, type="secondary"):
            if os.path.exists(file_path):
                os.remove(file_path)
                st.success("✅ All training data deleted! Starting fresh.")
                st.rerun()

    st.markdown("---")

    # Delete individual samples
    st.markdown("**Delete Individual Sample**")
    col_del1, col_del2 = st.columns([3, 1])

    with col_del1:
        delete_index = st.selectbox(
            "Select sample to delete:",
            options=range(len(data)),
            format_func=lambda i: f"#{i+1} - {data[i]['filename']} → {data[i]['selected_variant']}"
        )

    with col_del2:
        st.markdown("")  # Spacer
        st.markdown("")  # Spacer
        if st.button("🗑️ Delete", key="delete_individual"):
            # Remove the selected sample
            data.pop(delete_index)
            # Rewrite the file
            with open(file_path, "w") as f:
                for entry in data:
                    f.write(json.dumps(entry) + "\n")
            st.success(f"✅ Sample #{delete_index + 1} deleted!")
            st.rerun()

# --- 6. MAIN APP ROUTING ---
# Sidebar Navigation
page = st.sidebar.selectbox("Navigate", ["🏆 Tournament Mode", "📊 Admin Dashboard"])

if page == "📊 Admin Dashboard":
    run_admin_dashboard()

else:
    # === TOURNAMENT MODE ===
    st.title("🏆 Global ATS Bridge: The Tournament")

    # Processing Mode Selector
    processing_mode = st.radio("Processing Mode", ["📄 Single CV", "📚 Bulk Set"], horizontal=True)

    # Agent Mode Selector
    st.markdown("---")
    agent_mode = st.radio(
        "Agent Mode",
        ["⚡ Quick Mode (Hybrid Auditor Only)", "🏆 Tournament Mode (All 3 Agents)"],
        index=0,  # Default to Quick Mode
        horizontal=True,
        help="Quick Mode: Fast, cost-effective, uses only the validated Hybrid Auditor prompt. Tournament Mode: Compare all 3 agents (Conservative, Strategist, Hybrid Auditor)."
    )
    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        visa_status = st.selectbox("Target Visa Status", ["F-1 OPT (Stem)", "H-1B", "US Citizen"])
    with col2:
        if processing_mode == "📄 Single CV":
            uploaded_file = st.file_uploader("Upload CV (PDF)", type="pdf")
        else:
            uploaded_files = st.file_uploader("Upload CVs (PDF)", type="pdf", accept_multiple_files=True)

    # Session State for storing results across reruns
    # Single mode states
    if "results" not in st.session_state:
        st.session_state.results = None
    if "original_filename" not in st.session_state:
        st.session_state.original_filename = ""
    if "selected_variant" not in st.session_state:
        st.session_state.selected_variant = None
    if "original_pdf_bytes" not in st.session_state:
        st.session_state.original_pdf_bytes = None
    if "validation_report" not in st.session_state:
        st.session_state.validation_report = None
    if "session_id" not in st.session_state:
        st.session_state.session_id = None  # Unique ID for this tournament session
    if "fidelity_reports" not in st.session_state:
        st.session_state.fidelity_reports = {}  # {agent_name: fidelity_report}
    if "comprehensive_metrics" not in st.session_state:
        st.session_state.comprehensive_metrics = {}  # {agent_name: comprehensive_metrics_report}

    # Bulk mode states
    if "bulk_results" not in st.session_state:
        st.session_state.bulk_results = {}  # {filename: {Conservative: {...}, Strategist: {...}, Hybrid_Auditor: {...}}}
    if "bulk_selections" not in st.session_state:
        st.session_state.bulk_selections = {}  # {filename: "agent_name"}
    if "bulk_validation_reports" not in st.session_state:
        st.session_state.bulk_validation_reports = {}  # {filename: {...}}
    if "bulk_original_pdfs" not in st.session_state:
        st.session_state.bulk_original_pdfs = {}  # {filename: bytes}
    if "current_cv_index" not in st.session_state:
        st.session_state.current_cv_index = 0
    if "bulk_filenames" not in st.session_state:
        st.session_state.bulk_filenames = []  # Ordered list of filenames
    if "bulk_session_id" not in st.session_state:
        st.session_state.bulk_session_id = None  # Unique ID for bulk tournament session
    if "bulk_fidelity_reports" not in st.session_state:
        st.session_state.bulk_fidelity_reports = {}  # {filename: {agent_name: fidelity_report}}
    if "bulk_comprehensive_metrics" not in st.session_state:
        st.session_state.bulk_comprehensive_metrics = {}  # {filename: {agent_name: comprehensive_metrics}}

    # === SINGLE CV MODE ===
    if processing_mode == "📄 Single CV":
        if uploaded_file and st.button("🚀 Start Tournament"):
            # Validate file size (20MB limit for Gemini)
            file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
            if file_size_mb > 20:
                st.error(f"❌ File too large ({file_size_mb:.1f}MB). Max: 20MB")
                st.stop()

            # Reset state for new tournament
            st.session_state.results = {}
            st.session_state.original_filename = uploaded_file.name
            st.session_state.selected_variant = None
            # Store original PDF for comparison
            st.session_state.original_pdf_bytes = uploaded_file.getvalue()
            # Generate unique session ID for this tournament
            st.session_state.session_id = time.strftime("%Y%m%d_%H%M%S")

            # 1. Save Temp File for Vision
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(uploaded_file.getvalue())
                tmp_path = tmp.name

            try:
                # 2. Parallel Execution
                # Determine which agents to run based on mode
                if agent_mode == "⚡ Quick Mode (Hybrid Auditor Only)":
                    personas = ["Hybrid_Auditor"]
                    status_text = st.empty()
                    status_text.info("⚡ Running Hybrid Auditor... (Gemini 3 Flash)")
                else:
                    personas = ["Conservative", "Strategist", "Hybrid_Auditor"]
                    status_text = st.empty()
                    status_text.info("⚡ Agents are running in parallel... (Gemini 3 Flash)")

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    futures = {executor.submit(run_agent, tmp_path, p, visa_status): p for p in personas}

                    for future in concurrent.futures.as_completed(futures):
                        persona, data, fidelity_report, comprehensive_metrics_report = future.result()
                        st.session_state.results[persona] = data
                        st.session_state.fidelity_reports[persona] = fidelity_report
                        st.session_state.comprehensive_metrics[persona] = comprehensive_metrics_report

                # Run GPA validation on all results
                st.session_state.validation_report = validate_gpa_conversions(st.session_state.results)

                # Show completion message with validation status
                if st.session_state.validation_report.get("valid", True):
                    status_text.success("✅ Tournament Complete! All GPAs validated successfully.")
                else:
                    invalid_count = len(st.session_state.validation_report.get("invalid_gpas_found", []))
                    status_text.warning(f"⚠️ Tournament Complete! Found {invalid_count} invalid GPA(s). Check validation panel below.")

            finally:
                # Cleanup (guaranteed to run even if errors occur)
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

    # === BULK CV MODE ===
    else:
        if uploaded_files and st.button("🚀 Start Bulk Tournament"):
            # Validate all file sizes
            invalid_files = []
            for file in uploaded_files:
                file_size_mb = len(file.getvalue()) / (1024 * 1024)
                if file_size_mb > 20:
                    invalid_files.append(f"{file.name} ({file_size_mb:.1f}MB)")

            if invalid_files:
                st.error(f"❌ Files too large (Max 20MB each):\n" + "\n".join(f"- {f}" for f in invalid_files))
                st.stop()

            # Reset bulk state
            st.session_state.bulk_results = {}
            st.session_state.bulk_selections = {}
            st.session_state.bulk_validation_reports = {}
            st.session_state.bulk_original_pdfs = {}
            st.session_state.bulk_filenames = [f.name for f in uploaded_files]
            st.session_state.current_cv_index = 0
            # Generate unique session ID for this bulk tournament
            st.session_state.bulk_session_id = time.strftime("%Y%m%d_%H%M%S")

            # Process all PDFs
            # Determine which agents to run based on mode
            if agent_mode == "⚡ Quick Mode (Hybrid Auditor Only)":
                personas = ["Hybrid_Auditor"]
            else:
                personas = ["Conservative", "Strategist", "Hybrid_Auditor"]

            total_files = len(uploaded_files)

            # Create progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()

            for idx, uploaded_file in enumerate(uploaded_files):
                filename = uploaded_file.name
                status_text.info(f"⚡ Processing {idx + 1}/{total_files}: {filename}...")

                # Store original PDF
                st.session_state.bulk_original_pdfs[filename] = uploaded_file.getvalue()

                # Save temp file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name

                try:
                    # Run agents in parallel for this CV
                    cv_results = {}
                    cv_fidelity_reports = {}
                    cv_comprehensive_metrics = {}
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        futures = {executor.submit(run_agent, tmp_path, p, visa_status): p for p in personas}

                        for future in concurrent.futures.as_completed(futures):
                            persona, data, fidelity_report, comprehensive_metrics_report = future.result()
                            cv_results[persona] = data
                            cv_fidelity_reports[persona] = fidelity_report
                            cv_comprehensive_metrics[persona] = comprehensive_metrics_report

                    # Store results
                    st.session_state.bulk_results[filename] = cv_results
                    st.session_state.bulk_fidelity_reports[filename] = cv_fidelity_reports
                    st.session_state.bulk_comprehensive_metrics[filename] = cv_comprehensive_metrics

                    # Run validation
                    st.session_state.bulk_validation_reports[filename] = validate_gpa_conversions(cv_results)

                finally:
                    # Cleanup temp file
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)

                # Update progress
                progress_bar.progress((idx + 1) / total_files)

            # Completion message
            status_text.success(f"✅ Bulk Tournament Complete! Processed {total_files} CVs. Review and select winners below.")
            progress_bar.empty()

    # --- 7. DISPLAY RESULTS ---
    # === SINGLE CV DISPLAY ===
    if processing_mode == "📄 Single CV" and st.session_state.results:
        r = st.session_state.results

        # Build tab names with validation status indicators
        validation_report = st.session_state.get('validation_report', {})
        invalid_gpas = validation_report.get('invalid_gpas_found', [])

        # Get list of agents that were actually run
        available_agents = list(r.keys())

        # Create dict of agent -> has_invalid_gpa
        agent_validation_status = {}
        for agent_name in available_agents:
            has_invalid = any(item['agent'] == agent_name for item in invalid_gpas)
            agent_validation_status[agent_name] = has_invalid

        # Build tab names with status indicators
        tab_names = ["📋 Original CV"]
        for agent in available_agents:
            if agent_validation_status.get(agent, False):
                tab_names.append(f"🤖 {agent} ❌")  # Red X for invalid GPAs
            else:
                tab_names.append(f"🤖 {agent} ✅")  # Green check for valid

        # Create tabs dynamically based on number of agents
        tabs_list = st.tabs(tab_names)

        # ORIGINAL CV TAB
        with tabs_list[0]:
            st.markdown("### 📋 Original Uploaded Resume")
            if st.session_state.original_pdf_bytes:
                # Display original PDF from session state
                original_buffer = io.BytesIO(st.session_state.original_pdf_bytes)
                display_pdf(original_buffer, height=1200)
            else:
                st.warning("Original PDF not found in session state.")

        # GENERATED RESUMES TABS
        for i, key in enumerate(available_agents):
            with tabs_list[i + 1]:  # +1 because first tab is original CV
                data = r.get(key, {})

                # Check for errors first
                if "error" in data:
                    st.error(f"❌ {key} Failed:\n{data['error']}")
                    continue  # Skip the rest for this agent

                # Full PDF Preview (Full Width!)
                st.markdown(f"### 📄 {key} Resume Preview")
                pdf_preview = generate_dynamic_pdf(data)
                display_pdf(pdf_preview, height=1200)  # Extra tall for better visibility

                st.markdown("---")

                # COMPREHENSIVE QUALITY METRICS
                comprehensive_metrics_report = st.session_state.comprehensive_metrics.get(key, {})
                display_comprehensive_metrics(comprehensive_metrics_report, key)

                st.markdown("---")

                # SELECT BUTTON (Prominent and centered)
                # In Quick Mode, auto-select Hybrid_Auditor without button click
                if len(available_agents) == 1 and key == "Hybrid_Auditor":
                    if not st.session_state.selected_variant:
                        st.session_state.selected_variant = key
                        # Log Data (Flywheel) with validation report and comprehensive metrics
                        validation_report = st.session_state.get('validation_report', None)
                        session_id = st.session_state.get('session_id', None)
                        comprehensive_metrics_report = st.session_state.comprehensive_metrics.get(key, {})
                        save_training_data(st.session_state.original_filename, key, data, validation_report, session_id, "single", comprehensive_metrics_report)

                    st.success(f"✅ **{key} selected** (Quick Mode)")
                else:
                    # Tournament Mode: Show selection button
                    col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
                    with col_btn2:
                        if st.button(f"✅ Select {key} as Winner", key=f"btn_{key}", type="primary", use_container_width=True):
                            st.session_state.selected_variant = key
                            # Log Data (Flywheel) with validation report and comprehensive metrics
                            validation_report = st.session_state.get('validation_report', None)
                            session_id = st.session_state.get('session_id', None)
                            comprehensive_metrics_report = st.session_state.comprehensive_metrics.get(key, {})
                            save_training_data(st.session_state.original_filename, key, data, validation_report, session_id, "single", comprehensive_metrics_report)
                            st.toast(f"✅ {key} selected! Training data saved.")
                            st.rerun()  # Refresh to show download button

        # Show Download Section AFTER Selection
        if st.session_state.selected_variant:
            st.markdown("---")
            st.success(f"🎯 You selected: **{st.session_state.selected_variant}**")

            selected_data = r.get(st.session_state.selected_variant, {})
            if "error" not in selected_data:
                pdf_bytes = generate_dynamic_pdf(selected_data)

                col_download, col_reset = st.columns([3, 1])
                with col_download:
                    st.download_button(
                        label=f"⬇️ Download {st.session_state.selected_variant} Resume PDF",
                        data=pdf_bytes,
                        file_name=f"Resume_{st.session_state.selected_variant}.pdf",
                        mime="application/pdf",
                        type="primary",
                        use_container_width=True
                    )
                with col_reset:
                    if st.button("🔄 Reset", use_container_width=True):
                        st.session_state.selected_variant = None
                        st.rerun()

        # VALIDATION REPORT PANEL
        validation_report = st.session_state.get('validation_report', {})
        if validation_report and not validation_report.get('valid', True):
            st.markdown("---")
            with st.expander("⚠️ GPA Validation Report - Invalid GPAs Detected", expanded=True):
                st.warning(f"**Found {len(validation_report.get('invalid_gpas_found', []))} invalid GPA(s)** that don't match the authoritative grading standards.")

                invalid_gpas = validation_report.get('invalid_gpas_found', [])

                for idx, issue in enumerate(invalid_gpas, 1):
                    st.markdown(f"**Issue #{idx}:**")
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        st.metric("Agent", issue['agent'])
                        st.metric("Invalid GPA", issue['gpa'])
                    with col2:
                        st.text_area(
                            "Context (where it appeared)",
                            value=issue['context'],
                            height=100,
                            key=f"context_{idx}",
                            disabled=True
                        )
                    st.markdown("---")

                st.info("💡 **Why this matters:** These GPAs don't exist in the deterministic grading standards (grading_standards.json). The AI may have hallucinated or miscalculated the conversion. Review these carefully before selecting a winner.")

        with st.expander("🔍 Debug: See Raw JSON for all Agents"):
            st.json(st.session_state.results)

        # START NEW TOURNAMENT BUTTON
        st.markdown("---")
        col_new_1, col_new_2, col_new_3 = st.columns([1, 2, 1])
        with col_new_2:
            if st.button("🔄 Start New Tournament", type="primary", use_container_width=True):
                # Clear all session state
                st.session_state.results = None
                st.session_state.selected_variant = None
                st.session_state.original_filename = ""
                st.session_state.original_pdf_bytes = None
                st.rerun()

    # === BULK CV DISPLAY (CAROUSEL MODE) ===
    elif processing_mode == "📚 Bulk Set" and st.session_state.bulk_filenames:
        total_cvs = len(st.session_state.bulk_filenames)
        current_idx = st.session_state.current_cv_index
        current_filename = st.session_state.bulk_filenames[current_idx]

        # Progress Header
        st.markdown("---")
        col_progress1, col_progress2, col_progress3 = st.columns([1, 2, 1])

        with col_progress1:
            voted_count = len(st.session_state.bulk_selections)
            st.metric("Progress", f"{voted_count}/{total_cvs} Voted")

        with col_progress2:
            st.markdown(f"### 📄 CV {current_idx + 1}/{total_cvs}: `{current_filename}`")

        with col_progress3:
            # Show if current CV has been voted
            if current_filename in st.session_state.bulk_selections:
                st.success(f"✅ Voted: {st.session_state.bulk_selections[current_filename]}")
            else:
                st.warning("⏳ Not voted yet")

        # Progress bar
        progress_percentage = voted_count / total_cvs
        st.progress(progress_percentage, text=f"{voted_count}/{total_cvs} CVs completed")

        st.markdown("---")

        # Get current CV results
        r = st.session_state.bulk_results.get(current_filename, {})

        if not r:
            st.error(f"❌ No results found for {current_filename}")
        else:
            # Build tab names with validation status indicators
            validation_report = st.session_state.bulk_validation_reports.get(current_filename, {})
            invalid_gpas = validation_report.get('invalid_gpas_found', [])

            # Get list of agents that were actually run
            available_agents = list(r.keys())

            # Create dict of agent -> has_invalid_gpa
            agent_validation_status = {}
            for agent_name in available_agents:
                has_invalid = any(item['agent'] == agent_name for item in invalid_gpas)
                agent_validation_status[agent_name] = has_invalid

            # Build tab names with status indicators
            tab_names = ["📋 Original CV"]
            for agent in available_agents:
                if agent_validation_status.get(agent, False):
                    tab_names.append(f"🤖 {agent} ❌")  # Red X for invalid GPAs
                else:
                    tab_names.append(f"🤖 {agent} ✅")  # Green check for valid

            # Create tabs dynamically based on number of agents
            tabs_list = st.tabs(tab_names)

            # ORIGINAL CV TAB
            with tabs_list[0]:
                st.markdown("### 📋 Original Uploaded Resume")
                original_bytes = st.session_state.bulk_original_pdfs.get(current_filename)
                if original_bytes:
                    original_buffer = io.BytesIO(original_bytes)
                    display_pdf(original_buffer, height=1200)
                else:
                    st.warning("Original PDF not found.")

            # GENERATED RESUMES TABS
            for i, key in enumerate(available_agents):
                with tabs_list[i + 1]:  # +1 because first tab is original CV
                    data = r.get(key, {})

                    # Check for errors first
                    if "error" in data:
                        st.error(f"❌ {key} Failed:\n{data['error']}")
                        continue  # Skip the rest for this agent

                    # Full PDF Preview (Full Width!)
                    st.markdown(f"### 📄 {key} Resume Preview")
                    pdf_preview = generate_dynamic_pdf(data)
                    display_pdf(pdf_preview, height=1200)

                    st.markdown("---")

                    # COMPREHENSIVE QUALITY METRICS
                    cv_comprehensive_metrics = st.session_state.bulk_comprehensive_metrics.get(current_filename, {})
                    comprehensive_metrics_report = cv_comprehensive_metrics.get(key, {})
                    display_comprehensive_metrics(comprehensive_metrics_report, key)

                    st.markdown("---")

                    # SELECT BUTTON (Prominent and centered)
                    # In Quick Mode, auto-select Hybrid_Auditor without button click
                    if len(available_agents) == 1 and key == "Hybrid_Auditor":
                        if current_filename not in st.session_state.bulk_selections:
                            st.session_state.bulk_selections[current_filename] = key
                            # Log Data (Flywheel) with validation report and comprehensive metrics
                            bulk_session_id = st.session_state.get('bulk_session_id', None)
                            comprehensive_metrics_report = cv_comprehensive_metrics.get(key, {})
                            save_training_data(current_filename, key, data, validation_report, bulk_session_id, "bulk", comprehensive_metrics_report)

                        st.success(f"✅ **{key} selected** (Quick Mode)")
                    else:
                        # Tournament Mode: Show selection button
                        col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
                        with col_btn2:
                            # Check if this agent is already selected
                            current_selection = st.session_state.bulk_selections.get(current_filename)
                            button_type = "primary" if current_selection == key else "secondary"
                            button_label = f"✅ Selected: {key}" if current_selection == key else f"Select {key} as Winner"

                            if st.button(button_label, key=f"bulk_btn_{current_filename}_{key}", type=button_type, use_container_width=True):
                                # Save selection
                                st.session_state.bulk_selections[current_filename] = key
                                # Log Data (Flywheel) with validation report and comprehensive metrics
                                bulk_session_id = st.session_state.get('bulk_session_id', None)
                                comprehensive_metrics_report = cv_comprehensive_metrics.get(key, {})
                                save_training_data(current_filename, key, data, validation_report, bulk_session_id, "bulk", comprehensive_metrics_report)
                                st.toast(f"✅ {key} selected for {current_filename}!")
                                st.rerun()

            # VALIDATION REPORT PANEL
            if validation_report and not validation_report.get('valid', True):
                st.markdown("---")
                with st.expander("⚠️ GPA Validation Report - Invalid GPAs Detected", expanded=True):
                    st.warning(f"**Found {len(validation_report.get('invalid_gpas_found', []))} invalid GPA(s)** that don't match the authoritative grading standards.")

                    invalid_gpas = validation_report.get('invalid_gpas_found', [])

                    for idx, issue in enumerate(invalid_gpas, 1):
                        st.markdown(f"**Issue #{idx}:**")
                        col1, col2 = st.columns([1, 3])
                        with col1:
                            st.metric("Agent", issue['agent'])
                            st.metric("Invalid GPA", issue['gpa'])
                        with col2:
                            st.text_area(
                                "Context (where it appeared)",
                                value=issue['context'],
                                height=100,
                                key=f"bulk_context_{current_filename}_{idx}",
                                disabled=True
                            )
                        st.markdown("---")

                    st.info("💡 **Why this matters:** These GPAs don't exist in the deterministic grading standards (grading_standards.json). The AI may have hallucinated or miscalculated the conversion. Review these carefully before selecting a winner.")

            # NAVIGATION CONTROLS
            st.markdown("---")
            col_nav1, col_nav2, col_nav3, col_nav4 = st.columns([1, 1, 1, 1])

            with col_nav1:
                if current_idx > 0:
                    if st.button("⬅️ Previous CV", use_container_width=True):
                        st.session_state.current_cv_index -= 1
                        st.rerun()
                else:
                    st.button("⬅️ Previous CV", use_container_width=True, disabled=True)

            with col_nav2:
                # Show list of all CVs with checkmarks
                if st.button("📋 View All CVs", use_container_width=True):
                    with st.expander("All CVs in Set", expanded=True):
                        for idx, fname in enumerate(st.session_state.bulk_filenames):
                            status = "✅" if fname in st.session_state.bulk_selections else "⏳"
                            selected_agent = st.session_state.bulk_selections.get(fname, "Not voted")
                            st.text(f"{status} {idx + 1}. {fname} → {selected_agent}")

            with col_nav3:
                # Next button - only enabled if current CV has selection
                has_selection = current_filename in st.session_state.bulk_selections

                if current_idx < total_cvs - 1:
                    if has_selection:
                        if st.button("Next CV ➡️", use_container_width=True, type="primary"):
                            st.session_state.current_cv_index += 1
                            st.rerun()
                    else:
                        st.button("Next CV ➡️", use_container_width=True, disabled=True)
                        st.caption("⚠️ Select a winner first")
                else:
                    st.button("Next CV ➡️", use_container_width=True, disabled=True)

            with col_nav4:
                # Finish button - only enabled if all CVs voted
                all_voted = len(st.session_state.bulk_selections) == total_cvs

                if all_voted:
                    if st.button("🎉 Finish Set", use_container_width=True, type="primary"):
                        st.balloons()
                        st.success(f"🎉 Congratulations! You've completed all {total_cvs} CVs in this set!")
                        st.info(f"📊 Training data saved for {total_cvs} samples. Check the Admin Dashboard to review.")
                        # Optionally clear bulk state
                        if st.button("🔄 Start New Bulk Set"):
                            st.session_state.bulk_results = {}
                            st.session_state.bulk_selections = {}
                            st.session_state.bulk_validation_reports = {}
                            st.session_state.bulk_original_pdfs = {}
                            st.session_state.bulk_filenames = []
                            st.session_state.current_cv_index = 0
                            st.rerun()
                else:
                    st.button("🎉 Finish Set", use_container_width=True, disabled=True)
                    st.caption(f"⚠️ {total_cvs - len(st.session_state.bulk_selections)} CVs left")