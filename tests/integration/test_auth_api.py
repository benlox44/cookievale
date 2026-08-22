def test_panel_requires_login(client) -> None:
    response = client.get("/admin", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/admin/login"


def test_login_wrong_password(client) -> None:
    response = client.post("/admin/login", data={"password": "incorrecta"})
    assert response.status_code == 200
    assert "Contraseña incorrecta" in response.text


def test_login_success_sets_cookie(client, admin_password: str) -> None:
    response = client.post(
        "/admin/login", data={"password": admin_password}, follow_redirects=False
    )
    assert response.status_code == 303
    assert "admin_session" in response.cookies


def test_panel_accessible_with_cookie(admin_client) -> None:
    response = admin_client.get("/admin")
    assert response.status_code == 200


def test_logout_clears_session(client, admin_password: str) -> None:
    client.post("/admin/login", data={"password": admin_password})
    client.post("/admin/logout")
    assert client.get("/admin", follow_redirects=False).status_code == 303


def test_login_rate_limited(client) -> None:
    for _ in range(5):
        client.post("/admin/login", data={"password": "incorrecta"})
    response = client.post("/admin/login", data={"password": "incorrecta"})
    assert response.status_code == 200
    assert "Demasiados intentos" in response.text
