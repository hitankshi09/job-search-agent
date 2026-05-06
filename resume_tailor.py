import anthropic
import os
import re
from io import BytesIO
from dotenv import load_dotenv
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    HRFlowable,
    Table,
    TableStyle
)

load_dotenv()


def tailor_resume(resume_text, job, client):
    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=3000,
        messages=[{
            "role": "user",
            "content": f"""You are an expert resume writer and ATS optimization specialist.
Tailor the resume below to match this specific job.

STRICT RULES — you MUST follow ALL of these:
1.  Do NOT invent, fabricate, or exaggerate any experience, skill, or project
2.  Do NOT remove any real experience or projects from the resume
3.  Reword bullet points to naturally mirror keywords from the job description
4.  Reorder bullets within each role to surface most relevant ones first
5.  Keep identical section structure (Education, Skills, Work Experience, Academic Projects)
6.  Naturally incorporate matching keywords without stuffing
7.  If job mentions specific tools you have — make sure they appear prominently
8.  List Excel, SQL, Python etc. individually — never just "Microsoft Suite"
9.  Add contextual keywords like KPI, dashboard, stakeholder, agile,
    cross-functional naturally where they genuinely apply to your experience
10. Keep the resume to ONE single page only — this is critical
11. Keep ALL bullets from original — do not remove any
12. For each job role, rank bullets by relevance to the job description:
    - TOP 2 bullets = most relevant to job description → expand to 1.5-2 full lines
    - MIDDLE bullets = moderately relevant → keep at exactly 1 full line
    - LAST bullet per role = least relevant → keep short, 1 line maximum
13. NEVER leave 2-4 words hanging alone on a new line — this wastes space.
    If a bullet spills 2-4 words onto a new line either:
    a) Add meaningful detail to make it fill 1.5-2 lines properly, OR
    b) Trim it to fit cleanly on 1 line
14. Never remove an entire role, project, or section
15. If space remains at the bottom after writing all content:
    Do NOT add new information or fabricate details.
    Instead go back to the TOP 2 bullets per role and
    add only context that already exists in the original
    resume — such as specific numbers, tools, or outcomes
    that were mentioned but not yet included in that bullet.
    If no real detail remains to add, leave the space as is.
    A slightly unfilled page is better than exaggerated content.

Job Title:       {job.get('title')}
Company:         {job.get('company_name')}
Job Type:        {job.get('job_type')}
Job Description:
{job.get('description', '')[:2500]}

Original Resume:
{resume_text}

FORMAT RULES — follow exactly, no exceptions:
- Line 1: Full name in CAPS e.g. HITANKSHI JAIN
- Line 2: Contact details with @ symbol separated by | e.g. 445-260-9057 | email@gmail.com | LinkedIn | GitHub
- Section headers in ALL CAPS e.g. EDUCATION, SKILLS, WORK EXPERIENCE, ACADEMIC PROJECTS
- Company/Institution lines as: Company Name | Date
- Role/Degree lines as: *Job Title* | Location
- EVERY bullet MUST start with this exact character: •
- NEVER use ? or - or * for bullets
- Skills section: "Technical:" then skills, new line "Certificates:" then certs

Return plain text only. No markdown, no commentary."""
        }]
    )
    return response.content[0].text.strip()


def fix_line_order(text):
    """Force name before contact regardless of Claude output order"""
    lines        = text.split('\n')
    name_line    = None
    contact_line = None
    other_lines  = []

    for line in lines:
        s = line.strip()
        if not s:
            other_lines.append(line)
            continue
        if (s.isupper()
                and len(s) > 2
                and "|" not in s
                and "@" not in s
                and not s.startswith("•")
                and not s.startswith("?")):
            if name_line is None:
                name_line = line
            else:
                other_lines.append(line)
        elif "|" in s and "@" in s:
            if contact_line is None:
                contact_line = line
            else:
                other_lines.append(line)
        else:
            other_lines.append(line)

    result = []
    if name_line:    result.append(name_line)
    if contact_line: result.append(contact_line)
    result.extend(other_lines)
    return '\n'.join(result)


def build_story(tailored_text, font_size, bullet_leading, spaceBefore_company):
    """Builds the PDF story with adjustable sizing parameters"""

    content_width = 7.4 * inch

    # Your exact styles — only font_size, bullet_leading
    # and spaceBefore_company are adjustable for auto-fit
    name_style = ParagraphStyle(
        "name", fontName="Times-Roman", fontSize=22,
        alignment=1, spaceAfter=2, spaceBefore=0, leading=28
    )
    contact_style = ParagraphStyle(
        "contact", fontName="Times-Roman", fontSize=10,
        alignment=1, spaceAfter=6, spaceBefore=2, leading=5
    )
    section_style = ParagraphStyle(
        "section", fontName="Times-Bold", fontSize=11,
        spaceBefore=6, spaceAfter=0, leading=12, leftIndent=0
    )
    company_style = ParagraphStyle(
        "company", fontName="Times-Bold", fontSize=font_size,
        spaceAfter=0, spaceBefore=spaceBefore_company,
        leading=font_size + 0.5, leftIndent=-1
    )
    date_style = ParagraphStyle(
        "date", fontName="Times-Bold", fontSize=font_size,
        alignment=2, spaceAfter=0, spaceBefore=spaceBefore_company,
        leading=font_size + 2, leftIndent=-1
    )
    role_style = ParagraphStyle(
        "role", fontName="Times-Italic", fontSize=font_size,
        spaceAfter=0, spaceBefore=0, leading=font_size + 2, leftIndent=0
    )
    location_style = ParagraphStyle(
        "location", fontName="Times-Italic", fontSize=font_size,
        alignment=2, spaceAfter=0, spaceBefore=0,
        leading=font_size + 2, leftIndent=0
    )
    bullet_style = ParagraphStyle(
        "bullet", fontName="Times-Roman", fontSize=font_size,
        leftIndent=10, firstLineIndent=-7,
        spaceAfter=0, spaceBefore=1, leading=bullet_leading
    )
    skills_style = ParagraphStyle(
        "skills", fontName="Times-Roman", fontSize=font_size,
        spaceAfter=0, spaceBefore=1,
        leading=bullet_leading, leftIndent=0
    )
    normal_style = ParagraphStyle(
        "normal", fontName="Times-Roman", fontSize=font_size,
        spaceAfter=1, spaceBefore=0,
        leading=font_size + 2, leftIndent=0
    )

    story        = []
    lines        = tailored_text.split('\n')
    name_done    = False
    contact_done = False

    for line in lines:
        raw = line.strip()

        if raw == "":
            story.append(Spacer(1, 2))
            continue

        # Detect bullet BEFORE encoding
        is_bullet = False
        if raw.startswith("•") or raw.startswith("\u2022"):
            is_bullet = True
            raw = raw.lstrip("•\u2022").strip()
        elif raw.startswith("?") and len(raw) > 2:
            is_bullet = True
            raw = raw[1:].strip()
        elif raw.startswith("- "):
            is_bullet = True
            raw = raw[2:].strip()

        # Safe encode AFTER bullet detection
        safe = raw.encode('latin-1', 'replace').decode('latin-1')

        # NAME
        if not name_done:
            story.append(Paragraph(safe, name_style))
            name_done = True
            continue

        # CONTACT — with clickable hyperlinks
        if not contact_done:
            contact_html = (
                '445-260-9057 | '
                '<a href="mailto:Jain.hitankshi09@gmail.com" color="black">'
                '<u>Jain.hitankshi09@gmail.com</u></a> | '
                '<a href="https://www.linkedin.com/in/hitankshi-jain" color="black">'
                '<u>LinkedIn</u></a> | '
                '<a href="https://github.com/hitankshi09" color="black">'
                '<u>GitHub</u></a>'
            )
            story.append(Paragraph(contact_html, contact_style))
            contact_done = True
            continue

        # SECTION HEADERS
        if safe.isupper() and len(safe) > 2 and not is_bullet:
            story.append(Paragraph(safe, section_style))
            story.append(HRFlowable(
                width="100%", thickness=0.5,
                color=colors.black, spaceBefore=1, spaceAfter=3
            ))
            continue

        # COMPANY | DATE
        if " | " in safe and not is_bullet and not safe.startswith("*"):
            parts = safe.split(" | ", 1)
            left  = parts[0].strip()
            right = parts[1].strip()
            t = Table(
                [[
                    Paragraph(left,  company_style),
                    Paragraph(right, date_style)
                ]],
                colWidths=[content_width * 0.6, content_width * 0.4]
            )
            t.setStyle(TableStyle([
                ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING',   (0, 0), (-1, -1), 0),
                ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING',    (0, 0), (-1, -1), 0),
            ]))
            story.append(t)
            continue

        # ROLE | LOCATION
        if safe.startswith("*") and " | " in safe:
            clean = safe.replace("*", "")
            parts = clean.split(" | ", 1)
            left  = parts[0].strip()
            right = parts[1].strip()
            t = Table(
                [[
                    Paragraph(left,  role_style),
                    Paragraph(right, location_style)
                ]],
                colWidths=[content_width * 0.6, content_width * 0.4]
            )
            t.setStyle(TableStyle([
                ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING',   (0, 0), (-1, -1), 0),
                ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING',    (0, 0), (-1, -1), 0),
            ]))
            story.append(t)
            continue

        # SKILLS
        if safe.startswith("Technical:") or safe.startswith("Certificates:"):
            colon_idx = safe.index(":") + 1
            label     = safe[:colon_idx]
            content   = safe[colon_idx:]
            story.append(Paragraph(
                f"<b>{label}</b>{content}",
                skills_style
            ))
            continue

        # BULLETS
        if is_bullet:
            story.append(Paragraph(f"• {safe}", bullet_style))
            continue

        # REGULAR TEXT
        story.append(Paragraph(safe, normal_style))

    return story


def count_pages(story):
    """Test build to count pages without saving a file"""
    buf = BytesIO()
    test_doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        rightMargin=0.40*inch,
        leftMargin=0.40*inch,
        topMargin=0.25*inch,
        bottomMargin=0.30*inch
    )
    test_doc.build(story)
    return test_doc.page


def save_as_pdf(tailored_text, filename):

    tailored_text = fix_line_order(tailored_text)

    # Start with your exact working values
    font_size           = 10.5
    bullet_leading      = 11.0
    spaceBefore_company = 8

    while font_size >= 9.0:
        story = build_story(
            tailored_text,
            font_size,
            bullet_leading,
            spaceBefore_company
        )

        pages = count_pages(story)

        if pages <= 1:
            # Fits! Save the real file
            final_doc = SimpleDocTemplate(
                filename,
                pagesize=letter,
                rightMargin=0.40*inch,
                leftMargin=0.40*inch,
                topMargin=0.25*inch,
                bottomMargin=0.30*inch
            )
            final_doc.build(build_story(
                tailored_text,
                font_size,
                bullet_leading,
                spaceBefore_company
            ))
            print(f"  ✅ Fits 1 page! "
                  f"font={font_size} leading={bullet_leading} "
                  f"spacing={spaceBefore_company}")
            break

        else:
            print(f"  ⚠️  {pages} pages — adjusting...")

            # Step 1 — tighten bullet leading first
            if bullet_leading > 10.0:
                bullet_leading -= 0.25

            # Step 2 — reduce spacing between roles
            elif spaceBefore_company > 4:
                spaceBefore_company -= 1

            # Step 3 — reduce font size as last resort
            else:
                font_size      -= 0.25
                bullet_leading  = font_size + 0.5

    print(f"  📄 Saved: {filename}")


def make_filename(index, job):
    title   = job.get('title', 'Role')
    company = job.get('company_name', 'Company')
    posted  = job.get('posted_at', '')[:10]

    safe_title   = re.sub(r'[^\w\s]', '', title).strip().replace(' ', '_')
    safe_company = re.sub(r'[^\w\s]', '', company).strip().replace(' ', '_')

    parts    = [f"{index:02d}", safe_company, safe_title, posted]
    filename = "__".join(p for p in parts if p)
    return f"tailored_resumes/{filename}.pdf"


if __name__ == "__main__":
    from resume_parser import parse_resume

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    print("📄 Reading your resume...")
    resume_text = parse_resume("your_resume.pdf")

    test_job = {
        "title":        "Business Analyst",
        "company_name": "Capital One",
        "job_type":     "fulltime",
        "posted_at":    "2026-04-23",
        "description":  """We are looking for a Business Analyst with 3-5 years
        of experience. Required skills: SQL, PowerBI, Excel, Python.
        MS in Business Analytics or related field preferred.
        You will build dashboards, analyze KPIs, work with stakeholders
        across cross-functional teams using agile methodology.
        Responsibilities include data driven reporting, insights generation,
        and presenting findings to senior leadership.""",
        "apply_options": [{"link": "https://capitalone.com/careers"}],
        "source": "test"
    }

    os.makedirs("tailored_resumes", exist_ok=True)

    print(f"✍️  Tailoring for {test_job['title']} @ {test_job['company_name']}...")
    print("    20-30 seconds — Claude is rewriting your resume...\n")

    tailored = tailor_resume(resume_text, test_job, client)
    filename  = make_filename(1, test_job)
    save_as_pdf(tailored, filename)

    print(f"\n✅ Done! Open: {filename}")
    print("\n💡 Check:")
    print("   ✅ Name centered size 22")
    print("   ✅ Contact with clickable links")
    print("   ✅ Section headers flush left with underline")
    print("   ✅ All bullets preserved")
    print("   ✅ Guaranteed single page")

def prepare_application_data(profile, tailored_text):
    """
    Combines existing profile + tailored resume text
    into structured data for auto_apply.
    Zero extra Claude calls — uses what we already have!
    Tailored bullets from the job-specific resume are included.
    """
    # Extract tailored bullet points from the resume text
    lines   = tailored_text.split('\n')
    bullets = [
        l.strip().lstrip('•').strip()
        for l in lines
        if l.strip().startswith('•') and len(l.strip()) > 5
    ]

    # Get name parts safely
    full_name  = (profile.get("full_name") or
                  profile.get("name") or "")
    name_parts = full_name.split()
    first_name = (profile.get("first_name") or
                  (name_parts[0] if name_parts else ""))
    last_name  = (profile.get("last_name") or
                  (" ".join(name_parts[1:])
                   if len(name_parts) > 1 else ""))

    return {
        # Basic contact info — fixed facts
        "first_name":      first_name,
        "last_name":       last_name,
        "full_name":       full_name,
        "email":           profile.get("email", ""),
        "phone":           profile.get("phone", ""),
        "location":        profile.get("location", ""),
        "city":            profile.get("city", ""),
        "state":           profile.get("state", ""),
        "linkedin_url":    profile.get("linkedin_url", ""),
        "github_url":      profile.get("github_url", ""),

        # Structured data — fixed facts
        "education":       profile.get("education", []),
        "work_experience": profile.get("work_experience", []),
        "skills":          profile.get("skills", []),
        "certifications":  profile.get("certifications", []),

        # Tailored content — job specific!
        # These bullets are the reworded, optimized versions
        # that match this specific job description
        "tailored_bullets": bullets
    }