import json
from urllib.parse import quote
from dotenv import load_dotenv

load_dotenv()


# -------------------------------------------------------------------
# BUILD SMART LINKEDIN SEARCH URLS
# These open directly in LinkedIn with the right filters
# -------------------------------------------------------------------
def build_linkedin_urls(company, job_title):
    """
    Builds 3 targeted LinkedIn people search URLs.
    Opens directly in LinkedIn — uses their own search engine.
    """

    # Clean company name for URL
    company_clean = company.strip()

    # Priority 1 — Recruiters
    recruiter_query = f"{company_clean} recruiter talent acquisition"
    recruiter_url   = (
        f"https://www.linkedin.com/search/results/people/"
        f"?keywords={quote(recruiter_query)}"
        f"&origin=GLOBAL_SEARCH_HEADER"
    )

    # Priority 2 — Hiring managers / Senior roles
    manager_query = f"{company_clean} senior {job_title} manager analytics"
    manager_url   = (
        f"https://www.linkedin.com/search/results/people/"
        f"?keywords={quote(manager_query)}"
        f"&origin=GLOBAL_SEARCH_HEADER"
    )

    # Priority 3 — Same title peers
    peer_query = f"{company_clean} {job_title}"
    peer_url   = (
        f"https://www.linkedin.com/search/results/people/"
        f"?keywords={quote(peer_query)}"
        f"&origin=GLOBAL_SEARCH_HEADER"
    )

    return {
        "recruiter": {
            "label": "Recruiter / Talent Acquisition",
            "url":   recruiter_url
        },
        "manager": {
            "label": "Senior / Hiring Manager",
            "url":   manager_url
        },
        "peer": {
            "label": "Same Title / Peer",
            "url":   peer_url
        }
    }


# -------------------------------------------------------------------
# GENERATE SEARCH URLS FOR ALL TODAY'S JOBS
# Reads from applied_jobs.json → adds LinkedIn URLs
# -------------------------------------------------------------------
def prepare_linkedin_search(jobs_to_tailor):
    """
    Takes list of jobs that got tailored resumes today.
    Generates LinkedIn search URLs for each.
    Returns prepared outreach data.
    """
    outreach_data = []

    print(f"\n{'='*55}")
    print("  🔗 PHASE 2: LinkedIn Outreach Prep")
    print(f"{'='*55}\n")

    for i, job in enumerate(jobs_to_tailor):
        title   = job.get("title", "")
        company = job.get("company_name", "")

        print(f"  [{i+1}] {title} @ {company}")

        urls = build_linkedin_urls(company, title)

        print("       👔 Recruiter Search:")
        print(f"       {urls['recruiter']['url']}")
        print("       👤 Senior/Manager Search:")
        print(f"       {urls['manager']['url']}")
        print("       🤝 Peer Search:")
        print(f"       {urls['peer']['url']}\n")

        outreach_data.append({
            "job_id":      job.get("job_id", ""),
            "title":       title,
            "company":     company,
            "score":       job.get("total_score", 0),
            "search_urls": urls
        })

    # Save to file for linkedin_helper.py to use
    with open("outreach_prep.json", "w") as f:
        json.dump(outreach_data, f, indent=2)

    print("  ✅ Search URLs saved to outreach_prep.json")
    print("  💡 Now run: python linkedin_helper.py")
    print("     Paste profile URLs → get personalized DMs\n")

    return outreach_data


# -------------------------------------------------------------------
# TEST
# -------------------------------------------------------------------
if __name__ == "__main__":
    test_jobs = [
        {
            "job_id":       "test_001",
            "title":        "Business Analyst",
            "company_name": "Capital One",
            "total_score":  88
        },
        {
            "job_id":       "test_002",
            "title":        "Data Analyst",
            "company_name": "Deloitte",
            "total_score":  82
        }
    ]

    prepare_linkedin_search(test_jobs)