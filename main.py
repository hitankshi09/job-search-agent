import anthropic
import os
from dotenv import load_dotenv
from resume_parser import parse_resume, extract_profile
from job_searcher import search_jobs
from job_scorer import score_job_cached, get_top_jobs
from resume_tailor import (
    tailor_resume,
    save_as_pdf,
    make_filename,
    prepare_application_data
)
from job_tracker import filter_seen_jobs, mark_as_seen, update_excel, show_tracker_summary

load_dotenv()


def run_agent(
    resume_path  = "your_resume.pdf",
    min_score    = 80,    # strong matches only — no compromise
    max_tailored = 10,    # max 10 quality applications per day
    hours        = 48     # jobs from last 48 hours
):
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    print("\n" + "="*55)
    print("  🤖 HITANKSHI'S JOB SEARCH AGENT")
    print("  Powered by Claude")
    print("="*55)
    # Check if any LinkedIn follow-ups are due today
    from job_tracker import check_followups
    check_followups()
    print("\n  ⚙️  Settings:")
    print(f"     Min ATS score:   {min_score}/100 (strong matches only)")
    print(f"     Max resumes:     {max_tailored} per day")
    print(f"     Job freshness:   last {hours} hours")

    # -------------------------------------------
    # STEP 1 — Parse resume
    # -------------------------------------------
    print("\n📄 STEP 1: Reading your resume...")
    resume_text = parse_resume(resume_path)
    profile     = extract_profile(resume_text, client)

    print(f"  👤 Name:       {profile.get('name')}")
    print(f"  💼 Experience: {profile.get('years_of_experience')} years")
    print(f"  🛠  Skills:     {', '.join(profile.get('skills', [])[:5])}...")
    print(f"  📌 Titles:     {', '.join(profile.get('job_titles', []))}")

    # -------------------------------------------
    # STEP 2 — Search fresh jobs
    # -------------------------------------------
    print(f"\n🔍 STEP 2: Searching fresh jobs (last {hours} hours)...")
    jobs = search_jobs(profile, hours=hours)

    if not jobs:
        print("  ⚠️  No jobs found. Try increasing hours.")
        return

    # Remove jobs already seen in previous runs
    jobs = filter_seen_jobs(jobs)
    print(f"  ✅ Fresh unseen jobs: {len(jobs)}")

    if not jobs:
        print("  ⚠️  All jobs today were already seen before!")
        print("       Run again tomorrow for fresh postings.")
        update_excel()
        show_tracker_summary()
        return

    # -------------------------------------------
    # STEP 3 — Score all jobs (Haiku + cached)
    # -------------------------------------------
    print(f"\n📊 STEP 3: Scoring {len(jobs)} jobs...")
    print("  💡 Using Haiku model — fast and cost efficient")
    print("  💾 Cached results reused — no double billing\n")

    scored = []

    for i, job in enumerate(jobs):
        title   = job.get('title', '')
        company = job.get('company_name', '')
        try:
            result  = score_job_cached(job, profile, client)
            scored.append(result)
            score   = result.get('total_score', 0)
            verdict = result.get('ats_verdict', '')
            marker  = "🔥" if score >= 80 else "✅" if score >= 70 else "⬜"
            print(f"  {marker} [{i+1}/{len(jobs)}] "
                  f"{title} @ {company} → {score}/100")
        except Exception as e:
            print(f"  ⚠️  [{i+1}] Skipped {title}: {e}")

    # Summary
    strong = [j for j in scored if j.get('total_score', 0) >= 80]
    good   = [j for j in scored if 70 <= j.get('total_score', 0) < 80]
    weak   = [j for j in scored if j.get('total_score', 0) < 70]

    print("\n  📊 Scoring Summary:")
    print(f"     Total scored:         {len(scored)}")
    print(f"     🔥 Strong (≥80):      {len(strong)}")
    print(f"     ✅ Good (70-79):      {len(good)}")
    print(f"     ⬜ Below threshold:   {len(weak)}")

    # Get all jobs above minimum score
    top_jobs = get_top_jobs(scored, min_score=min_score)

    if not top_jobs:
        print(f"\n  ⚠️  No jobs scored ≥ {min_score} today.")
        print("  💡 This is the agent protecting your quality!")
        print("     Options:")
        print("     - Run again tomorrow for fresh postings")
        print("     - Lower min_score to 75 for more results")
        update_excel()
        show_tracker_summary()
        return

    # Cap at max_tailored
    jobs_to_tailor = top_jobs[:max_tailored]

    print(f"\n  🎯 {len(top_jobs)} strong matches found")
    print(f"  ✍️  Tailoring {len(jobs_to_tailor)} resumes today")

    if len(top_jobs) > max_tailored:
        print(f"  ℹ️  {len(top_jobs) - max_tailored} more eligible jobs "
              f"— tracked for manual apply (no tailored resume)")

    # -------------------------------------------
    # STEP 4 — Tailor resumes (Opus — quality matters)
    # -------------------------------------------
    print(f"\n✍️  STEP 4: Tailoring {len(jobs_to_tailor)} resumes with Claude Opus...")
    print(f"  ⏱️  Estimated time: ~{len(jobs_to_tailor) * 30} seconds\n")

    os.makedirs("tailored_resumes", exist_ok=True)

    results = []
    errors  = []

    for i, match in enumerate(jobs_to_tailor):
        job     = match["job"]
        score   = match["total_score"]
        verdict = match["ats_verdict"]
        title   = job.get("title", "")
        company = job.get("company_name", "")

        apply_link    = ""
        apply_options = job.get("apply_options", [])
        if apply_options:
            apply_link = apply_options[0].get("link", "")

        print(f"  [{i+1}/{len(jobs_to_tailor)}] {title} @ {company}")
        print(f"  Score: {score}/100 — {verdict}")

        try:
            # Step 4a — Tailor resume text
            tailored = tailor_resume(resume_text, job, client)

            # Step 4b — Save as PDF
            filename = make_filename(i + 1, job)
            save_as_pdf(tailored, filename)

            # Step 4c — Mark as seen immediately
            mark_as_seen(
                job,
                score       = score,
                verdict     = verdict,
                resume_file = filename
            )

            # Step 4d — Prepare app data for Phase 3
            app_data = prepare_application_data(profile, tailored)

            # Step 4e — Add to results
            results.append({
                "rank":     i + 1,
                "title":    title,
                "company":  company,
                "score":    score,
                "verdict":  verdict,
                "type":     job.get("job_type", "").upper(),
                "posted":   job.get("posted_at", "")[:10],
                "apply":    apply_link,
                "file":     filename,
                "job":      job,
                "app_data": app_data
            })

            print(f"  ✅ Done: {filename}")

        except Exception as e:
            print(f"  ⚠️  Error tailoring {title} @ {company}: {e}")
            errors.append(f"{title} @ {company}: {e}")

        print()

    # Track remaining eligible jobs (scored ≥ min_score but no tailored resume)
    remaining_eligible = top_jobs[max_tailored:]
    manual_apply = []

    for match in remaining_eligible:
        job     = match["job"]
        score   = match["total_score"]
        verdict = match["ats_verdict"]
        title   = job.get("title", "")
        company = job.get("company_name", "")
        apply_options = job.get("apply_options", [])
        apply_link    = apply_options[0].get("link", "") if apply_options else ""

        mark_as_seen(
            job,
            score   = score,
            verdict = verdict,
            status  = "Apply — No Tailored Resume"
        )
        manual_apply.append({
            "title":   title,
            "company": company,
            "score":   score,
            "verdict": verdict,
            "type":    job.get("job_type", "").upper(),
            "posted":  job.get("posted_at", "")[:10],
            "apply":   apply_link,
        })

    # -------------------------------------------
    # FINAL SUMMARY
    # -------------------------------------------
    print("\n" + "="*55)
    print("  ✅ AGENT COMPLETE!")
    print("="*55)

    # Cost estimate
    scoring_cost  = len(scored)  * 0.0005  # Haiku ~$0.0005 per call
    tailoring_cost = len(results) * 0.03   # Opus ~$0.03 per resume
    total_cost    = scoring_cost + tailoring_cost + 0.01
    print("\n  📊 Today's Results:")
    print(f"     Jobs found:           {len(jobs)}")
    print(f"     Strong matches (≥80): {len(top_jobs)}")
    print(f"     Resumes generated:    {len(results)}")
    print(f"     Manual apply (≥{min_score}, no resume): {len(manual_apply)}")
    if errors:
        print(f"     Errors:               {len(errors)}")
    print(f"\n  💰 Estimated cost this run: ~${total_cost:.2f}")
    print("\n  📁 Resumes saved to: tailored_resumes/")

    # Apply in priority order
    print("\n  --- APPLY IN THIS ORDER ---\n")
    priority = sorted(results, key=lambda x: x["score"], reverse=True)

    for r in priority:
        print(f"  🔥 [{r['rank']}] {r['title']} @ {r['company']}")
        print(f"       Score:   {r['score']}/100 — {r['verdict']}")
        print(f"       Type:    {r['type']}")
        print(f"       Posted:  {r['posted']}")
        print(f"       Apply:   {r['apply']}")
        print(f"       Resume:  {r['file']}\n")

    print("  💡 Next steps:")
    print("     1. Apply through company website first")
    print("     2. Then job portal if not available")
    print("     3. Connect with relevant people on LinkedIn")
    print("     4. Follow up after 1 week")

    if manual_apply:
        print(f"\n  --- ALSO APPLY (no tailored resume — use original) ---\n")
        manual_sorted = sorted(manual_apply, key=lambda x: x["score"], reverse=True)
        for r in manual_sorted:
            print(f"  ✅ {r['title']} @ {r['company']}")
            print(f"       Score:   {r['score']}/100 — {r['verdict']}")
            print(f"       Type:    {r['type']}")
            print(f"       Posted:  {r['posted']}")
            print(f"       Apply:   {r['apply']}\n")



    # Update Excel tracker and show summary
    update_excel()
    show_tracker_summary()

    # # -------------------------------------------
    # # PHASE 2 — Prepare LinkedIn outreach
    # # -------------------------------------------
    # if results:
    #     from linkedin_finder import prepare_linkedin_search
    #     jobs_for_outreach = [
    #         {
    #             "job_id":       r["company"] + r["title"],
    #             "title":        r["title"],
    #             "company_name": r["company"],
    #             "total_score":  r["score"]
    #         }
    #         for r in results
    #     ]
    #     prepare_linkedin_search(jobs_for_outreach)

    # # -------------------------------------------
    # # PHASE 3 — Semi-auto apply
    # # -------------------------------------------
    # if results:
    #     apply_now = input(
    #         "\n  🚀 Ready to auto-apply now? (y/n): "
    #     ).strip().lower()

    #     if apply_now == 'y':
    #         from auto_apply import run_auto_apply
    #         run_auto_apply(results)

    # print("\n" + "="*55)



if __name__ == "__main__":
    run_agent(
        resume_path  = "your_resume.pdf",
        min_score    = 75,    # strong matches only
        max_tailored = 10,    # max 10 per day
        hours        = 72     # last 72 hours
    )