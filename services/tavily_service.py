"""
tavily_service.py
Wraps the Tavily Search API for StudyMate AI's Resource Hub and AI Tutor.

Responsibilities:
- Read TAVILY_API_KEY from .env
- Build smart search queries (topic + question + resource type)
- Return REAL results only (title, url, content snippet, domain)
- Never fabricate URLs
- Gracefully handle API failures / no results / timeouts
"""

import os
from tavily import TavilyClient
from utils.helpers import domain_from_url


# A broad set of trusted educational / technical domains StudyMate AI knows
# about. These are used ONLY as optional filters / ranking hints - Tavily's
# own web search is never restricted to just these unless the user opts in
# via Settings -> Preferred resource domains.
TRUSTED_EDU_DOMAINS = [
    "geeksforgeeks.org", "unacademy.com", "nptel.ac.in", "coursera.org",
    "edx.org", "ocw.mit.edu", "khanacademy.org", "freecodecamp.org",
    "w3schools.com", "developer.mozilla.org", "tutorialspoint.com",
    "programiz.com", "scaler.com", "simplilearn.com", "ibm.com",
    "learn.microsoft.com", "aws.amazon.com", "cloud.google.com",
    "arduino.cc", "raspberrypi.org", "arm.com", "st.com", "espressif.com",
    "owasp.org", "cisco.com", "redhat.com", "docker.com", "kubernetes.io",
    "github.com", "youtube.com",
]

RESOURCE_TYPE_KEYWORDS = {
    "All": "",
    "Courses": "course",
    "Tutorials": "tutorial",
    "Documentation": "official documentation",
    "Videos": "video lecture",
    "Articles": "article guide",
    "University material": "university lecture notes",
    "Projects": "project example",
}


class TavilyService:
    def __init__(self):
        self.api_key = os.getenv("TAVILY_API_KEY", "").strip()
        self.client = None
        self.available = False
        self.init_error = None

        if not self.api_key:
            self.init_error = "TAVILY_API_KEY is missing from your .env file."
            return

        try:
            self.client = TavilyClient(api_key=self.api_key)
            self.available = True
        except Exception as e:
            self.init_error = f"Could not initialize Tavily client: {e}"

    def search_resources(self, topic: str, question: str = "", resource_type: str = "All",
                          max_results: int = 6, preferred_domains=None,
                          search_depth: str = "advanced") -> dict:
        """
        Returns:
            {
                "success": bool,
                "error": str or None,
                "results": [
                    {"title", "url", "content", "domain", "resource_type"}
                ]
            }
        """
        if not self.available:
            return {"success": False, "error": self.init_error or "Tavily is not configured.", "results": []}

        if not topic or not topic.strip():
            return {"success": False, "error": "Please provide a topic to search resources for.", "results": []}

        type_keyword = RESOURCE_TYPE_KEYWORDS.get(resource_type, "")
        query_parts = [topic.strip()]
        if question and question.strip():
            query_parts.append(question.strip())
        if type_keyword:
            query_parts.append(type_keyword)
        else:
            query_parts.append("tutorial course documentation")

        query = " ".join(query_parts)[:400]

        search_kwargs = {
            "query": query,
            "max_results": max(3, min(max_results, 10)),
            "search_depth": search_depth,
        }

        if preferred_domains:
            search_kwargs["include_domains"] = preferred_domains

        try:
            response = self.client.search(**search_kwargs)
        except Exception as e:
            msg = str(e)
            if "401" in msg or "Unauthorized" in msg or "api_key" in msg.lower():
                friendly = "Your Tavily API key appears to be invalid or unauthorized."
            elif "timeout" in msg.lower():
                friendly = "The web search timed out. Please check your internet connection and try again."
            else:
                friendly = f"Web search failed: {msg}"
            return {"success": False, "error": friendly, "results": []}

        raw_results = response.get("results", []) if isinstance(response, dict) else []

        if not raw_results:
            return {
                "success": True,
                "error": None,
                "results": [],
                "message": "No resources were found for this search. Try a broader topic or different keywords.",
            }

        cleaned = []
        for r in raw_results:
            url = r.get("url", "")
            if not url:
                continue
            cleaned.append({
                "title": r.get("title", "Untitled resource").strip() or "Untitled resource",
                "url": url,
                "content": (r.get("content", "") or "").strip(),
                "domain": domain_from_url(url),
                "resource_type": resource_type,
                "score": r.get("score", 0),
            })

        return {"success": True, "error": None, "results": cleaned}

    def get_context_for_gemini(self, topic: str, question: str, max_results: int = 4) -> str:
        """
        Runs a focused search and formats results into a compact text block
        that can be handed to Gemini as grounding context (title + url + snippet).
        Returns an empty string if search fails or finds nothing - the AI Tutor
        will simply proceed without web context in that case.
        """
        result = self.search_resources(
            topic=topic, question=question, resource_type="All",
            max_results=max_results, search_depth="basic",
        )
        if not result["success"] or not result["results"]:
            return ""

        lines = []
        for r in result["results"]:
            lines.append(f"- {r['title']} | {r['url']} | {r['content'][:200]}")
        return "\n".join(lines)
