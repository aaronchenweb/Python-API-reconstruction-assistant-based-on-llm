from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from test_file.Fastapi.main import app

# Create a test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_books.db"
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
    
    # Register a test user and get token
    response = client.post(
        "/register",
        json={"email": "book_test@example.com", "password": "password123"},
    )
    global token
    token = response.json()["access_token"]

def teardown_module():
    # Drop the database tables
    Base.metadata.drop_all(bind=engine)

def test_create_book():
    response = client.post(
        "/books/",
        json={
            "title": "Test Book",
            "description": "A test book",
            "author": "Test Author",
            "year": 2022
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Book"
    assert data["author"] == "Test Author"
    assert "id" in data
    global book_id
    book_id = data["id"]

def test_read_books():
    response = client.get(
        "/books/",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0

def test_read_book():
    # First create a book
    create_response = client.post(
        "/books/",
        json={
            "title": "Single Book",
            "description": "A single test book",
            "author": "Single Author",
            "year": 2023
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    book_id = create_response.json()["id"]
    
    # Then read it
    response = client.get(
        f"/books/{book_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Single Book"
    assert data["author"] == "Single Author"

def test_update_book():
    # First create a book
    create_response = client.post(
        "/books/",
        json={
            "title": "Update Book",
            "description": "A book to update",
            "author": "Update Author",
            "year": 2023
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    book_id = create_response.json()["id"]
    
    # Then update it
    response = client.put(
        f"/books/{book_id}",
        json={
            "title": "Updated Book",
            "description": "An updated book",
            "author": "Updated Author",
            "year": 2024
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Book"
    assert data["author"] == "Updated Author"
    assert data["year"] == 2024

def test_delete_book():
    # First create a book
    create_response = client.post(
        "/books/",
        json={
            "title": "Delete Book",
            "description": "A book to delete",
            "author": "Delete Author",
            "year": 2023
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    book_id = create_response.json()["id"]
    
    # Then delete it
    response = client.delete(
        f"/books/{book_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    
    # Verify it's gone
    get_response = client.get(
        f"/books/{book_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert get_response.status_code == 404