import json
import re
import sqlite3
import uuid

from conftest import ADMIN_PWD, USER_PWD


def login(client, user="admin", pwd=ADMIN_PWD):
    return client.post("/login", json={"username": user, "password": pwd})


def test_healthz(client):
    assert client.get("/healthz").get_json() == {"status": "ok"}


def test_login_ok_e_falha(client):
    assert login(client).status_code == 200
    assert login(client, pwd=USER_PWD).status_code == 401


def test_senha_armazenada_com_hash(client, tmp_path):
    client.post("/register", json={"username": "ana", "password": USER_PWD})
    with sqlite3.connect(tmp_path / "t.db") as db:
        stored = db.execute("SELECT password_hash FROM users WHERE username='ana'").fetchone()[0]
    assert stored != USER_PWD
    assert stored.startswith(("scrypt:", "pbkdf2:"))


def test_tasks_exigem_login(client):
    assert client.get("/tasks").status_code == 401


def test_criar_listar_concluir(client):
    login(client)
    assert client.post("/tasks", json={"title": "estudar devsecops"}).status_code == 201
    tasks = client.get("/tasks").get_json()
    assert tasks[0]["title"] == "estudar devsecops"
    assert client.post(f"/tasks/{tasks[0]['id']}/done", json={}).status_code == 200


def test_busca_resiste_a_sql_injection(client):
    login(client)
    client.post("/tasks", json={"title": "normal"})
    resp = client.get("/tasks", query_string={"q": "' OR '1'='1"})
    assert resp.get_json() == []


def test_login_resiste_a_sql_injection(client):
    assert login(client, user="admin' --", pwd="x").status_code == 401


def test_login_com_html_e_endpoint_debug_removido(client):
    assert client.get("/login", headers={"Accept": "text/html"}).status_code == 200
    assert client.get("/debug/info").status_code == 404
    assert client.application.config["DEBUG"] is False


def test_xss_armazenado_escapado_no_html(client):
    login(client)
    payload = "<script>alert(1)</script>"
    client.post("/tasks", json={"title": payload})

    response = client.get("/tasks", headers={"Accept": "text/html"})
    assert response.status_code == 200
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in response.get_data(as_text=True)
    assert payload not in response.get_data(as_text=True)


def test_busca_q_escapada_no_html(client):
    login(client)
    payload = "<script>alert(1)</script>"

    response = client.get("/tasks", query_string={"q": payload}, headers={"Accept": "text/html"})
    assert response.status_code == 200
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in response.get_data(as_text=True)
    assert payload not in response.get_data(as_text=True)


def test_busca_q_sem_sessao_entrega_html_escapado(client):
    payload = '" onmouseover=alert(1) x="'

    response = client.get("/tasks", query_string={"q": payload})
    assert response.status_code == 200
    assert "&#34; onmouseover=alert(1) x=&#34;" in response.get_data(as_text=True)
    assert payload not in response.get_data(as_text=True)


def test_busca_q_escapada_na_tela_de_login(client):
    payload = "<script>alert(1)</script>"

    response = client.get("/tasks", query_string={"q": payload}, headers={"Accept": "text/html"})
    assert response.status_code == 200
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in response.get_data(as_text=True)
    assert payload not in response.get_data(as_text=True)


def test_busca_q_escapada_diretamente_no_login(client):
    payload = "<script>alert(1)</script>"

    response = client.get("/login", query_string={"q": payload})
    assert response.status_code == 200
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in response.get_data(as_text=True)
    assert payload not in response.get_data(as_text=True)


def test_erro_login_escapa_usuario_no_html(client):
    payload = "<script>alert(1)</script>"
    login_page = client.get("/login")
    csrf_token = re.search(
        r'name="csrf_token" value="([^"]+)"', login_page.get_data(as_text=True)
    ).group(1)

    response = client.post(
        "/login",
        data={
            "username": payload,
            "password": "senha-incorreta",
            "csrf_token": csrf_token,
        },
        headers={"Accept": "text/html"},
    )
    assert response.status_code == 401
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in response.get_data(as_text=True)
    assert payload not in response.get_data(as_text=True)


def test_logs_json_com_eventos_request_id_e_sem_dados_sensiveis(client, capsys):
    password_marker = "PASSWORD_MUST_NOT_BE_LOGGED"
    cookie_marker = "COOKIE_MUST_NOT_BE_LOGGED"
    title_marker = "TITLE_MUST_NOT_BE_LOGGED"
    search_marker = "SEARCH_MUST_NOT_BE_LOGGED"

    failed = client.post(
        "/login",
        json={"username": "admin", "password": password_marker},
        headers={"Cookie": f"session={cookie_marker}"},
    )
    assert failed.status_code == 401
    assert uuid.UUID(failed.headers["X-Request-ID"])

    assert login(client).status_code == 200
    assert client.post("/tasks", json={"title": title_marker}).status_code == 201
    assert client.get("/tasks", query_string={"q": search_marker}).status_code == 200
    output = capsys.readouterr().out
    events = [json.loads(line) for line in output.splitlines() if line.strip()]

    event_names = {event["event"] for event in events}
    assert {
        "login_success",
        "login_failure",
        "task_created",
        "tasks_listed",
        "request_completed",
    } <= event_names
    for event in events:
        assert uuid.UUID(event["request_id"])
        assert event["ip"]

    login_failure = next(event for event in events if event["event"] == "login_failure")
    assert login_failure["username"] == "admin"

    login_success = next(event for event in events if event["event"] == "login_success")
    assert login_success["username"] == "admin"

    task_created = next(event for event in events if event["event"] == "task_created")
    assert task_created["title_size"] == len(title_marker)
    assert "title" not in task_created

    tasks_listed = next(event for event in events if event["event"] == "tasks_listed")
    assert tasks_listed["search_size"] == len(search_marker)
    assert "search" not in tasks_listed

    serialized_logs = json.dumps(events)
    for marker in (password_marker, cookie_marker, title_marker, search_marker):
        assert marker not in serialized_logs


def test_cabecalhos_de_seguranca_presentes(client):
    response = client.get("/login")

    assert response.headers["Content-Security-Policy"] == (
        "default-src 'self'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; "
        "object-src 'none'; script-src 'self'; style-src 'self'"
    )
    assert "unsafe-inline" not in response.headers["Content-Security-Policy"]
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response.headers["Permissions-Policy"] == "geolocation=(), microphone=(), camera=()"
    assert response.headers["Cache-Control"] == "no-store"


def test_formularios_post_tem_token_csrf(client):
    login_page = client.get("/login").get_data(as_text=True)
    login_token = re.search(r'name="csrf_token" value="([^"]+)"', login_page).group(1)
    assert login_token

    response = client.post(
        "/login",
        data={"username": "admin", "password": ADMIN_PWD, "csrf_token": login_token},
        headers={"Accept": "text/html"},
    )
    assert response.status_code == 303

    assert client.post("/tasks", json={"title": "tarefa para concluir"}).status_code == 201
    tasks_page = client.get("/tasks", headers={"Accept": "text/html"}).get_data(as_text=True)
    task_tokens = re.findall(r'name="csrf_token" value="([^"]+)"', tasks_page)
    assert len(task_tokens) == 3
    assert len(set(task_tokens)) == 1
    task_token = task_tokens[0]

    created = client.post(
        "/tasks",
        data={"title": "tarefa enviada por formulário", "csrf_token": task_token},
        headers={"Accept": "text/html"},
    )
    assert created.status_code == 303

    tasks_page = client.get("/tasks", headers={"Accept": "text/html"}).get_data(as_text=True)
    completion_action = re.search(r'<form method="post" action="([^"]+/done)">', tasks_page).group(
        1
    )
    completion_token = re.search(
        r'<form method="post" action="[^"]+/done">\s*'
        r'<input type="hidden" name="csrf_token" value="([^"]+)"',
        tasks_page,
    ).group(1)
    completed = client.post(
        completion_action,
        data={"csrf_token": completion_token},
        headers={"Accept": "text/html"},
    )
    assert completed.status_code == 303

    tasks_page = client.get("/tasks", headers={"Accept": "text/html"}).get_data(as_text=True)
    logout_match = re.search(
        r'<form method="post" action="([^"]*/logout)">\s*'
        r'<input type="hidden" name="csrf_token" value="([^"]+)"',
        tasks_page,
    )
    assert logout_match
    logout_response = client.post(
        logout_match.group(1),
        data={"csrf_token": logout_match.group(2)},
        headers={"Accept": "text/html"},
    )
    assert logout_response.status_code == 303


def test_form_post_sem_csrf_rejeitado_e_json_isento(client):
    response = client.post(
        "/login",
        data={"username": "admin", "password": ADMIN_PWD},
        headers={"Accept": "text/html"},
    )
    assert response.status_code == 403

    assert login(client).status_code == 200
    assert client.post("/tasks", json={"title": "json permanece isento"}).status_code == 201
