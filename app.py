"""TaskFlow: gerenciador de tarefas (Flask + SQLite)."""

import json
import logging
import os
import sqlite3
import sys
import time
import uuid
from datetime import datetime, timezone

from flask import Flask, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash


class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "ts": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "event": record.getMessage(),
        }
        payload.update(getattr(record, "fields", {}))
        return json.dumps(payload, ensure_ascii=False)


class StdoutHandler(logging.StreamHandler):
    def __init__(self):
        super().__init__(sys.stdout)

    @property
    def stream(self):
        return sys.stdout

    @stream.setter
    def stream(self, _value):
        pass


def build_logger():
    logger = logging.getLogger("taskflow")
    if not logger.handlers:
        handler = StdoutHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


log = build_logger()

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
        DEBUG=os.environ.get("FLASK_DEBUG", "0") == "1",
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

    def wants_html():
        return request.accept_mimetypes.accept_html > request.accept_mimetypes["application/json"]

    def log_event(event, level=logging.INFO, **fields):
        log.log(
            level,
            event,
            extra={
                "fields": {
                    "request_id": g.get("request_id"),
                    "ip": request.remote_addr,
                    **fields,
                }
            },
        )

    @app.before_request
    def start_request():
        g.request_id = str(uuid.uuid4())
        g.request_started = time.perf_counter()

    @app.after_request
    def finish_request(response):
        response.headers["X-Request-ID"] = g.request_id
        log_event(
            "request_completed",
            method=request.method,
            path=request.path,
            status=response.status_code,
            duration_ms=round((time.perf_counter() - g.request_started) * 1000, 1),
        )
        return response

    @app.get("/")
    def index():
        return redirect(url_for("list_tasks" if current_user_id() else "login_page"))

    @app.get("/login")
    def login_page():
        return render_template(
            "login.html", error=None, username="", term=request.args.get("q", "")
        )

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
        data = request.get_json(silent=True) or request.form
        username = (data.get("username") or "").strip()
        row = (
            get_db()
            .execute(
                "SELECT id, password_hash FROM users WHERE username = ?",
                (username,),
            )
            .fetchone()
        )
        if row is None or not check_password_hash(row["password_hash"], data.get("password") or ""):
            log_event("login_failure", level=logging.WARNING, username=username)
            error = (
                f"Credenciais inválidas para {username}"
                if username
                else "Credenciais inválidas"
            )
            if request.is_json:
                return jsonify(error=error), 401
            return render_template("login.html", error=error, username=username), 401
        session.clear()
        session["user_id"] = row["id"]
        log_event("login_success", username=username)
        if not request.is_json:
            return redirect(url_for("list_tasks", q=data.get("q", "")), code=303)
        return jsonify(status="ok")

    @app.post("/logout")
    def logout():
        session.clear()
        if wants_html():
            return redirect(url_for("login_page"), code=303)
        return jsonify(status="ok")

    @app.get("/tasks")
    def list_tasks():
        uid = current_user_id()
        if uid is None:
            if wants_html() or "q" in request.args:
                return render_template(
                    "login.html", error=None, username="", term=request.args.get("q", "")
                )
            return jsonify(error="não autenticado"), 401
        term = request.args.get("q", "")
        rows = (
            get_db()
            .execute(
                "SELECT id, title, done FROM tasks WHERE owner_id = ? AND title LIKE ?",
                (uid, f"%{term}%"),
            )
            .fetchall()
        )
        log_event(
            "tasks_listed",
            result_count=len(rows),
            search_size=len(term),
        )
        if wants_html():
            return render_template("tasks.html", tasks=rows, term=term)
        return jsonify([dict(r) for r in rows])

    @app.post("/tasks")
    def create_task():
        uid = current_user_id()
        if uid is None:
            return jsonify(error="não autenticado"), 401
        data = request.get_json(silent=True) or request.form
        title = (data.get("title") or "").strip()
        if not title:
            return jsonify(error="título obrigatório"), 400
        cur = get_db().execute("INSERT INTO tasks (owner_id, title) VALUES (?, ?)", (uid, title))
        get_db().commit()
        log_event("task_created", title_size=len(title))
        if wants_html():
            return redirect(url_for("list_tasks"), code=303)
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
        if wants_html():
            return redirect(url_for("list_tasks"), code=303)
        return jsonify(status="ok")

    return app


app = create_app() if os.environ.get("SECRET_KEY") else None

if __name__ == "__main__":
    if app is None:
        raise SystemExit("Defina SECRET_KEY antes de iniciar.")
    app.run(
        host="127.0.0.1",
        port=int(os.environ.get("PORT", "5000")),
        debug=app.config["DEBUG"],
    )
