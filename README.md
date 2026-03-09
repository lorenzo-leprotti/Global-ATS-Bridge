# Global ATS Bridge

Lossless international CV normalization — translates and restructures resumes from 9 languages into US ATS-optimized format using Gemini Flash Vision and reinforcement learning.

## The Problem

International candidates routinely get rejected by Applicant Tracking Systems before a human ever sees their resume. Multi-column layouts, non-English text, unfamiliar grading scales (Italian 110L, Indian CGPA, German 1.0–5.0), and regional formatting conventions all cause parsing failures. Qualified people get filtered out by machines.

## The Solution

Global ATS Bridge takes any international CV as a PDF and produces a clean, ATS-optimized US-format resume — preserving every detail while restructuring for American hiring systems.

- **9-language mirror-translation** — Italian, Portuguese, French, Spanish, German, Indian formats, UK English, and more, translated to US English with zero semantic loss
- **Structural normalization** — reorders sections into reverse-chronological US standard format with proper headings
- **Deterministic grade conversion** — maps international academic honors to US GPA equivalents using rigid lookup tables (no hallucination)
- **Structured JSON output** — every field extracted into a normalized schema for downstream processing
- **PDF export** — generates a clean, formatted US-style resume ready to submit

## How It Works

1. **PDF upload** — user uploads an international CV through the Streamlit interface
2. **Vision extraction** — Gemini Flash Vision reads the full document, handling multi-column layouts, tables, and graphical elements
3. **Mirror-translation** — content is translated to US English while preserving the original meaning and technical terminology
4. **Structural reordering** — sections are reorganized into the US "Gold Standard" reverse-chronological format
5. **JSON normalization** — all data is extracted into a structured, validated JSON schema
6. **Quality audit** — an 8-metric scoring system evaluates the output for fidelity and completeness
7. **PDF generation** — a formatted US-style resume is produced via ReportLab

The system uses a **reinforcement learning reward loop**: validated "golden sample" CVs serve as few-shot benchmarks, and every transformation is scored against quality metrics. The reward signal drives prompt refinement over time.

## Supported Languages

Italian, Portuguese, French, Spanish, German, Indian regional formats, UK English, and additional European formats. Each language has dedicated handling for its specific conventions — date formats, grading scales, honorifics, and section ordering.

## Quality Metrics

Every transformation is scored across 8 dimensions:

- Bullet preservation rate
- Translation fidelity
- Structural compliance
- Section completeness
- Date format accuracy
- Grade conversion accuracy
- Contact info extraction
- Overall semantic retention

The aggregate score feeds an RL reward signal that validates prompt effectiveness against the golden sample benchmark set.

## Tech Stack

Python · Streamlit · Gemini Flash Vision · ReportLab

## Architecture

```
├── app.py                  # Streamlit application
├── prompts.py              # Agent personas and prompt engineering
├── metrics.py              # Quality scoring engine
├── enhanced_metrics.py     # RL reward system
├── optimize_prompts.py     # Prompt optimization pipeline
├── bulk_evaluation.py      # Batch evaluation runner
├── documentation/          # Extended project documentation
├── data/                   # Grade conversion tables and mappings
├── test_cvs/               # Test CV corpus
└── rl_training_cvs/        # Golden sample training set
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

</details>

## License

MIT
