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
