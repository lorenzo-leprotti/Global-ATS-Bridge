#!/usr/bin/env python3
# bulk_evaluation.py
# Bulk CV evaluation script for baseline/RL/fine-tuned model comparison

import os
import json
import time
import argparse
from pathlib import Path
from typing import List, Dict
import warnings

# Suppress Gemini deprecation warning
warnings.filterwarnings("ignore", message="All support for the `google.generativeai` package has ended")

import google.generativeai as genai
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

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

def process_single_cv(
    pdf_path: str,
    agent_name: str,
    visa_status: str = "F-1 OPT (Stem)",
    max_retries: int = 3
) -> Dict:
    """
    Process a single CV with the specified agent.

    Args:
        pdf_path: Path to PDF file
        agent_name: Name of agent (Conservative, Strategist, Hybrid_Auditor)
        visa_status: User's visa status
        max_retries: Number of retry attempts

    Returns:
        dict with results and metrics
    """
    result = {
        "pdf_path": pdf_path,
        "filename": os.path.basename(pdf_path),
        "agent_name": agent_name,
        "success": False,
        "error": None,
        "result_json": None,
        "base_metrics": None,
        "rl_reward": None,
        "processing_time": 0
    }

    start_time = time.time()

    try:
        # 1. Upload PDF
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

        # 2. Generate response
        gen_config = genai.GenerationConfig(
            temperature=0.0,
            max_output_tokens=65536,  # Maximum supported - prevents truncation
            response_mime_type="application/json"
        )

        model = genai.GenerativeModel('gemini-3-flash-preview', generation_config=gen_config)

        # Get system prompt
        agent_instructions = prompts.get_agent_prompt(agent_name)
        system_prompt = f"{prompts.BASE_INSTRUCTIONS}\n\nSTYLE RULES FOR THIS AGENT:\n{agent_instructions}"

        response = model.generate_content([system_prompt, f"USER VISA: {visa_status}", gemini_file])

        # 3. Parse JSON
        raw_response = response.text
        clean_text = raw_response.replace("```json", "").replace("```", "").strip()
        result_json = json.loads(clean_text)

        result["result_json"] = result_json

        # 4. Extract original text for metrics
        extract_model = genai.GenerativeModel('gemini-3-flash-preview')
        extract_prompt = "Extract all text from this PDF exactly as written. Return only the raw text, no formatting."
        extract_response = extract_model.generate_content([extract_prompt, gemini_file])
        original_text = extract_response.text

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
    agent_name: str,
    max_workers: int = 3,
    visa_status: str = "F-1 OPT (Stem)"
) -> List[Dict]:
    """
    Process multiple CVs in parallel.

    Args:
        pdf_paths: List of PDF file paths
        agent_name: Name of agent to use
        max_workers: Number of parallel workers
        visa_status: Default visa status

    Returns:
        List of result dicts
    """
    results = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        futures = {
            executor.submit(process_single_cv, pdf_path, agent_name, visa_status): pdf_path
            for pdf_path in pdf_paths
        }

        # Process as they complete
        with tqdm(total=len(pdf_paths), desc=f"Processing with {agent_name}") as pbar:
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                pbar.update(1)

                # Log errors
                if not result["success"]:
                    print(f"  ❌ {result['filename']}: {result['error']}")

    return results


# ============================================================================
# EVALUATION & REPORTING
# ============================================================================

def generate_evaluation_report(
    results: List[Dict],
    agent_name: str,
    output_dir: str = "evaluation_results"
) -> Dict:
    """
    Generate comprehensive evaluation report from results.

    Args:
        results: List of processing results
        agent_name: Name of agent
        output_dir: Output directory for reports

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

    # Generate report
    report = {
        "agent_name": agent_name,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_cvs": len(results),
        "successful": len(successful_results),
        "failed": len(failed_results),
        "success_rate": len(successful_results) / len(results) if results else 0,
        "bulk_statistics": bulk_stats,
        "failed_files": [{"filename": r["filename"], "error": r["error"]} for r in failed_results]
    }

    # Save detailed results
    detailed_output = os.path.join(output_dir, f"{agent_name}_detailed_results.json")
    with open(detailed_output, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Save summary report
    summary_output = os.path.join(output_dir, f"{agent_name}_summary.json")
    with open(summary_output, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # Print summary
    print(f"\n{'='*60}")
    print(f"📊 EVALUATION SUMMARY: {agent_name}")
    print(f"{'='*60}")
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
    print(f"\n📁 Detailed results saved to: {detailed_output}")
    print(f"📁 Summary saved to: {summary_output}")
    print(f"{'='*60}\n")

    return report


def compare_agents(
    results_baseline: Dict,
    results_improved: Dict,
    output_dir: str = "evaluation_results"
) -> None:
    """
    Compare two agent evaluation results.

    Args:
        results_baseline: Summary report from baseline agent
        results_improved: Summary report from improved agent (RL/fine-tuned)
        output_dir: Output directory
    """
    baseline_stats = results_baseline["bulk_statistics"]
    improved_stats = results_improved["bulk_statistics"]

    improvement = improved_stats["mean_reward"] - baseline_stats["mean_reward"]
    improvement_pct = (improvement / baseline_stats["mean_reward"] * 100) if baseline_stats["mean_reward"] > 0 else 0

    comparison = {
        "baseline_agent": results_baseline["agent_name"],
        "improved_agent": results_improved["agent_name"],
        "baseline_mean_reward": baseline_stats["mean_reward"],
        "improved_mean_reward": improved_stats["mean_reward"],
        "absolute_improvement": improvement,
        "relative_improvement_pct": improvement_pct,
        "baseline_passing_rate": baseline_stats["passing_rate"],
        "improved_passing_rate": improved_stats["passing_rate"],
        "verdict": "IMPROVED" if improvement > 0.01 else "NEUTRAL" if improvement > -0.01 else "DEGRADED"
    }

    # Save comparison
    comparison_output = os.path.join(output_dir, "agent_comparison.json")
    with open(comparison_output, 'w', encoding='utf-8') as f:
        json.dump(comparison, f, indent=2, ensure_ascii=False)

    # Print comparison
    print(f"\n{'='*60}")
    print(f"🔄 AGENT COMPARISON")
    print(f"{'='*60}")
    print(f"Baseline:         {results_baseline['agent_name']}")
    print(f"Improved:         {results_improved['agent_name']}")
    print(f"\nMean Reward:")
    print(f"  Baseline:       {baseline_stats['mean_reward']:.4f}")
    print(f"  Improved:       {improved_stats['mean_reward']:.4f}")
    print(f"  Delta:          {improvement:+.4f} ({improvement_pct:+.2f}%)")
    print(f"\nPassing Rate:")
    print(f"  Baseline:       {baseline_stats['passing_rate']:.1%}")
    print(f"  Improved:       {improved_stats['passing_rate']:.1%}")
    print(f"\nVerdict:          {comparison['verdict']}")
    print(f"\n📁 Comparison saved to: {comparison_output}")
    print(f"{'='*60}\n")


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Bulk CV Evaluation for RL Training")
    parser.add_argument("--cv-dir", type=str, required=True, help="Directory containing CV PDFs")
    parser.add_argument("--agent", type=str, default="Hybrid_Auditor",
                        choices=["Conservative", "Strategist", "Hybrid_Auditor"],
                        help="Agent to use for processing")
    parser.add_argument("--workers", type=int, default=1, help="Number of parallel workers")
    parser.add_argument("--output-dir", type=str, default="evaluation_results",
                        help="Output directory for results")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of CVs to process")
    parser.add_argument("--compare-with", type=str, default=None,
                        help="Path to baseline summary.json for comparison")

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
    print(f"🤖 Using agent: {args.agent}")
    print(f"⚙️  Parallel workers: {args.workers}\n")

    # Process batch
    results = process_cv_batch(
        [str(pdf) for pdf in pdf_files],
        args.agent,
        max_workers=args.workers
    )

    # Generate report
    summary = generate_evaluation_report(results, args.agent, args.output_dir)

    # Compare with baseline if provided
    if args.compare_with:
        print(f"\n📊 Loading baseline results from {args.compare_with}...")
        try:
            with open(args.compare_with, 'r') as f:
                baseline_summary = json.load(f)
            compare_agents(baseline_summary, summary, args.output_dir)
        except Exception as e:
            print(f"❌ Failed to load baseline: {e}")

    print("\n✅ Bulk evaluation complete!")


if __name__ == "__main__":
    main()
