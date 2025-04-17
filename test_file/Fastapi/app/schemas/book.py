from typing import Optional
from pydantic import BaseModel

class BookBase(BaseModel):
    title: str
    description: Optional[str] = None
    author: str
    year: int

class BookCreate(BookBase):
    pass

class BookUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    author: Optional[str] = None
    year: Optional[int] = None

class Book(BookBase):
    id: int
    owner_id: int

    class Config:
        orm_mode = True
