# Pre-RL Baseline Evaluation Guide

## Overview

The `pre_rl_evaluation.py` script is designed for running comprehensive baseline evaluations before RL training sessions. It processes CVs with the Hybrid_Auditor agent, generates detailed metrics, visualizations, and automatically filters high-quality CVs for your upcoming RL training.

## Features

✅ **Automated Processing**: Processes up to 30 (or any number) of CVs in parallel
✅ **Comprehensive Scoring**: Uses RL reward metrics to evaluate each CV
✅ **Visual Charts**: Generates bar charts showing CV names and scores
✅ **Automatic Filtering**: Exports high-quality CVs (score ≥ 0.80) to a dedicated RL training folder
✅ **CSV Export**: Creates a table with all CV scores for easy reference
✅ **Detailed Reports**: JSON summaries with bulk statistics

## Quick Start

### 1. Prepare Your CVs

Place all CVs in a directory, for example:
```bash
mkdir test_cvs
# Copy your 30 CVs into test_cvs/
```

### 2. Run the Evaluation

Basic command:
```bash
python pre_rl_evaluation.py --cv-dir test_cvs
```

With custom options:
```bash
python pre_rl_evaluation.py \
  --cv-dir test_cvs \
  --workers 5 \
  --export-threshold 0.85 \
  --output-dir my_evaluation_results \
  --rl-cv-dir my_rl_training_set
```

### 3. Review the Results

After processing, you'll find:

```
evaluation_results/
├── pre_rl_scores_chart.png      # Visual bar chart
├── scores_table.csv             # CSV with all scores
├── summary_report.json          # Aggregate statistics
└── detailed_results.json        # Full per-CV data

rl_training_cvs/
├── cv1_score0.876_A.pdf         # High-quality CVs
├── cv2_score0.823_B+.pdf
├── ...
└── export_manifest.json         # Export metadata
```

## Command-Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--cv-dir` | Directory containing CV PDFs **(required)** | - |
| `--workers` | Number of parallel processing threads | 3 |
| `--output-dir` | Output directory for results | `evaluation_results` |
| `--export-threshold` | Minimum RL score to export CV | 0.80 |
| `--rl-cv-dir` | Directory for high-quality CVs | `rl_training_cvs` |
| `--limit` | Limit number of CVs to process | None (all) |
| `--no-export` | Skip exporting CVs to RL folder | False |

## Understanding the Output

### Score Chart

The generated PNG chart shows:
- **Green bars**: A/A+ grade CVs (excellent)
- **Blue bars**: B/B+ grade CVs (good)
- **Orange bars**: C/C+ grade CVs (acceptable)
- **Red bars**: D/F grade CVs (needs improvement)
- **Red dashed line**: Passing threshold (0.80)

### CSV Table

Columns:
- `Filename`: Original PDF filename
- `Candidate`: Extracted candidate name
- `RL_Score`: RL reward score (0.0 - 1.0)
- `Grade`: Letter grade (A+ to F)
- `Base_Score`: Base metrics score
- `Processing_Time`: Time taken to process

### Summary Report

Key metrics:
- `mean_reward`: Average RL score across all CVs
- `median_reward`: Middle value
- `passing_rate`: Percentage of CVs scoring ≥ 0.80
- `grade_distribution`: Count of each grade

## Example Workflow

### For 30 CV Pre-RL Test

```bash
# 1. Run the evaluation
python pre_rl_evaluation.py --cv-dir test_cvs_30 --workers 5

# 2. Review the chart
open evaluation_results/pre_rl_scores_chart.png

# 3. Check the CSV for detailed scores
open evaluation_results/scores_table.csv

# 4. Use the high-quality CVs for RL training
ls rl_training_cvs/
```

### Adjust Threshold for Stricter Quality

If you want only the best CVs (score ≥ 0.90):

```bash
python pre_rl_evaluation.py \
  --cv-dir test_cvs_30 \
  --export-threshold 0.90 \
  --rl-cv-dir rl_premium_cvs
```

## Troubleshooting

### Issue: "No PDF files found"
- Ensure PDFs are directly in the specified directory
- Check file extensions are `.pdf` (lowercase)

### Issue: "API key missing"
- Check `.streamlit/secrets.toml` exists
- Verify `GOOGLE_API_KEY` is set

### Issue: Processing too slow
- Increase `--workers` (try 5-8 for faster processing)
- Reduce dataset with `--limit 10` for testing

### Issue: Too few CVs exported
- Lower `--export-threshold` (try 0.75 or 0.70)
- Check summary report to see score distribution

## Integration with RL Training

After running the pre-RL evaluation:

1. **Review Statistics**: Check `summary_report.json` for baseline metrics
2. **Select Training Set**: Use CVs in `rl_training_cvs/` folder
3. **Track Improvement**: Save summary report to compare post-RL results
4. **Iterate**: Re-run evaluation after RL to measure improvement

## Tips

- **Start Small**: Test with `--limit 5` first to verify everything works
- **Parallel Workers**: Don't exceed 8 workers (API rate limits)
- **Quality over Quantity**: Use `--export-threshold 0.85` for premium training data
- **Save Baselines**: Keep all `summary_report.json` files for comparison

## Support

If you encounter issues, check:
1. `debug_json_errors/` folder for JSON parsing errors
2. Console output for specific error messages
3. Verify API key and internet connection
