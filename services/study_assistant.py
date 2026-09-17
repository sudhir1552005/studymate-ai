"""
study_assistant.py
Central orchestration layer for StudyMate AI's AI Tutor feature.

This is the single entry point the UI calls. It:
1. Optionally searches Tavily for grounding web context.
2. Calls Gemini with topic + question + notes + web context.
3. Optionally fetches resource cards (for display, not just grounding).
4. Returns one unified, structured dictionary the UI can render directly.
"""

from services.gemini_service import GeminiService
from services.tavily_service import TavilyService


class StudyAssistantApp:
    """
    Usage:
        assistant = StudyAssistantApp()
        result = assistant.invoke(
            topic="Cyber Security",
            question="Explain phishing attacks.",
            notes="",
            student_level="Beginner",
            learning_style="Simple explanation",
            web_search_enabled=True,
        )
    """

    def __init__(self):
        self.gemini = GeminiService()
        self.tavily = TavilyService()

    def invoke(self, topic: str, question: str, notes: str = "",
               student_level: str = "Beginner",
               learning_style: str = "Simple explanation",
               web_search_enabled: bool = True,
               resource_count: int = 6) -> dict:

        errors = []

        # -- input validation -------------------------------------------------
        if not topic or not topic.strip():
            return self._error_result("Please enter a topic before starting.")
        if not question or not question.strip():
            return self._error_result("Please enter a question before starting.")

        if not self.gemini.available:
            errors.append(self.gemini.init_error)

        # -- Step 1: Web search for grounding context + display resources -----
        web_context = ""
        resources = []

        if web_search_enabled:
            if self.tavily.available:
                context_result = self.tavily.search_resources(
                    topic=topic, question=question, resource_type="All",
                    max_results=resource_count, search_depth="advanced",
                )
                if context_result["success"] and context_result["results"]:
                    resources = context_result["results"]
                    web_context = "\n".join(
                        f"- {r['title']} | {r['url']} | {r['content'][:200]}"
                        for r in resources
                    )
                elif context_result.get("error"):
                    errors.append(context_result["error"])
            else:
                errors.append(self.tavily.init_error)

        # -- Step 2: Ask Gemini ------------------------------------------------
        if self.gemini.available:
            ai_result = self.gemini.generate_study_response(
                topic=topic, question=question, student_level=student_level,
                learning_style=learning_style, notes_context=notes,
                web_context=web_context,
            )
        else:
            ai_result = None

        if not ai_result or not ai_result.get("success"):
            error_msg = (ai_result.get("error") if ai_result else None) or \
                        (errors[0] if errors else "The AI tutor could not generate a response. Please try again.")
            return {
                "success": False,
                "error": error_msg,
                "explanation": "",
                "simple_definition": "",
                "summary": "",
                "key_points": [],
                "examples": [],
                "common_mistakes": [],
                "exam_tips": [],
                "further_learning": [],
                "resources": resources,
                "sources": [],
            }

        return {
            "success": True,
            "error": None,
            "explanation": ai_result["explanation"],
            "simple_definition": ai_result["simple_definition"],
            "summary": ai_result["summary"],
            "key_points": ai_result["key_points"],
            "examples": ai_result["examples"],
            "common_mistakes": ai_result["common_mistakes"],
            "exam_tips": ai_result["exam_tips"],
            "further_learning": ai_result["further_learning"],
            "resources": resources,
            "sources": ai_result["sources"],
        }

    @staticmethod
    def _error_result(message: str) -> dict:
        return {
            "success": False,
            "error": message,
            "explanation": "",
            "simple_definition": "",
            "summary": "",
            "key_points": [],
            "examples": [],
            "common_mistakes": [],
            "exam_tips": [],
            "further_learning": [],
            "resources": [],
            "sources": [],
        }
