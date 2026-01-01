#!/usr/bin/env python3
# optimize_prompts.py
# Programmatically selects "Gold Standard" few-shot examples to update dynamic_prompts.json

import os
import json
import time
from pathlib import Path
import google.generativeai as genai

# --- CONFIGURATION ---
DATA_SOURCES = [
    "data/training_data.jsonl",
    "evaluation_results_rl/detailed_results.json",
    "evaluation_results_rl_v2/detailed_results.json",
    "evaluation_results_rl_v3/detailed_results.json"
]
OUTPUT_FILE = "data/dynamic_prompts.json"
REWARD_THRESHOLD = 0.90
MAX_EXAMPLES = 3  # Keep prompt length manageable

def load_candidates():
    """Loads candidates from multiple data sources."""
    candidates = []
    for source in DATA_SOURCES:
        if not os.path.exists(source):
            continue
            
        print(f"🔍 Scanning {source}...")
        try:
            if source.endswith(".jsonl"):
                with open(source, "r") as f:
                    for line in f:
                        entry = json.loads(line)
                        process_entry(entry, candidates)
            else:
                with open(source, "r") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for entry in data:
                            process_entry(entry, candidates)
        except Exception as e:
            print(f"⚠️ Error reading {source}: {e}")
            
    return candidates

def process_entry(entry, candidates):
    """Processes a single entry from any source."""
    # Handle different structures
    metrics = entry.get("comprehensive_metrics", {})
    rl_reward = metrics.get("rl_reward") or entry.get("rl_reward")
    
    if not rl_reward or not isinstance(rl_reward, dict):
        return
        
    reward = rl_reward.get("reward", 0)
    
    if reward >= REWARD_THRESHOLD:
        candidates.append({
            "reward": reward,
            "filename": entry.get("filename"),
            "final_json": entry.get("final_json") or entry.get("result_json"),
            "original_text": entry.get("original_text")
        })

def init_gemini():
    """Initialize Gemini API."""
    # Try to get from streamlit secrets
    secrets_path = ".streamlit/secrets.toml"
    if os.path.exists(secrets_path):
        with open(secrets_path, "r") as f:
            for line in f:
                if "GOOGLE_API_KEY" in line:
                    api_key = line.split("=")[1].strip().strip('"')
                    genai.configure(api_key=api_key)
                    return True
    
    # Fallback to env var
    api_key = os.environ.get("GOOGLE_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
        return True
    return False

def extract_text_from_pdf(pdf_path):
    """Extracts raw text from PDF using Gemini."""
    try:
        print(f"📄 Extracting text from {pdf_path}...")
        gemini_file = genai.upload_file(pdf_path, mime_type="application/pdf")
        
        # Wait for processing
        timeout = 30
        start_time = time.time()
        while gemini_file.state.name == "PROCESSING":
            if time.time() - start_time > timeout:
                return None
            time.sleep(1)
            gemini_file = genai.get_file(gemini_file.name)
            
        model = genai.GenerativeModel('gemini-3-flash-preview')
        prompt = "Extract all text from this PDF exactly as written. Return only the raw text, no formatting."
        response = model.generate_content([prompt, gemini_file])
        
        text = response.text
        gemini_file.delete()
        return text
    except Exception as e:
        print(f"❌ Error extracting text: {e}")
        return None

def find_pdf(filename):
    """Tries to find the PDF in known directories."""
    search_dirs = ["test_cvs", "rl_training_cvs", "archive"]
    
    # Standard exact match search
    for d in search_dirs:
        path = Path(d) / filename
        if path.exists():
            return str(path)
            
    # Fuzzy match for rl_training_cvs (handles _score suffix)
    # Example: filename "cv_name.pdf" matches "cv_name_score0.9_A.pdf"
    if "rl_training_cvs" in search_dirs:
        rl_dir = Path("rl_training_cvs")
        if rl_dir.exists():
            stem = Path(filename).stem
            for file_path in rl_dir.glob("*.pdf"):
                if file_path.name.startswith(stem):
                    return str(file_path)

    return None

def main():
    print("🔧 Initializing Gemini...")
    if not init_gemini():
        print("❌ Could not initialize Gemini API.")
        return

    candidates = load_candidates()
                
    if not candidates:
        print("⚠️ No candidates found meeting the reward threshold.")
        return
        
    # Sort by reward descending
    candidates.sort(key=lambda x: x["reward"], reverse=True)
    
    # Select top candidates
    selected_examples = []
    for cand in candidates:
        if len(selected_examples) >= MAX_EXAMPLES:
            break
            
        source_text = cand.get("original_text")
        
        # If original_text is missing (legacy entries), try to extract it
        if not source_text:
            pdf_path = find_pdf(cand["filename"])
            if pdf_path:
                source_text = extract_text_from_pdf(pdf_path)
            else:
                print(f"⚠️ Could not find PDF for {cand['filename']}, skipping.")
                continue
                
        if source_text:
            selected_examples.append({
                "source_cv_text": source_text,
                "optimized_json": cand["final_json"],
                "reward_score": cand["reward"]
            })
            print(f"✅ Added {cand['filename']} (Reward: {cand['reward']:.3f})")

    if selected_examples:
        with open(OUTPUT_FILE, "w") as f:
            json.dump(selected_examples, f, indent=2)
        print(f"🚀 Successfully updated {OUTPUT_FILE} with {len(selected_examples)} Gold Standards.")
    else:
        print("❌ No examples were successfully processed.")

if __name__ == "__main__":
    main()
