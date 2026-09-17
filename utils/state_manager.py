"""
state_manager.py

Centralized Streamlit session state + persistent per-user StudyMate AI data.

Every student's History, Bookmarks, Notes, Quiz Results, Progress,
and Settings are loaded/saved using the currently authenticated user_id.
"""

import json

import streamlit as st

from database.database import (
    init_db,
    get_history,
    add_history,
    delete_history,
    get_bookmarks,
    add_bookmark as db_add_bookmark,
    remove_bookmark as db_remove_bookmark,
    get_notes,
    save_notes,
    delete_notes,
    get_quiz_history,
    add_quiz_result,
    get_settings,
    save_settings,
    delete_all_user_data,
)

from utils.helpers import now_str


# ============================================================
# CURRENT USER
# ============================================================

def _current_user_id():
    """
    Return the ID of the currently logged-in user.
    """

    return st.session_state.get("user_id")


# ============================================================
# INITIALIZE SESSION STATE
# ============================================================

def init_session_state():
    """
    Initialize all Streamlit session-state values used
    by the StudyMate AI application.
    """

    # Make sure database tables exist.
    init_db()

    defaults = {

        # ----------------------------------------------------
        # Authentication
        # ----------------------------------------------------

        "authenticated": False,

        "user_id": None,

        "user_name": "",

        "user_email": "",

        "auth_mode": "login",


        # ----------------------------------------------------
        # Navigation
        # ----------------------------------------------------

        "current_page": "🏠 Dashboard",


        # ----------------------------------------------------
        # AI Tutor / History
        # ----------------------------------------------------

        "history": [],


        # ----------------------------------------------------
        # Bookmarks
        # ----------------------------------------------------

        "bookmarks": [],


        # ----------------------------------------------------
        # Notes Lab
        # ----------------------------------------------------

        "notes_text": "",

        "notes_filename": "",


        # ----------------------------------------------------
        # Quiz Center
        # ----------------------------------------------------

        "current_quiz": None,

        "quiz_submitted": False,

        "quiz_answers": {},

        "quiz_history": [],


        # ----------------------------------------------------
        # Progress / Statistics
        # ----------------------------------------------------

        "topics_studied": set(),

        "questions_asked": 0,

        "quizzes_completed": 0,

        "resources_found": 0,

        "resources_opened": 0,

        "study_sessions": 0,


        # ----------------------------------------------------
        # Settings
        # ----------------------------------------------------

        "settings_student_level": "Beginner",

        "settings_learning_style": "Simple explanation",

        "settings_resource_count": 6,

        "settings_web_search_enabled": True,

        "settings_preferred_domains": [],


        # ----------------------------------------------------
        # UI / AI state
        # ----------------------------------------------------

        "last_ai_result": None,

        "last_error": None,


        # ----------------------------------------------------
        # Internal state
        # ----------------------------------------------------

        "_user_data_loaded_for": None,

        "_last_quiz_saved": None,
    }


    # --------------------------------------------------------
    # Add missing keys only
    # --------------------------------------------------------

    for key, value in defaults.items():

        if key not in st.session_state:

            # Make copies of mutable objects.
            if isinstance(value, list):

                value = list(value)

            elif isinstance(value, set):

                value = set(value)

            elif isinstance(value, dict):

                value = dict(value)

            st.session_state[key] = value


# ============================================================
# LOAD USER DATA
# ============================================================

def load_user_data(user_id: int):
    """
    Load persistent data belonging ONLY to the authenticated user.

    This is the main function that keeps Student A's data
    separate from Student B's data.
    """

    if not user_id:
        return


    # --------------------------------------------------------
    # Prevent unnecessary database reloads
    # --------------------------------------------------------

    if (
        st.session_state.get("_user_data_loaded_for")
        == user_id
    ):

        return


    # ========================================================
    # HISTORY
    # ========================================================

    history_rows = get_history(user_id)

    history = []

    topics = set()


    for row in history_rows:

        try:

            response = json.loads(
                row["response_json"]
            )

        except Exception:

            response = {}


        history.append({

            "topic":
                row["topic"],

            "question":
                row["question"],

            "response":
                response,

            "timestamp":
                row["created_at"],

        })


        if row["topic"]:

            topics.add(
                row["topic"]
            )


    # ========================================================
    # BOOKMARKS
    # ========================================================

    bookmarks = []

    for row in get_bookmarks(user_id):

        bookmarks.append({

            "title":
                row["title"],

            "url":
                row["url"],

            "domain":
                row["domain"] or "",

            "topic":
                row["topic"] or "",

            "timestamp":
                row["created_at"],

        })


    # ========================================================
    # NOTES
    # ========================================================

    notes = get_notes(user_id)


    # ========================================================
    # QUIZ HISTORY
    # ========================================================

    quiz_rows = get_quiz_history(user_id)

    quiz_history = []


    for row in quiz_rows:

        quiz_history.append({

            "subject":
                row["subject"],

            "score":
                row["score"],

            "total":
                row["total"],

            "timestamp":
                row["created_at"],

        })


    # ========================================================
    # SETTINGS
    # ========================================================

    settings = get_settings(user_id) or {}


    # ========================================================
    # UPDATE SESSION STATE
    # ========================================================

    st.session_state.history = history

    st.session_state.bookmarks = bookmarks

    st.session_state.quiz_history = quiz_history

    st.session_state.topics_studied = topics

    st.session_state.questions_asked = len(
        history
    )

    st.session_state.quizzes_completed = len(
        quiz_history
    )

    st.session_state.study_sessions = len(
        history
    )

    st.session_state.resources_found = 0

    st.session_state.resources_opened = 0


    # --------------------------------------------------------
    # Reset current quiz state
    # --------------------------------------------------------

    st.session_state.current_quiz = None

    st.session_state.quiz_submitted = False

    st.session_state.quiz_answers = {}


    # --------------------------------------------------------
    # Reset temporary AI state
    # --------------------------------------------------------

    st.session_state.last_ai_result = None

    st.session_state.last_error = None


    # ========================================================
    # LOAD NOTES
    # ========================================================

    if notes:

        st.session_state.notes_text = (
            notes["content"]
        )

        st.session_state.notes_filename = (
            notes["filename"]
        )

    else:

        st.session_state.notes_text = ""

        st.session_state.notes_filename = ""


    # ========================================================
    # LOAD SETTINGS
    # ========================================================

    st.session_state.settings_student_level = (

        settings.get(
            "student_level",
            "Beginner"
        )

    )


    st.session_state.settings_learning_style = (

        settings.get(
            "learning_style",
            "Simple explanation"
        )

    )


    try:

        st.session_state.settings_resource_count = int(

            settings.get(
                "resource_count",
                6
            )

        )

    except Exception:

        st.session_state.settings_resource_count = 6


    # SQLite stores boolean values as 0/1.

    st.session_state.settings_web_search_enabled = bool(

        settings.get(
            "web_search_enabled",
            1
        )

    )


    # ========================================================
    # PREFERRED DOMAINS
    # ========================================================

    try:

        preferred_domains = settings.get(
            "preferred_domains_json",
            "[]"
        )

        st.session_state.settings_preferred_domains = (

            json.loads(
                preferred_domains
            )

        )

    except Exception:

        st.session_state.settings_preferred_domains = []


    # ========================================================
    # MARK DATA AS LOADED
    # ========================================================

    st.session_state._user_data_loaded_for = user_id


# ============================================================
# SAVE CURRENT SETTINGS
# ============================================================

def save_current_settings():
    """
    Save the current user's application settings.
    """

    user_id = _current_user_id()

    if not user_id:
        return


    save_settings(

        user_id,

        st.session_state.settings_student_level,

        st.session_state.settings_learning_style,

        st.session_state.settings_resource_count,

        st.session_state.settings_web_search_enabled,

        json.dumps(
            st.session_state.settings_preferred_domains
        ),

    )


# ============================================================
# ADD HISTORY ENTRY
# ============================================================

def add_history_entry(
    topic: str,
    question: str,
    response: dict
):
    """
    Save an AI Tutor interaction for the currently
    authenticated user.
    """

    user_id = _current_user_id()

    if not user_id:
        return


    timestamp = now_str()


    # --------------------------------------------------------
    # Update current session
    # --------------------------------------------------------

    entry = {

        "topic":
            topic,

        "question":
            question,

        "response":
            response,

        "timestamp":
            timestamp,

    }


    st.session_state.history.insert(
        0,
        entry
    )


    st.session_state.questions_asked += 1


    st.session_state.topics_studied.add(
        topic
    )


    st.session_state.study_sessions += 1


    # --------------------------------------------------------
    # Save permanently to database
    # --------------------------------------------------------

    add_history(

        user_id,

        topic,

        question,

        json.dumps(
            response,
            ensure_ascii=False
        ),

        timestamp,

    )


# ============================================================
# ADD BOOKMARK
# ============================================================

def add_bookmark(
    title: str,
    url: str,
    domain: str,
    topic: str
):
    """
    Save a bookmark for the currently authenticated user.
    """

    user_id = _current_user_id()

    if not user_id:
        return


    # --------------------------------------------------------
    # Prevent duplicate URL
    # --------------------------------------------------------

    for bookmark in st.session_state.bookmarks:

        if bookmark["url"] == url:

            return


    timestamp = now_str()


    # --------------------------------------------------------
    # Update session
    # --------------------------------------------------------

    st.session_state.bookmarks.insert(

        0,

        {

            "title":
                title,

            "url":
                url,

            "domain":
                domain,

            "topic":
                topic,

            "timestamp":
                timestamp,

        }

    )


    # --------------------------------------------------------
    # Save to database
    # --------------------------------------------------------

    db_add_bookmark(

        user_id,

        title,

        url,

        domain,

        topic,

        timestamp,

    )


# ============================================================
# REMOVE BOOKMARK
# ============================================================

def remove_bookmark(url: str):
    """
    Remove a bookmark belonging to the current user.
    """

    user_id = _current_user_id()


    # --------------------------------------------------------
    # Remove from session
    # --------------------------------------------------------

    st.session_state.bookmarks = [

        bookmark

        for bookmark in st.session_state.bookmarks

        if bookmark["url"] != url

    ]


    # --------------------------------------------------------
    # Remove from database
    # --------------------------------------------------------

    if user_id:

        db_remove_bookmark(
            user_id,
            url
        )


# ============================================================
# SAVE USER NOTES
# ============================================================

def save_user_notes(
    filename: str,
    content: str
):
    """
    Save notes belonging to the currently authenticated user.
    """

    user_id = _current_user_id()

    if not user_id:
        return


    timestamp = now_str()


    # --------------------------------------------------------
    # Update session
    # --------------------------------------------------------

    st.session_state.notes_filename = filename

    st.session_state.notes_text = content


    # --------------------------------------------------------
    # Save permanently
    # --------------------------------------------------------

    save_notes(

        user_id,

        filename,

        content,

        timestamp,

    )


# ============================================================
# DELETE USER NOTES
# ============================================================

def delete_user_notes():
    """
    Delete the current user's saved notes.
    """

    user_id = _current_user_id()

    if not user_id:
        return


    delete_notes(
        user_id
    )


    st.session_state.notes_text = ""

    st.session_state.notes_filename = ""


# ============================================================
# RECORD QUIZ RESULT
# ============================================================

def record_quiz_result(
    subject: str,
    score: int,
    total: int
):
    """
    Save a quiz result for the currently authenticated user.
    """

    user_id = _current_user_id()

    if not user_id:
        return


    timestamp = now_str()


    # --------------------------------------------------------
    # Update session
    # --------------------------------------------------------

    st.session_state.quiz_history.insert(

        0,

        {

            "subject":
                subject,

            "score":
                score,

            "total":
                total,

            "timestamp":
                timestamp,

        }

    )


    st.session_state.quizzes_completed += 1


    # --------------------------------------------------------
    # Save permanently
    # --------------------------------------------------------

    add_quiz_result(

        user_id,

        subject,

        score,

        total,

        timestamp,

    )


# ============================================================
# CLEAR ALL USER DATA
# ============================================================

def clear_all_session_data():
    """
    Delete ALL persistent data belonging to the
    currently logged-in user.

    The authentication identity is preserved.
    """

    user_id = _current_user_id()


    # --------------------------------------------------------
    # Delete database data
    # --------------------------------------------------------

    if user_id:

        delete_all_user_data(
            user_id
        )


    # --------------------------------------------------------
    # Preserve authentication
    # --------------------------------------------------------

    keep = {

        "authenticated",

        "user_id",

        "user_name",

        "user_email",

        "auth_mode",

    }


    # --------------------------------------------------------
    # Clear everything else
    # --------------------------------------------------------

    for key in list(
        st.session_state.keys()
    ):

        if key not in keep:

            del st.session_state[key]


    # --------------------------------------------------------
    # Reinitialize state
    # --------------------------------------------------------

    init_session_state()


    # Make sure we don't reload
    # deleted data from database.

    st.session_state._user_data_loaded_for = user_id