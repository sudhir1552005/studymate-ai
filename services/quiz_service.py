"""
quiz_service.py
Handles quiz generation (via Gemini) and scoring logic for Quiz Center
and the Notes Lab's "Generate Quiz" feature.
"""

from services.gemini_service import GeminiService


class QuizService:
    def __init__(self):
        self.gemini = GeminiService()

    def generate_quiz(self, subject: str, difficulty: str, num_questions: int) -> dict:
        if not self.gemini.available:
            return {"success": False, "error": self.gemini.init_error, "questions": []}
        if not subject or not subject.strip():
            return {"success": False, "error": "Please select or enter a subject for the quiz.", "questions": []}
        return self.gemini.generate_quiz(subject.strip(), difficulty, num_questions)

    def generate_quiz_from_notes(self, notes_text: str, num_questions: int) -> dict:
        if not self.gemini.available:
            return {"success": False, "error": self.gemini.init_error, "questions": []}
        if not notes_text or not notes_text.strip():
            return {"success": False, "error": "No notes are available. Please upload notes first.", "questions": []}
        return self.gemini.generate_notes_quiz(notes_text, num_questions)

    @staticmethod
    def score_quiz(questions: list, answers: dict) -> dict:
        """
        questions: list of {question, options, correct_answer, explanation}
        answers:   {index: selected_option_text}

        Returns:
            {
                "score": int,
                "total": int,
                "results": [
                    {question, selected, correct_answer, is_correct, explanation}
                ],
                "topics_to_revise": [question_text for wrong answers]
            }
        """
        results = []
        score = 0
        topics_to_revise = []

        for i, q in enumerate(questions):
            selected = answers.get(i)
            correct = q.get("correct_answer", "")
            is_correct = (selected == correct) and selected is not None
            if is_correct:
                score += 1
            else:
                topics_to_revise.append(q.get("question", ""))

            results.append({
                "question": q.get("question", ""),
                "selected": selected if selected is not None else "Not answered",
                "correct_answer": correct,
                "is_correct": is_correct,
                "explanation": q.get("explanation", ""),
            })

        return {
            "score": score,
            "total": len(questions),
            "results": results,
            "topics_to_revise": topics_to_revise,
        }
