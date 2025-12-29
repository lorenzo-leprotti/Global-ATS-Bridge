# Quick Start Guide: Enhanced Metrics System

## 🚀 Quick Start (5 Minutes)

### Test Single CV with Enhanced Metrics

1. **Start the app**:
   ```bash
   streamlit run app.py
   ```

2. **Upload a CV** in Tournament Mode

3. **View RL Reward Score** - displayed prominently at top of each agent's results

4. **Expand details** to see:
   - Base metrics breakdown
   - Enhanced RL metrics
   - Component contributions

### Run Bulk Evaluation (100+ CVs)

```bash
# Basic usage
python bulk_evaluation.py --cv-dir test_cvs --agent Hybrid_Auditor --workers 3

# With comparison
python bulk_evaluation.py \
  --cv-dir test_cvs \
  --agent Hybrid_Auditor_V2 \
  --compare-with baseline_results/Hybrid_Auditor_summary.json
```

## 📊 View Results

### In Streamlit App

1. Go to **📊 Admin Dashboard** (sidebar)
2. **First thing you see**: RL Reward Statistics
   - Mean/Median/Min/Max
   - Grade distribution
   - Passing rate
3. Expand "Component-wise Averages" for detailed breakdown

### In Terminal

After bulk evaluation, you'll see:

```
📊 EVALUATION SUMMARY: Hybrid_Auditor
============================================================
Total CVs:        100
Successful:       98
Failed:           2
Success Rate:     98.0%

🎯 RL Reward Statistics:
Mean Reward:      0.8534
Median Reward:    0.8612
Std Dev:          0.0891
Min Reward:       0.6234
Max Reward:       0.9678
Passing Rate:     82.0% (≥0.80)
```

## 🎯 Optimization Strategy

### Current Baseline → RL Training → Fine-tuning

#### Step 1: Baseline (Week 1)
```bash
# Run 100 CVs with current best prompt
python bulk_evaluation.py --cv-dir test_cvs --agent Hybrid_Auditor --output-dir baseline

# Record mean reward (e.g., 0.8534)
```

#### Step 2: RL Training (Weeks 2-3)
- Use reward scores as supervision signal
- Train model to maximize RL reward
- Focus on weak components (check component_averages)

**Target**: +5-10% improvement → 0.90+ mean reward

#### Step 3: Fine-tuning (Weeks 4-5)
- Export high-quality samples (≥0.90 reward)
- Fine-tune on Vertex AI
- Re-evaluate

**Target**: Consistent 0.93+ mean reward

#### Step 4: Compare
```bash
python bulk_evaluation.py \
  --cv-dir test_cvs \
  --agent Hybrid_Auditor_FineTuned \
  --compare-with baseline/Hybrid_Auditor_summary.json
```

## 🔧 Troubleshooting

### "No RL reward data available"
- Make sure you're processing CVs with the updated app.py
- RL rewards are added automatically during processing

### JSON Parse Error
- Check `debug_raw_response.txt` and `debug_cleaned_response.txt`
- Increase `max_output_tokens` in bulk_evaluation.py (line 94)

### Low Scores Across Board
- Check individual component scores to identify weakness
- Review failed CVs in detailed_results.json
- Adjust prompt in prompts.py

## 📈 Success Metrics

### Production Ready
- Mean reward ≥ 0.90
- Passing rate ≥ 95%
- Max reward ≥ 0.96

### Acceptable
- Mean reward ≥ 0.85
- Passing rate ≥ 80%
- Few hard constraint failures

### Needs Improvement
- Mean reward < 0.85
- Passing rate < 80%
- Frequent JSON errors

## 💡 Pro Tips

1. **Start small**: Test with 10-20 CVs first to validate setup
2. **Monitor failures**: Check failed_files in summary.json
3. **Track trends**: Admin Dashboard shows trends over time
4. **Export data**: Use training_data.jsonl for RL training
5. **Adjust weights**: Fine-tune component weights based on your priorities

## 📁 Output Files

### After Bulk Evaluation
```
evaluation_results/
├── Hybrid_Auditor_summary.json       # Aggregate stats
├── Hybrid_Auditor_detailed_results.json  # Per-CV results
└── agent_comparison.json             # If using --compare-with
```

### In Streamlit App
```
data/
└── training_data.jsonl               # All processed CVs with rewards
```

## 🎓 Understanding the Score

Your RL reward combines:
- **60%** - Existing quality metrics (bullet preservation, JSON integrity, etc.)
- **8%** - Entity preservation (dates, numbers)
- **7%** - Information density (no over-compression)
- **5%** - Action verb quality (professional language)
- **15%** - ATS compliance (recruiter-friendly)

**Goal**: Optimize this single metric through RL → Fine-tuning

## Next: RL Training

Once you have baseline results:
1. Identify weak components (check component_averages)
2. Create RL training set focusing on those areas
3. Use reward as loss function
4. Re-evaluate and compare

**Expected improvement**: 0.85 → 0.92+ mean reward
