"""SQLite persistence for MiniLang Compiler Studio."""
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "database" / "compiler_studio.db"


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS compilation_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            program_name TEXT NOT NULL,
            source_code TEXT NOT NULL,
            optimize_enabled INTEGER NOT NULL,
            success INTEGER NOT NULL,
            token_count INTEGER NOT NULL,
            symbol_count INTEGER NOT NULL,
            folded_constants INTEGER NOT NULL,
            diagnostic_count INTEGER NOT NULL,
            duration_ms REAL NOT NULL,
            stdout_text TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS saved_programs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL UNIQUE,
            category TEXT NOT NULL,
            source_code TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """)
        samples = [
            ("Constant Folding & Arithmetic", "Optimization", "# MiniLang Sample: Constant Folding + Arithmetic\nLET base: INT = 12 + 8 * 3;\nLET bonus: INT = 10;\nLET total: INT = base + bonus;\nDISPLAY \"Computed Total:\";\nDISPLAY total;\n"),
            ("Typed Variables & Floats", "Types & I/O", "# MiniLang Sample: Types & Output\nLET greeting: STR = \"MiniLang Compiler Ready!\";\nLET rate: FLOAT = 1.25;\nLET score: FLOAT = rate * 8;\nDISPLAY greeting;\nDISPLAY score;\n"),
            ("Semantic Error (Undeclared Var)", "Diagnostics", "# MiniLang Sample: Undeclared Variable Error\nLET count: INT = 5;\nLET result: INT = count + missing_var;\nDISPLAY result;\n"),
        ]
        for title, cat, code in samples:
            db.execute("INSERT OR IGNORE INTO saved_programs (title, category, source_code, created_at) VALUES (?, ?, ?, ?)", (title, cat, code, now_iso()))
