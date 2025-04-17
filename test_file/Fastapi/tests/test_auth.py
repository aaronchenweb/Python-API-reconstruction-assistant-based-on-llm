from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from test_file.Fastapi.main import app

# Create a test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override the get_db dependency
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Create the test client
client = TestClient(app)

def setup_module():
    # Create the database tables
    Base.metadata.create_all(bind=engine)

def teardown_module():
    # Drop the database tables
    Base.metadata.drop_all(bind=engine)

def test_register_user():
    response = client.post(
        "/register",
        json={"email": "test@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_user():
    # First register a user
    client.post(
        "/register",
        json={"email": "login_test@example.com", "password": "password123"},
    )
    
    # Then login
    response = client.post(
        "/token",
        data={"username": "login_test@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_wrong_password():
    # First register a user
    client.post(
        "/register",
        json={"email": "wrong_password@example.com", "password": "password123"},
    )
    
    # Then try to login with wrong password
    response = client.post(
        "/token",
        data={"username": "wrong_password@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401