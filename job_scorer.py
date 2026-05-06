import json
import re
import os
import anthropic
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

CACHE_FILE = "score_cache.json"


# -------------------------------------------------------------------
# CACHE FUNCTIONS — avoid re-scoring same job twice
# -------------------------------------------------------------------
def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}


def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


# -------------------------------------------------------------------
# ATS SCORER — uses Haiku for speed and cost efficiency
# Haiku is 20x cheaper than Opus — perfect for scoring
# Quality scoring still maintained — just cheaper model
# -------------------------------------------------------------------
def score_job(job, profile, client):
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",  # 20x cheaper than Opus
        max_tokens=800,
        messages=[{
            "role": "user",
            "content": f"""You are an ATS (Applicant Tracking System) scoring engine,
mimicking how enterprise systems like Workday and Taleo rank candidates internally.

Score this candidate against the job using EXACTLY these 5 weighted categories.
Return ONLY raw JSON, no markdown, no backticks:

{{
  "total_score": 0,
  "breakdown": {{
    "hard_skills": {{
      "score": 0,
      "max": 40,
      "matched": [],
      "missing": []
    }},
    "job_title": {{
      "score": 0,
      "max": 25,
      "reasoning": ""
    }},
    "experience": {{
      "score": 0,
      "max": 20,
      "reasoning": ""
    }},
    "education": {{
      "score": 0,
      "max": 10,
      "reasoning": ""
    }},
    "contextual_keywords": {{
      "score": 0,
      "max": 5,
      "matched": []
    }}
  }},
  "ats_verdict": "",
  "top_gaps": []
}}

SCORING RULES:

HARD SKILLS (max 40 points):
- Exact keyword match = full points per skill
- Related or partial match = half points
- Missing required skill = 0
- Examples: SQL, Python, PowerBI, Tableau, Excel, R

JOB TITLE (max 25 points):
- Exact title match = 25
- Same family = 20
- Related title = 15
- Loosely related = 5
- Unrelated = 0

EXPERIENCE (max 20 points):
- Meets or exceeds required years = 20
- Within 1 year below = 15
- Within 2 years below = 10
- More than 2 years below = 0

EDUCATION (max 10 points):
- Exact field match = 10
- Related field = 7
- Different field same level = 4
- Lower degree = 2

CONTEXTUAL KEYWORDS (max 5 points):
- KPI, dashboard, stakeholder, reporting,
  data driven, cross-functional, agile, insights
- 1 point per match, max 5

ATS VERDICT:
- "STRONG MATCH" if total >= 80
- "GOOD MATCH"   if total >= 70
- "MODERATE MATCH" if total >= 55
- "WEAK MATCH"   if total < 55

Candidate:
- Years of experience: {profile['years_of_experience']}
- Skills: {', '.join(profile.get('skills', []))}
- Past titles: {', '.join(profile.get('job_titles', []))}
- Education: {profile.get('education', '')}

Job Title: {job.get('title')}
Company: {job.get('company_name')}
Description:
{job.get('description', '')[:2000]}"""
        }]
    )

    raw = response.content[0].text.strip()
    raw = re.sub(r"```json|```", "", raw).strip()
    result = json.loads(raw)
    result["job"] = job
    return result


# -------------------------------------------------------------------
# CACHED SCORER — skips Claude if job was scored in last 48 hours
# -------------------------------------------------------------------
def score_job_cached(job, profile, client):
    cache  = load_cache()
    job_id = job.get("job_id", "")

    # Check cache first
    if job_id and job_id in cache:
        cached_time = datetime.fromisoformat(cache[job_id]["cached_at"])
        if datetime.now() - cached_time < timedelta(hours=48):
            print(f"  💾 Cached: {job.get('title')} @ {job.get('company_name')}")
            result = cache[job_id]["result"]
            result["job"] = job  # always attach fresh job data
            return result

    # Not cached — score with Claude
    result = score_job(job, profile, client)

    # Save to cache (don't cache the job object — too large)
    cache_result = {k: v for k, v in result.items() if k != "job"}
    cache[job_id] = {
        "cached_at": datetime.now().isoformat(),
        "result":    cache_result
    }
    save_cache(cache)
    return result


# -------------------------------------------------------------------
# FILTER — only keep STRONG matches (score >= 80 by default)
# -------------------------------------------------------------------
def get_top_jobs(scored_jobs, min_score=80):
    strong = [j for j in scored_jobs if j.get("total_score", 0) >= min_score]
    return sorted(strong, key=lambda x: x["total_score"], reverse=True)


# -------------------------------------------------------------------
# PRETTY PRINT
# -------------------------------------------------------------------
def print_score_report(result):
    job = result["job"]
    b   = result.get("breakdown", {})

    print(f"\n{'='*55}")
    print(f"  {job.get('title')} @ {job.get('company_name')}")
    print(f"  ATS Verdict : {result.get('ats_verdict')}")
    print(f"  Total Score : {result.get('total_score')}/100")
    print(f"{'='*55}")
    print(f"  Hard Skills     {b.get('hard_skills',{}).get('score',0):>3}/40")
    print(f"    ✅ {', '.join(b.get('hard_skills',{}).get('matched',[]))}")
    print(f"    ❌ {', '.join(b.get('hard_skills',{}).get('missing',[]))}")
    print(f"  Job Title       {b.get('job_title',{}).get('score',0):>3}/25")
    print(f"    {b.get('job_title',{}).get('reasoning','')}")
    print(f"  Experience      {b.get('experience',{}).get('score',0):>3}/20")
    print(f"    {b.get('experience',{}).get('reasoning','')}")
    print(f"  Education       {b.get('education',{}).get('score',0):>3}/10")
    print(f"    {b.get('education',{}).get('reasoning','')}")
    print(f"  Contextual      {b.get('contextual_keywords',{}).get('score',0):>3}/5")
    print(f"    ✅ {', '.join(b.get('contextual_keywords',{}).get('matched',[]))}")
    if result.get("top_gaps"):
        print(f"  🔧 Gaps: {', '.join(result.get('top_gaps',[]))}")


# -------------------------------------------------------------------
# TEST
# -------------------------------------------------------------------
if __name__ == "__main__":
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    test_profile = {
        "name": "Hitankshi Jain",
        "years_of_experience": 4,
        "skills": ["Python", "R", "SQL", "Microsoft Suite", "PowerBI"],
        "job_titles": ["Business Analyst", "Business Analyst Intern"],
        "education": "MS Business Analytics, Drexel University"
    }

    test_jobs = [
        {
            "title": "Business Analyst",
            "company_name": "Capital One",
            "description": """Business Analyst with 3-5 years experience.
            Required: SQL, PowerBI, Excel, Python. MS in Business Analytics preferred.
            Build dashboards, analyze KPIs, work with stakeholders using agile.""",
            "job_id": "test_001",
            "job_type": "fulltime",
            "posted_at": "2026-04-24",
            "apply_options": [{"link": "https://capitalone.com/careers"}],
            "source": "test"
        }
    ]

    print("Testing scorer with Haiku + caching...\n")
    for job in test_jobs:
        print(f"Scoring: {job['title']} @ {job['company_name']}...")
        result = score_job_cached(job, test_profile, client)
        print_score_report(result)

    print("\nRunning again — should use cache:")
    for job in test_jobs:
        result = score_job_cached(job, test_profile, client)
        print(f"Score: {result['total_score']}/100")