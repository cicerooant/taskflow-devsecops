import sqlite3

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
    assert client.post(f"/tasks/{tasks[0]['id']}/done").status_code == 200


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

    response = client.get(
        "/tasks", query_string={"q": payload}, headers={"Accept": "text/html"}
    )
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

    response = client.get(
        "/tasks", query_string={"q": payload}, headers={"Accept": "text/html"}
    )
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

    response = client.post(
        "/login",
        data={"username": payload, "password": "senha-incorreta"},
        headers={"Accept": "text/html"},
    )
    assert response.status_code == 401
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in response.get_data(as_text=True)
    assert payload not in response.get_data(as_text=True)
