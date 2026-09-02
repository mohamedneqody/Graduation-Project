def test_signup_success(client):
    response = client.post("/api/v1/auth/signup", json={"email": "test@test.com", "password": "pass"})
    assert response.status_code == 201
    assert response.json()["email"] == "test@test.com"
    assert "id" in response.json()

def test_signup_duplicate_email(client):
    client.post("/api/v1/auth/signup", json={"email": "test@test.com", "password": "pass"})
    response = client.post("/api/v1/auth/signup", json={"email": "test@test.com", "password": "newpass"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"

def test_login_wrong_password(client):
    client.post("/api/v1/auth/signup", json={"email": "test@test.com", "password": "pass"})
    response = client.post("/api/v1/auth/login", json={"email": "test@test.com", "password": "wrong"})
    assert response.status_code == 401

def test_access_me_without_token(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"

def test_access_me_with_valid_token(client):
    client.post("/api/v1/auth/signup", json={"email": "user@test.com", "password": "123"})
    login_res = client.post("/api/v1/auth/login", json={"email": "user@test.com", "password": "123"})
    token = login_res.json()["access_token"]
    
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "user@test.com"
