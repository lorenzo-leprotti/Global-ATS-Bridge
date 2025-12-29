# Global ATS Bridge - Quick Commands Reference

## 🚀 **Running the Application**

### Start Streamlit App
```bash
streamlit run app.py
```

### Run in Production Mode (Optimized)
```bash
streamlit run app.py --server.headless true --server.port 8501
```

---

## 🧪 **Testing & Development**

### Run Test Suite
```bash
cd tests
python test_prompts.py
```

### Generate Test CVs
```bash
cd tests
python pdf_generator_script.py
```

### Clear Test Outputs
```bash
rm tests/debug_raw_response.txt
rm tests/test_output_*.json
rm tests/test_metrics_report.json
```

---

## 📊 **Data Management**

### View Training Data
```bash
cat data/training_data.jsonl | jq '.'
```

### Count Total Samples
```bash
wc -l < data/training_data.jsonl
```

### Export Training Data (Last 10 Samples)
```bash
tail -n 10 data/training_data.jsonl > recent_samples.jsonl
```

### Backup Training Data
```bash
cp data/training_data.jsonl data/training_data_backup_$(date +%Y%m%d).jsonl
```

### Clear Training Data (Fresh Start)
```bash
rm data/training_data.jsonl
touch data/training_data.jsonl
```

---

## 📈 **Metrics & Analysis**

### View Comprehensive Metrics for Last Sample
```bash
tail -n 1 data/training_data.jsonl | jq '.comprehensive_metrics'
```

### Count Agent Wins
```bash
cat data/training_data.jsonl | jq -r '.selected_variant' | sort | uniq -c
```

### Get Average Overall Score
```bash
cat data/training_data.jsonl | jq -s 'map(.comprehensive_metrics.overall_score) | add / length'
```

### Find Failed Validations (GPA Errors)
```bash
cat data/training_data.jsonl | jq 'select(.validation_report.valid == false)'
```

### Find Truncation Issues
```bash
cat data/training_data.jsonl | jq 'select(.comprehensive_metrics.metrics.completeness_check.total_truncated > 0)'
```

---

## 🔧 **Environment & Dependencies**

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Update Dependencies
```bash
pip install --upgrade streamlit google-generativeai reportlab
pip freeze > requirements.txt
```

### Check Installed Versions
```bash
pip list | grep -E "streamlit|google|reportlab"
```

### Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# OR
venv\Scripts\activate  # Windows
```

---

## 🗂️ **Git Operations**

### Initial Commit (Clean Repo)
```bash
git add app.py prompts.py metrics.py requirements.txt README.md
git add data/grading_standards.json
git add .gitignore
git commit -m "Initial commit: Global ATS Bridge MVP"
```

### Commit Data Updates
```bash
git add data/training_data.jsonl
git commit -m "Update training data: $(wc -l < data/training_data.jsonl) samples"
```

### Commit Prompt Improvements
```bash
git add prompts.py
git commit -m "Update prompts: Anti-lazy policy + mirror-translation rules"
```

### View Git Status
```bash
git status
```

---

## 🐛 **Debugging**

### Check API Key
```bash
echo $GOOGLE_API_KEY
# OR
cat .streamlit/secrets.toml
```

### Test Gemini API Connection
```bash
python -c "import google.generativeai as genai; genai.configure(api_key='YOUR_KEY'); print('✅ API Connected')"
```

### View Streamlit Logs
```bash
streamlit run app.py --logger.level debug
```

### Check File Permissions
```bash
ls -la data/
ls -la tests/
```

---

## 📦 **Deployment**

### Deploy to Streamlit Cloud
1. Push code to GitHub
2. Go to https://share.streamlit.io
3. Connect GitHub repo
4. Add `GOOGLE_API_KEY` to Secrets
5. Deploy!

### Local Production Server
```bash
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

---

## 🧹 **Cleanup**

### Remove All Cache
```bash
rm -rf .streamlit/cache
rm -rf __pycache__
rm -rf tests/__pycache__
rm -rf venv
```

### Remove Test Artifacts
```bash
rm tests/debug_raw_response.txt
rm tests/test_output_*.json
rm test_*.json
```

### Full Reset (DANGER!)
```bash
# Backup first!
cp -r data/ data_backup/

# Then reset
rm data/training_data.jsonl
rm -rf __pycache__
touch data/training_data.jsonl
```

---

## 🔍 **Quick Diagnostics**

### Check Project Structure
```bash
tree -I 'venv|__pycache__|*.pyc|.DS_Store' -L 2
```

### Verify All Core Files
```bash
ls -1 app.py prompts.py metrics.py requirements.txt README.md
ls -1 data/grading_standards.json
```

### Count Lines of Code
```bash
wc -l app.py prompts.py metrics.py
```

### Search for TODOs
```bash
grep -rn "TODO\|FIXME\|HACK" app.py prompts.py metrics.py
```

---

## 💡 **Pro Tips**

### Run App in Background
```bash
nohup streamlit run app.py > streamlit.log 2>&1 &
```

### Monitor Real-Time Logs
```bash
tail -f streamlit.log
```

### Quick Restart
```bash
pkill -f streamlit && streamlit run app.py
```

### Format Python Code
```bash
black app.py prompts.py metrics.py
```

### Lint Code
```bash
pylint app.py prompts.py metrics.py
```

---

## 📚 **Documentation**

### Generate API Docs
```bash
pydoc -w app prompts metrics
```

### View Module Help
```bash
python -c "import prompts; help(prompts.AGENT_PROMPTS)"
python -c "import metrics; help(metrics.run_all_metrics)"
```

---

## 🎯 **Quick Workflows**

### Daily Development Loop
```bash
# 1. Pull latest
git pull

# 2. Start app
streamlit run app.py

# 3. Test changes
cd tests && python test_prompts.py

# 4. Commit improvements
git add . && git commit -m "Feature: <description>"
git push
```

### Before Presenting to VP
```bash
# 1. Run full test suite
cd tests && python test_prompts.py

# 2. Check metrics health
cat data/training_data.jsonl | jq -s 'map(.comprehensive_metrics.overall_score) | add / length'

# 3. Verify no truncation issues
cat data/training_data.jsonl | jq 'select(.comprehensive_metrics.metrics.completeness_check.total_truncated > 0)' | wc -l

# 4. Start demo
streamlit run app.py
```

---

## ⚠️ **Emergency Commands**

### Kill Stuck Streamlit Process
```bash
pkill -9 -f streamlit
```

### Recover from Corrupted Training Data
```bash
# Backup
cp data/training_data.jsonl data/training_data_corrupted.jsonl

# Filter valid JSON lines only
cat data/training_data_corrupted.jsonl | jq -c '.' 2>/dev/null > data/training_data.jsonl
```

### Reset to Last Known Good State
```bash
git stash
git checkout main
git pull
```

---

**Last Updated:** Dec 22, 2024
**Version:** 3.0 (Gemini 3 Flash + Mirror-Fidelity)
