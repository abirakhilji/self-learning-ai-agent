"""Long-term memory for the agent: a small SQLite store of lessons.

Each lesson is one short sentence the agent wrote about itself after finishing
a task ("Answer with only the number when asked for a bare value"). Before a
new task, the most relevant lessons are retrieved and put in the system prompt.
"""

import re
import sqlite3
import time
from pathlib import Path

DB_PATH = Path(__file__).parent / "memory.db"

STOPWORDS = {
    "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "is", "are",
    "it", "this", "that", "with", "as", "be", "when", "if", "you", "i", "my",
    "what", "how", "do", "does", "next", "time", "task", "user",
}


def _connect(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS lessons (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               created_at REAL NOT NULL,
               task TEXT NOT NULL,
               outcome TEXT NOT NULL,
               lesson TEXT NOT NULL
           )"""
    )
    return conn


def _tokens(text):
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {w for w in words if w not in STOPWORDS and len(w) > 1}


def save_lesson(task, outcome, lesson, db_path=DB_PATH):
    """Store one lesson. Skips exact duplicates."""
    lesson = lesson.strip()
    if not lesson:
        return
    with _connect(db_path) as conn:
        exists = conn.execute(
            "SELECT 1 FROM lessons WHERE lesson = ?", (lesson,)
        ).fetchone()
        if not exists:
            conn.execute(
                "INSERT INTO lessons (created_at, task, outcome, lesson) VALUES (?, ?, ?, ?)",
                (time.time(), task, outcome, lesson),
            )


def retrieve(task, k=3, db_path=DB_PATH):
    """Return up to k lessons most relevant to `task` (keyword overlap + recency)."""
    query = _tokens(task)
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT created_at, task, lesson FROM lessons"
        ).fetchall()
    scored = []
    for created_at, past_task, lesson in rows:
        overlap = len(query & _tokens(past_task + " " + lesson))
        if overlap == 0:
            continue
        scored.append((overlap, created_at, lesson))
    scored.sort(reverse=True)  # more overlap first, then newer
    picked = [lesson for _, _, lesson in scored[:k]]
    # General lessons (style, format) share few keywords with new tasks,
    # so fill any free slots with the most recent lessons.
    for _, _, lesson in sorted(
        ((c, t, l) for c, t, l in rows), reverse=True
    ):
        if len(picked) >= k:
            break
        if lesson not in picked:
            picked.append(lesson)
    return picked


def all_lessons(db_path=DB_PATH):
    with _connect(db_path) as conn:
        return conn.execute(
            "SELECT id, outcome, lesson FROM lessons ORDER BY id"
        ).fetchall()


def clear(db_path=DB_PATH):
    with _connect(db_path) as conn:
        conn.execute("DELETE FROM lessons")
