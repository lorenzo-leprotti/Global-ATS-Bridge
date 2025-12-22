🌍 Global ATS Bridge
International CV Normalization & Precision Extraction Engine
Global ATS Bridge is a high-fidelity recruitment automation tool designed to bridge the gap between international candidate backgrounds and the US job market. It utilizes Gemini 2.5 Pro Vision to parse, translate, and reorder diverse CV formats into "US-Ready," ATS-optimized documents without sacrificing data integrity.

🎯 The Core Problem
International candidates often face "parsing rejection" due to:

Layout Complexity: Multi-column designs that traditional ATS cannot read.

Linguistic Drift: Loose translations of technical achievements.

Grading Variance: Non-standard academic scales (e.g., 110L/110 in Italy) that don't map to a US 4.0 GPA.

✨ Key Features
1. The "Mirror-Translation" Engine
Unlike general AI rewriters, our Hybrid Auditor performs a mirror-image translation. If the source has 5 bullets, the output has 5 bullets—ensuring 100% semantic fidelity from Portuguese, Italian, or French to English.

2. Deterministic Grading Repository
Integrates a verified JSON-based lookup table (WES/ECTS standards) to convert international grades.

Example: Original Grade: 110L/110 (US Equivalent: 4.0 GPA)

3. Multi-Agent Tournament System
Runs three specialized agents in parallel to determine the highest quality output:

Conservative: Verbatim extraction, zero modification.

Strategist: Optimized US context mapping.

Hybrid Auditor: The "Piana Standard"—structural optimization with mirror-fidelity.

4. Integrity Checksum & Metrics
Every transformation is audited by a custom metrics module that tracks:

Bullet Preservation: Ensuring 1:1 mapping of achievements.

Phantom Detection: Automatically omitting sections if no data exists.

Structural Compliance: Forcing the sequence: Summary → Experience → Education → Skills.

🛠️ Project Structure
Plaintext

├── app.py                # Streamlit UI & Tournament logic
├── prompts.py            # Systematic AI instructions & personas
├── metrics.py            # Quality Assurance & Checksum logic
├── grading_standards.json# Deterministic GPA mapping (WES/ECTS)
├── validated_examples.json# Few-shot "Golden Samples" for ICL
└── pdf_generator-script.py# High-variance CV generator for stress-testing
🚀 Getting Started
Prerequisites
Python 3.10+

Google Cloud Project with Gemini API access

Installation
Clone the repository:

Bash

git clone https://github.com/your-username/global-ats-bridge.git
cd global-ats-bridge
Set up virtual environment:

Bash

python -m venv venv
source venv/bin/activate  # Mac/Linux
# or .\venv\Scripts\activate on Windows
Install dependencies:

Bash

pip install -r requirements.txt
Set Environment Variable:

Bash

export GOOGLE_API_KEY="your_key_here"
Running the App
Bash

streamlit run app.py
📈 Roadmap
[x] Deterministic Grading Engine (Italy, India, France, Germany, etc.)

[x] Multi-Agent Tournament UI

[x] Mirror-Translation Logic

[ ] Phase 2: Integration with Microsoft Dynamics 365 ERP.

[ ] Phase 3: Reinforcement Learning from Human Feedback (RLHF) loop.

📄 License
Distributed under the MIT License. See LICENSE for more information.
