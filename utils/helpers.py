"""
helpers.py
General-purpose helper utilities for StudyMate AI:
- The multi-domain subject catalog
- Small formatting / validation helpers
- Safe wrappers so the UI never crashes on bad input
"""

from datetime import datetime


# ---------------------------------------------------------------------------
# SUBJECT CATALOG
# ---------------------------------------------------------------------------
# A large, categorized catalog of academic subjects. Students can also type
# any custom subject that is not in this list.

SUBJECT_CATALOG = {
    "💻 Computer Science": [
        "Python", "C", "C++", "Java", "Data Structures", "Algorithms",
        "Object Oriented Programming", "Operating Systems",
        "Computer Architecture", "Compiler Design", "Theory of Computation",
    ],
    "🤖 AI & Data": [
        "Artificial Intelligence", "Machine Learning", "Deep Learning",
        "Natural Language Processing", "Computer Vision", "Generative AI",
        "Data Science", "Statistics", "Big Data", "Data Analytics",
    ],
    "🔐 Cyber Security & Networking": [
        "Cyber Security", "Ethical Hacking", "Network Security",
        "Cryptography", "Digital Forensics", "Web Security",
        "Cloud Security", "IoT Security", "Computer Networks", "TCP/IP",
        "Network Protocols",
    ],
    "🔧 Embedded Systems & Electronics": [
        "Embedded Systems", "Embedded C", "Microcontrollers",
        "Microprocessors", "Arduino", "ESP32", "Raspberry Pi", "STM32",
        "ARM", "AVR", "PIC", "RTOS", "FreeRTOS", "Sensors", "Actuators",
        "GPIO", "UART", "SPI", "I2C", "CAN", "PWM", "Interrupts", "Timers",
        "ADC", "DAC", "Digital Electronics", "Analog Electronics",
        "PCB Design", "Robotics", "IoT",
    ],
    "🌐 Web & Software": [
        "HTML", "CSS", "JavaScript", "React", "Node.js", "Django", "Flask",
        "REST API", "Software Engineering", "Software Testing", "Git",
        "GitHub", "DevOps",
    ],
    "🗄️ Database & Cloud": [
        "DBMS", "SQL", "MySQL", "PostgreSQL", "MongoDB", "Database Design",
        "Cloud Computing", "AWS", "Azure", "Google Cloud", "Docker",
        "Kubernetes",
    ],
    "⚙️ Engineering": [
        "Electrical Engineering", "Electronics Engineering",
        "Control Systems", "Signal Processing", "Communication Systems",
        "Power Systems", "Mechanical Engineering", "Engineering Mathematics",
    ],
    "🔬 Science & Mathematics": [
        "Mathematics", "Calculus", "Linear Algebra", "Probability",
        "Physics", "Chemistry",
    ],
    "📊 Management & General": [
        "Business Management", "Project Management", "Economics",
        "Accounting", "Digital Marketing", "Communication Skills",
        "Research Methodology",
    ],
}


def get_all_subjects():
    """Flat, sorted list of every subject in the catalog."""
    subjects = []
    for topics in SUBJECT_CATALOG.values():
        subjects.extend(topics)
    return sorted(set(subjects))


def get_popular_subjects(limit: int = 8):
    """A small curated list used on the Dashboard 'Popular subjects' row."""
    popular = [
        "Python", "Machine Learning", "Cyber Security", "Embedded Systems",
        "Data Structures", "Computer Networks", "Artificial Intelligence",
        "DBMS",
    ]
    return popular[:limit]


# ---------------------------------------------------------------------------
# FORMATTING / VALIDATION
# ---------------------------------------------------------------------------

def now_str() -> str:
    """Human-readable timestamp for history/bookmarks."""
    return datetime.now().strftime("%d %b %Y, %I:%M %p")


def clean_text(text: str) -> str:
    """Trim and normalize whitespace in user-entered text."""
    if not text:
        return ""
    return " ".join(text.split()).strip()


def is_blank(text: str) -> bool:
    return not text or not text.strip()


def truncate(text: str, length: int = 160) -> str:
    if not text:
        return ""
    text = text.strip()
    return text if len(text) <= length else text[:length].rsplit(" ", 1)[0] + "…"


def safe_get(d: dict, key: str, default=""):
    """Dict access that never raises, always returns a usable default."""
    if not isinstance(d, dict):
        return default
    value = d.get(key, default)
    return value if value is not None else default


def domain_from_url(url: str) -> str:
    """Extract a readable domain name from a URL for display in resource cards."""
    if not url:
        return "unknown source"
    try:
        cleaned = url.replace("https://", "").replace("http://", "")
        domain = cleaned.split("/")[0]
        domain = domain.replace("www.", "")
        return domain
    except Exception:
        return "unknown source"
