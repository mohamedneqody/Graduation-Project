
from fastapi.testclient import TestClient
from app.main import app
from app.dependencies.auth import get_current_user
from app.models.customer import Customer
import uuid

client = TestClient(app)

async def override_get_current_user():
    c = Customer()
    c.auth_user_id = uuid.uuid4()
    c.email = 'test@test.com'
    return c

app.dependency_overrides[get_current_user] = override_get_current_user

def run():
    response = client.post('/api/v1/prescriptions/', files={'file': ('test.jpg', b'abc', 'image/jpeg')})
    print(response.status_code)
    print(response.json())

if __name__ == '__main__':
    run()

