"""
database.py

SQLite database layer for StudyMate AI.

Every student-owned record is connected to a unique user_id.
This keeps each student's History, Notes, Bookmarks, Quiz Results,
and Settings separated from other students.

Also includes Forgot Password / Password Reset support.
"""

from pathlib import Path
import sqlite3


# ============================================================
# DATABASE LOCATION
# ============================================================

DB_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "studymate.db"
)


# ============================================================
# DATABASE CONNECTION
# ============================================================

def _connect():
    """Create a SQLite connection."""

    DB_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    conn = sqlite3.connect(DB_PATH)

    conn.row_factory = sqlite3.Row

    conn.execute(
        "PRAGMA foreign_keys = ON"
    )

    return conn


# ============================================================
# INITIALIZE DATABASE
# ============================================================

def init_db():
    """Create all StudyMate AI tables."""

    with _connect() as conn:

        conn.executescript("""

        CREATE TABLE IF NOT EXISTS users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            email TEXT NOT NULL UNIQUE COLLATE NOCASE,

            password_hash TEXT NOT NULL,

            created_at TEXT NOT NULL,

            last_login TEXT

        );


        CREATE TABLE IF NOT EXISTS study_history (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            topic TEXT NOT NULL,

            question TEXT NOT NULL,

            response_json TEXT NOT NULL,

            created_at TEXT NOT NULL,

            FOREIGN KEY(user_id)
                REFERENCES users(id)
                ON DELETE CASCADE

        );


        CREATE TABLE IF NOT EXISTS bookmarks (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            title TEXT NOT NULL,

            url TEXT NOT NULL,

            domain TEXT,

            topic TEXT,

            created_at TEXT NOT NULL,

            UNIQUE(user_id, url),

            FOREIGN KEY(user_id)
                REFERENCES users(id)
                ON DELETE CASCADE

        );


        CREATE TABLE IF NOT EXISTS notes (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            filename TEXT NOT NULL,

            content TEXT NOT NULL,

            updated_at TEXT NOT NULL,

            UNIQUE(user_id, filename),

            FOREIGN KEY(user_id)
                REFERENCES users(id)
                ON DELETE CASCADE

        );


        CREATE TABLE IF NOT EXISTS quiz_results (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            subject TEXT NOT NULL,

            score INTEGER NOT NULL,

            total INTEGER NOT NULL,

            created_at TEXT NOT NULL,

            FOREIGN KEY(user_id)
                REFERENCES users(id)
                ON DELETE CASCADE

        );


        CREATE TABLE IF NOT EXISTS settings (

            user_id INTEGER PRIMARY KEY,

            student_level TEXT NOT NULL
                DEFAULT 'Beginner',

            learning_style TEXT NOT NULL
                DEFAULT 'Simple explanation',

            resource_count INTEGER NOT NULL
                DEFAULT 6,

            web_search_enabled INTEGER NOT NULL
                DEFAULT 1,

            preferred_domains_json TEXT NOT NULL
                DEFAULT '[]',

            FOREIGN KEY(user_id)
                REFERENCES users(id)
                ON DELETE CASCADE

        );


        CREATE TABLE IF NOT EXISTS password_reset_tokens (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            reset_code TEXT NOT NULL,

            expires_at TEXT NOT NULL,

            used INTEGER NOT NULL DEFAULT 0,

            created_at TEXT NOT NULL,

            FOREIGN KEY(user_id)
                REFERENCES users(id)
                ON DELETE CASCADE

        );

        """)


# ============================================================
# USERS
# ============================================================

def create_user(
    name: str,
    email: str,
    password_hash: str,
    created_at: str
):

    """Create a new student account."""

    init_db()

    try:

        with _connect() as conn:

            cursor = conn.execute(
                """
                INSERT INTO users
                (
                    name,
                    email,
                    password_hash,
                    created_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    name.strip(),
                    email.strip().lower(),
                    password_hash,
                    created_at
                )
            )

            user_id = cursor.lastrowid

            conn.execute(
                """
                INSERT INTO settings(user_id)
                VALUES (?)
                """,
                (user_id,)
            )

            return {
                "success": True,
                "user_id": user_id,
                "error": None
            }

    except sqlite3.IntegrityError:

        return {
            "success": False,
            "user_id": None,
            "error": "An account with this email already exists."
        }

    except Exception as e:

        return {
            "success": False,
            "user_id": None,
            "error": f"Could not create account: {e}"
        }


def get_user_by_email(email: str):

    """Find a student by email."""

    init_db()

    with _connect() as conn:

        row = conn.execute(
            """
            SELECT *
            FROM users
            WHERE email = ?
            COLLATE NOCASE
            """,
            (email.strip().lower(),)
        ).fetchone()

        return dict(row) if row else None


def update_last_login(
    user_id: int,
    timestamp: str
):

    with _connect() as conn:

        conn.execute(
            """
            UPDATE users
            SET last_login = ?
            WHERE id = ?
            """,
            (timestamp, user_id)
        )


def get_user_profile(user_id: int):

    init_db()

    with _connect() as conn:

        row = conn.execute(
            """
            SELECT
                id,
                name,
                email,
                created_at,
                last_login
            FROM users
            WHERE id = ?
            """,
            (user_id,)
        ).fetchone()

        return dict(row) if row else None


# ============================================================
# PASSWORD RESET
# ============================================================

def create_password_reset(
    user_id: int,
    reset_code: str,
    expires_at: str,
    created_at: str
):
    """
    Create a password reset code.

    Old unused reset codes for the same user are invalidated.
    """

    with _connect() as conn:

        conn.execute(
            """
            UPDATE password_reset_tokens
            SET used = 1
            WHERE user_id = ?
            AND used = 0
            """,
            (user_id,)
        )

        conn.execute(
            """
            INSERT INTO password_reset_tokens
            (
                user_id,
                reset_code,
                expires_at,
                used,
                created_at
            )
            VALUES (?, ?, ?, 0, ?)
            """,
            (
                user_id,
                reset_code,
                expires_at,
                created_at
            )
        )


def verify_password_reset_code(
    user_id: int,
    reset_code: str,
    current_time: str
):
    """
    Check whether a reset code is valid and not expired.
    """

    with _connect() as conn:

        row = conn.execute(
            """
            SELECT id
            FROM password_reset_tokens
            WHERE user_id = ?
            AND reset_code = ?
            AND used = 0
            AND expires_at > ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (
                user_id,
                reset_code,
                current_time
            )
        ).fetchone()

        return dict(row) if row else None


def complete_password_reset(
    user_id: int,
    reset_code: str,
    new_password_hash: str,
    current_time: str
):
    """
    Change the user's password if the reset code is valid.

    Returns True if successful.
    """

    with _connect() as conn:

        row = conn.execute(
            """
            SELECT id
            FROM password_reset_tokens
            WHERE user_id = ?
            AND reset_code = ?
            AND used = 0
            AND expires_at > ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (
                user_id,
                reset_code,
                current_time
            )
        ).fetchone()

        if not row:
            return False

        conn.execute(
            """
            UPDATE users
            SET password_hash = ?
            WHERE id = ?
            """,
            (
                new_password_hash,
                user_id
            )
        )

        conn.execute(
            """
            UPDATE password_reset_tokens
            SET used = 1
            WHERE id = ?
            """,
            (row["id"],)
        )

        return True


# ============================================================
# HISTORY
# ============================================================

def get_history(user_id: int):

    init_db()

    with _connect() as conn:

        rows = conn.execute(
            """
            SELECT
                topic,
                question,
                response_json,
                created_at
            FROM study_history
            WHERE user_id = ?
            ORDER BY id DESC
            """,
            (user_id,)
        ).fetchall()

        return [dict(row) for row in rows]


def add_history(
    user_id: int,
    topic: str,
    question: str,
    response_json: str,
    created_at: str
):

    with _connect() as conn:

        conn.execute(
            """
            INSERT INTO study_history
            (
                user_id,
                topic,
                question,
                response_json,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                topic,
                question,
                response_json,
                created_at
            )
        )


def delete_history(user_id: int):

    with _connect() as conn:

        conn.execute(
            """
            DELETE FROM study_history
            WHERE user_id = ?
            """,
            (user_id,)
        )


# ============================================================
# BOOKMARKS
# ============================================================

def get_bookmarks(user_id: int):

    init_db()

    with _connect() as conn:

        rows = conn.execute(
            """
            SELECT
                title,
                url,
                domain,
                topic,
                created_at
            FROM bookmarks
            WHERE user_id = ?
            ORDER BY id DESC
            """,
            (user_id,)
        ).fetchall()

        return [dict(row) for row in rows]


def add_bookmark(
    user_id: int,
    title: str,
    url: str,
    domain: str,
    topic: str,
    created_at: str
):

    with _connect() as conn:

        conn.execute(
            """
            INSERT OR IGNORE INTO bookmarks
            (
                user_id,
                title,
                url,
                domain,
                topic,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                title,
                url,
                domain,
                topic,
                created_at
            )
        )


def remove_bookmark(
    user_id: int,
    url: str
):

    with _connect() as conn:

        conn.execute(
            """
            DELETE FROM bookmarks
            WHERE user_id = ?
            AND url = ?
            """,
            (
                user_id,
                url
            )
        )


# ============================================================
# NOTES
# ============================================================

def get_notes(user_id: int):

    init_db()

    with _connect() as conn:

        row = conn.execute(
            """
            SELECT
                filename,
                content,
                updated_at
            FROM notes
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (user_id,)
        ).fetchone()

        return dict(row) if row else None


def save_notes(
    user_id: int,
    filename: str,
    content: str,
    updated_at: str
):

    with _connect() as conn:

        conn.execute(
            """
            INSERT INTO notes
            (
                user_id,
                filename,
                content,
                updated_at
            )
            VALUES (?, ?, ?, ?)

            ON CONFLICT(user_id, filename)
            DO UPDATE SET
                content = excluded.content,
                updated_at = excluded.updated_at
            """,
            (
                user_id,
                filename,
                content,
                updated_at
            )
        )


def delete_notes(user_id: int):

    with _connect() as conn:

        conn.execute(
            """
            DELETE FROM notes
            WHERE user_id = ?
            """,
            (user_id,)
        )


# ============================================================
# QUIZ HISTORY
# ============================================================

def get_quiz_history(user_id: int):

    init_db()

    with _connect() as conn:

        rows = conn.execute(
            """
            SELECT
                subject,
                score,
                total,
                created_at
            FROM quiz_results
            WHERE user_id = ?
            ORDER BY id DESC
            """,
            (user_id,)
        ).fetchall()

        return [dict(row) for row in rows]


def add_quiz_result(
    user_id: int,
    subject: str,
    score: int,
    total: int,
    created_at: str
):

    with _connect() as conn:

        conn.execute(
            """
            INSERT INTO quiz_results
            (
                user_id,
                subject,
                score,
                total,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                subject,
                score,
                total,
                created_at
            )
        )


# ============================================================
# SETTINGS
# ============================================================

def get_settings(user_id: int):

    init_db()

    with _connect() as conn:

        row = conn.execute(
            """
            SELECT
                student_level,
                learning_style,
                resource_count,
                web_search_enabled,
                preferred_domains_json
            FROM settings
            WHERE user_id = ?
            """,
            (user_id,)
        ).fetchone()

        return dict(row) if row else None


def save_settings(
    user_id: int,
    student_level: str,
    learning_style: str,
    resource_count: int,
    web_search_enabled: bool,
    preferred_domains_json: str
):

    with _connect() as conn:

        conn.execute(
            """
            INSERT INTO settings
            (
                user_id,
                student_level,
                learning_style,
                resource_count,
                web_search_enabled,
                preferred_domains_json
            )
            VALUES (?, ?, ?, ?, ?, ?)

            ON CONFLICT(user_id)
            DO UPDATE SET
                student_level = excluded.student_level,
                learning_style = excluded.learning_style,
                resource_count = excluded.resource_count,
                web_search_enabled = excluded.web_search_enabled,
                preferred_domains_json = excluded.preferred_domains_json
            """,
            (
                user_id,
                student_level,
                learning_style,
                resource_count,
                1 if web_search_enabled else 0,
                preferred_domains_json
            )
        )


# ============================================================
# DELETE ALL USER DATA
# ============================================================

def delete_all_user_data(user_id: int):
    """
    Delete application data belonging to one user.

    The actual user account is NOT deleted.
    """

    with _connect() as conn:

        conn.execute(
            """
            DELETE FROM study_history
            WHERE user_id = ?
            """,
            (user_id,)
        )

        conn.execute(
            """
            DELETE FROM bookmarks
            WHERE user_id = ?
            """,
            (user_id,)
        )

        conn.execute(
            """
            DELETE FROM notes
            WHERE user_id = ?
            """,
            (user_id,)
        )

        conn.execute(
            """
            DELETE FROM quiz_results
            WHERE user_id = ?
            """,
            (user_id,)
        )

        conn.execute(
            """
            DELETE FROM settings
            WHERE user_id = ?
            """,
            (user_id,)
        )

        # Re-create default settings
        conn.execute(
            """
            INSERT INTO settings(user_id)
            VALUES (?)
            """,
            (user_id,)
        )