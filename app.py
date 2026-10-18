"""TaskFlow (versão ORIGINAL, propositalmente vulnerável, para fins didáticos)."""
import os
import sqlite3

from flask import Flask, jsonify, request, session

app = Flask(__name__)
app.secret_key = "9f1c2e7a8b4d6e30a1b2c3d4e5f60718"
ADMIN_PASSWORD = "Xk7Qp2vLe4Rz8Tn3Wm5Yb9"
DB_PATH = os.environ.get("DB_PATH", "taskflow.db")


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL, password TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL, title TEXT NOT NULL, done INTEGER NOT NULL DEFAULT 0);
        """
    )
    conn.execute(
        "INSERT OR IGNORE INTO users (username, password) VALUES ('admin', '%s')" % ADMIN_PASSWORD
    )
    conn.commit()
    conn.close()


@app.get("/healthz")
def healthz():
    return jsonify(status="ok")


@app.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    conn = db()
    conn.execute(
        f"INSERT INTO users (username, password) VALUES ('{data['username']}', '{data['password']}')"
    )
    conn.commit()
    return jsonify(status="criado"), 201


@app.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    conn = db()
    row = conn.execute(
        "SELECT id FROM users WHERE username = '" + data.get("username", "")
        + "' AND password = '" + data.get("password", "") + "'"
    ).fetchone()
    if row is None:
        return jsonify(error="credenciais inválidas"), 401
    session["user_id"] = row["id"]
    return jsonify(status="ok")


@app.get("/tasks")
def list_tasks():
    if "user_id" not in session:
        return jsonify(error="não autenticado"), 401
    q = request.args.get("q", "")
    rows = db().execute(
        f"SELECT id, title, done FROM tasks WHERE owner_id = {session['user_id']} AND title LIKE '%{q}%'"
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.post("/tasks")
def create_task():
    if "user_id" not in session:
        return jsonify(error="não autenticado"), 401
    title = (request.get_json(silent=True) or {}).get("title", "")
    conn = db()
    conn.execute(f"INSERT INTO tasks (owner_id, title) VALUES ({session['user_id']}, '{title}')")
    conn.commit()
    return jsonify(status="criado"), 201


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
