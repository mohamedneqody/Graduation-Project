def test_create_product_success(client):
    response = client.post("/api/v1/products", json={"name": "Test Laptop", "price": 1500.0})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Laptop"
    assert data["price"] == 1500.0
    assert "id" in data

def test_create_product_invalid_data(client):
    # إرسال price كنص بدلاً من رقم (أو فقدان حقل مطلوب)
    response = client.post("/api/v1/products", json={"name": "Test Laptop"})
    assert response.status_code == 422 # Unprocessable Entity

def test_get_non_existent_product(client):
    response = client.get("/api/v1/products/999")
    assert response.status_code == 404

def test_delete_product(client):
    # إنشاء منتج أولاً
    create_res = client.post("/api/v1/products", json={"name": "To Delete", "price": 10.0})
    product_id = create_res.json()["id"]
    
    # حذف المنتج
    delete_res = client.delete(f"/api/v1/products/{product_id}")
    assert delete_res.status_code == 204
    
    # التأكد من أنه غير موجود
    get_res = client.get(f"/api/v1/products/{product_id}")
    assert get_res.status_code == 404
