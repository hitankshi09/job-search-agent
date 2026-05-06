import requests
import os
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

JSEARCH_API_KEY = os.getenv("JSEARCH_API_KEY")

SKIP_KEYWORDS = [
    "us citizen", "us citizenship", "green card",
    "security clearance", "clearance required",
    "must be authorized", "no sponsorship",
    "active clearance", "secret clearance",
    "us persons only", "itar",
    "ts/sci", "poly clearance",      # ← add these
    "top secret", "must have clearance"  # ← add these
]

# Core analyst titles
CORE_TITLES = [
    "Business Analyst",
    "Data Analyst",
    "Operations Analyst",
    "Financial Analyst",
    "Reporting Analyst",
    "Business Intelligence Analyst",  
    "Product Analyst",                
]

# Multiple targeted queries for broader coverage
JSEARCH_QUERIES = [
    "Business Analyst SQL PowerBI USA",
    "Data Analyst Python Tableau USA",
    "Business Intelligence Analyst USA",
    "Operations Analyst contract USA",
    "Reporting Analyst finance healthcare USA",
]

# Job type priority order
TYPE_ORDER = {
    "contract":   0,
    "fulltime":   1,
    "temporary":  2,
    "freelance":  3,
    "parttime":   4,
    "internship": 5
}


# -------------------------------------------------------------------
# LAYER 1 — JSearch (multiple targeted queries)
# -------------------------------------------------------------------
def search_jsearch(profile, hours=24):
    """
    Runs multiple targeted queries on JSearch
    for broader market coverage.
    """
    profile_titles = profile.get("job_titles", [])
    all_titles     = list(dict.fromkeys(profile_titles + CORE_TITLES))
    date_filter    = "today" if hours <= 24 else "3days"

    headers = {
        "X-RapidAPI-Key":  JSEARCH_API_KEY,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
    }

    all_jobs = []
    seen_ids = set()

    # Build queries — profile titles + targeted queries
    queries = [
        f"{' OR '.join(all_titles)} USA"
    ] + JSEARCH_QUERIES

    print(f"  🔎 JSearch: running {len(queries)} queries...")

    for query in queries:
        params = {
            "query":       query,
            "page":        "1",
            "num_pages":   "2",
            "date_posted": date_filter,
            "country":     "us",
            "language":    "en"
        }

        try:
            resp = requests.get(
                "https://jsearch.p.rapidapi.com/search",
                headers=headers,
                params=params,
                timeout=10
            )

            if resp.status_code != 200:
                print(f"    ⚠️  JSearch error: {resp.status_code}")
                continue

            jobs = resp.json().get("data", [])
            new  = 0

            for job in jobs:
                job_id = job.get("job_id", "")
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)

                job_type_raw = (
                    job.get("job_employment_type") or ""
                ).lower()

                if "contract" in job_type_raw:
                    job_type = "contract"
                elif "temporary" in job_type_raw:
                    job_type = "temporary"
                elif "part" in job_type_raw:
                    job_type = "parttime"
                elif "intern" in job_type_raw:
                    job_type = "internship"
                elif "freelance" in job_type_raw:
                    job_type = "freelance"
                else:
                    job_type = "fulltime"

                all_jobs.append({
                    "title":         job.get("job_title"),
                    "company_name":  job.get("employer_name"),
                    "description":   job.get("job_description"),
                    "job_id":        job_id,
                    "posted_at":     job.get(
                        "job_posted_at_datetime_utc", ""
                    ),
                    "job_type":      job_type,
                    "location":      job.get("job_city", "USA"),
                    "apply_options": [{
                        "link":  job.get("job_apply_link"),
                        "title": "Direct Apply"
                    }],
                    "source": "jsearch"
                })
                new += 1

            print(f"    ✅ '{query[:40]}...' → {new} new jobs")
            time.sleep(1)  # be respectful to API

        except Exception as e:
            print(f"    ❌ Error: {e}")

    print(f"  📦 JSearch total: {len(all_jobs)} jobs\n")
    return all_jobs


# -------------------------------------------------------------------
# LAYER 2 — JobSpy (Indeed + Glassdoor + ZipRecruiter)
# -------------------------------------------------------------------
def search_jobspy(profile, hours=24):
    """
    Uses JobSpy to scrape Indeed and ZipRecruiter.
    No date filter here — applied_jobs.json tracker
    handles deduplication across runs instead.
    """
    try:
        from jobspy import scrape_jobs
    except ImportError:
        print("  ⚠️  JobSpy not installed. Run: pip install python-jobspy")
        return []

    profile_titles = profile.get("job_titles", [])
    all_titles     = list(dict.fromkeys(profile_titles + CORE_TITLES))
    all_jobs       = []
    seen_ids       = set()

    # Search top 3 most relevant titles
    search_titles = all_titles[:5]

    print("  🔎 JobSpy: searching Indeed + ZipRecruiter...")

    for title in search_titles:
        try:
            print(f"    Searching: '{title}'...")
            df = scrape_jobs(
                site_name      = ["indeed", "zip_recruiter"],
                search_term    = title,
                location       = "United States",
                results_wanted = 50,
                country_indeed = "USA"
            )

            if df is None or df.empty:
                print(f"    ⚠️  No results for '{title}'")
                continue

            new = 0
            for _, row in df.iterrows():
                # Create unique ID
                job_id = str(row.get("id", "")) or (
                    str(row.get("title", "")) +
                    str(row.get("company", ""))
                )

                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)

                # Get job type
                job_type_raw = str(
                    row.get("job_type", "") or ""
                ).lower()

                if "contract" in job_type_raw:
                    job_type = "contract"
                elif "temporary" in job_type_raw:
                    job_type = "temporary"
                elif "part" in job_type_raw:
                    job_type = "parttime"
                elif "intern" in job_type_raw:
                    job_type = "internship"
                else:
                    job_type = "fulltime"

                # Get location
                city  = str(row.get("location", "") or "USA")
                state = str(row.get("state", "") or "")
                loc   = f"{city}, {state}".strip(", ")

                # Get description
                desc = str(row.get("description", "") or "")

                # Get apply link
                link = str(row.get("job_url", "") or "")

                # Get posted date
                posted = ""
                if row.get("date_posted"):
                    posted = str(row["date_posted"])

                all_jobs.append({
                    "title":        str(row.get("title", "") or ""),
                    "company_name": str(row.get("company", "") or ""),
                    "description":  desc,
                    "job_id":       job_id,
                    "posted_at":    posted,
                    "job_type":     job_type,
                    "location":     loc,
                    "apply_options": [{"link": link, "title": "Direct"}],
                    "source":       str(row.get("site", "jobspy"))
                })
                new += 1

            print(f"    ✅ '{title}' → {new} new jobs")
            time.sleep(2)

        except Exception as e:
            print(f"    ❌ JobSpy error for '{title}': {e}")
            continue

    print(f"  📦 JobSpy total: {len(all_jobs)} jobs\n")
    return all_jobs


# -------------------------------------------------------------------
# DEDUPLICATE — across all sources combined
# -------------------------------------------------------------------
# Keywords that indicate a relevant analyst role
RELEVANT_KEYWORDS = [
    "business analyst", "data analyst", "operations analyst",
    "financial analyst", "reporting analyst", "analytics",
    "business intelligence", "bi analyst", "product analyst",
    "systems analyst", "strategy analyst", "insights analyst"
]

IRRELEVANT_KEYWORDS = [
    # Wrong analyst types
    "behavior analyst", "behavioural analyst",
    "security analyst", "cybersecurity analyst",
    "security operations", "security operations analyst",
    "tax analyst", "credit analyst",
    "malware analyst", 
    "imagery analyst", 
    "sustainability analyst",
    "institutional research", "food safety",
    "commercial products analyst",

    # Non-analyst roles
    "military", "army", "national guard",
    "store manager", "sales manager",
    "financial advisor", "product manager",
    "program manager", "category manager",
    "technical director", "director",
    "architect", "solutions consultant",
    "co-op", "coordinator", "specialist",
    "gtm", "devops", "software engineer",
    "data engineer", "machine learning engineer",
    "quality engineer", "requirement engineer",
    "marketing manager", "product marketing",
    "system integrator", "sales operations"
]

def is_relevant_job(job):
    """Quick free check — is this actually an analyst role we want?"""
    title = (job.get("title") or "").lower()

    # Skip if title contains irrelevant keywords
    if any(kw in title for kw in IRRELEVANT_KEYWORDS):
        return False

    # Keep if title contains relevant keywords
    if any(kw in title for kw in RELEVANT_KEYWORDS):
        return True

    # If title is unclear — check description for analyst keywords
    desc = (job.get("description") or "").lower()
    if any(kw in desc for kw in RELEVANT_KEYWORDS):
        return True

    # Nothing matched — skip it
    return False

def filter_old_jobs(jobs, days=7):
    """
    Remove jobs older than X days.
    Runs after collection — more reliable than JobSpy's hours_old.
    """
    from datetime import datetime, timedelta
    cutoff  = datetime.now() - timedelta(days=days)
    fresh   = []
    old_count = 0

    for job in jobs:
        posted = job.get("posted_at", "")
        if not posted:
            fresh.append(job)  # keep if no date
            continue

        try:
            # Handle different date formats
            posted_str = str(posted)[:10]  # take YYYY-MM-DD part
            posted_dt  = datetime.strptime(posted_str, "%Y-%m-%d")
            if posted_dt >= cutoff:
                fresh.append(job)
            else:
                old_count += 1
        except:
            fresh.append(job)  # keep if can't parse

    if old_count > 0:
        print(f"  📅 Removed {old_count} jobs older than {days} days")

    return fresh

def deduplicate(jobs):
    seen   = set()
    unique = []

    for job in jobs:
        # Use multiple fields to detect duplicates
        title   = (job.get("title") or "").lower().strip()
        company = (job.get("company_name") or "").lower().strip()
        job_id  = job.get("job_id") or f"{title}_{company}"

        # Also catch same job from different sources
        combo_key = f"{title}_{company}"

        if job_id in seen or combo_key in seen:
            continue

        seen.add(job_id)
        seen.add(combo_key)
        unique.append(job)

    return unique


# -------------------------------------------------------------------
# FILTER — visa restrictions + blank titles
# -------------------------------------------------------------------
def filter_jobs(jobs):
    filtered = []

    for job in jobs:
        desc    = (job.get("description") or "").lower()
        title   = (job.get("title") or "").strip()
        company = (job.get("company_name") or "").strip()

        if not title:
            continue
        
        # NEW — skip irrelevant roles
        if not is_relevant_job(job):
            print(f"    🚫 Irrelevant: {title} @ {company}")
            continue

        if any(kw in desc for kw in SKIP_KEYWORDS):
            print(f"    ⛔ Skipped (visa): {title} @ {company}")
            continue

        filtered.append(job)

    return filtered


# -------------------------------------------------------------------
# MAIN ENTRY — combines all sources
# -------------------------------------------------------------------
def search_jobs(profile, hours=24):
    print(f"\n{'='*55}")
    print(f"  JOB SEARCH — Fresh jobs from last {hours} hours")
    print(f"  Run time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*55}\n")

    all_jobs = []

    # Layer 1 — JSearch
    print("  📡 Layer 1: JSearch (Google Jobs aggregator)")
    jsearch_jobs = search_jsearch(profile, hours)
    all_jobs.extend(jsearch_jobs)

    # Layer 2 — JobSpy
    print("  📡 Layer 2: JobSpy (Indeed + Glassdoor + ZipRecruiter)")
    jobspy_jobs = search_jobspy(profile, hours)
    all_jobs.extend(jobspy_jobs)

    print(f"  📦 Combined raw total: {len(all_jobs)} jobs")

    # Remove old jobs first
    fresh_jobs = filter_old_jobs(all_jobs, days=14)

    # Deduplicate across all sources
    unique_jobs = deduplicate(fresh_jobs)
    print(f"  🔄 After deduplication: {len(unique_jobs)} jobs")

    # Filter visa restrictions
    print("\n  🔍 Filtering visa-restricted roles...")
    filtered = filter_jobs(unique_jobs)
    print(f"  ✅ Ready for scoring: {len(filtered)} jobs\n")

    # Sort by priority — contracts first
    filtered.sort(
        key=lambda x: TYPE_ORDER.get(x.get("job_type"), 99)
    )

    return filtered


# -------------------------------------------------------------------
# TEST
# -------------------------------------------------------------------
if __name__ == "__main__":
    test_profile = {
        "name":                "Hitankshi Jain",
        "years_of_experience": 4,
        "skills":              ["Python", "R", "SQL", "PowerBI", "Tableau"],
        "job_titles":          ["Business Analyst", "Data Analyst"],
        "education":           "MS Business Analytics, Drexel University"
    }

    print("Testing expanded job search...\n")
    jobs = search_jobs(test_profile, hours=24)

    print("\n--- Results ---")
    print(f"Total jobs found: {len(jobs)}\n")

    # Show source breakdown
    sources = {}
    for job in jobs:
        src = job.get("source", "unknown")
        sources[src] = sources.get(src, 0) + 1

    print("Source breakdown:")
    for src, count in sources.items():
        print(f"  {src}: {count} jobs")

    print("\nFirst 10 jobs:")
    for i, job in enumerate(jobs[:10]):
        print(f"\n[{i+1}] {job['title']} @ {job['company_name']}")
        print(f"     Type:    {job['job_type']}")
        print(f"     Source:  {job['source']}")
        print(f"     Posted:  {job['posted_at']}")
        print(f"     Apply:   {job['apply_options'][0]['link']}")