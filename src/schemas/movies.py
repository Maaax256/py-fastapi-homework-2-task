from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import timedelta, date as date_type

from pydantic.v1 import validator


class MovieListItemSchema(BaseModel):
    id: int = Field(...)
    name: str = Field(...)
    date: date_type = Field(...)
    score: float = Field(...)
    overview: str = Field(...)


class MovieListResponseSchema(BaseModel):
    movies: List[MovieListItemSchema] = Field(...)
    prev_page: Optional[str] = Field(None)
    next_page: Optional[str] = Field(None)
    total_pages: int = Field(...)
    total_items: int = Field(...)


class MovieCreateSchema(BaseModel):
    name: str = Field(..., max_length=255)
    date: date_type = Field(...)
    score: float = Field(..., ge=0, le=100)
    overview: str = Field(...)
    status: str = Field(..., pattern="^(Released|Post Production|In Production)$")
    budget: float = Field(..., ge=0)
    revenue: float = Field(..., ge=0)
    country: str = Field(...)
    genres: List[str] = Field(...)
    actors: List[str] = Field(...)
    languages: List[str] = Field(...)

    @validator("date")
    def validate_date(cls, value):
        if value > date_type.today() + timedelta(days=365):
            raise ValueError("The date must not be more than one year in the future.")
        return value


class MovieDetailSchema(BaseModel):
    id: int = Field(...)
    name: str = Field(...)
    date: date_type = Field(...)
    score: float = Field(...)
    overview: str = Field(...)
    status: str = Field(...)
    budget: float = Field(...)
    revenue: float = Field(...)
    country: Optional[dict] = Field(None)
    genres: List[dict] = Field(...)
    actors: List[dict] = Field(...)
    languages: List[dict] = Field(...)
