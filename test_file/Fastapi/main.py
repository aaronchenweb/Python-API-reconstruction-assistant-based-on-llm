from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import auth, books

# Create the database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="BookAPI",
    description="A simple API to manage books",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(books.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Book API! Visit /docs for the API documentation."}