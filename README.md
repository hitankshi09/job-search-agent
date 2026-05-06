# 🤖 Personalised Job Search Agent
### Built for F1 visa holders targeting Analytics roles in the USA

---

## ⚠️ Important — Who This Is Built For

This agent was built for a **very specific situation**. Before you clone it, make sure this matches you:

- 🎓 You are on an **F1 visa** (OPT/STEM OPT) in the USA
- 📊 You are targeting **Business/Data Analytics roles** — Business Analyst, Data Analyst, BI Analyst, Power BI Analyst, and similar
- 🛠 Your skills include some mix of **Python, SQL, Power BI, Tableau, Excel**
- 🚫 You need to **automatically filter out** jobs that require US citizenship or Green Card

If that's not you, the agent will still work — but the filters, scoring logic, and resume tailoring prompts are all tuned for this profile. You'll need to adjust them for your situation.

---

## What It Does

Most job search tools optimise for volume — apply more, hope more.

This one optimises for **fit**.

Here's the full pipeline, end to end:

```
Your Resume (PDF)
      ↓
Resume Parser       → Extracts your profile: skills, titles, years of experience
      ↓
Job Searcher        → Finds jobs posted in the last 48 hours via JSearch API
      ↓
Visa Filter         → Removes any job requiring US citizenship or Green Card
      ↓
ATS Scorer          → Scores each job across 5 categories (0–100) using Claude
      ↓
Resume Tailor       → Rewrites your resume for each strong match (score ≥ 80)
      ↓
LinkedIn Finder     → Finds the right person to reach out to at each company
      ↓
Outreach Generator  → Writes a personalised LinkedIn connection note per job
      ↓
Job Tracker         → Logs everything to Excel — scores, links, status, outreach
```

---

## Project Structure

```
job-agent/
├── main.py                  # Orchestrator — runs the full pipeline
├── resume_parser.py         # Reads your PDF resume, extracts structured profile
├── job_searcher.py          # Searches JSearch API for fresh jobs
├── job_scorer.py            # ATS scoring engine powered by Claude
├── resume_tailor.py         # Tailors resume per job using Claude
├── linkedin_finder.py       # Finds relevant LinkedIn contacts at each company
├── linkedin_helper.py       # LinkedIn outreach utilities
├── outreach_prep.py         # Generates personalised connection notes
├── job_tracker.py           # Tracks all applications in Excel
├── dashboard.py             # Summary dashboard for your job search
├── auto_apply.py            # Automation utilities
├── requirements.txt         # All dependencies
├── .env.example             # Template for your API keys
└── your_resume.pdf          # Drop your resume here (not included in repo)
```

---

## Setup

### 1. Clone the repo
```bash
git clone https://github.com/yourusername/job-agent.git
cd job-agent
```

### 2. Create a virtual environment
```bash
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set up your API keys

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Then fill in your keys:
```
ANTHROPIC_API_KEY=your-anthropic-api-key-here
JSEARCH_API_KEY=your-rapidapi-jsearch-key-here
```

- **Anthropic API key** → [console.anthropic.com](https://console.anthropic.com)
- **JSearch API key** → [rapidapi.com](https://rapidapi.com/search/jsearch) (free tier available)

### 5. Add your resume

Drop your resume as `your_resume.pdf` in the root folder.

### 6. Run the agent
```bash
python main.py
```

---

## What You Get After Each Run

- 📁 `tailored_resumes/` — up to 10 tailored PDFs, one per strong match
- 📊 `job_search_tracker.xlsx` — every job scored, ranked, with apply links
- 💬 Personalised LinkedIn outreach notes ready to copy-paste

---

## How the ATS Scoring Works

Each job is scored across **5 categories** using Claude:

| Category | What it checks |
|---|---|
| Skills Match | Do your technical skills match what they need? |
| Title Relevance | How close is your past experience to this role? |
| Experience Level | Does your years of experience fit the seniority? |
| Industry Fit | Have you worked in a relevant domain? |
| Education Match | Does your degree match their requirements? |

Only jobs scoring **80 or above** get a tailored resume generated. This keeps quality high and API costs low.

---

## Cost Per Run

This agent uses Claude claude-haiku-4-5 for scoring (fast + cheap) and Claude Sonnet for resume tailoring (higher quality). A typical daily run with 20 jobs scored and 10 resumes tailored costs approximately **$0.03 – $0.08**.

---

## Built By

**Hitankshi Jain**
Business Analyst @ Neuralix Inc. | MS Business Analytics, Drexel University

[LinkedIn](https://www.linkedin.com/in/hitankshijain/) • [GitHub](https://github.com/hitankshi09)

---

## A Note on Customisation

If you want to adapt this for your own profile, the main things to change are:

- `job_searcher.py` — the job title keywords and search queries
- `job_scorer.py` — the scoring criteria and weights
- `resume_tailor.py` — the tailoring prompt to match your background
- `main.py` — the `min_score` threshold (currently 80) and `max_tailored` limit (currently 10)

Everything else should work as-is.
