"""Flask REST API for MiniLang Compiler Studio."""
import sys
from pathlib import Path
from flask import Flask, jsonify, request
from flask_cors import CORS

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from compiler.minilang_engine import compile_program
from database import DB_PATH, connect, init_db, now_iso

app = Flask(__name__)
CORS(app)


@app.get("/api/health")
def health():
    with connect() as db:
        runs_count = db.execute("SELECT COUNT(*) FROM compilation_runs").fetchone()[0]
    return jsonify({"status": "ok", "service": "MiniLang Compiler API", "database": str(DB_PATH), "runs_count": runs_count})


@app.get("/api/programs")
def get_programs():
    with connect() as db:
        rows = db.execute("SELECT * FROM saved_programs ORDER BY id ASC").fetchall()
        return jsonify([dict(r) for r in rows])


@app.post("/api/programs")
def save_program():
    body = request.get_json(silent=True) or {}
    title = str(body.get("title") or "").strip()[:80]
    source = str(body.get("source") or "")
    category = str(body.get("category") or "Custom")[:32]
    if not title or not source.strip():
        return jsonify({"error": "Provide both a program title and source code."}), 400
    with connect() as db:
        db.execute("INSERT OR REPLACE INTO saved_programs (title, category, source_code, created_at) VALUES (?, ?, ?, ?)", (title, category, source, now_iso()))
        row = db.execute("SELECT * FROM saved_programs WHERE title=?", (title,)).fetchone()
        return jsonify(dict(row)), 201


@app.post("/api/compile")
def compile_endpoint():
    body = request.get_json(silent=True) or {}
    source = str(body.get("source") or "")
    optimize = bool(body.get("optimize", True))
    program_name = str(body.get("program_name") or "Untitled Program")[:80]
    res = compile_program(source, optimize=optimize)
    with connect() as db:
        db.execute("""INSERT INTO compilation_runs
            (program_name, source_code, optimize_enabled, success, token_count, symbol_count, folded_constants, diagnostic_count, duration_ms, stdout_text, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                program_name,
                source,
                1 if optimize else 0,
                1 if res["success"] else 0,
                len(res["tokens"]),
                len(res["symbolTable"]),
                res["foldedConstants"],
                len(res["diagnostics"]),
                res["execution"]["durationMs"],
                res["execution"]["stdout"],
                now_iso(),
            ))
    return jsonify(res)


@app.get("/api/history")
def history():
    with connect() as db:
        rows = db.execute("SELECT * FROM compilation_runs ORDER BY id DESC LIMIT 50").fetchall()
        return jsonify([dict(r) for r in rows])


@app.get("/api/database/summary")
def db_summary():
    with connect() as db:
        tables = {
            "compilation_runs": db.execute("SELECT COUNT(*) FROM compilation_runs").fetchone()[0],
            "saved_programs": db.execute("SELECT COUNT(*) FROM saved_programs").fetchone()[0],
        }
    return jsonify({"database_file": str(DB_PATH), "tables": tables})


@app.get("/api/database/<table>")
def db_table(table):
    if table not in ("compilation_runs", "saved_programs"):
        return jsonify({"error": "Invalid table name."}), 404
    with connect() as db:
        rows = db.execute(f"SELECT * FROM {table} ORDER BY id DESC LIMIT 100").fetchall()
        return jsonify({"table": table, "rows": [dict(r) for r in rows]})


init_db()

if __name__ == "__main__":
    print("MiniLang Compiler API running at http://127.0.0.1:5000")
    print("SQLite database:", DB_PATH)
    app.run(debug=True, port=5000)
