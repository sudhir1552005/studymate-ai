"""
gemini_service.py
Wraps Google's Gemini API (google-genai SDK) for StudyMate AI.

Responsibilities:
- Read GEMINI_API_KEY from .env
- Build robust, student-level-aware prompts
- Ask Gemini for STRUCTURED JSON output
- Parse that JSON safely (Gemini sometimes wraps JSON in ```json fences)
- Never let an API failure crash the app -> always return a usable dict
"""

import os
import json
import re

from google import genai
from google.genai import types

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")


class GeminiService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.client = None
        self.available = False
        self.init_error = None

        if not self.api_key:
            self.init_error = "GEMINI_API_KEY is missing from your .env file."
            return

        try:
            self.client = genai.Client(api_key=self.api_key)
            self.available = True
        except Exception as e:
            self.init_error = f"Could not initialize Gemini client: {e}"

    # ------------------------------------------------------------------
    # INTERNAL HELPERS
    # ------------------------------------------------------------------

    def _call_model(self, system_instruction: str, user_prompt: str,
                     temperature: float = 0.4, max_output_tokens: int = 3000) -> dict:
        """Single low-level call to Gemini. Returns {'success', 'text', 'error'}."""
        if not self.available:
            return {"success": False, "text": "", "error": self.init_error or "Gemini is not configured."}

        try:
            response = self.client.models.generate_content(
                model=GEMINI_MODEL,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                ),
            )
            text = (response.text or "").strip()
            if not text:
                return {"success": False, "text": "", "error": "Gemini returned an empty response."}
            return {"success": True, "text": text, "error": None}

        except Exception as e:
            msg = str(e)
            if "API key" in msg or "PERMISSION_DENIED" in msg or "401" in msg:
                friendly = "Your Gemini API key appears to be invalid or unauthorized."
            elif "quota" in msg.lower() or "429" in msg:
                friendly = "The Gemini API rate limit / quota was reached. Please try again shortly."
            elif "timeout" in msg.lower():
                friendly = "The request to Gemini timed out. Please check your internet connection and try again."
            else:
                friendly = f"Gemini request failed: {msg}"
            return {"success": False, "text": "", "error": friendly}

    @staticmethod
    def _extract_json(raw_text: str) -> dict:
        """
        Gemini sometimes wraps JSON in ```json ... ``` fences, or adds
        stray text before/after. This robustly extracts the JSON object.
        """
        if not raw_text:
            return {}

        text = raw_text.strip()
        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"^```\s*", "", text)
        text = re.sub(r"```\s*$", "", text)
        text = text.strip()

        try:
            return json.loads(text)
        except Exception:
            pass

        # Fallback: find the first { ... last } block
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                return {}
        return {}

    # ------------------------------------------------------------------
    # PUBLIC: MAIN STUDY EXPLANATION
    # ------------------------------------------------------------------

    def generate_study_response(self, topic: str, question: str, student_level: str,
                                 learning_style: str, notes_context: str = "",
                                 web_context: str = "") -> dict:
        """
        Core AI Tutor call. Returns a structured dict matching the app's
        expected schema, even on failure (with empty/default fields).
        """

        system_instruction = (
            "You are StudyMate AI, an expert, patient, multi-domain academic tutor. "
            "You teach subjects ranging from Computer Science, AI/ML, Cyber Security, "
            "Embedded Systems and Electronics, Web Development, Databases, Cloud, "
            "core Engineering, Mathematics/Science, and Management topics.\n\n"
            "STRICT RULES:\n"
            "1. Explain according to the student's stated level (Beginner / Intermediate / Advanced).\n"
            "2. NEVER invent, guess, or hallucinate resource URLs. If web context is provided, "
            "you may reference it only in the 'sources' field using EXACTLY the URLs given to you. "
            "If no web context is provided, leave 'sources' as an empty list.\n"
            "3. If study notes context is provided, ground your answer in it and mention when "
            "you are using information from the student's notes.\n"
            "4. Clearly separate factual explanation from illustrative examples.\n"
            "5. Be encouraging, clear, and student-friendly. Avoid unnecessary jargon for Beginners.\n"
            "6. Respond with STRICT, VALID JSON ONLY. No markdown fences, no commentary outside JSON.\n\n"
            "Return JSON in EXACTLY this schema:\n"
            "{\n"
            '  "explanation": "detailed explanation tailored to the learning style",\n'
            '  "simple_definition": "one or two sentence plain-language definition",\n'
            '  "summary": "concise 3-5 sentence summary",\n'
            '  "key_points": ["point 1", "point 2", "..."],\n'
            '  "examples": ["real-world example 1", "practical example 2"],\n'
            '  "common_mistakes": ["mistake 1", "mistake 2"],\n'
            '  "exam_tips": ["tip 1", "tip 2"],\n'
            '  "further_learning": ["suggested next topic or skill 1", "suggestion 2"],\n'
            '  "sources": ["only URLs copied exactly from provided web context, else empty list"]\n'
            "}"
        )

        style_instructions = {
            "Simple explanation": "Keep it short, simple, and beginner-friendly. Avoid heavy jargon.",
            "Detailed explanation": "Provide an in-depth, thorough explanation with technical depth.",
            "Exam preparation": "Focus on exam-relevant points, definitions, and likely exam questions.",
            "Practical/project based": "Focus on hands-on application, code/circuit/project usage.",
            "Interview preparation": "Focus on interview-style Q&A depth, key concepts interviewers probe.",
        }
        style_note = style_instructions.get(learning_style, "Provide a clear, well-structured explanation.")

        prompt_parts = [
            f"TOPIC: {topic}",
            f"STUDENT QUESTION: {question}",
            f"STUDENT LEVEL: {student_level}",
            f"LEARNING STYLE: {learning_style} -> {style_note}",
        ]

        if notes_context:
            prompt_parts.append(
                "STUDENT'S UPLOADED NOTES (use as grounding context where relevant):\n"
                f"{notes_context[:6000]}"
            )

        if web_context:
            prompt_parts.append(
                "WEB SEARCH CONTEXT (real, verified sources - you may cite these exact URLs "
                "in the 'sources' field, do not alter them):\n"
                f"{web_context[:4000]}"
            )
        else:
            prompt_parts.append("No web search context was provided. Leave 'sources' as an empty list.")

        user_prompt = "\n\n".join(prompt_parts)

        result = self._call_model(system_instruction, user_prompt, temperature=0.4, max_output_tokens=3500)

        if not result["success"]:
            return self._empty_study_response(error=result["error"])

        parsed = self._extract_json(result["text"])
        if not parsed:
            return self._empty_study_response(
                error="Gemini's response could not be parsed. Please try asking again."
            )

        return {
            "success": True,
            "error": None,
            "explanation": parsed.get("explanation", ""),
            "simple_definition": parsed.get("simple_definition", ""),
            "summary": parsed.get("summary", ""),
            "key_points": parsed.get("key_points", []) or [],
            "examples": parsed.get("examples", []) or [],
            "common_mistakes": parsed.get("common_mistakes", []) or [],
            "exam_tips": parsed.get("exam_tips", []) or [],
            "further_learning": parsed.get("further_learning", []) or [],
            "sources": parsed.get("sources", []) or [],
        }

    @staticmethod
    def _empty_study_response(error: str) -> dict:
        return {
            "success": False,
            "error": error,
            "explanation": "",
            "simple_definition": "",
            "summary": "",
            "key_points": [],
            "examples": [],
            "common_mistakes": [],
            "exam_tips": [],
            "further_learning": [],
            "sources": [],
        }

    # ------------------------------------------------------------------
    # PUBLIC: NOTES LAB OPERATIONS
    # ------------------------------------------------------------------

    def process_notes(self, notes_text: str, operation: str, extra_instruction: str = "") -> dict:
        """
        operation: one of 'summarize', 'explain', 'questions', 'quiz',
                   'answer_question', 'revision_points'
        """
        if not notes_text or not notes_text.strip():
            return {"success": False, "error": "No notes text available to process.", "content": ""}

        op_instructions = {
            "summarize": "Write a clear, well-organized summary of these notes.",
            "explain": "Explain these notes in simple, easy-to-understand language, as if teaching a student.",
            "questions": "Generate 8-10 thoughtful study questions based on these notes (no answers needed).",
            "revision_points": "Extract concise bullet-point revision notes covering all key facts.",
            "answer_question": f"Answer this specific question using ONLY the notes as context: {extra_instruction}",
        }
        instruction = op_instructions.get(operation, "Process these notes helpfully for a student.")

        system_instruction = (
            "You are StudyMate AI's Notes Lab assistant. You work strictly from the notes text "
            "provided by the student. Respond with STRICT VALID JSON ONLY in this schema:\n"
            '{ "content": "your full response as a well-formatted string (use \\n for line breaks)" }'
        )

        user_prompt = f"INSTRUCTION: {instruction}\n\nNOTES:\n{notes_text[:8000]}"

        result = self._call_model(system_instruction, user_prompt, temperature=0.3, max_output_tokens=2500)
        if not result["success"]:
            return {"success": False, "error": result["error"], "content": ""}

        parsed = self._extract_json(result["text"])
        content = parsed.get("content", "") if parsed else result["text"]
        if not content:
            content = result["text"]

        return {"success": True, "error": None, "content": content}

    def generate_notes_quiz(self, notes_text: str, num_questions: int = 5) -> dict:
        """Generate a quiz strictly from uploaded notes."""
        return self._generate_quiz_internal(
            source_description=f"the student's uploaded notes:\n{notes_text[:8000]}",
            subject="Uploaded Notes",
            difficulty="Medium",
            num_questions=num_questions,
        )

    # ------------------------------------------------------------------
    # PUBLIC: QUIZ GENERATION (also used directly by quiz_service.py)
    # ------------------------------------------------------------------

    def generate_quiz(self, subject: str, difficulty: str, num_questions: int) -> dict:
        return self._generate_quiz_internal(
            source_description=f"the academic subject: {subject}",
            subject=subject,
            difficulty=difficulty,
            num_questions=num_questions,
        )

    def _generate_quiz_internal(self, source_description: str, subject: str,
                                 difficulty: str, num_questions: int) -> dict:
        system_instruction = (
            "You are StudyMate AI's Quiz Generator. Create high-quality, accurate multiple-choice "
            "questions. Each question must have exactly 4 options, one correct answer, and a clear "
            "explanation. Respond with STRICT VALID JSON ONLY in this schema:\n"
            "{\n"
            '  "questions": [\n'
            "    {\n"
            '      "question": "question text",\n'
            '      "options": ["option A", "option B", "option C", "option D"],\n'
            '      "correct_answer": "the exact text of the correct option",\n'
            '      "explanation": "why this answer is correct"\n'
            "    }\n"
            "  ]\n"
            "}"
        )

        user_prompt = (
            f"Create {num_questions} multiple-choice questions about {source_description}.\n"
            f"Difficulty level: {difficulty}.\n"
            "Ensure questions are accurate, unambiguous, and educational. "
            "Vary question types (conceptual, applied, factual)."
        )

        result = self._call_model(system_instruction, user_prompt, temperature=0.5, max_output_tokens=3500)
        if not result["success"]:
            return {"success": False, "error": result["error"], "questions": []}

        parsed = self._extract_json(result["text"])
        questions = parsed.get("questions", []) if parsed else []

        # Validate structure defensively
        valid_questions = []
        for q in questions:
            if (isinstance(q, dict) and q.get("question") and
                    isinstance(q.get("options"), list) and len(q.get("options")) >= 2 and
                    q.get("correct_answer")):
                valid_questions.append({
                    "question": q.get("question", ""),
                    "options": q.get("options", []),
                    "correct_answer": q.get("correct_answer", ""),
                    "explanation": q.get("explanation", "No explanation provided."),
                })

        if not valid_questions:
            return {"success": False, "error": "Gemini did not return a valid quiz. Please try again.", "questions": []}

        return {"success": True, "error": None, "questions": valid_questions}
