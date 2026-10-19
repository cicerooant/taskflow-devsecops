"""TaskFlow: gerenciador de tarefas (Flask + SQLite)."""

import os
import sqlite3

from flask import Flask, g, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id INTEGER NOT NULL REFERENCES users(id),
    title TEXT NOT NULL,
    done INTEGER NOT NULL DEFAULT 0
);
"""


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(
        DB_PATH=os.environ.get("DB_PATH", "taskflow.db"),
        SECRET_KEY=os.environ.get("SECRET_KEY"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "1") == "1",
    )
    if test_config:
        app.config.update(test_config)
    if not app.config["SECRET_KEY"]:
        raise RuntimeError("SECRET_KEY não definida (use variável de ambiente)")

    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DB_PATH"])
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close_db(_exc):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    def init_db():
        with sqlite3.connect(app.config["DB_PATH"]) as db:
            db.executescript(SCHEMA)
            admin_password = os.environ.get("ADMIN_PASSWORD")
            if admin_password:
                db.execute(
                    "INSERT OR IGNORE INTO users (username, password_hash) VALUES (?, ?)",
                    ("admin", generate_password_hash(admin_password)),
                )

    init_db()

    def current_user_id():
        return session.get("user_id")

    @app.get("/healthz")
    def healthz():
        return jsonify(status="ok")

    @app.post("/register")
    def register():
        data = request.get_json(silent=True) or {}
        username = (data.get("username") or "").strip()
        password = data.get("password") or ""
        if not username or len(password) < 8:
            return jsonify(error="usuário obrigatório e senha com 8+ caracteres"), 400
        try:
            get_db().execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, generate_password_hash(password)),
            )
            get_db().commit()
        except sqlite3.IntegrityError:
            return jsonify(error="usuário já existe"), 409
        return jsonify(status="criado"), 201

    @app.post("/login")
    def login():
        data = request.get_json(silent=True) or {}
        row = (
            get_db()
            .execute(
                "SELECT id, password_hash FROM users WHERE username = ?",
                (data.get("username") or "",),
            )
            .fetchone()
        )
        if row is None or not check_password_hash(row["password_hash"], data.get("password") or ""):
            return jsonify(error="credenciais inválidas"), 401
        session.clear()
        session["user_id"] = row["id"]
        return jsonify(status="ok")

    @app.post("/logout")
    def logout():
        session.clear()
        return jsonify(status="ok")

    @app.get("/tasks")
    def list_tasks():
        uid = current_user_id()
        if uid is None:
            return jsonify(error="não autenticado"), 401
        term = request.args.get("q", "")
        rows = (
            get_db()
            .execute(
                "SELECT id, title, done FROM tasks WHERE owner_id = "
                + str(uid) + " AND title LIKE '%" + term + "%'"
            )
            .fetchall()
        )
        return jsonify([dict(r) for r in rows])

    @app.post("/tasks")
    def create_task():
        uid = current_user_id()
        if uid is None:
            return jsonify(error="não autenticado"), 401
        title = ((request.get_json(silent=True) or {}).get("title") or "").strip()
        if not title:
            return jsonify(error="título obrigatório"), 400
        cur = get_db().execute("INSERT INTO tasks (owner_id, title) VALUES (?, ?)", (uid, title))
        get_db().commit()
        return jsonify(id=cur.lastrowid, title=title, done=0), 201

    @app.post("/tasks/<int:task_id>/done")
    def complete_task(task_id):
        uid = current_user_id()
        if uid is None:
            return jsonify(error="não autenticado"), 401
        cur = get_db().execute(
            "UPDATE tasks SET done = 1 WHERE id = ? AND owner_id = ?", (task_id, uid)
        )
        get_db().commit()
        if cur.rowcount == 0:
            return jsonify(error="tarefa não encontrada"), 404
        return jsonify(status="ok")

    return app


app = create_app() if os.environ.get("SECRET_KEY") else None

if __name__ == "__main__":
    if app is None:
        raise SystemExit("Defina SECRET_KEY antes de iniciar.")
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")))
