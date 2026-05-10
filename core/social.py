"""
core/social.py — Posts research reports to LinkedIn.

WHY THIS FILE EXISTS:
After research completes, the user has a great report sitting on their screen.
This file lets them share it to LinkedIn with one click.
The AI automatically reformats the report for LinkedIn because LinkedIn
content should be professional, structured and engaging.

HOW IT WORKS:
1. User clicks share button in app.py
2. app.py calls post_linkedin()
3. The function calls Groq LLM to format the content
4. Then LinkedIn API is called to publish the post
"""

import os
import requests
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from core.models import groq_llm
from dotenv import load_dotenv

load_dotenv()


# ── LLM FOR FORMATTING ────────────────────────────────────────────
# Using Groq because it is fast and inexpensive.

# def _get_llm():
#     return ChatGroq(
#         model="llama-3.3-70b-versatile",
#         temperature=0.4,
#         api_key=os.getenv("GROQ_API_KEY")
#     )


# ════════════════════════════════════════════════════════════════════
# LINKEDIN POST GENERATION
# ════════════════════════════════════════════════════════════════════

linkedin_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a LinkedIn thought leader who shares research insights.

FORMAT RULES:
- Start with ONE strong hook sentence
- Write 3 short paragraphs explaining insights
- Use line breaks between paragraphs
- End with ONE thoughtful question to invite discussion
- Add 5 relevant hashtags on the last line
- Total length: 150 to 250 words
- Tone: professional but human
- No bullet points
"""),

    ("human", """Write a LinkedIn post about this research.

Topic: {topic}

Report summary:
{summary}

Write the LinkedIn post now:""")
])


def format_linkedin_post(report: str, topic: str) -> str:
    """
    Sends report to LLM and returns a LinkedIn-ready post.
    """

    llm   = groq_llm
    chain = linkedin_prompt | llm | StrOutputParser()

    return chain.invoke({
        "topic": topic,
        "summary": report[:1500]
    })


# ════════════════════════════════════════════════════════════════════
# LINKEDIN POSTING FUNCTION
# ════════════════════════════════════════════════════════════════════

def post_linkedin(report: str, topic: str) -> dict:
    """
    Posts research as a LinkedIn post using LinkedIn API.
    """

    try:

        access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
        person_id    = os.getenv("LINKEDIN_PERSON_ID")

        if not access_token:
            return {"success": False, "error": "Missing LINKEDIN_ACCESS_TOKEN in .env"}

        if not person_id:
            return {"success": False, "error": "Missing LINKEDIN_PERSON_ID in .env"}

        post_text = format_linkedin_post(report, topic)

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0"
        }

        payload = {
            "author": f"urn:li:person:{person_id}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": post_text},
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }

        response = requests.post(
            "https://api.linkedin.com/v2/ugcPosts",
            headers=headers,
            json=payload,
            timeout=15
        )

        if response.status_code in [200, 201]:

            post_id = response.json().get("id", "")
            post_url = f"https://www.linkedin.com/feed/update/{post_id}"

            print(f"[Social] LinkedIn post published: {post_url}")

            return {
                "success": True,
                "platform": "linkedin",
                "url": post_url
            }

        else:

            error_msg = f"LinkedIn API error {response.status_code}"

            if response.status_code == 401:
                error_msg = "LinkedIn token expired. Generate new token."

            elif response.status_code == 403:
                error_msg = "LinkedIn app needs w_member_social permission."

            return {
                "success": False,
                "platform": "linkedin",
                "error": error_msg
            }

    except Exception as e:

        return {
            "success": False,
            "platform": "linkedin",
            "error": str(e)
        }