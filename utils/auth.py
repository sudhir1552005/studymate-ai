"""
auth.py

Authentication system for StudyMate AI.

Features:
- Sign Up
- Login
- Logout
- Forgot Password
- Password Reset
- Secure bcrypt password hashing
- Per-user session identity

UI NOTE:
render_auth_page() now renders a dark, futuristic AI-SaaS themed
authentication screen (glass panels, animated gradient background,
decorative top nav, gradient segmented tabs). No backend logic,
database calls, or session-state keys used elsewhere in the app
have been removed, renamed, or altered.
"""

import random
import textwrap
from datetime import datetime, timedelta

import streamlit as st
import bcrypt

from database.database import (
    create_user,
    get_user_by_email,
    update_last_login,
    create_password_reset,
    verify_password_reset_code,
    complete_password_reset,
)

from utils.helpers import now_str


# ============================================================
# PASSWORD HELPERS
# ============================================================

def hash_password(password: str) -> str:

    password_bytes = password.encode("utf-8")

    hashed = bcrypt.hashpw(
        password_bytes,
        bcrypt.gensalt()
    )

    return hashed.decode("utf-8")


def verify_password(
    password: str,
    password_hash: str
) -> bool:

    try:

        return bcrypt.checkpw(
            password.encode("utf-8"),
            password_hash.encode("utf-8")
        )

    except Exception:

        return False


# ============================================================
# LOGIN
# ============================================================

def login_user(
    email: str,
    password: str
):

    email = email.strip().lower()

    if not email:

        return {
            "success": False,
            "error": "Please enter your email address.",
            "user": None,
        }

    if not password:

        return {
            "success": False,
            "error": "Please enter your password.",
            "user": None,
        }

    user = get_user_by_email(email)

    if not user:

        return {
            "success": False,
            "error": "No account found with this email.",
            "user": None,
        }

    if not verify_password(
        password,
        user["password_hash"]
    ):

        return {
            "success": False,
            "error": "Incorrect password.",
            "user": None,
        }

    update_last_login(
        user["id"],
        now_str()
    )

    return {
        "success": True,
        "error": None,
        "user": user,
    }


# ============================================================
# SIGN UP
# ============================================================

def signup_user(
    name: str,
    email: str,
    password: str,
    confirm_password: str
):

    name = name.strip()

    email = email.strip().lower()

    if not name:

        return {
            "success": False,
            "error": "Please enter your name.",
            "user": None,
        }

    if len(name) < 2:

        return {
            "success": False,
            "error": "Name must contain at least 2 characters.",
            "user": None,
        }

    if not email:

        return {
            "success": False,
            "error": "Please enter your email address.",
            "user": None,
        }

    if "@" not in email or "." not in email:

        return {
            "success": False,
            "error": "Please enter a valid email address.",
            "user": None,
        }

    if not password:

        return {
            "success": False,
            "error": "Please enter a password.",
            "user": None,
        }

    if len(password) < 8:

        return {
            "success": False,
            "error": "Password must contain at least 8 characters.",
            "user": None,
        }

    if password != confirm_password:

        return {
            "success": False,
            "error": "Passwords do not match.",
            "user": None,
        }

    password_hash = hash_password(password)

    result = create_user(
        name,
        email,
        password_hash,
        now_str(),
    )

    if not result["success"]:

        return {
            "success": False,
            "error": result["error"],
            "user": None,
        }

    user = get_user_by_email(email)

    return {
        "success": True,
        "error": None,
        "user": user,
    }


# ============================================================
# SET AUTHENTICATED USER
# ============================================================

def set_authenticated_user(
    user: dict
):

    st.session_state.authenticated = True

    st.session_state.user_id = int(
        user["id"]
    )

    st.session_state.user_name = (
        user["name"]
    )

    st.session_state.user_email = (
        user["email"]
    )

    st.session_state._user_data_loaded_for = None


# ============================================================
# FORGOT PASSWORD
# ============================================================

def generate_reset_code():

    return str(
        random.randint(100000, 999999)
    )


def request_password_reset(
    email: str
):

    email = email.strip().lower()

    if not email:

        return {
            "success": False,
            "error": "Please enter your email address.",
            "user": None,
        }

    user = get_user_by_email(email)

    if not user:

        return {
            "success": False,
            "error": "No account found with this email.",
            "user": None,
        }

    # Six-digit reset code
    reset_code = generate_reset_code()

    # Code is valid for 10 minutes
    expires_at = (
        datetime.now() + timedelta(minutes=10)
    ).strftime("%Y-%m-%d %H:%M:%S")

    create_password_reset(
        user["id"],
        reset_code,
        expires_at,
        now_str()
    )

    return {
        "success": True,
        "error": None,
        "user": user,
        "reset_code": reset_code,
        "expires_at": expires_at,
    }


def reset_password(
    user_id: int,
    reset_code: str,
    new_password: str,
    confirm_password: str
):

    reset_code = reset_code.strip()

    if not reset_code:

        return {
            "success": False,
            "error": "Please enter the reset code."
        }

    if not reset_code.isdigit() or len(reset_code) != 6:

        return {
            "success": False,
            "error": "Reset code must contain 6 digits."
        }

    if not new_password:

        return {
            "success": False,
            "error": "Please enter a new password."
        }

    if len(new_password) < 8:

        return {
            "success": False,
            "error": "Password must contain at least 8 characters."
        }

    if new_password != confirm_password:

        return {
            "success": False,
            "error": "Passwords do not match."
        }

    current_time = now_str()

    valid_code = verify_password_reset_code(
        user_id,
        reset_code,
        current_time
    )

    if not valid_code:

        return {
            "success": False,
            "error": "Invalid or expired reset code."
        }

    new_password_hash = hash_password(
        new_password
    )

    success = complete_password_reset(
        user_id,
        reset_code,
        new_password_hash,
        current_time
    )

    if not success:

        return {
            "success": False,
            "error": "Password reset failed. Please request a new code."
        }

    return {
        "success": True,
        "error": None
    }


# ============================================================
# LOGOUT
# ============================================================

def logout_user():
    """
    Safely log out the current user.

    We keep the application session-state structure intact
    and only reset the authentication/user identity.
    """

    # Reset authentication
    st.session_state.authenticated = False
    st.session_state.user_id = None
    st.session_state.user_name = ""
    st.session_state.user_email = ""
    st.session_state.auth_mode = "login"

    # Reset user-data loading marker
    st.session_state._user_data_loaded_for = None

    # Reset temporary/user-specific data
    st.session_state.history = []
    st.session_state.bookmarks = []

    st.session_state.notes_text = ""
    st.session_state.notes_filename = ""

    st.session_state.current_quiz = None
    st.session_state.quiz_submitted = False
    st.session_state.quiz_answers = {}
    st.session_state.quiz_history = []

    st.session_state.topics_studied = set()

    st.session_state.questions_asked = 0
    st.session_state.quizzes_completed = 0
    st.session_state.resources_found = 0
    st.session_state.resources_opened = 0
    st.session_state.study_sessions = 0

    st.session_state.last_ai_result = None
    st.session_state.last_error = None

    # Reset page
    st.session_state.current_page = "🏠 Dashboard"


# ============================================================
# UI HELPER — decorative star field (cosmetic only)
# ============================================================

_STAR_POSITIONS = [
    (6, 12, 0.0), (14, 82, 1.1), (22, 46, 2.3), (9, 65, 0.6),
    (31, 91, 1.8), (18, 30, 2.9), (40, 8, 0.4), (48, 74, 1.4),
    (60, 20, 2.1), (66, 88, 0.9), (75, 40, 1.6), (82, 60, 2.6),
    (90, 15, 0.2), (95, 70, 1.2), (28, 55, 0.7), (55, 95, 2.0),
]


def _render_star_field() -> str:

    stars = []

    for top, left, delay in _STAR_POSITIONS:

        stars.append(
            f'<div class="sm-star" style="top:{top}%; left:{left}%; '
            f'animation-delay:{delay}s;"></div>'
        )

    return "".join(stars)


# ============================================================
# UI HELPER — PASSWORD STRENGTH (display only, no logic change)
# ============================================================

def _password_strength(password: str):
    """
    Returns (score 0-4, label, css_class) for a simple visual
    password-strength indicator. Purely cosmetic — does NOT
    affect validation, which still happens in signup_user().
    """

    if not password:
        return 0, "", ""

    score = 0

    if len(password) >= 8:
        score += 1
    if len(password) >= 12:
        score += 1
    if any(c.isdigit() for c in password):
        score += 1
    if any(c.isupper() for c in password) and any(c.islower() for c in password):
        score += 1
    if any(not c.isalnum() for c in password):
        score += 1

    score = min(score, 4)

    labels = {
        0: ("Very weak", "sm-weak"),
        1: ("Weak", "sm-weak"),
        2: ("Fair", "sm-fair"),
        3: ("Good", "sm-good"),
        4: ("Strong", "sm-strong"),
    }

    label, css_class = labels[score]

    return score, label, css_class


# ============================================================
# LOGIN / SIGNUP / FORGOT PASSWORD UI
# ============================================================

def render_auth_page():

    if st.session_state.get(
        "authenticated",
        False
    ):

        return True


    # --------------------------------------------------------
    # Initialize forgot-password / auth-mode session variables
    # --------------------------------------------------------

    if "forgot_user_id" not in st.session_state:
        st.session_state.forgot_user_id = None

    if "forgot_email" not in st.session_state:
        st.session_state.forgot_email = ""

    if "forgot_code_sent" not in st.session_state:
        st.session_state.forgot_code_sent = False

    if "forgot_reset_code" not in st.session_state:
        st.session_state.forgot_reset_code = ""

    if "forgot_expires_at" not in st.session_state:
        st.session_state.forgot_expires_at = ""

    if "auth_mode" not in st.session_state:
        st.session_state.auth_mode = "login"


    # --------------------------------------------------------
    # STYLING — dark futuristic AI-SaaS theme (auth screen only)
    # --------------------------------------------------------

    st.markdown(
        textwrap.dedent(
        """
        <style>

        :root {
            --sm-purple: #7C3AED;
            --sm-purple-2: #6366F1;
            --sm-blue: #3B82F6;
            --sm-blue-2: #2563EB;
            --sm-cyan: #22D3EE;
            --sm-cyan-2: #06B6D4;
            --sm-white: #F8FAFC;
            --sm-muted: #94A3B8;
            --sm-border: rgba(255,255,255,0.12);
            --sm-glass: rgba(15,23,42,0.55);
        }

        /* Hide Streamlit chrome on the auth screen for a landing-page feel */
        header[data-testid="stHeader"] { background: transparent !important; }
        #MainMenu, footer { visibility: hidden; }

        .block-container {
            padding-top: 1.2rem !important;
            padding-bottom: 0rem !important;
            max-width: 1300px !important;
        }

        /* ---------- Full futuristic animated background ---------- */
        .stApp {
            background:
                radial-gradient(ellipse 900px 600px at 15% 20%, rgba(124,58,237,0.35) 0%, rgba(124,58,237,0) 60%),
                radial-gradient(ellipse 900px 700px at 85% 75%, rgba(34,211,238,0.22) 0%, rgba(34,211,238,0) 60%),
                radial-gradient(ellipse 700px 500px at 70% 15%, rgba(59,130,246,0.20) 0%, rgba(59,130,246,0) 60%),
                linear-gradient(160deg, #020617 0%, #0B0F3A 45%, #111B55 75%, #24105F 100%);
            background-attachment: fixed;
        }

        /* Subtle animated grid overlay */
        .sm-grid-overlay {
            position: fixed;
            inset: 0;
            z-index: 0;
            pointer-events: none;
            background-image:
                linear-gradient(rgba(255,255,255,0.035) 1px, transparent 1px),
                linear-gradient(90deg, rgba(255,255,255,0.035) 1px, transparent 1px);
            background-size: 48px 48px;
            mask-image: radial-gradient(ellipse 80% 80% at 50% 30%, black 40%, transparent 100%);
        }

        /* Large slow-moving glow orbs */
        .sm-orb {
            position: fixed;
            border-radius: 9999px;
            filter: blur(90px);
            opacity: 0.55;
            z-index: 0;
            pointer-events: none;
            animation: sm-orb-float 16s ease-in-out infinite;
        }
        .sm-orb-a {
            width: 420px; height: 420px;
            top: -120px; left: -100px;
            background: radial-gradient(circle, var(--sm-purple) 0%, transparent 70%);
        }
        .sm-orb-b {
            width: 460px; height: 460px;
            bottom: -160px; right: -120px;
            background: radial-gradient(circle, var(--sm-cyan) 0%, transparent 70%);
            animation-delay: 3s;
        }
        .sm-orb-c {
            width: 320px; height: 320px;
            top: 30%; right: 8%;
            background: radial-gradient(circle, var(--sm-blue) 0%, transparent 70%);
            animation-delay: 6s;
            opacity: 0.35;
        }
        @keyframes sm-orb-float {
            0%, 100% { transform: translate(0px, 0px) scale(1); }
            50%      { transform: translate(24px, -22px) scale(1.05); }
        }

        /* Flowing light streak */
        .sm-streak {
            position: fixed;
            z-index: 0;
            pointer-events: none;
            width: 900px;
            height: 240px;
            left: 5%;
            top: 55%;
            background: linear-gradient(100deg, transparent 0%, rgba(139,92,246,0.16) 35%, rgba(34,211,238,0.14) 55%, transparent 80%);
            filter: blur(20px);
            transform: rotate(-8deg);
            animation: sm-streak-drift 20s ease-in-out infinite;
        }
        @keyframes sm-streak-drift {
            0%, 100% { transform: rotate(-8deg) translateX(0px); }
            50%      { transform: rotate(-8deg) translateX(40px); }
        }

        /* Twinkling star field */
        .sm-star {
            position: fixed;
            width: 3px;
            height: 3px;
            border-radius: 9999px;
            background: #ffffff;
            z-index: 0;
            pointer-events: none;
            animation: sm-twinkle 4.5s ease-in-out infinite;
        }
        @keyframes sm-twinkle {
            0%, 100% { opacity: 0.15; }
            50%      { opacity: 0.9; }
        }

        /* ---------- Decorative top navigation ---------- */
        .sm-nav {
            position: relative;
            z-index: 2;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 14px 28px;
            border-radius: 9999px;
            background: rgba(15,23,42,0.45);
            border: 1px solid var(--sm-border);
            backdrop-filter: blur(16px);
            box-shadow: 0 0 30px rgba(99,102,241,0.15);
            margin-bottom: 34px;
            flex-wrap: wrap;
            gap: 10px;
        }
        .sm-nav-brand {
            font-weight: 800;
            font-size: 16px;
            color: var(--sm-white);
            letter-spacing: 0.02em;
        }
        .sm-nav-links {
            display: flex;
            gap: 28px;
            font-size: 14px;
            color: #CBD5E1;
            font-weight: 500;
        }
        .sm-nav-cta {
            background: rgba(99,102,241,0.18);
            border: 1px solid rgba(139,92,246,0.4);
            color: var(--sm-white);
            padding: 7px 16px;
            border-radius: 9999px;
            font-size: 13.5px;
            font-weight: 600;
        }

        /* ---------- Hero (left) content ---------- */
        .sm-pill {
            display: inline-block;
            font-size: 12.5px;
            font-weight: 600;
            color: #C4B5FD;
            background: rgba(124,58,237,0.16);
            border: 1px solid rgba(139,92,246,0.35);
            padding: 6px 16px;
            border-radius: 9999px;
            margin-bottom: 20px;
            position: relative;
            z-index: 1;
        }
        .sm-hero-title {
            position: relative;
            z-index: 1;
            font-size: 46px;
            font-weight: 900;
            line-height: 1.05;
            color: var(--sm-white);
            margin-bottom: 10px;
            letter-spacing: -0.01em;
        }
        .sm-hero-title .sm-grad {
            background: linear-gradient(90deg, var(--sm-purple-2), var(--sm-cyan));
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
        }
        .sm-hero-headline {
            position: relative;
            z-index: 1;
            font-size: 21px;
            font-weight: 700;
            color: #E2E8F0;
            margin-bottom: 12px;
        }
        .sm-hero-sub {
            position: relative;
            z-index: 1;
            font-size: 14.5px;
            color: var(--sm-muted);
            line-height: 1.6;
            margin-bottom: 30px;
            max-width: 480px;
        }

        /* ---------- Feature cards ---------- */
        .sm-feature {
            position: relative;
            z-index: 1;
            display: flex;
            gap: 16px;
            align-items: flex-start;
            background: var(--sm-glass);
            border: 1px solid var(--sm-border);
            border-radius: 18px;
            padding: 18px 20px;
            margin-bottom: 14px;
            backdrop-filter: blur(12px);
            transition: transform 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease;
        }
        .sm-feature:hover {
            transform: translateY(-3px);
            border-color: rgba(139,92,246,0.5);
            box-shadow: 0 10px 30px -10px rgba(99,102,241,0.35);
        }
        .sm-icon-box {
            min-width: 46px;
            height: 46px;
            border-radius: 13px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 21px;
        }
        .sm-icon-purple { background: linear-gradient(135deg, #6366F1, #7C3AED); }
        .sm-icon-cyan   { background: linear-gradient(135deg, #0EA5E9, #22D3EE); }
        .sm-icon-teal   { background: linear-gradient(135deg, #059669, #14B8A6); }
        .sm-feature-title {
            font-size: 15.5px;
            font-weight: 700;
            color: var(--sm-white);
            margin-bottom: 3px;
        }
        .sm-feature-desc {
            font-size: 13px;
            color: var(--sm-muted);
            line-height: 1.5;
        }

        .sm-quote {
            position: relative;
            z-index: 1;
            font-style: italic;
            font-size: 15px;
            color: #CBD5E1;
            margin-top: 22px;
        }
        .sm-quote-line {
            width: 56px;
            height: 3px;
            border-radius: 9999px;
            margin-top: 10px;
            background: linear-gradient(90deg, var(--sm-purple-2), var(--sm-cyan));
            box-shadow: 0 0 12px rgba(99,102,241,0.7);
        }

        /* ---------- Auth card (right) ---------- */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 28px !important;
            border: 1px solid var(--sm-border) !important;
            background: var(--sm-glass) !important;
            backdrop-filter: blur(20px);
            box-shadow:
                0 0 60px rgba(99,102,241,0.20),
                inset 0 1px 0 rgba(255,255,255,0.06) !important;
            padding: 14px 8px !important;
            animation: sm-card-in 0.6s ease;
        }
        @keyframes sm-card-in {
            from { opacity: 0; transform: translateY(14px); }
            to   { opacity: 1; transform: translateY(0px); }
        }

        .sm-card-title {
            font-size: 24px;
            font-weight: 800;
            color: var(--sm-white);
            margin-bottom: 4px;
        }
        .sm-card-subtitle {
            font-size: 13.5px;
            color: var(--sm-muted);
            margin-bottom: 22px;
        }

        /* ---------- Segmented control buttons ---------- */
        .stButton > button {
            border-radius: 12px !important;
            font-weight: 600 !important;
            transition: all 0.2s ease-in-out !important;
        }
        .stButton > button[kind="primary"] {
            background: linear-gradient(90deg, var(--sm-purple) 0%, var(--sm-blue) 55%, var(--sm-cyan) 100%) !important;
            border: none !important;
            color: #ffffff !important;
            box-shadow: 0 10px 26px -8px rgba(99,102,241,0.65);
        }
        .stButton > button[kind="primary"]:hover {
            transform: translateY(-1px);
            box-shadow: 0 14px 32px -8px rgba(34,211,238,0.55);
        }
        .stButton > button[kind="secondary"] {
            background: rgba(255,255,255,0.04) !important;
            border: 1px solid var(--sm-border) !important;
            color: #CBD5E1 !important;
        }
        .stButton > button[kind="secondary"]:hover {
            background: rgba(255,255,255,0.09) !important;
            border-color: rgba(139,92,246,0.5) !important;
            transform: translateY(-1px);
        }

        /* ---------- Inputs ---------- */
        .stTextInput > div > div > input,
        div[data-baseweb="input"] input,
        div[data-baseweb="base-input"] input {
            border-radius: 12px !important;
            border: 1px solid var(--sm-border) !important;
            background-color: transparent !important;
            color: #0F172A !important;
            -webkit-text-fill-color: #0F172A !important;
            caret-color: #0F172A !important;
            padding: 10px 14px 10px 42px !important;
            transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
        }
        .stTextInput > div > div,
        div[data-baseweb="base-input"] {
            background: #F1F5F9 !important;
            border-radius: 12px !important;
        }
        .stTextInput > div > div > input::placeholder {
            color: rgba(71,85,105,0.65) !important;
            -webkit-text-fill-color: rgba(71,85,105,0.65) !important;
        }
        .stTextInput > div > div > input:focus {
            border-color: var(--sm-cyan) !important;
            box-shadow: 0 0 0 3px rgba(34,211,238,0.18) !important;
        }
        .stTextInput > label {
            font-weight: 600 !important;
            color: #E2E8F0 !important;
            font-size: 13px !important;
        }
        .stTextInput input[type="password"] {
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%2394A3B8' stroke-width='1.5'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' d='M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 0h10.5a1.5 1.5 0 011.5 1.5v7.5a1.5 1.5 0 01-1.5 1.5h-10.5a1.5 1.5 0 01-1.5-1.5v-7.5a1.5 1.5 0 011.5-1.5z'/%3E%3C/svg%3E") !important;
            background-repeat: no-repeat !important;
            background-position: 14px center !important;
            background-size: 18px 18px !important;
        }
        .stTextInput input[aria-label*="Email"] {
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%2394A3B8' stroke-width='1.5'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' d='M2.25 6.75c0-.621.504-1.125 1.125-1.125h17.25c.621 0 1.125.504 1.125 1.125v10.5c0 .621-.504 1.125-1.125 1.125H3.375A1.125 1.125 0 012.25 17.25V6.75zM2.4 6.9l9.6 6 9.6-6'/%3E%3C/svg%3E") !important;
            background-repeat: no-repeat !important;
            background-position: 14px center !important;
            background-size: 18px 18px !important;
        }
        .stTextInput input[aria-label="Full Name"] {
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%2394A3B8' stroke-width='1.5'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' d='M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.5 20.25a8.25 8.25 0 0115 0'/%3E%3C/svg%3E") !important;
            background-repeat: no-repeat !important;
            background-position: 14px center !important;
            background-size: 18px 18px !important;
        }
        .stTextInput input[aria-label="6-Digit Reset Code"] {
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%2394A3B8' stroke-width='1.5'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' d='M15.75 5.25a3 3 0 013 3m3 0a6 6 0 01-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1121.75 8.25z'/%3E%3C/svg%3E") !important;
            background-repeat: no-repeat !important;
            background-position: 14px center !important;
            background-size: 18px 18px !important;
        }

        /* ---------- Password strength meter ---------- */
        .sm-strength-track {
            width: 100%;
            height: 6px;
            border-radius: 9999px;
            background: rgba(255,255,255,0.08);
            margin-top: 6px;
            overflow: hidden;
        }
        .sm-strength-fill {
            height: 100%;
            border-radius: 9999px;
            transition: width 0.3s ease, background 0.3s ease;
        }
        .sm-weak   .sm-strength-fill { background: #F87171; }
        .sm-fair   .sm-strength-fill { background: #FBBF24; }
        .sm-good   .sm-strength-fill { background: #22D3EE; }
        .sm-strong .sm-strength-fill { background: #34D399; }
        .sm-strength-label {
            font-size: 12px;
            font-weight: 600;
            margin-top: 4px;
        }
        .sm-weak   .sm-strength-label { color: #F87171; }
        .sm-fair   .sm-strength-label { color: #FBBF24; }
        .sm-good   .sm-strength-label { color: #22D3EE; }
        .sm-strong .sm-strength-label { color: #34D399; }

        .sm-link-row {
            text-align: right;
            font-size: 12.5px;
            margin-top: -6px;
            margin-bottom: 14px;
            color: #A5B4FC;
        }

        .sm-divider-row {
            display: flex;
            align-items: center;
            gap: 12px;
            margin: 18px 0 14px 0;
            color: var(--sm-muted);
            font-size: 12px;
        }
        .sm-divider-line {
            flex: 1;
            height: 1px;
            background: var(--sm-border);
        }

        .sm-switch-text {
            text-align: center;
            font-size: 13px;
            color: var(--sm-muted);
            margin-bottom: 10px;
        }

        .sm-trust-row {
            text-align: center;
            margin-top: 16px;
            font-size: 12px;
            color: var(--sm-muted);
        }

        /* ---------- Page footer ---------- */
        .sm-footer {
            position: relative;
            z-index: 1;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 46px;
            padding: 18px 6px 30px 6px;
            font-size: 12.5px;
            color: rgba(148,163,184,0.75);
        }
        .sm-footer-left {
            display: flex;
            gap: 24px;
            flex-wrap: wrap;
        }

        /* Collapse hero panel gracefully on narrow screens */
        @media (max-width: 900px) {
            .sm-hero-title { font-size: 34px; }
            .sm-nav-links { display: none; }
        }

        </style>

        <div class="sm-grid-overlay"></div>
        <div class="sm-orb sm-orb-a"></div>
        <div class="sm-orb sm-orb-b"></div>
        <div class="sm-orb sm-orb-c"></div>
        <div class="sm-streak"></div>
        """
        )
        + _render_star_field(),
        unsafe_allow_html=True
    )


    # --------------------------------------------------------
    # DECORATIVE TOP NAV
    # --------------------------------------------------------

    st.markdown(
        textwrap.dedent(
        """
        <div class="sm-nav">
            <div class="sm-nav-brand">🎓 STUDYMATE AI</div>
            <div class="sm-nav-links">
                <span>🏠 Home</span>
                <span>✨ Features</span>
                <span>⚙ How It Works</span>
                <span>ⓘ About</span>
            </div>
            <div class="sm-nav-cta">👤 Student Portal</div>
        </div>
        """
        ),
        unsafe_allow_html=True
    )


    # ========================================================
    # TWO-COLUMN LAYOUT
    # ========================================================

    left_col, right_col = st.columns([1, 1.05])


    # --------------------------------------------------------
    # LEFT — BRAND / HERO PANEL (pure HTML, no widgets)
    # --------------------------------------------------------

    with left_col:

        st.markdown(
            textwrap.dedent(
            """
            <div class="sm-pill">✨ AI-POWERED LEARNING PLATFORM</div>
            <div class="sm-hero-title">STUDYMATE <span class="sm-grad">AI</span></div>
            <div class="sm-hero-headline">Learn smarter. Understand faster.</div>
            <div class="sm-hero-sub">Your personal AI academic companion — powered by advanced AI tutoring and smart, curated web resources.</div>

            <div class="sm-feature">
                <div class="sm-icon-box sm-icon-purple">🤖</div>
                <div>
                    <div class="sm-feature-title">AI Tutor</div>
                    <div class="sm-feature-desc">Personalized explanations for any academic topic.</div>
                </div>
            </div>

            <div class="sm-feature">
                <div class="sm-icon-box sm-icon-cyan">🌐</div>
                <div>
                    <div class="sm-feature-title">Smart Resources</div>
                    <div class="sm-feature-desc">Discover useful learning resources from the web.</div>
                </div>
            </div>

            <div class="sm-feature">
                <div class="sm-icon-box sm-icon-teal">📚</div>
                <div>
                    <div class="sm-feature-title">Personalized Learning</div>
                    <div class="sm-feature-desc">Track your study history, quizzes, notes and progress.</div>
                </div>
            </div>

            <div class="sm-quote">"A smarter you, for a brighter tomorrow."</div>
            <div class="sm-quote-line"></div>
            """
            ),
            unsafe_allow_html=True
        )


    # --------------------------------------------------------
    # RIGHT — AUTHENTICATION CARD
    # --------------------------------------------------------

    with right_col:

        with st.container(border=True):

            st.write("")  # small top breathing room inside the card

            # ---------------- Segmented control ----------------

            seg_col1, seg_col2, seg_col3 = st.columns(3)

            modes = [
                ("login", "🔐 Login"),
                ("signup", "📝 Sign Up"),
                ("forgot", "🔑 Reset"),
            ]

            current_mode = st.session_state.auth_mode

            for seg_col, (mode_key, label) in zip(
                [seg_col1, seg_col2, seg_col3], modes
            ):

                with seg_col:

                    btn_type = "primary" if current_mode == mode_key else "secondary"

                    if st.button(
                        label,
                        key=f"seg_{mode_key}",
                        use_container_width=True,
                        type=btn_type,
                    ):

                        st.session_state.auth_mode = mode_key
                        st.rerun()

            st.write("")

            # ============================================
            # LOGIN
            # ============================================

            if current_mode == "login":

                st.markdown(
                    '<div class="sm-card-title">Welcome back 👋</div>',
                    unsafe_allow_html=True
                )
                st.markdown(
                    '<div class="sm-card-subtitle">Sign in to continue your learning journey.</div>',
                    unsafe_allow_html=True
                )

                email = st.text_input(
                    "Email",
                    placeholder="student@example.com",
                    key="login_email"
                )

                password = st.text_input(
                    "Password",
                    type="password",
                    placeholder="Enter your password",
                    key="login_password"
                )

                st.markdown(
                    '<div class="sm-link-row">Forgot password? '
                    'Use the <b>Reset</b> tab above.</div>',
                    unsafe_allow_html=True
                )

                if st.button(
                    "🚀 Sign In",
                    use_container_width=True,
                    type="primary",
                    key="login_submit"
                ):

                    result = login_user(
                        email,
                        password
                    )

                    if result["success"]:

                        set_authenticated_user(
                            result["user"]
                        )

                        st.success(
                            f"Welcome back, "
                            f"{result['user']['name']}! 🎉"
                        )

                        st.rerun()

                    else:

                        st.error(
                            result["error"]
                        )

                st.markdown(
                    textwrap.dedent(
                    """
                    <div class="sm-divider-row">
                        <div class="sm-divider-line"></div>
                        <div>or</div>
                        <div class="sm-divider-line"></div>
                    </div>
                    <div class="sm-switch-text">Don't have an account?</div>
                    """
                    ),
                    unsafe_allow_html=True
                )

                if st.button(
                    "Create Account →",
                    use_container_width=True,
                    type="secondary",
                    key="goto_signup"
                ):

                    st.session_state.auth_mode = "signup"
                    st.rerun()

                st.markdown(
                    '<div class="sm-trust-row">🛡️ Your data is safe and secure.</div>',
                    unsafe_allow_html=True
                )


            # ============================================
            # SIGNUP
            # ============================================

            elif current_mode == "signup":

                st.markdown(
                    '<div class="sm-card-title">Create your StudyMate account 🚀</div>',
                    unsafe_allow_html=True
                )
                st.markdown(
                    '<div class="sm-card-subtitle">Start your personalized learning journey today.</div>',
                    unsafe_allow_html=True
                )

                name = st.text_input(
                    "Full Name",
                    placeholder="Your name",
                    key="signup_name"
                )

                email = st.text_input(
                    "Email Address",
                    placeholder="student@example.com",
                    key="signup_email"
                )

                password = st.text_input(
                    "Password",
                    type="password",
                    placeholder="At least 8 characters",
                    key="signup_password"
                )

                # Password strength indicator (cosmetic only)
                score, label, css_class = _password_strength(password)

                if password:

                    fill_pct = int((score / 4) * 100)

                    st.markdown(
                        textwrap.dedent(
                        f"""
                        <div class="{css_class}">
                            <div class="sm-strength-track">
                                <div class="sm-strength-fill" style="width:{fill_pct}%;"></div>
                            </div>
                            <div class="sm-strength-label">{label}</div>
                        </div>
                        """
                        ),
                        unsafe_allow_html=True
                    )

                confirm_password = st.text_input(
                    "Confirm Password",
                    type="password",
                    placeholder="Enter password again",
                    key="signup_confirm_password"
                )

                st.caption(
                    "🔒 Your password is securely protected."
                )

                if st.button(
                    "✨ Create Account",
                    use_container_width=True,
                    type="primary",
                    key="signup_submit"
                ):

                    result = signup_user(
                        name,
                        email,
                        password,
                        confirm_password,
                    )

                    if result["success"]:

                        set_authenticated_user(
                            result["user"]
                        )

                        st.success(
                            "Account created successfully! 🎉"
                        )

                        st.rerun()

                    else:

                        st.error(
                            result["error"]
                        )

                st.markdown(
                    '<div class="sm-switch-text" style="margin-top:16px;">'
                    'Already have an account?</div>',
                    unsafe_allow_html=True
                )

                if st.button(
                    "← Back to Login",
                    use_container_width=True,
                    type="secondary",
                    key="goto_login_from_signup"
                ):

                    st.session_state.auth_mode = "login"
                    st.rerun()


            # ============================================
            # FORGOT PASSWORD
            # ============================================

            else:  # current_mode == "forgot"

                st.markdown(
                    '<div class="sm-card-title">Forgot your password? 🔑</div>',
                    unsafe_allow_html=True
                )
                st.markdown(
                    '<div class="sm-card-subtitle">Enter your registered email address to '
                    "reset your password.</div>",
                    unsafe_allow_html=True
                )

                email = st.text_input(
                    "Registered Email",
                    placeholder="student@example.com",
                    key="forgot_email_input"
                )

                if st.button(
                    "📩 Generate Reset Code",
                    use_container_width=True,
                    type="primary",
                    key="forgot_generate"
                ):

                    result = request_password_reset(
                        email
                    )

                    if result["success"]:

                        st.session_state.forgot_user_id = (
                            result["user"]["id"]
                        )

                        st.session_state.forgot_email = email

                        st.session_state.forgot_code_sent = True

                        st.session_state.forgot_reset_code = (
                            result["reset_code"]
                        )

                        st.session_state.forgot_expires_at = (
                            result["expires_at"]
                        )

                        st.success(
                            "Reset code generated successfully."
                        )

                        st.info(
                            f"🔐 Your reset code is: "
                            f"**{result['reset_code']}**\n\n"
                            f"⏱️ This code expires at "
                            f"{result['expires_at']} "
                            f"(valid for 10 minutes)."
                        )

                    else:

                        st.error(
                            result["error"]
                        )

                if st.session_state.forgot_code_sent:

                    st.markdown(
                        '<div class="sm-divider-row">'
                        '<div class="sm-divider-line"></div>'
                        '<div>step 2</div>'
                        '<div class="sm-divider-line"></div>'
                        '</div>',
                        unsafe_allow_html=True
                    )

                    st.markdown(
                        '<div class="sm-card-title" style="font-size:18px;">'
                        '🔐 Enter verification code</div>',
                        unsafe_allow_html=True
                    )

                    st.caption(
                        "For this local academic project, the reset code "
                        "is displayed above. In a production application, "
                        "this code would be sent by email."
                    )

                    code = st.text_input(
                        "6-Digit Reset Code",
                        max_chars=6,
                        placeholder="123456",
                        key="password_reset_code"
                    )

                    new_password = st.text_input(
                        "New Password",
                        type="password",
                        placeholder="At least 8 characters",
                        key="reset_new_password"
                    )

                    confirm_password = st.text_input(
                        "Confirm New Password",
                        type="password",
                        placeholder="Enter password again",
                        key="reset_confirm_password"
                    )

                    if st.button(
                        "🔄 Reset Password",
                        use_container_width=True,
                        type="primary",
                        key="forgot_reset_submit"
                    ):

                        result = reset_password(
                            st.session_state.forgot_user_id,
                            code,
                            new_password,
                            confirm_password
                        )

                        if result["success"]:

                            st.success(
                                "🎉 Password reset successfully!"
                            )

                            st.info(
                                "You can now switch to the Login tab "
                                "and sign in with your new password."
                            )

                            # Clear reset state
                            st.session_state.forgot_user_id = None
                            st.session_state.forgot_email = ""
                            st.session_state.forgot_code_sent = False
                            st.session_state.forgot_reset_code = ""
                            st.session_state.forgot_expires_at = ""

                        else:

                            st.error(
                                result["error"]
                            )

                st.markdown(
                    '<div class="sm-switch-text" style="margin-top:16px;">'
                    'Remembered your password?</div>',
                    unsafe_allow_html=True
                )

                if st.button(
                    "← Back to Login",
                    use_container_width=True,
                    type="secondary",
                    key="goto_login_from_forgot"
                ):

                    st.session_state.auth_mode = "login"
                    st.rerun()


    # ========================================================
    # PAGE FOOTER
    # ========================================================

    st.markdown(
        textwrap.dedent(
        """
        <div class="sm-footer">
            <div class="sm-footer-left">
                <div>👥 Empowering Students</div>
                <div>🛡️ Secure &amp; Private</div>
                <div>✨ Built for Learners</div>
            </div>
            <div>© 2026 StudyMate AI. All rights reserved.</div>
        </div>
        """
        ),
        unsafe_allow_html=True
    )

    return False