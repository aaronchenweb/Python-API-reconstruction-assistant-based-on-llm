from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_active_user
from app.models.book import Book
from app.models.user import User
from app.schemas.book import BookCreate, BookUpdate, Book as BookSchema

router = APIRouter(
    prefix="/books",
    tags=["books"],
)

@router.post("/", response_model=BookSchema)
def create_book(
    book: BookCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    db_book = Book(**book.dict(), owner_id=current_user.id)
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    return db_book

@router.get("/", response_model=List[BookSchema])
def read_books(
    skip: int = 0,
    limit: int = 100,
    title: Optional[str] = Query(None, description="Filter by title"),
    author: Optional[str] = Query(None, description="Filter by author"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    query = db.query(Book).filter(Book.owner_id == current_user.id)
    
    if title:
        query = query.filter(Book.title.contains(title))
    if author:
        query = query.filter(Book.author.contains(author))
    
    books = query.offset(skip).limit(limit).all()
    return books

@router.get("/{book_id}", response_model=BookSchema)
def read_book(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    db_book = db.query(Book).filter(Book.id == book_id, Book.owner_id == current_user.id).first()
    if db_book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return db_book

@router.put("/{book_id}", response_model=BookSchema)
def update_book(
    book_id: int,
    book: BookUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    db_book = db.query(Book).filter(Book.id == book_id, Book.owner_id == current_user.id).first()
    if db_book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    
    update_data = book.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_book, key, value)
    
    db.commit()
    db.refresh(db_book)
    return db_book

@router.delete("/{book_id}", response_model=BookSchema)
def delete_book(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    db_book = db.query(Book).filter(Book.id == book_id, Book.owner_id == current_user.id).first()
    if db_book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    
    db.delete(db_book)
    db.commit()
    return db_book