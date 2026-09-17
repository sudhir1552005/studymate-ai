"""
StudyMate AI — AI-Powered Multi-Domain Student Study Assistant
================================================================
Run with:  streamlit run app.py

Author: (your name here)
"""

import os
import streamlit as st
from dotenv import load_dotenv

from utils.state_manager import (
    init_session_state, load_user_data, add_history_entry, add_bookmark, remove_bookmark,
    record_quiz_result, clear_all_session_data, save_user_notes, save_current_settings,
)
from utils.auth import render_auth_page, logout_user
from utils.helpers import (
    SUBJECT_CATALOG, get_all_subjects, get_popular_subjects,
    now_str, clean_text, is_blank, truncate,
)
from utils.pdf_utils import extract_text_from_upload
from services.study_assistant import StudyAssistantApp
from services.tavily_service import TavilyService
from services.quiz_service import QuizService

# ---------------------------------------------------------------------------
# APP CONFIG
# ---------------------------------------------------------------------------

load_dotenv()

st.set_page_config(
    page_title="StudyMate AI",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_session_state()

# ---------------------------------------------------------------------------
# AUTHENTICATION GATE
# ---------------------------------------------------------------------------
# Every page below this point is available only after login.
if not render_auth_page():
    st.stop()

# Load data belonging ONLY to the authenticated user.
load_user_data(st.session_state.user_id)


# ---------------------------------------------------------------------------
# CACHED SERVICE INSTANCES (avoid re-creating API clients on every rerun)
# ---------------------------------------------------------------------------

@st.cache_resource
def get_study_assistant():
    return StudyAssistantApp()


@st.cache_resource
def get_tavily_service():
    return TavilyService()


@st.cache_resource
def get_quiz_service():
    return QuizService()


assistant = get_study_assistant()
tavily_service = get_tavily_service()
quiz_service = get_quiz_service()


# ---------------------------------------------------------------------------
# CUSTOM CSS — premium SaaS / EdTech design system
# ---------------------------------------------------------------------------

def inject_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

        #MainMenu, footer, header { visibility: hidden; }

        :root {
            --sm-primary: #4F46E5;
            --sm-primary-dark: #4338CA;
            --sm-secondary: #6366F1;
            --sm-blue: #2563EB;
            --sm-cyan: #06B6D4;
            --sm-bg: #F8FAFC;
            --sm-card: #FFFFFF;
            --sm-text: #0F172A;
            --sm-muted: #64748B;
            --sm-success: #10B981;
            --sm-warning: #F59E0B;
            --sm-error: #EF4444;
            --sm-border: #E2E8F0;
        }

        /* ---- App background: flat, light, no heavy gradient ---- */
        .stApp { background: var(--sm-bg); }
        .main .block-container { padding-top: 1.6rem; padding-bottom: 3rem; }

        /* ---- Sidebar: clean white, not dark ---- */
        section[data-testid="stSidebar"] {
            background: #FFFFFF;
            border-right: 1px solid var(--sm-border);
        }
        section[data-testid="stSidebar"] hr { border-color: var(--sm-border); }
        section[data-testid="stSidebar"] .stCaption, section[data-testid="stSidebar"] small {
            color: var(--sm-muted) !important;
        }

        .sm-logo {
            font-size: 1.45rem;
            font-weight: 800;
            color: var(--sm-text);
            margin-bottom: 0px;
        }
        .sm-tagline {
            font-size: 0.78rem;
            color: var(--sm-muted);
            font-style: italic;
            margin-top: -4px;
            margin-bottom: 4px;
        }

        /* ---- Sidebar navigation styled as pill list ---- */
        section[data-testid="stSidebar"] div[role="radiogroup"] {
            display: flex;
            flex-direction: column;
            gap: 2px;
        }
        section[data-testid="stSidebar"] div[role="radiogroup"] label {
            display: flex;
            align-items: center;
            padding: 10px 14px;
            border-radius: 10px;
            cursor: pointer;
            transition: background 0.15s ease;
        }
        section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
            background: #F1F5F9;
        }
        section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
            background: linear-gradient(90deg, #EEF2FF 0%, #F5F3FF 100%);
        }
        section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) p {
            color: var(--sm-primary) !important;
            font-weight: 700 !important;
        }
        section[data-testid="stSidebar"] div[role="radiogroup"] label p {
            color: var(--sm-text);
            font-size: 0.93rem;
            font-weight: 500;
            margin: 0;
        }

        /* ---- Sidebar profile card ---- */
        .sm-sidebar-profile {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 12px 4px 14px 4px;
        }
        .sm-avatar {
            width: 40px;
            height: 40px;
            min-width: 40px;
            border-radius: 50%;
            background: linear-gradient(135deg, #4F46E5, #2563EB);
            color: #FFFFFF;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 0.9rem;
        }
        .sm-sidebar-profile-name { font-weight: 700; font-size: 0.92rem; color: var(--sm-text); line-height: 1.2; }
        .sm-sidebar-profile-email { font-size: 0.75rem; color: var(--sm-muted); line-height: 1.2; }

        /* ---- Top bar ---- */
        .sm-topbar-title {
            font-size: 1.3rem;
            font-weight: 800;
            color: var(--sm-text);
            padding-top: 6px;
        }
        .sm-topbar-user {
            display: flex;
            align-items: center;
            gap: 10px;
            justify-content: flex-end;
            padding-top: 2px;
        }
        .sm-avatar-sm {
            width: 34px;
            height: 34px;
            min-width: 34px;
            border-radius: 50%;
            background: linear-gradient(135deg, #4F46E5, #2563EB);
            color: #fff;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 0.8rem;
        }
        .sm-topbar-user-name { font-weight: 700; font-size: 0.84rem; color: var(--sm-text); line-height: 1.15; }
        .sm-topbar-user-level { font-size: 0.72rem; color: var(--sm-muted); line-height: 1.15; }
        div[data-testid="stForm"] { border: none; padding: 0; }

        /* ---- Inputs ---- */
        div[data-baseweb="input"] > div, div[data-baseweb="select"] > div, div[data-baseweb="base-input"] {
            border-radius: 10px !important;
            border-color: var(--sm-border) !important;
        }
        div[data-baseweb="input"]:focus-within > div {
            border-color: var(--sm-primary) !important;
            box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.12) !important;
        }

        /* ---- Hero / page header: subtle tint, not a bold gradient ---- */
        .sm-header {
            padding: 22px 28px;
            background: linear-gradient(135deg, #EEF2FF 0%, #F5F3FF 55%, #ECFEFF 100%);
            border: 1px solid var(--sm-border);
            border-radius: 18px;
            color: var(--sm-text);
            margin-bottom: 22px;
        }
        .sm-header h1 { margin: 0; font-size: 1.5rem; font-weight: 800; color: var(--sm-text); }
        .sm-header p { margin: 6px 0 0 0; color: var(--sm-muted); font-size: 0.95rem; }
        .sm-hero-badge {
            display: inline-block;
            margin-top: 12px;
            padding: 4px 13px;
            border-radius: 999px;
            background: linear-gradient(90deg, #4F46E5, #2563EB);
            color: #fff;
            font-size: 0.7rem;
            font-weight: 700;
            letter-spacing: 0.03em;
        }

        .sm-card {
            background: var(--sm-card);
            border-radius: 16px;
            padding: 20px 22px;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05);
            border: 1px solid var(--sm-border);
            margin-bottom: 16px;
        }

        .sm-metric {
            background: var(--sm-card);
            border-radius: 16px;
            padding: 18px 20px;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05);
            border: 1px solid var(--sm-border);
            text-align: left;
            transition: box-shadow 0.15s ease, transform 0.15s ease;
        }
        .sm-metric:hover { box-shadow: 0 8px 20px rgba(15, 23, 42, 0.08); transform: translateY(-2px); }
        .sm-metric .value { font-size: 1.8rem; font-weight: 800; color: var(--sm-text); margin-top: 2px; }
        .sm-metric .label {
            font-size: 0.78rem; color: var(--sm-muted); font-weight: 700;
            text-transform: uppercase; letter-spacing: 0.03em;
        }

        .sm-badge {
            display: inline-block;
            padding: 3px 12px;
            border-radius: 999px;
            font-size: 0.72rem;
            font-weight: 700;
            margin-right: 6px;
        }
        .badge-purple { background: #EDE9FE; color: #6D28D9; }
        .badge-teal   { background: #CCFBF1; color: #0F766E; }
        .badge-green  { background: #D1FAE5; color: #047857; }
        .badge-orange { background: #FEF3C7; color: #B45309; }
        .badge-red    { background: #FEE2E2; color: #B91C1C; }
        .badge-blue   { background: #DBEAFE; color: #1D4ED8; }

        .sm-resource-card {
            background: var(--sm-card);
            border: 1px solid var(--sm-border);
            border-radius: 14px;
            padding: 16px 18px;
            margin-bottom: 12px;
            transition: box-shadow 0.15s ease, transform 0.15s ease;
        }
        .sm-resource-card:hover { box-shadow: 0 8px 20px rgba(15, 23, 42, 0.08); transform: translateY(-2px); }
        .sm-resource-title { font-weight: 700; font-size: 1.02rem; color: var(--sm-text); margin-bottom: 2px; }
        .sm-resource-domain { font-size: 0.78rem; color: var(--sm-primary); font-weight: 600; }
        .sm-resource-desc { font-size: 0.88rem; color: var(--sm-muted); margin-top: 6px; }

        .sm-empty {
            text-align: center;
            padding: 40px 20px;
            color: var(--sm-muted);
        }

        .sm-section-title {
            font-size: 1.1rem;
            font-weight: 800;
            color: var(--sm-text);
            margin: 6px 0 12px 0;
        }

        div.stButton > button {
            border-radius: 10px;
            font-weight: 700;
            border: 1px solid var(--sm-border);
            padding: 0.55rem 1.1rem;
            background: #FFFFFF;
            color: var(--sm-text);
            transition: all 0.15s ease;
        }
        div.stButton > button:hover {
            border-color: #C7D2FE;
            background: #F8FAFF;
        }
        div.stButton > button[kind="primary"] {
            background: linear-gradient(90deg, #4F46E5, #2563EB);
            color: white;
            border: none;
            box-shadow: 0 4px 12px rgba(79, 70, 229, 0.22);
        }
        div.stButton > button[kind="primary"]:hover {
            box-shadow: 0 6px 18px rgba(79, 70, 229, 0.32);
            transform: translateY(-1px);
        }

        .stTabs [data-baseweb="tab-list"] { gap: 6px; }
        .stTabs [data-baseweb="tab"] {
            border-radius: 10px 10px 0 0;
            padding: 8px 16px;
            font-weight: 600;
        }
    </style>
    """, unsafe_allow_html=True)


inject_css()


# ---------------------------------------------------------------------------
# SMALL UI HELPERS
# ---------------------------------------------------------------------------

def page_header(title: str, subtitle: str, badge: str = None):
    badge_html = f'<div class="sm-hero-badge">{badge}</div>' if badge else ""
    st.markdown(f"""
    <div class="sm-header">
        <h1>{title}</h1>
        <p>{subtitle}</p>
        {badge_html}
    </div>
    """, unsafe_allow_html=True)


def metric_card(col, label, value, icon=""):
    col.markdown(f"""
    <div class="sm-metric">
        <div class="label">{icon} {label}</div>
        <div class="value">{value}</div>
    </div>
    """, unsafe_allow_html=True)


def empty_state(message: str, icon: str = "📭"):
    st.markdown(f"""
    <div class="sm-empty">
        <div style="font-size:2.4rem;">{icon}</div>
        <p>{message}</p>
    </div>
    """, unsafe_allow_html=True)


def resource_card(resource: dict, topic_for_bookmark: str = ""):
    title = resource.get("title", "Untitled resource")
    url = resource.get("url", "")
    domain = resource.get("domain", "")
    content = truncate(resource.get("content", ""), 180)

    with st.container():
        st.markdown(f"""
        <div class="sm-resource-card">
            <div class="sm-resource-title">{title}</div>
            <div class="sm-resource-domain">🌐 {domain}</div>
            <div class="sm-resource-desc">{content}</div>
        </div>
        """, unsafe_allow_html=True)
        c1, c2, _ = st.columns([1, 1, 3])
        with c1:
            st.link_button("🔗 Open Resource", url, use_container_width=True)
        with c2:
            if st.button("🔖 Save", key=f"save_{url}", use_container_width=True):
                add_bookmark(title, url, domain, topic_for_bookmark)
                st.toast("Resource bookmarked!", icon="🔖")
        if st.session_state.get(f"_opened_{url}") is None:
            st.session_state[f"_opened_{url}"] = True
            st.session_state.resources_found += 1


def error_box(message: str):
    st.error(f"⚠️ {message}")


def success_box(message: str):
    st.success(f"✅ {message}")


def api_status_banner():
    problems = []
    if not assistant.gemini.available:
        problems.append(f"Gemini AI: {assistant.gemini.init_error}")
    if not assistant.tavily.available:
        problems.append(f"Tavily Search: {assistant.tavily.init_error}")
    if problems:
        with st.container():
            st.warning(
                "**⚙️ Some services are not fully configured.** "
                "Add your API keys to a `.env` file to enable full functionality.\n\n"
                + "\n\n".join(f"- {p}" for p in problems)
            )


def render_top_bar():
    """Global top bar shown above every page: page title, search, notifications,
    a settings shortcut, and the current user's chip. All actions here are real
    (search jumps to AI Tutor with the query pre-filled; settings navigates to
    Settings; notifications shows an honest 'no notifications yet' toast) —
    nothing here fakes functionality that doesn't exist yet."""
    current_page = st.session_state.current_page
    display_title = current_page.split(" ", 1)[1] if " " in current_page else current_page

    tc1, tc2, tc3 = st.columns([2, 4, 3])

    with tc1:
        st.markdown(f'<div class="sm-topbar-title">{display_title}</div>', unsafe_allow_html=True)

    with tc2:
        with st.form("topbar_search_form", clear_on_submit=True):
            sc1, sc2 = st.columns([6, 1])
            with sc1:
                search_query = st.text_input(
                    "Search", placeholder="Search subjects, topics, or ask anything...",
                    label_visibility="collapsed", key="topbar_search_input",
                )
            with sc2:
                search_submitted = st.form_submit_button("🔍")
        if search_submitted and not is_blank(search_query):
            st.session_state["_prefill_topic"] = clean_text(search_query)
            st.session_state.current_page = "🤖 AI Tutor"
            st.rerun()

    with tc3:
        bc1, bc2, bc3 = st.columns([1, 1, 3])
        with bc1:
            if st.button("🔔", key="topbar_notif", help="Notifications"):
                st.toast("You're all caught up! No new notifications.", icon="🔔")
        with bc2:
            if st.button("⚙️", key="topbar_settings_btn", help="Settings"):
                st.session_state.current_page = "⚙️ Settings"
                st.rerun()
        with bc3:
            user_name = st.session_state.get("user_name", "Student") or "Student"
            initials = "".join([p[0].upper() for p in user_name.split()[:2]]) or "S"
            st.markdown(f"""
            <div class="sm-topbar-user">
                <div class="sm-avatar-sm">{initials}</div>
                <div>
                    <div class="sm-topbar-user-name">{user_name}</div>
                    <div class="sm-topbar-user-level">{st.session_state.settings_student_level}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='margin-bottom: 6px;'></div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# PAGE: DASHBOARD
# ---------------------------------------------------------------------------

def render_dashboard():
    page_header("🏠 Dashboard", "Good to see you 👋 — here's your learning snapshot.")
    api_status_banner()

    c1, c2, c3, c4, c5 = st.columns(5)
    metric_card(c1, "Topics Studied", len(st.session_state.topics_studied), "📘")
    metric_card(c2, "Questions Asked", st.session_state.questions_asked, "❓")
    metric_card(c3, "Quizzes Completed", st.session_state.quizzes_completed, "🎯")
    metric_card(c4, "Resources Found", st.session_state.resources_found, "🌐")
    metric_card(c5, "Study Sessions", st.session_state.study_sessions, "⏱️")

    st.markdown("<br>", unsafe_allow_html=True)
    left, right = st.columns([2, 1])

    with left:
        st.markdown('<div class="sm-section-title">🚀 Quick Start</div>', unsafe_allow_html=True)
        qcols = st.columns(3)
        quick_actions = [
            ("🤖 Ask AI Tutor", "🤖 AI Tutor"),
            ("📄 Upload Notes", "📄 Notes Lab"),
            ("🎯 Take a Quiz", "🎯 Quiz Center"),
        ]
        for col, (label, target) in zip(qcols, quick_actions):
            if col.button(label, use_container_width=True, type="primary"):
                st.session_state.current_page = target
                st.rerun()

        st.markdown('<div class="sm-section-title">🔥 Popular Subjects</div>', unsafe_allow_html=True)
        pop_cols = st.columns(4)
        for i, subj in enumerate(get_popular_subjects(8)):
            with pop_cols[i % 4]:
                if st.button(subj, key=f"pop_{subj}", use_container_width=True):
                    st.session_state["_prefill_topic"] = subj
                    st.session_state.current_page = "🤖 AI Tutor"
                    st.rerun()

        st.markdown('<div class="sm-section-title">🕘 Recent Activity</div>', unsafe_allow_html=True)
        if st.session_state.history:
            for entry in st.session_state.history[:5]:
                st.markdown(f"""
                <div class="sm-card">
                    <span class="sm-badge badge-purple">{entry['topic']}</span>
                    <span style="color:#9ca3af; font-size:0.78rem;">{entry['timestamp']}</span>
                    <div style="margin-top:6px; font-weight:600;">{entry['question']}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            empty_state("No activity yet. Ask your first question in the AI Tutor!", "🌱")

    with right:
        st.markdown('<div class="sm-section-title">🎯 Continue Learning</div>', unsafe_allow_html=True)
        if st.session_state.topics_studied:
            for t in list(st.session_state.topics_studied)[:6]:
                st.markdown(f'<span class="sm-badge badge-teal">{t}</span>', unsafe_allow_html=True)
        else:
            empty_state("Your studied topics will appear here.", "🎓")

        st.markdown('<div class="sm-section-title">💡 Recommended</div>', unsafe_allow_html=True)
        recs = ["Machine Learning", "Cyber Security", "Embedded C", "DBMS", "Operating Systems"]
        for r in recs:
            st.markdown(f"- {r}")


# ---------------------------------------------------------------------------
# PAGE: AI TUTOR
# ---------------------------------------------------------------------------

def render_ai_tutor():
    page_header(
        "🤖 AI Tutor",
        "Ask any academic question and get a structured, level-aware explanation.",
        badge="AI-POWERED LEARNING",
    )
    api_status_banner()

    with st.form("ai_tutor_form"):
        c1, c2 = st.columns([1, 1])
        with c1:
            topic = st.text_input(
                "Subject / Topic",
                value=st.session_state.pop("_prefill_topic", ""),
                placeholder="e.g. Cyber Security, Embedded Systems, Python",
            )
        with c2:
            question = st.text_input("Your Question", placeholder="e.g. Explain phishing attacks.")

        c3, c4 = st.columns(2)
        with c3:
            student_level = st.selectbox(
                "Student Level", ["Beginner", "Intermediate", "Advanced"],
                index=["Beginner", "Intermediate", "Advanced"].index(st.session_state.settings_student_level),
            )
        with c4:
            learning_style = st.selectbox(
                "Learning Style",
                ["Simple explanation", "Detailed explanation", "Exam preparation",
                 "Practical/project based", "Interview preparation"],
                index=["Simple explanation", "Detailed explanation", "Exam preparation",
                       "Practical/project based", "Interview preparation"].index(
                    st.session_state.settings_learning_style),
            )

        uploaded_file = st.file_uploader("📎 Optional: Upload PDF/TXT notes for extra context", type=["pdf", "txt"])
        web_search = st.checkbox("🌐 Enable web search for real resources",
                                  value=st.session_state.settings_web_search_enabled)

        submitted = st.form_submit_button("🚀 Start Learning", type="primary", use_container_width=True)

    if submitted:
        topic_c, question_c = clean_text(topic), clean_text(question)

        if is_blank(topic_c):
            error_box("Please enter a subject/topic.")
            return
        if is_blank(question_c):
            error_box("Please enter a question.")
            return

        notes_context = ""
        if uploaded_file is not None:
            extraction = extract_text_from_upload(uploaded_file)
            if extraction["success"]:
                notes_context = extraction["text"]
                st.info(f"📎 {extraction['message']}")
            else:
                st.warning(f"⚠️ Notes not used: {extraction['message']}")

        with st.spinner("🧠 StudyMate AI is thinking..."):
            result = assistant.invoke(
                topic=topic_c, question=question_c, notes=notes_context,
                student_level=student_level, learning_style=learning_style,
                web_search_enabled=web_search,
                resource_count=st.session_state.settings_resource_count,
            )

        if not result["success"]:
            error_box(result["error"])
            return

        add_history_entry(topic_c, question_c, result)
        st.session_state.last_ai_result = result
        success_box("Response generated!")

    result = st.session_state.get("last_ai_result")
    if result and result.get("success"):
        render_ai_result(result)
    elif not submitted:
        empty_state("Fill in a topic and question above, then click 'Start Learning'.", "🧠")


def render_ai_result(result: dict):
    tabs = st.tabs(["📖 Explanation", "✨ Key Points", "💡 Examples",
                     "⚠️ Common Mistakes", "📝 Exam Tips", "🌐 Resources"])

    with tabs[0]:
        if result.get("simple_definition"):
            st.markdown(f"**Definition:** {result['simple_definition']}")
        st.markdown(result.get("explanation", "No explanation available."))
        if result.get("summary"):
            st.markdown("---")
            st.markdown(f"**Summary:** {result['summary']}")

    with tabs[1]:
        pts = result.get("key_points", [])
        if pts:
            for p in pts:
                st.markdown(f"- {p}")
        else:
            empty_state("No key points generated.", "✨")

    with tabs[2]:
        ex = result.get("examples", [])
        if ex:
            for e in ex:
                st.markdown(f"💡 {e}")
        else:
            empty_state("No examples generated.", "💡")

    with tabs[3]:
        mistakes = result.get("common_mistakes", [])
        if mistakes:
            for m in mistakes:
                st.markdown(f"⚠️ {m}")
        else:
            empty_state("No common mistakes listed.", "⚠️")

    with tabs[4]:
        tips = result.get("exam_tips", [])
        if tips:
            for t in tips:
                st.markdown(f"📝 {t}")
        else:
            empty_state("No exam tips generated.", "📝")
        further = result.get("further_learning", [])
        if further:
            st.markdown("---")
            st.markdown("**➡️ Further Learning:**")
            for f in further:
                st.markdown(f"- {f}")

    with tabs[5]:
        resources = result.get("resources", [])
        topic_for_bm = st.session_state.history[0]["topic"] if st.session_state.history else ""
        if resources:
            for r in resources:
                resource_card(r, topic_for_bm)
        else:
            empty_state("No web resources found. Try enabling web search.", "🌐")


# ---------------------------------------------------------------------------
# PAGE: EXPLORE SUBJECTS
# ---------------------------------------------------------------------------

def render_explore_subjects():
    page_header("📚 Explore Subjects", "Browse StudyMate AI's full academic catalog.")

    search = st.text_input("🔍 Search subjects", placeholder="Type to filter...")
    custom = st.text_input("➕ Or type any custom subject not listed below")

    if custom and st.button("Ask about this custom subject", type="primary"):
        st.session_state["_prefill_topic"] = custom
        st.session_state.current_page = "🤖 AI Tutor"
        st.rerun()

    for category, subjects in SUBJECT_CATALOG.items():
        filtered = [s for s in subjects if search.lower() in s.lower()] if search else subjects
        if not filtered:
            continue
        with st.expander(f"{category}  ·  {len(filtered)} topics", expanded=bool(search)):
            cols = st.columns(4)
            for i, subj in enumerate(filtered):
                with cols[i % 4]:
                    if st.button(subj, key=f"subj_{category}_{subj}", use_container_width=True):
                        st.session_state["_prefill_topic"] = subj
                        st.session_state.current_page = "🤖 AI Tutor"
                        st.rerun()


# ---------------------------------------------------------------------------
# PAGE: RESOURCE HUB
# ---------------------------------------------------------------------------

def render_resource_hub():
    page_header("🌐 Resource Hub", "Discover real, verified learning resources across the web.")
    api_status_banner()

    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        topic = st.text_input("Topic", placeholder="e.g. Machine Learning")
    with c2:
        resource_type = st.selectbox(
            "Resource Type",
            ["All", "Courses", "Tutorials", "Documentation", "Videos", "Articles",
             "University material", "Projects"],
        )
    with c3:
        max_results = st.slider("Number of results", 3, 10, st.session_state.settings_resource_count)

    query = st.text_input("Optional: refine your search query", placeholder="e.g. beginner friendly, with projects")

    if st.button("🔍 Search Resources", type="primary", use_container_width=True):
        if is_blank(topic):
            error_box("Please enter a topic to search.")
        else:
            with st.spinner("🔎 Searching the web for real resources..."):
                result = tavily_service.search_resources(
                    topic=clean_text(topic), question=clean_text(query),
                    resource_type=resource_type, max_results=max_results,
                    preferred_domains=st.session_state.settings_preferred_domains or None,
                )
            st.session_state["_resource_hub_result"] = result
            st.session_state["_resource_hub_topic"] = clean_text(topic)

    result = st.session_state.get("_resource_hub_result")
    if result:
        if not result["success"]:
            error_box(result["error"])
        elif not result["results"]:
            empty_state(result.get("message", "No resources found. Try a different topic."), "🔍")
        else:
            st.markdown(f'<div class="sm-section-title">Found {len(result["results"])} resources</div>',
                        unsafe_allow_html=True)
            for r in result["results"]:
                resource_card(r, st.session_state.get("_resource_hub_topic", ""))
    else:
        empty_state("Enter a topic above and click 'Search Resources' to get started.", "🌐")


# ---------------------------------------------------------------------------
# PAGE: NOTES LAB
# ---------------------------------------------------------------------------

def render_notes_lab():
    page_header("📄 Notes Lab", "Upload your study notes and let AI summarize, explain, and quiz you.")
    api_status_banner()

    uploaded_file = st.file_uploader("Upload PDF or TXT notes", type=["pdf", "txt"], key="notes_lab_upload")

    if uploaded_file is not None:
        if st.button("📥 Load Notes", type="primary"):
            with st.spinner("Extracting text..."):
                extraction = extract_text_from_upload(uploaded_file)
            if extraction["success"]:
                st.session_state.notes_text = extraction["text"]
                st.session_state.notes_filename = uploaded_file.name
                save_user_notes(uploaded_file.name, extraction["text"])
                success_box(extraction["message"])
            else:
                error_box(extraction["message"])

    if not st.session_state.notes_text:
        empty_state("Upload a PDF or TXT file and click 'Load Notes' to begin.", "📄")
        return

    st.markdown(f"**📎 Loaded:** `{st.session_state.notes_filename}` "
                f"({len(st.session_state.notes_text)} characters)")
    with st.expander("👀 Preview extracted text"):
        st.text(truncate(st.session_state.notes_text, 2000))

    tabs = st.tabs(["📝 Summarize", "💬 Explain", "❓ Generate Questions",
                     "🎯 Generate Quiz", "🗣️ Ask From Notes", "📌 Revision Points"])

    with tabs[0]:
        if st.button("Generate Summary", key="btn_summarize"):
            with st.spinner("Summarizing..."):
                res = assistant.gemini.process_notes(st.session_state.notes_text, "summarize")
            if res["success"]:
                st.markdown(res["content"])
            else:
                error_box(res["error"])

    with tabs[1]:
        if st.button("Explain Notes", key="btn_explain"):
            with st.spinner("Explaining..."):
                res = assistant.gemini.process_notes(st.session_state.notes_text, "explain")
            if res["success"]:
                st.markdown(res["content"])
            else:
                error_box(res["error"])

    with tabs[2]:
        if st.button("Generate Study Questions", key="btn_questions"):
            with st.spinner("Generating questions..."):
                res = assistant.gemini.process_notes(st.session_state.notes_text, "questions")
            if res["success"]:
                st.markdown(res["content"])
            else:
                error_box(res["error"])

    with tabs[3]:
        num_q = st.slider("Number of quiz questions", 3, 10, 5, key="notes_quiz_count")
        if st.button("Generate Quiz From Notes", key="btn_notes_quiz", type="primary"):
            with st.spinner("Building quiz..."):
                res = quiz_service.generate_quiz_from_notes(st.session_state.notes_text, num_q)
            if res["success"]:
                st.session_state.current_quiz = res["questions"]
                st.session_state.quiz_answers = {}
                st.session_state.quiz_submitted = False
                st.session_state["_last_quiz_saved"] = None
                st.session_state["_quiz_subject"] = st.session_state.notes_filename or "Uploaded Notes"
                success_box("Quiz generated! Head to Quiz Center to take it.")
                if st.button("Go to Quiz Center →"):
                    st.session_state.current_page = "🎯 Quiz Center"
                    st.rerun()
            else:
                error_box(res["error"])

    with tabs[4]:
        note_question = st.text_input("Ask a question about your notes", key="notes_qa_input")
        if st.button("Get Answer", key="btn_notes_qa"):
            if is_blank(note_question):
                error_box("Please type a question.")
            else:
                with st.spinner("Finding the answer..."):
                    res = assistant.gemini.process_notes(
                        st.session_state.notes_text, "answer_question", extra_instruction=note_question)
                if res["success"]:
                    st.markdown(res["content"])
                else:
                    error_box(res["error"])

    with tabs[5]:
        if st.button("Generate Revision Points", key="btn_revision"):
            with st.spinner("Extracting key revision points..."):
                res = assistant.gemini.process_notes(st.session_state.notes_text, "revision_points")
            if res["success"]:
                st.markdown(res["content"])
            else:
                error_box(res["error"])


# ---------------------------------------------------------------------------
# PAGE: QUIZ CENTER
# ---------------------------------------------------------------------------

def render_quiz_center():
    page_header("🎯 Quiz Center", "Test your knowledge with AI-generated quizzes.")
    api_status_banner()

    if not st.session_state.current_quiz:
        c1, c2, c3 = st.columns(3)
        with c1:
            subject = st.text_input("Subject", placeholder="e.g. Data Structures")
        with c2:
            difficulty = st.selectbox("Difficulty", ["Easy", "Medium", "Hard"])
        with c3:
            num_q = st.slider("Number of Questions", 3, 10, 5)

        if st.button("🎲 Generate Quiz", type="primary", use_container_width=True):
            if is_blank(subject):
                error_box("Please enter a subject for the quiz.")
            else:
                with st.spinner("Building your quiz..."):
                    res = quiz_service.generate_quiz(clean_text(subject), difficulty, num_q)
                if res["success"]:
                    st.session_state.current_quiz = res["questions"]
                    st.session_state.quiz_answers = {}
                    st.session_state.quiz_submitted = False
                    st.session_state["_last_quiz_saved"] = None
                    st.session_state["_quiz_subject"] = clean_text(subject)
                    st.rerun()
                else:
                    error_box(res["error"])
        else:
            empty_state("Choose a subject and difficulty, then generate a quiz.", "🎯")
        return

    quiz = st.session_state.current_quiz
    subject = st.session_state.get("_quiz_subject", "Quiz")

    st.markdown(f'<div class="sm-section-title">📘 {subject} — {len(quiz)} Questions</div>',
                unsafe_allow_html=True)

    if not st.session_state.quiz_submitted:
        with st.form("quiz_form"):
            for i, q in enumerate(quiz):
                st.markdown(f"**Q{i+1}. {q['question']}**")
                answer = st.radio(
                    f"quiz_q_{i}", q["options"], index=None,
                    key=f"quiz_radio_{i}", label_visibility="collapsed",
                )
                st.session_state.quiz_answers[i] = answer
                st.markdown("---")

            submitted = st.form_submit_button("✅ Submit Quiz", type="primary", use_container_width=True)

        if submitted:
            st.session_state.quiz_submitted = True
            st.rerun()

        if st.button("🗑️ Discard Quiz"):
            st.session_state.current_quiz = None
            st.session_state.quiz_answers = {}
            st.session_state._last_quiz_saved = None
            st.rerun()

    else:
        scored = quiz_service.score_quiz(quiz, st.session_state.quiz_answers)

        # Save a completed quiz only once.
        quiz_save_key = (
            subject,
            tuple(
                (r.get("question", ""), r.get("selected", ""))
                for r in scored.get("results", [])
            ),
        )
        if st.session_state.get("_last_quiz_saved") != quiz_save_key:
            record_quiz_result(subject, scored["score"], scored["total"])
            st.session_state["_last_quiz_saved"] = quiz_save_key

        pct = (scored["score"] / scored["total"] * 100) if scored["total"] else 0
        badge_class = "badge-green" if pct >= 70 else ("badge-orange" if pct >= 40 else "badge-red")

        st.markdown(f"""
        <div class="sm-card" style="text-align:center;">
            <div style="font-size:1.1rem; font-weight:700;">Your Score</div>
            <div style="font-size:2.4rem; font-weight:800; color:var(--sm-primary);">
                {scored['score']} / {scored['total']}
            </div>
            <span class="sm-badge {badge_class}">{pct:.0f}%</span>
        </div>
        """, unsafe_allow_html=True)

        for i, r in enumerate(scored["results"]):
            icon = "✅" if r["is_correct"] else "❌"
            st.markdown(f"**{icon} Q{i+1}. {r['question']}**")
            st.markdown(f"- Your answer: `{r['selected']}`")
            if not r["is_correct"]:
                st.markdown(f"- Correct answer: `{r['correct_answer']}`")
            st.caption(f"💡 {r['explanation']}")
            st.markdown("---")

        if scored["topics_to_revise"]:
            st.markdown("**📌 Topics to revise:**")
            for t in scored["topics_to_revise"]:
                st.markdown(f"- {t}")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔁 Try Another Quiz", type="primary", use_container_width=True):
                st.session_state.current_quiz = None
                st.session_state.quiz_answers = {}
                st.session_state.quiz_submitted = False
                st.session_state._last_quiz_saved = None
                st.rerun()
        with c2:
            if st.button("🏠 Back to Dashboard", use_container_width=True):
                st.session_state.current_quiz = None
                st.session_state.quiz_answers = {}
                st.session_state.quiz_submitted = False
                st.session_state.current_page = "🏠 Dashboard"
                st.rerun()


# ---------------------------------------------------------------------------
# PAGE: PROGRESS
# ---------------------------------------------------------------------------

def render_progress():
    page_header("📈 Progress", "Track your learning journey this session.")

    c1, c2, c3, c4 = st.columns(4)
    metric_card(c1, "Topics Studied", len(st.session_state.topics_studied), "📘")
    metric_card(c2, "Questions Asked", st.session_state.questions_asked, "❓")
    metric_card(c3, "Quizzes Completed", st.session_state.quizzes_completed, "🎯")
    metric_card(c4, "Study Sessions", st.session_state.study_sessions, "⏱️")

    st.markdown('<div class="sm-section-title">🎯 Quiz Performance</div>', unsafe_allow_html=True)
    if st.session_state.quiz_history:
        chart_data = {
            "Quiz #": [f"#{i+1}" for i in range(len(st.session_state.quiz_history))][::-1],
            "Score %": [
                round(q["score"] / q["total"] * 100, 1) if q["total"] else 0
                for q in st.session_state.quiz_history
            ][::-1],
        }
        st.bar_chart(chart_data, x="Quiz #", y="Score %")

        st.markdown('<div class="sm-section-title">📋 Quiz History</div>', unsafe_allow_html=True)
        for q in st.session_state.quiz_history:
            st.markdown(f"""
            <div class="sm-card">
                <span class="sm-badge badge-purple">{q['subject']}</span>
                <span style="color:#9ca3af; font-size:0.78rem;">{q['timestamp']}</span>
                <div style="margin-top:6px; font-weight:700;">Score: {q['score']} / {q['total']}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        empty_state("Take a quiz to see your performance here.", "📊")

    st.markdown('<div class="sm-section-title">📘 Topics Covered</div>', unsafe_allow_html=True)
    if st.session_state.topics_studied:
        for t in st.session_state.topics_studied:
            st.markdown(f'<span class="sm-badge badge-teal">{t}</span>', unsafe_allow_html=True)
    else:
        empty_state("Topics you study will be tracked here.", "📘")


# ---------------------------------------------------------------------------
# PAGE: BOOKMARKS
# ---------------------------------------------------------------------------

def render_bookmarks():
    page_header("🔖 Bookmarks", "Your saved learning resources.")

    if not st.session_state.bookmarks:
        empty_state("No bookmarks yet. Save resources from the Resource Hub or AI Tutor.", "🔖")
        return

    for b in st.session_state.bookmarks:
        st.markdown(f"""
        <div class="sm-resource-card">
            <div class="sm-resource-title">{b['title']}</div>
            <div class="sm-resource-domain">🌐 {b['domain']} &nbsp;·&nbsp;
                <span class="sm-badge badge-purple">{b['topic'] or 'General'}</span></div>
            <div class="sm-resource-desc">Saved on {b['timestamp']}</div>
        </div>
        """, unsafe_allow_html=True)
        c1, c2, _ = st.columns([1, 1, 3])
        with c1:
            st.link_button("🔗 Open", b["url"], use_container_width=True)
        with c2:
            if st.button("🗑️ Remove", key=f"rm_{b['url']}", use_container_width=True):
                remove_bookmark(b["url"])
                st.rerun()


# ---------------------------------------------------------------------------
# PAGE: HISTORY
# ---------------------------------------------------------------------------

def render_history():
    page_header("💬 History", "Your full conversation history this session.")

    if not st.session_state.history:
        empty_state("No conversation history yet. Ask a question in AI Tutor.", "💬")
        return

    if st.button("🗑️ Clear All History"):
        st.session_state.history = []
        st.rerun()

    for i, entry in enumerate(st.session_state.history):
        with st.expander(f"🕐 {entry['timestamp']} — {entry['topic']}: {truncate(entry['question'], 60)}"):
            st.markdown(f"**Topic:** {entry['topic']}")
            st.markdown(f"**Question:** {entry['question']}")
            st.markdown("---")
            resp = entry["response"]
            if resp.get("summary"):
                st.markdown(f"**Summary:** {resp['summary']}")
            if resp.get("explanation"):
                st.markdown(resp["explanation"])


# ---------------------------------------------------------------------------
# PAGE: SETTINGS
# ---------------------------------------------------------------------------

def render_settings():
    page_header("⚙️ Settings", "Customize your StudyMate AI experience.")

    st.session_state.settings_student_level = st.selectbox(
        "Default Student Level", ["Beginner", "Intermediate", "Advanced"],
        index=["Beginner", "Intermediate", "Advanced"].index(st.session_state.settings_student_level),
    )

    styles = ["Simple explanation", "Detailed explanation", "Exam preparation",
              "Practical/project based", "Interview preparation"]
    st.session_state.settings_learning_style = st.selectbox(
        "Default Learning Style", styles, index=styles.index(st.session_state.settings_learning_style),
    )

    st.session_state.settings_resource_count = st.slider(
        "Default Resource Count", 3, 10, st.session_state.settings_resource_count,
    )

    st.session_state.settings_web_search_enabled = st.checkbox(
        "Enable web search by default", value=st.session_state.settings_web_search_enabled,
    )

    from services.tavily_service import TRUSTED_EDU_DOMAINS
    st.session_state.settings_preferred_domains = st.multiselect(
        "Preferred resource domains (optional — leave empty to search the whole web)",
        TRUSTED_EDU_DOMAINS, default=st.session_state.settings_preferred_domains,
    )

    # Persist these preferences for the currently logged-in student.
    save_current_settings()

    st.markdown("---")
    st.markdown('<div class="sm-section-title">🔐 API Status</div>', unsafe_allow_html=True)
    gc1, gc2 = st.columns(2)
    with gc1:
        if assistant.gemini.available:
            st.success("✅ Gemini API connected")
        else:
            st.error(f"❌ Gemini API: {assistant.gemini.init_error}")
    with gc2:
        if assistant.tavily.available:
            st.success("✅ Tavily API connected")
        else:
            st.error(f"❌ Tavily API: {assistant.tavily.init_error}")

    st.markdown("---")
    st.markdown('<div class="sm-section-title">🧹 Danger Zone</div>', unsafe_allow_html=True)
    if st.button("🗑️ Clear All Session Data", type="primary"):
        clear_all_session_data()
        st.success("All session data cleared.")
        st.rerun()


# ---------------------------------------------------------------------------
# SIDEBAR NAVIGATION
# ---------------------------------------------------------------------------

NAV_ITEMS = [
    "🏠 Dashboard", "🤖 AI Tutor", "📚 Explore Subjects", "🌐 Resource Hub",
    "📄 Notes Lab", "🎯 Quiz Center", "📈 Progress", "🔖 Bookmarks",
    "💬 History", "⚙️ Settings",
]

with st.sidebar:
    st.markdown('<div class="sm-logo">🎓 STUDYMATE AI</div>', unsafe_allow_html=True)
    st.markdown('<div class="sm-tagline">"Learn anything. Build everything."</div>', unsafe_allow_html=True)
    st.markdown("---")

    selected = st.radio(
        "Navigate", NAV_ITEMS, index=NAV_ITEMS.index(st.session_state.current_page),
        label_visibility="collapsed",
    )
    if selected != st.session_state.current_page:
        st.session_state.current_page = selected
        st.rerun()

    st.markdown("---")

    _user_name = st.session_state.get("user_name", "Student") or "Student"
    _initials = "".join([p[0].upper() for p in _user_name.split()[:2]]) or "S"
    st.markdown(f"""
    <div class="sm-sidebar-profile">
        <div class="sm-avatar">{_initials}</div>
        <div>
            <div class="sm-sidebar-profile-name">{_user_name}</div>
            <div class="sm-sidebar-profile-email">{st.session_state.get('user_email', '')}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.caption(f"📘 {len(st.session_state.topics_studied)} topics studied")
    st.caption(f"🎓 Level: {st.session_state.settings_student_level}")

    if st.button("🚪 Logout", use_container_width=True):
        logout_user()

    st.caption("Built with Python + Streamlit + Gemini + Tavily")


# ---------------------------------------------------------------------------
# PAGE ROUTER
# ---------------------------------------------------------------------------

PAGES = {
    "🏠 Dashboard": render_dashboard,
    "🤖 AI Tutor": render_ai_tutor,
    "📚 Explore Subjects": render_explore_subjects,
    "🌐 Resource Hub": render_resource_hub,
    "📄 Notes Lab": render_notes_lab,
    "🎯 Quiz Center": render_quiz_center,
    "📈 Progress": render_progress,
    "🔖 Bookmarks": render_bookmarks,
    "💬 History": render_history,
    "⚙️ Settings": render_settings,
}

render_top_bar()
PAGES[st.session_state.current_page]()