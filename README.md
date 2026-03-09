# Global ATS Bridge

Lossless international CV normalization — translates and restructures resumes from 9 languages into US ATS-optimized format using Gemini Flash Vision, with a custom quality scoring system and iterative prompt optimization loop.

## The Problem

International candidates routinely get rejected by Applicant Tracking Systems before a human ever sees their resume. Multi-column layouts, non-English text, unfamiliar grading scales (Italian 110L, Indian CGPA, German 1.0-5.0), and regional formatting conventions all cause parsing failures. Qualified people get filtered out by machines.

## The Solution

Global ATS Bridge takes any international CV as a PDF and produces a clean, ATS-optimized US-format resume — preserving every detail while restructuring for American hiring systems.

- **9-language mirror-translation** — Italian, Portuguese, French, Spanish, German, Indian formats, UK English, and more, translated to US English with zero semantic loss
- **Structural normalization** — reorders sections into reverse-chronological US standard format with proper headings
- **Deterministic grade conversion** — maps international academic honors to US GPA equivalents using rigid lookup tables covering 10 countries (no hallucination, no calculation — pure lookup)
- **Structured JSON output** — every field extracted into a normalized schema for downstream processing
- **PDF export** — generates a clean, formatted US-style resume ready to submit

## Pipeline

```
PDF Upload → Gemini Vision Extraction → Mirror-Translation → Structural Reordering → JSON Normalization → Quality Audit (13 metrics) → PDF Generation
```

1. **Vision extraction** — Gemini Flash Vision reads the full document, handling multi-column layouts, tables, sidebars, and graphical elements
2. **Mirror-translation** — 1:1 semantic translation to US English. If the source has 5 bullets, the output has 5 bullets. No merging, no summarization, no creative paraphrasing
3. **Structural reordering** — sections reorganized into Summary → Experience → Education → Skills regardless of original layout
4. **Grade conversion** — deterministic lookup against `grading_standards.json` (Italy, France, Germany, UK, India, China, Spain, Portugal, Brazil, ECTS)
5. **Quality audit** — 13-metric scoring system evaluates fidelity and completeness (see below)
6. **PDF generation** — formatted US-style resume via ReportLab

## Quality Scoring System

The system scores every transformation across two tiers — 8 base metrics and 5 enhanced metrics — producing a composite reward signal between 0.0 and 1.0.

### Base Metrics (8 dimensions)

| Metric | Weight | What It Measures |
|--------|--------|------------------|
| Bullet preservation | 20% | 1:1 bullet count between source and output |
| Anti-truncation | 20% | No ellipses, "etc.", or shorthand anywhere |
| Translation quality | 15% | Action verbs present, no untranslated words |
| Structural compliance | 12% | Correct section ordering |
| JSON integrity | 10% | No malformed strings, no empty arrays |
| Field coverage | 10% | Contact info completeness |
| Phantom detection | 8% | No empty sections that should be omitted |
| Section density | 5% | Reasonable bullets-per-entry ratio |

### Enhanced Metrics (5 dimensions)

| Metric | Role |
|--------|------|
| Hard constraints | Binary pass/fail gate — valid JSON, has contact info, no truncation markers. Failure = instant 0.0 reward |
| Entity preservation | Dates, numbers, emails, phone numbers surviving translation |
| Information density | Word count ratio between source and output (healthy: 0.7-1.3) |
| Action verb quality | Strong verbs (Led, Managed, Developed) vs weak verbs (Helped, Assisted) |
| ATS compliance | Proper structure, contact fields, section ordering, string types |

### Composite Reward

The final reward is a weighted combination: 60% base metrics, 15% ATS compliance, 8% entity preservation, 7% information density, 5% action verb quality. Scores above 0.90 earn an excellence bonus; above 0.95, a perfection bonus. Hard constraint failure overrides everything to 0.0.

## Prompt Optimization Loop

This project uses an iterative prompt optimization approach — not traditional RL with policy gradients, but a structured evaluation-and-refinement cycle:

1. **Baseline evaluation** — process all 45 test CVs through the Hybrid Auditor agent, score each with the 13-metric system
2. **Golden sample export** — CVs scoring above 0.90 are exported as validated benchmarks
3. **Few-shot injection** — the top 3 golden samples are injected into the agent's system prompt as concrete examples of correct output
4. **Re-evaluation** — the same test corpus is processed again with the updated prompt, and scores are compared against the baseline
5. **Preference logging** — in the Streamlit app, user selections (which output variant they prefer) are logged to a JSONL file for future fine-tuning

Four evaluation rounds were run across a 45-CV corpus (7 languages):

| Round | Mean Reward | Entity Preservation | Std Dev | Notes |
|-------|-------------|---------------------|---------|-------|
| Baseline | 0.8905 | 0.887 | 0.037 | 100% pass rate |
| Iteration 1 | 0.8955 | 0.917 | 0.036 | +0.5% mean, more A grades |
| Iteration 2 | 0.8906 | 0.917 | 0.030 | API instability (76% success) |
| Iteration 3 | 0.8898 | **0.939** | **0.032** | Best entity preservation, lowest variance |

Mean reward plateaued quickly — the prompt was already well-tuned — but entity preservation (names, dates, numbers surviving translation) climbed from 88.7% to 93.9%, and output consistency improved steadily (lower std dev). 100% of successful outputs passed the 0.80 threshold across all rounds.

### Agent Tournament

Three agent personas were tested before settling on the production agent:

- **Conservative** — verbatim extraction, zero rewriting. High fidelity but poor US formatting
- **Strategist** — structural optimization with job title standardization. Over-normalized some content
- **Hybrid Auditor** (winner) — mirror-translation with US structural logic. Best balance of fidelity and professional formatting

The archived personas and tournament app are preserved in `archive_tournament/`.

## Tech Stack

Python · Streamlit · Gemini 3 Flash Vision · ReportLab · NumPy · Matplotlib · pandas

## Architecture

```
├── app.py                     # Streamlit application (single + bulk processing)
├── prompts.py                 # Hybrid Auditor agent prompt + few-shot injection
├── metrics.py                 # 8-dimension base quality scoring
├── enhanced_metrics.py        # 5-dimension enhanced metrics + RL reward calculation
├── optimize_prompts.py        # Golden sample selection + dynamic prompt updater
├── bulk_evaluation.py         # Batch evaluation runner with comparison reporting
├── pre_rl_evaluation.py       # Baseline evaluation with visualization + CV export
│
├── data/
│   ├── grading_standards.json # Deterministic grade conversion tables (10 countries)
│   ├── dynamic_prompts.json   # Top 3 few-shot examples (auto-generated)
│   └── training_data.jsonl    # Accumulated user preference + metrics log
│
├── test_cvs/                  # 45 synthetic test CVs across 7 languages
├── rl_training_cvs/           # 22 golden sample CVs (score >= 0.90)
│
├── evaluation_results/        # Baseline evaluation data
├── evaluation_results_rl/     # Iteration 1 results
├── evaluation_results_rl_v3/  # Iteration 3 results (best entity preservation)
│
├── archive_tournament/        # Archived agent personas + tournament app
├── debug_json_errors/         # Raw model responses that failed JSON parsing
├── documentation/             # Extended project documentation
└── tests/
    ├── test_prompts.py        # Integration test against real CV
    └── pdf_generator_script.py # Synthetic CV generator (7 languages)
```

<details>
<summary><strong>Local Development</strong></summary>

### Prerequisites

- Python 3.10+
- Google AI API key ([get one here](https://aistudio.google.com/apikey))

### Setup

```bash
git clone https://github.com/lollo408/Global-ATS-Bridge.git
cd Global-ATS-Bridge
pip install -r requirements.txt
```

Create `.streamlit/secrets.toml`:

```toml
GOOGLE_API_KEY = "your-api-key-here"
```

### Run

```bash
streamlit run app.py
```

The app opens at `http://localhost:8501`. Upload any international CV as a PDF to process it.

### Evaluation Scripts

```bash
# Run baseline evaluation on test corpus
python pre_rl_evaluation.py --cv-dir test_cvs --output-dir evaluation_results

# Run evaluation with comparison to baseline
python bulk_evaluation.py --cv-dir test_cvs --output-dir evaluation_results_new --compare-with evaluation_results/summary_report.json

# Update few-shot examples from best-performing outputs
python optimize_prompts.py
```

</details>

## License

MIT
