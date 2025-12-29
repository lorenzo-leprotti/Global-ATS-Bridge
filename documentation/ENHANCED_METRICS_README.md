# Enhanced Metrics System for RL Training

## Overview

This enhanced metrics system provides a comprehensive, differentiable reward function for evaluating CV extraction quality. It's designed to support your full ML pipeline: **Baseline → RL Training → Fine-tuning**.

## Architecture

### 3-Tier Scoring System

```
┌─────────────────────────────────────────────────────────────┐
│  TIER 1: Hard Constraints (Pass/Fail)                       │
│  - JSON validity, schema compliance, no truncation          │
│  - If failed: reward = 0.0, stop evaluation                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  TIER 2: Base Quality Metrics (60% weight)                  │
│  - Bullet preservation, JSON integrity, phantom detection   │
│  - Structural compliance, translation quality, etc.         │
│  - From existing metrics.py                                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  TIER 3: Enhanced Semantic Metrics (40% weight)             │
│  - Entity preservation (dates, numbers) - 8%                │
│  - Information density - 7%                                  │
│  - Action verb quality - 5%                                  │
│  - ATS compliance - 15%                                      │
│  - Temporal consistency - 5%                                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
                    RL REWARD SCORE
                    (0.0 - 1.0)
```

## Components

### 1. `enhanced_metrics.py`

Core module with advanced metrics:

- **`check_hard_constraints()`** - Binary pass/fail checks
- **`calculate_entity_preservation()`** - Preserves dates, numbers, emails, phones
- **`calculate_information_density()`** - Detects over-compression or hallucination
- **`calculate_action_verb_quality()`** - Measures professional CV language
- **`calculate_ats_compliance_score()`** - ATS-friendliness checks
- **`calculate_rl_reward()`** - Main reward function (combines all metrics)
- **`calculate_bulk_statistics()`** - Aggregate stats for bulk runs
- **`compare_model_outputs()`** - Compare baseline vs improved models

### 2. Updated `app.py`

Streamlit interface now shows:

- **Individual CV Testing**: RL Reward displayed prominently at top
- **Expandable Details**: Base metrics + enhanced metrics in sub-sections
- **Admin Dashboard**: Bulk session averages displayed first with:
  - Mean/Median/Min/Max reward
  - Grade distribution chart
  - Component-wise averages
  - Passing rate (% scoring ≥0.80)

### 3. `bulk_evaluation.py`

Command-line tool for processing 100+ CVs:

```bash
# Process 100 CVs with Hybrid_Auditor agent
python bulk_evaluation.py \
  --cv-dir test_cvs \
  --agent Hybrid_Auditor \
  --workers 3 \
  --output-dir baseline_results

# Compare with baseline
python bulk_evaluation.py \
  --cv-dir test_cvs \
  --agent Hybrid_Auditor_RL \
  --workers 3 \
  --output-dir rl_results \
  --compare-with baseline_results/Hybrid_Auditor_summary.json
```

## Usage

### Step 1: Baseline Evaluation (Current Model)

```bash
# Process all CVs in test_cvs folder
python bulk_evaluation.py \
  --cv-dir test_cvs \
  --agent Hybrid_Auditor \
  --workers 3 \
  --output-dir baseline_results
```

**Output:**
- `baseline_results/Hybrid_Auditor_detailed_results.json` - Full results for each CV
- `baseline_results/Hybrid_Auditor_summary.json` - Aggregate statistics

**Example Summary:**
```json
{
  "agent_name": "Hybrid_Auditor",
  "total_cvs": 100,
  "successful": 98,
  "failed": 2,
  "success_rate": 0.98,
  "bulk_statistics": {
    "mean_reward": 0.8534,
    "median_reward": 0.8612,
    "std_reward": 0.0891,
    "min_reward": 0.6234,
    "max_reward": 0.9678,
    "passing_rate": 0.82,
    "grade_distribution": {
      "A+": 5,
      "A": 18,
      "A-": 23,
      "B+": 28,
      "B": 16,
      "B-": 6,
      "C": 2
    },
    "component_averages": {
      "base_overall": 0.8421,
      "entity_preservation": 0.9123,
      "information_density": 0.8734,
      "action_verb_quality": 0.7456,
      "ats_compliance": 0.9234
    }
  }
}
```

### Step 2: RL Training (Next Phase)

After baseline evaluation, you can:

1. **Export training data** from Admin Dashboard
2. **Train RL model** using rewards as supervision signal
3. **Re-evaluate** with RL-trained model
4. **Compare** improvements

```bash
# Evaluate RL-trained model
python bulk_evaluation.py \
  --cv-dir test_cvs \
  --agent Hybrid_Auditor_RL \
  --workers 3 \
  --output-dir rl_results \
  --compare-with baseline_results/Hybrid_Auditor_summary.json
```

**Comparison Output:**
```
🔄 AGENT COMPARISON
============================================================
Baseline:         Hybrid_Auditor
Improved:         Hybrid_Auditor_RL

Mean Reward:
  Baseline:       0.8534
  Improved:       0.8923
  Delta:          +0.0389 (+4.56%)

Passing Rate:
  Baseline:       82.0%
  Improved:       91.0%

Verdict:          IMPROVED
```

### Step 3: Fine-tuning with Vertex AI (Final Phase)

After RL training, fine-tune on Vertex AI:

1. Export high-quality samples (reward ≥ 0.90)
2. Create fine-tuning dataset
3. Fine-tune Gemini model on Vertex AI
4. Re-evaluate and compare

## Viewing Results in App

### Individual CV Testing

1. Upload CV in Tournament Mode
2. See **RL Reward Score** prominently displayed at top
3. Expand "Detailed Metrics Breakdown" to see:
   - Base metrics (8 metrics from metrics.py)
   - Enhanced RL Metrics (4 advanced metrics)
   - Component contributions breakdown

### Admin Dashboard

1. Navigate to "📊 Admin Dashboard"
2. **First section**: RL Reward Statistics (Bulk Average)
   - See mean/median/min/max across all processed CVs
   - Grade distribution chart
   - Component-wise averages in expandable section
3. View individual session performance
4. Export training data for RL

## Metric Weights (Configurable)

Current weight distribution in `enhanced_metrics.py`:

```python
weights = {
    "base_overall": 0.60,           # Existing 8 metrics
    "entity_preservation": 0.08,    # Dates, numbers preserved
    "information_density": 0.07,    # No over-compression
    "action_verb_quality": 0.05,    # Professional language
    "ats_compliance": 0.15          # ATS-friendliness
}
```

**To adjust weights**: Edit `enhanced_metrics.py` line 330-337

## Interpreting Scores

### Reward Grades

- **A+ (0.97-1.00)**: Exceptional - perfect extraction
- **A (0.93-0.96)**: Excellent - production ready
- **A- (0.90-0.92)**: Very good - minor issues
- **B+ (0.87-0.89)**: Good - acceptable for most use cases
- **B (0.83-0.86)**: Satisfactory - needs improvement
- **B- (0.80-0.82)**: Marginal - significant issues
- **C+ & below**: Failing - major problems

### Passing Threshold

- **≥ 0.80**: Considered "passing" for production use
- **< 0.80**: Requires investigation and improvement

## Common Issues & Solutions

### Low Entity Preservation Score

**Symptom**: Dates, numbers missing from output

**Solution**:
- Check if PDF has poor OCR quality
- Verify extraction prompt captures all content
- Increase max_output_tokens to avoid truncation

### Low Information Density

**Symptom**: Score < 0.70 or > 1.30

**Solution**:
- < 0.70: Model is over-compressing (summarizing too much)
- \> 1.30: Model is hallucinating or adding content
- Review prompt to emphasize 1:1 mapping

### Low Action Verb Quality

**Symptom**: Weak ratio > 30%

**Solution**:
- Prompt emphasizes passive language preservation
- May need RL training to encourage stronger verbs
- Check if original CV uses weak language

### Low ATS Compliance

**Symptom**: Missing required fields or structure

**Solution**:
- Verify schema compliance
- Check section order (Summary → Experience → Education → Skills)
- Ensure all contact fields present

## Next Steps: RL Training Pipeline

### Phase 1: Data Collection (Current)
- ✅ Run baseline evaluation on 100+ CVs
- ✅ Generate reward scores for each CV
- ✅ Identify high-quality samples (reward ≥ 0.90)

### Phase 2: RL Training
- Use rewards as supervision signal
- Train policy to maximize RL reward
- Focus on improving low-scoring components
- **Target**: +5-10% mean reward improvement

### Phase 3: Fine-tuning (Vertex AI)
- Export top-performing samples
- Create fine-tuning dataset
- Fine-tune Gemini on Vertex AI
- **Target**: Consistent 0.90+ scores

### Phase 4: Production Deployment
- Deploy fine-tuned model
- Monitor production metrics
- Continuous improvement cycle

## Files Created

1. **`enhanced_metrics.py`** - Core metrics module
2. **`bulk_evaluation.py`** - Bulk processing script
3. **`app.py`** - Updated with RL reward display
4. **`ENHANCED_METRICS_README.md`** - This documentation

## Questions?

For issues or questions:
- Check debug output from bulk_evaluation.py
- Review individual CV results in detailed_results.json
- Inspect Admin Dashboard for trends
- Adjust weights in enhanced_metrics.py as needed

**Key Insight**: The RL reward is a comprehensive, differentiable signal that balances extraction fidelity (60%), semantic quality (25%), and business value (15%). This gives you a single metric to optimize during RL training and fine-tuning.
