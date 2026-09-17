# 🎓 StudyMate AI — AI-Powered Multi-Domain Student Study Assistant

> "Learn anything. Build everything."

A professional, Python + Streamlit academic project that combines **Google Gemini**
(reasoning/explanation) and **Tavily** (real-time web search) to tutor students
across Computer Science, AI/ML, Cyber Security, Embedded Systems, Web Dev,
Databases, Cloud, core Engineering, Math/Science, and Management subjects.

---

## 1. Project Structure

```
studymate_ai/
│
├── app.py                      # Main Streamlit app (UI, pages, routing, CSS)
├── requirements.txt
├── .env                        # YOU create this (not committed) — your real keys
├── .env.example                # Template to copy from
├── .gitignore
│
├── services/
│   ├── __init__.py
│   ├── gemini_service.py       # Gemini API wrapper + prompt engineering
│   ├── tavily_service.py       # Tavily API wrapper (real resource search)
│   ├── study_assistant.py      # StudyAssistantApp.invoke() orchestrator
│   └── quiz_service.py         # Quiz generation + scoring logic
│
├── utils/
│   ├── __init__.py
│   ├── pdf_utils.py            # PDF/TXT text extraction (pypdf)
│   ├── state_manager.py        # Central st.session_state init/helpers
│   └── helpers.py              # Subject catalog + formatting helpers
│
├── data/
│   └── demo_notes.txt          # Sample notes file for testing Notes Lab
│
└── README.md
```

**Where every file must be created:** copy each file into a folder named
`studymate_ai` (or any name you like) opened directly in VS Code, keeping the
exact relative paths above — `services/` and `utils/` must be siblings of
`app.py`, each containing their own `__init__.py`.

---

## 2. Installation (Windows PowerShell)

Open the project folder in VS Code, open a PowerShell terminal (`Ctrl + ~`), then:

```powershell
# 1. (Optional but recommended) Create a virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create your .env file from the template
Copy-Item .env.example .env

# 4. Open .env in VS Code and paste your real keys:
#    GEMINI_API_KEY=...
#    TAVILY_API_KEY=...

# 5. Run the app
streamlit run app.py
```

The app opens automatically at **http://localhost:8501**.

If PowerShell blocks the venv activation script, run this once as your user
(not required if you skip the virtual environment step):

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

---

## 3. Testing Checklist

Use this checklist before your demo/viva:

- [ ] App launches with `streamlit run app.py` with no traceback
- [ ] Dashboard shows 5 metric cards, all starting at 0
- [ ] AI Tutor: ask "Explain phishing attacks" under topic "Cyber Security" →
      explanation, key points, examples, mistakes, exam tips all populate
- [ ] AI Tutor: Resources tab shows real clickable URLs (not fake ones)
- [ ] AI Tutor: upload `data/demo_notes.txt` and ask a question about
      "deadlock" → answer reflects the uploaded notes
- [ ] Explore Subjects: search "Arduino" → filters correctly; clicking a
      subject jumps to AI Tutor with topic pre-filled
- [ ] Resource Hub: search "Machine Learning", filter type = "Courses" →
      results appear with working "Open Resource" buttons
- [ ] Resource Hub: click "Save" on a resource → appears in Bookmarks
- [ ] Notes Lab: Summarize / Explain / Generate Questions / Revision Points
      all return non-empty output
- [ ] Notes Lab: "Generate Quiz" → redirects to a working quiz in Quiz Center
- [ ] Quiz Center: generate a 5-question quiz on "Python", answer all, submit
      → score displayed, correct/incorrect shown with explanations
- [ ] Progress: quiz history bar chart updates after each quiz
- [ ] Bookmarks: remove a saved resource → disappears immediately
- [ ] History: previous Q&A entries listed with timestamps; "Clear All" works
- [ ] Settings: change default student level/style → persists across pages
- [ ] Settings: "Clear All Session Data" resets all counters or 0
- [ ] Remove/blank out `.env` values → app still loads and shows a friendly
      warning banner instead of crashing
- [ ] Disconnect internet → Tavily search fails gracefully with a friendly
      error message (Gemini-only explanation still works)

---

## 4. Demo Questions for Presentation

Use a mix of subjects to show off the multi-domain catalog:

1. **Topic:** Cyber Security → *"Explain phishing attacks."*
2. **Topic:** Embedded Systems → *"What is the difference between a
   microcontroller and a microprocessor?"*
3. **Topic:** Machine Learning → *"Explain overfitting with a real-world
   example."*
4. **Topic:** Computer Networks → *"How does the TCP three-way handshake
   work?"*
5. **Topic:** DBMS → *"What is database normalization and why is it
   important?"*
6. **Topic:** Arduino → *"How do I read a value from an analog sensor using
   ADC on Arduino?"*
7. **Topic:** Operating Systems → *"Explain deadlock and its four necessary
   conditions."*
8. **Topic:** Python → *"What is the difference between a list and a tuple?"*
9. **Topic:** Cloud Computing → *"Compare IaaS, PaaS, and SaaS."*
10. **Topic:** Ethical Hacking → *"What is the difference between a black hat
    and a white hat hacker?"*

---

## 5. Viva Explanation Guide

**Problem Statement:**
Students juggle many subjects (CS, AI, embedded systems, electronics, etc.)
and struggle to find trustworthy explanations plus real learning resources in
one place. Generic chatbots answer questions but don't verify or surface real
resource links, and don't help organize notes, quizzes, or progress.

**Proposed Solution:**
StudyMate AI combines a large-language model (Gemini) for structured,
level-aware explanations with a real-time web search engine (Tavily) for
verified resource discovery — wrapped in a single Streamlit dashboard that
also handles notes processing, quiz generation, bookmarking, and progress
tracking, all in one session.

**Architecture:**
A modular Python/Streamlit app: `app.py` is the presentation layer; the
`services/` package isolates external API calls (Gemini, Tavily) and business
logic (quiz scoring, orchestration); `utils/` holds cross-cutting concerns
(session state, PDF parsing, helpers). `StudyAssistantApp.invoke()` is the
single orchestration entry point that ties Gemini + Tavily + notes context
together and returns one structured response.

**Role of Gemini:** Natural-language reasoning engine. Given a strict system
prompt, it returns **structured JSON** (explanation, definition, summary, key
points, examples, mistakes, exam tips, further learning) tailored to the
student's level and learning style — this is prompt engineering in action.

**Role of Tavily:** Real-time web search / information retrieval. It returns
actual indexed pages (title, URL, snippet) for a query built from
topic + question + resource-type keywords. These verified URLs are shown
directly to the student and optionally passed to Gemini as grounding context
so Gemini never has to invent a link.

**PDF Processing:** `pypdf` extracts raw text per page from uploaded PDFs (or
reads TXT directly); the text is capped and fed to Gemini as extra context for
Summarize / Explain / Generate Questions / Generate Quiz / Ask-from-Notes /
Revision Points — all grounded strictly in the uploaded material.

**Prompt Engineering:** Every Gemini call uses a strict system instruction
enforcing: level-appropriate tone, separation of fact vs. example, a fixed
JSON schema, and an explicit rule never to fabricate URLs — only URLs
literally present in the supplied web context may be echoed back.

**Resource Recommendation:** The Resource Hub and AI Tutor's Resources tab
both surface Tavily's real results as clickable resource cards, filterable by
type (courses, tutorials, docs, videos, etc.) and optionally restricted to a
preferred domain list from Settings.

**Quiz Generation:** Gemini generates multiple-choice questions (4 options +
correct answer + explanation) either from a chosen subject/difficulty or
directly from uploaded notes; `quiz_service.py` scores answers locally and
reports which topics need revision.

**Advantages:** single tool for explanation + verified resources + notes +
quizzes + progress; no fabricated links; gracefully degrades if an API key is
missing; runs entirely locally with one command.

**Limitations:** progress/history/bookmarks are session-only (reset on
restart) since no database is used; explanation quality depends on the LLM;
web search results depend on Tavily's index and can vary run to run.

**Future Scope:** persistent storage (SQLite/Firebase) for multi-session
progress, user accounts/login, spaced-repetition flashcards, voice input,
multi-language support, and analytics dashboards for instructors.

---

## 6. Notes

- Never commit your real `.env` — only `.env.example` should be in version
  control (already handled by `.gitignore`).
- The Gemini model used is configurable via `GEMINI_MODEL` in `.env`
  (defaults to `gemini-2.5-flash`).
- All resource URLs shown anywhere in the app come directly from Tavily's
  live search results — none are hard-coded.
