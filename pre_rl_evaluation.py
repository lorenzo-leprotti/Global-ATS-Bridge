#!/usr/bin/env python3
# pre_rl_evaluation.py
# Pre-RL baseline evaluation with visualization and automatic CV filtering

import os
import json
import time
import argparse
import shutil
from pathlib import Path
from typing import List, Dict
import google.generativeai as genai
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import matplotlib.pyplot as plt
import pandas as pd
from pypdf import PdfReader  # Local PDF extraction

# Import project modules
import prompts
import metrics
import enhanced_metrics


# ============================================================================
# CONFIGURATION
# ============================================================================

def init_gemini(api_key_path: str = ".streamlit/secrets.toml"):
    """Initialize Gemini API."""
    try:
        if os.path.exists(api_key_path):
            with open(api_key_path, 'r') as f:
                for line in f:
                    if line.startswith('GOOGLE_API_KEY'):
                        api_key = line.split('=')[1].strip().strip('"')
                        genai.configure(api_key=api_key)
                        return True

        # Fallback to environment variable
        api_key = os.getenv('GOOGLE_API_KEY')
        if api_key:
            genai.configure(api_key=api_key)
            return True

        return False
    except Exception as e:
        print(f"❌ Failed to initialize Gemini: {e}")
        return False


# ============================================================================
# CV PROCESSING
# ============================================================================

def extract_text_locally(pdf_path: str) -> str:
    """Extract text from PDF locally using pypdf."""
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        print(f"⚠️ Local text extraction failed for {os.path.basename(pdf_path)}: {e}")
        return ""

def process_single_cv(
    pdf_path: str,
    visa_status: str = "F-1 OPT (Stem)",
) -> Dict:
    """
    Process a single CV with Hybrid_Auditor agent.

    Args:
        pdf_path: Path to PDF file
        visa_status: User's visa status

    Returns:
        dict with results and metrics
    """
    result = {
        "pdf_path": pdf_path,
        "filename": os.path.basename(pdf_path),
        "success": False,
        "error": None,
        "result_json": None,
        "base_metrics": None,
        "rl_reward": None,
        "processing_time": 0,
        "candidate_name": "Unknown"
    }

    start_time = time.time()

    try:
        # 1. Extract original text LOCALLY (Fast, no API call)
        original_text = extract_text_locally(pdf_path)
        
        # Fallback: If local extraction fails/empty (e.g., scanned image), use a placeholder
        # We skip the API text extraction to save time. Metrics might suffer slightly for scans.
        if not original_text:
            original_text = "[TEXT EXTRACTION FAILED - SCANNED DOCUMENT]"

        # 2. Upload PDF for Vision Processing
        gemini_file = genai.upload_file(pdf_path, mime_type="application/pdf")

        # Wait for processing
        timeout = 30
        upload_start = time.time()
        while gemini_file.state.name == "PROCESSING":
            if time.time() - upload_start > timeout:
                result["error"] = f"File processing timeout after {timeout}s"
                return result
            time.sleep(1)
            gemini_file = genai.get_file(gemini_file.name)

        if gemini_file.state.name == "FAILED":
            result["error"] = "File processing failed"
            return result

        # 3. Generate structured JSON with Hybrid_Auditor
        gen_config = genai.GenerationConfig(
            temperature=0.0,
            max_output_tokens=65536,  # Maximum supported by Gemini
            response_mime_type="application/json"
        )

        model = genai.GenerativeModel('gemini-3-flash-preview', generation_config=gen_config)

        # Get Hybrid_Auditor prompt
        agent_data = prompts.AGENT_PROMPTS["Hybrid_Auditor"]
        system_prompt = f"{prompts.BASE_INSTRUCTIONS}\n\nSTYLE RULES FOR THIS AGENT:\n{agent_data['instructions']}"

        response = model.generate_content([system_prompt, f"USER VISA: {visa_status}", gemini_file])

        # Check finish reason
        finish_reason = "UNKNOWN"
        if hasattr(response, 'candidates') and response.candidates:
            finish_reason_code = response.candidates[0].finish_reason
            finish_reason_map = {1: "STOP", 2: "MAX_TOKENS", 3: "SAFETY", 4: "RECITATION", 5: "OTHER"}
            finish_reason = finish_reason_map.get(finish_reason_code, f"UNKNOWN_{finish_reason_code}")

            if finish_reason_code == 2:  # MAX_TOKENS - response truncated
                result["error"] = f"Response truncated (MAX_TOKENS). Length: {len(response.text)} chars. Increase max_output_tokens."
                return result

        # 4. Parse JSON
        raw_response = response.text
        clean_text = raw_response.replace("```json", "").replace("```", "").strip()

        try:
            result_json = json.loads(clean_text)
        except json.JSONDecodeError as e:
            result["error"] = f"JSON parse error: {str(e)} | Finish: {finish_reason} | Length: {len(raw_response)} chars"
            return result

        result["result_json"] = result_json

        # Extract candidate name
        candidate_name = result_json.get("contact_info", {}).get("name", "Unknown")
        result["candidate_name"] = candidate_name

        # 5. Calculate metrics
        base_metrics = metrics.run_all_metrics(original_text, result_json)
        result["base_metrics"] = base_metrics

        # 6. Calculate RL reward
        rl_reward = enhanced_metrics.calculate_rl_reward(
            original_text,
            result_json,
            raw_response,
            base_metrics
        )
        result["rl_reward"] = rl_reward

        # Cleanup
        gemini_file.delete()

        result["success"] = True

    except json.JSONDecodeError as json_err:
        result["error"] = f"JSON parse error: {str(json_err)}"
    except Exception as e:
        result["error"] = str(e)

    result["processing_time"] = time.time() - start_time
    return result


def process_cv_batch(
    pdf_paths: List[str],
    max_workers: int = 3,
    visa_status: str = "F-1 OPT (Stem)"
) -> List[Dict]:
    """
    Process multiple CVs in parallel.

    Args:
        pdf_paths: List of PDF file paths
        max_workers: Number of parallel workers
        visa_status: Default visa status

    Returns:
        List of result dicts
    """
    results = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        futures = {
            executor.submit(process_single_cv, pdf_path, visa_status): pdf_path
            for pdf_path in pdf_paths
        }

        # Process as they complete
        with tqdm(total=len(pdf_paths), desc="Processing CVs") as pbar:
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                pbar.update(1)

                # Log status
                if result["success"]:
                    reward = result["rl_reward"]["reward"]
                    grade = result["rl_reward"]["grade"]
                    print(f"  ✅ {result['filename']}: Score={reward:.4f} ({grade})")
                else:
                    print(f"  ❌ {result['filename']}: {result['error']}")

    return results


# ============================================================================
# VISUALIZATION & REPORTING
# ============================================================================

def generate_score_chart(
    results: List[Dict],
    output_dir: str = "evaluation_results"
) -> str:
    """
    Generate a bar chart showing CV names and their RL scores.

    Args:
        results: List of processing results
        output_dir: Output directory

    Returns:
        Path to saved chart
    """
    # Extract data for successful results
    successful_results = [r for r in results if r["success"]]

    # Sort by score (descending)
    successful_results.sort(key=lambda x: x["rl_reward"]["reward"], reverse=True)

    # Prepare data
    filenames = [r["candidate_name"] if r["candidate_name"] != "Unknown" else r["filename"][:20]
                 for r in successful_results]
    scores = [r["rl_reward"]["reward"] for r in successful_results]
    grades = [r["rl_reward"]["grade"] for r in successful_results]

    # Create figure
    fig, ax = plt.subplots(figsize=(14, max(8, len(filenames) * 0.4)))

    # Color bars by grade
    colors = []
    for grade in grades:
        if grade in ['A+', 'A', 'A-']:
            colors.append('#2ecc71')  # Green
        elif grade in ['B+', 'B', 'B-']:
            colors.append('#3498db')  # Blue
        elif grade in ['C+', 'C']:
            colors.append('#f39c12')  # Orange
        else:
            colors.append('#e74c3c')  # Red

    # Create horizontal bar chart
    y_pos = range(len(filenames))
    bars = ax.barh(y_pos, scores, color=colors, edgecolor='black', linewidth=0.5)

    # Customize chart
    ax.set_yticks(y_pos)
    ax.set_yticklabels(filenames, fontsize=9)
    ax.set_xlabel('RL Reward Score', fontsize=12, fontweight='bold')
    ax.set_title('Pre-RL Baseline Evaluation: CV Scores (Hybrid_Auditor)',
                 fontsize=14, fontweight='bold', pad=20)
    ax.axvline(x=0.80, color='red', linestyle='--', linewidth=2, alpha=0.7, label='Passing Threshold (0.80)')
    ax.set_xlim(0, 1.0)
    ax.grid(axis='x', alpha=0.3)
    ax.legend(loc='lower right')

    # Add score labels on bars
    for i, (bar, score, grade) in enumerate(zip(bars, scores, grades)):
        width = bar.get_width()
        ax.text(width + 0.01, bar.get_y() + bar.get_height()/2,
                f'{score:.3f} ({grade})',
                ha='left', va='center', fontsize=8, fontweight='bold')

    plt.tight_layout()

    # Save chart
    chart_path = os.path.join(output_dir, "pre_rl_scores_chart.png")
    plt.savefig(chart_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"\n📊 Score chart saved to: {chart_path}")
    return chart_path


def export_high_quality_cvs(
    results: List[Dict],
    threshold: float = 0.80,
    output_dir: str = "rl_training_cvs"
) -> Dict:
    """
    Export CVs that meet quality threshold to designated folder.

    Args:
        results: List of processing results
        threshold: Minimum RL reward score
        output_dir: Destination folder for high-quality CVs

    Returns:
        Export statistics dict
    """
    os.makedirs(output_dir, exist_ok=True)

    # Filter high-quality CVs
    high_quality = [r for r in results if r["success"] and r["rl_reward"]["reward"] >= threshold]

    export_stats = {
        "total_cvs": len(results),
        "successful": len([r for r in results if r["success"]]),
        "exported": 0,
        "threshold": threshold,
        "output_dir": output_dir,
        "exported_files": []
    }

    # Copy files
    for result in high_quality:
        src_path = result["pdf_path"]
        filename = result["filename"]
        score = result["rl_reward"]["reward"]
        grade = result["rl_reward"]["grade"]

        # Create descriptive filename
        name_parts = filename.rsplit(".", 1)
        new_filename = f"{name_parts[0]}_score{score:.3f}_{grade}.{name_parts[1]}"
        dst_path = os.path.join(output_dir, new_filename)

        # Copy file
        shutil.copy2(src_path, dst_path)

        export_stats["exported"] += 1
        export_stats["exported_files"].append({
            "original": filename,
            "exported_as": new_filename,
            "score": score,
            "grade": grade
        })

    # Save export manifest
    manifest_path = os.path.join(output_dir, "export_manifest.json")
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(export_stats, f, indent=2, ensure_ascii=False)

    print(f"\n📁 Exported {export_stats['exported']} high-quality CVs to: {output_dir}")
    print(f"   Threshold: ≥{threshold:.2f}")
    print(f"   Manifest saved to: {manifest_path}")

    return export_stats


def generate_evaluation_report(
    results: List[Dict],
    output_dir: str = "evaluation_results"
) -> Dict:
    """
    Generate comprehensive evaluation report.

    Args:
        results: List of processing results
        output_dir: Output directory

    Returns:
        Summary statistics dict
    """
    os.makedirs(output_dir, exist_ok=True)

    # Filter successful results
    successful_results = [r for r in results if r["success"]]
    failed_results = [r for r in results if not r["success"]]

    # Extract RL rewards
    rl_rewards = [r["rl_reward"] for r in successful_results if r["rl_reward"]]

    # Calculate bulk statistics
    bulk_stats = enhanced_metrics.calculate_bulk_statistics(rl_rewards)

    # Create detailed table data
    table_data = []
    for r in successful_results:
        table_data.append({
            "Filename": r["filename"],
            "Candidate": r["candidate_name"],
            "RL_Score": r["rl_reward"]["reward"],
            "Grade": r["rl_reward"]["grade"],
            "Base_Score": r["base_metrics"]["overall_score"],
            "Processing_Time": f"{r['processing_time']:.1f}s"
        })

    # Sort by RL score
    table_data.sort(key=lambda x: x["RL_Score"], reverse=True)

    # Generate report
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "agent": "Hybrid_Auditor",
        "total_cvs": len(results),
        "successful": len(successful_results),
        "failed": len(failed_results),
        "success_rate": len(successful_results) / len(results) if results else 0,
        "bulk_statistics": bulk_stats,
        "cv_scores": table_data,
        "failed_files": [{"filename": r["filename"], "error": r["error"]} for r in failed_results]
    }

    # Save detailed results
    detailed_output = os.path.join(output_dir, "detailed_results.json")
    with open(detailed_output, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Save summary report
    summary_output = os.path.join(output_dir, "summary_report.json")
    with open(summary_output, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # Save CSV table
    csv_output = os.path.join(output_dir, "scores_table.csv")
    df = pd.DataFrame(table_data)
    df.to_csv(csv_output, index=False)

    # Print summary
    print(f"\n{'='*70}")
    print(f"📊 PRE-RL BASELINE EVALUATION SUMMARY")
    print(f"{'='*70}")
    print(f"Agent:            Hybrid_Auditor")
    print(f"Total CVs:        {report['total_cvs']}")
    print(f"Successful:       {report['successful']}")
    print(f"Failed:           {report['failed']}")
    print(f"Success Rate:     {report['success_rate']:.1%}")
    print(f"\n🎯 RL Reward Statistics:")
    print(f"Mean Reward:      {bulk_stats['mean_reward']:.4f}")
    print(f"Median Reward:    {bulk_stats['median_reward']:.4f}")
    print(f"Std Dev:          {bulk_stats['std_reward']:.4f}")
    print(f"Min Reward:       {bulk_stats['min_reward']:.4f}")
    print(f"Max Reward:       {bulk_stats['max_reward']:.4f}")
    print(f"Passing Rate:     {bulk_stats['passing_rate']:.1%} (≥0.80)")
    print(f"\n📁 Results saved to:")
    print(f"   Detailed:      {detailed_output}")
    print(f"   Summary:       {summary_output}")
    print(f"   CSV Table:     {csv_output}")
    print(f"{'='*70}\n")

    # Print top 5 and bottom 5
    if len(table_data) >= 5:
        print("🏆 Top 5 Performers:")
        for i, cv in enumerate(table_data[:5], 1):
            print(f"   {i}. {cv['Candidate'][:30]:30s} | Score: {cv['RL_Score']:.4f} ({cv['Grade']})")

        print("\n⚠️  Bottom 5 Performers:")
        for i, cv in enumerate(table_data[-5:], 1):
            print(f"   {i}. {cv['Candidate'][:30]:30s} | Score: {cv['RL_Score']:.4f} ({cv['Grade']})")
        print()

    return report


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Pre-RL Baseline Evaluation with Visualization")
    parser.add_argument("--cv-dir", type=str, required=True,
                        help="Directory containing CV PDFs")
    parser.add_argument("--workers", type=int, default=3,
                        help="Number of parallel workers (default: 3)")
    parser.add_argument("--output-dir", type=str, default="evaluation_results",
                        help="Output directory for results (default: evaluation_results)")
    parser.add_argument("--export-threshold", type=float, default=0.90,
                        help="Minimum score to export CV for RL training (default: 0.90)")
    parser.add_argument("--rl-cv-dir", type=str, default="rl_training_cvs",
                        help="Directory to export high-quality CVs (default: rl_training_cvs)")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limit number of CVs to process")
    parser.add_argument("--no-export", action="store_true",
                        help="Skip exporting CVs to RL training folder")

    args = parser.parse_args()

    # Initialize Gemini
    print("🔧 Initializing Gemini API...")
    if not init_gemini():
        print("❌ Failed to initialize Gemini. Check API key configuration.")
        return

    print("✅ Gemini initialized\n")

    # Find all PDFs
    cv_dir = Path(args.cv_dir)
    pdf_files = sorted(cv_dir.glob("*.pdf"))

    if args.limit:
        pdf_files = pdf_files[:args.limit]

    if not pdf_files:
        print(f"❌ No PDF files found in {args.cv_dir}")
        return

    print(f"📂 Found {len(pdf_files)} PDF files in {args.cv_dir}")
    print(f"🤖 Using agent: Hybrid_Auditor")
    print(f"⚙️  Parallel workers: {args.workers}")
    print(f"📊 Export threshold: ≥{args.export_threshold:.2f}\n")

    # Process batch
    results = process_cv_batch(
        [str(pdf) for pdf in pdf_files],
        max_workers=args.workers
    )

    # Generate report
    summary = generate_evaluation_report(results, args.output_dir)

    # Generate visualization
    generate_score_chart(results, args.output_dir)

    # Export high-quality CVs
    if not args.no_export:
        export_stats = export_high_quality_cvs(
            results,
            threshold=args.export_threshold,
            output_dir=args.rl_cv_dir
        )

    print("\n✅ Pre-RL baseline evaluation complete!")
    print(f"\n💡 Next steps:")
    print(f"   1. Review the score chart: {args.output_dir}/pre_rl_scores_chart.png")
    print(f"   2. Check the CSV table: {args.output_dir}/scores_table.csv")
    if not args.no_export:
        print(f"   3. High-quality CVs ready for RL: {args.rl_cv_dir}/")
        print(f"   4. Use these CVs for your RL training session")


if __name__ == "__main__":
    main()
