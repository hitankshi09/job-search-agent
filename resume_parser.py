import fitz
import json
import re
import anthropic
import os
from dotenv import load_dotenv

load_dotenv()


def parse_resume(pdf_path):
    doc  = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text


def extract_profile(resume_text, client):
    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=3000,
        messages=[{
            "role": "user",
            "content": f"""Extract from this resume and return ONLY raw JSON,
no markdown, no backticks:
{{
  "name":                "",
  "first_name":          "",
  "last_name":           "",
  "full_name":           "",
  "email":               "",
  "phone":               "",
  "location":            "",
  "city":                "",
  "state":               "",
  "linkedin_url":        "",
  "github_url":          "",
  "years_of_experience": 0,
  "skills":              [],
  "job_titles":          [],
  "visa_status":         "",
  "education": [
    {{
      "university":  "",
      "degree":      "",
      "field":       "",
      "start_date":  "",
      "end_date":    "",
      "location":    "",
      "gpa":         ""
    }}
  ],
  "work_experience": [
    {{
      "company":     "",
      "title":       "",
      "start_date":  "",
      "end_date":    "",
      "location":    "",
      "description": "",
      "bullets":     []
    }}
  ],
  "certifications": []
}}

Resume:
{resume_text}"""
        }]
    )
    raw = response.content[0].text.strip()
    raw = re.sub(r"```json|```", "", raw).strip()
    return json.loads(raw)


if __name__ == "__main__":
    client      = anthropic.Anthropic(
        api_key=os.getenv("ANTHROPIC_API_KEY")
    )
    resume_text = parse_resume("your_resume.pdf")
    profile     = extract_profile(resume_text, client)

    print("\n--- Your Profile ---")
    print(f"Name:       {profile.get('full_name')}")
    print(f"Email:      {profile.get('email')}")
    print(f"Phone:      {profile.get('phone')}")
    print(f"Experience: {profile.get('years_of_experience')} years")
    print(f"Skills:     {', '.join(profile.get('skills', [])[:5])}")
    print("\nEducation:")
    for edu in profile.get("education", []):
        print(f"  {edu.get('university')} — "
              f"{edu.get('degree')} {edu.get('field')}")
        print(f"  {edu.get('start_date')} → {edu.get('end_date')}")
    print("\nWork Experience:")
    for exp in profile.get("work_experience", []):
        print(f"  {exp.get('company')} | {exp.get('title')}")
        print(f"  {exp.get('start_date')} → {exp.get('end_date')}")