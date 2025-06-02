from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from src.database import get_db, MovieModel
from src.database.models import CountryModel, GenreModel, ActorModel, LanguageModel
from src.schemas.movies import MovieCreateSchema, MovieListItemSchema, MovieDetailSchema

from src.schemas.movies import MovieListResponseSchema

router = APIRouter()


@router.get("/movies/", response_model=MovieListResponseSchema)
async def get_movies(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=20),
    db: AsyncSession = Depends(get_db)
):
    total_movies = await db.scalar(select(func.count(MovieModel.id)))
    if total_movies == 0:
        raise HTTPException(status_code=404, detail="No movies found.")

    total_pages = (total_movies + per_page - 1) // per_page
    if page > total_pages:
        raise HTTPException(status_code=404, detail="No movies found.")

    movies_query = (
        select(MovieModel)
        .order_by(MovieModel.id.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    movies = await db.execute(movies_query)
    movies_list = [
        MovieListItemSchema(
            id=movie.id,
            name=movie.name,
            date=movie.date,
            score=movie.score,
            overview=movie.overview,
        )
        for movie in movies.scalars().all()
    ]

    prev_page = (
        f"/theater/movies/?page={page - 1}&per_page={per_page}" if page > 1 else None
    )
    next_page = (
        f"/theater/movies/?page={page + 1}&per_page={per_page}" if page < total_pages else None
    )

    return MovieListResponseSchema(
        movies=movies_list,
        prev_page=prev_page,
        next_page=next_page,
        total_pages=total_pages,
        total_items=total_movies,
    )


@router.post(
    "/movies/",
    status_code=status.HTTP_201_CREATED,
    response_model=MovieDetailSchema
)
async def create_movie(
        movie_data: MovieCreateSchema,
        db: AsyncSession = Depends(get_db)
):
    existing_movie = await db.scalar(
        select(MovieModel)
        .where(MovieModel.name == movie_data.name)
        .where(MovieModel.date == movie_data.date)
    )
    if existing_movie:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A movie with the name '{movie_data.name}' and "
                   f"release date '{movie_data.date}' already exists.",
        )
    try:
        country = await db.scalar(select(CountryModel).where(CountryModel.code == movie_data.country))
        if not country:
            country = CountryModel(code=movie_data.country)
            db.add(country)
            await db.flush()

        genres = []
        for genre_name in movie_data.genres:
            genre = await db.scalar(select(GenreModel).where(GenreModel.name == genre_name))
            if not genre:
                genre = GenreModel(name=genre_name)
                db.add(genre)
                await db.flush()
            genres.append(genre)

        actors = []
        for actor_name in movie_data.actors:
            actor = await db.scalar(select(ActorModel).where(ActorModel.name == actor_name))
            if not actor:
                actor = ActorModel(name=actor_name)
                db.add(actor)
                await db.flush()
            actors.append(actor)

        languages = []
        for language_name in movie_data.languages:
            language = await db.scalar(select(LanguageModel).where(LanguageModel.name == language_name))
            if not language:
                language = LanguageModel(name=language_name)
                db.add(language)
                await db.flush()
            languages.append(language)

        new_movie = MovieModel(
            name=movie_data.name,
            date=movie_data.date,
            score=movie_data.score,
            overview=movie_data.overview,
            status=movie_data.status,
            budget=movie_data.budget,
            revenue=movie_data.revenue,
            country_id=country.id,
            genres=genres,
            actors=actors,
            languages=languages,
        )
        db.add(new_movie)
        await db.commit()
        await db.refresh(new_movie)

        return MovieDetailSchema(
            id=new_movie.id,
            name=new_movie.name,
            date=new_movie.date,
            score=new_movie.score,
            overview=new_movie.overview,
            status=new_movie.status,
            budget=new_movie.budget,
            revenue=new_movie.revenue,
            country={"id": country.id, "code": country.code, "name": country.name} if country else None,
            genres=[{"id": genre.id, "name": genre.name} for genre in genres],
            actors=[{"id": actor.id, "name": actor.name} for actor in actors],
            languages=[{"id": language.id, "name": language.name} for language in languages]
        )

    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The input data is invalid (e.g., missing required fields, invalid values)"
        )


@router.get("/movies/{movie_id}/", response_model=MovieDetailSchema)
async def get_movie_details(
    movie_id: int,
    db: AsyncSession = Depends(get_db)
):
    movie_query = (
        select(MovieModel)
        .where(MovieModel.id == movie_id)
        .options(
            joinedload(MovieModel.country),
            joinedload(MovieModel.genres),
            joinedload(MovieModel.actors),
            joinedload(MovieModel.languages)
        )
    )
    movie = await db.scalar(movie_query)

    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie with the given ID was not found."
        )

    return MovieDetailSchema(
        id=movie.id,
        name=movie.name,
        date=movie.date,
        score=movie.score,
        overview=movie.overview,
        status=movie.status,
        budget=movie.budget,
        revenue=movie.revenue,
        country={
            "id": movie.country.id,
            "code": movie.country.code,
            "name": movie.country.name
        } if movie.country else None,
        genres=[{"id": genre.id, "name": genre.name} for genre in movie.genres],
        actors=[{"id": actor.id, "name": actor.name} for actor in movie.actors],
        languages=[{"id": language.id, "name": language.name} for language in movie.languages]
    )


@router.delete("/movies/{movie_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    movie_query = select(MovieModel).where(MovieModel.id == movie_id)
    movie = await db.scalar(movie_query)

    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie with the given ID was not found."
        )

    await db.delete(movie)
    await db.commit()


@router.patch("/movies/{movie_id}/", status_code=status.HTTP_200_OK)
async def update_movie(movie_id: int, movie_data: dict, db: AsyncSession = Depends(get_db)):
    movie_query = select(MovieModel).where(MovieModel.id == movie_id)
    movie = await db.scalar(movie_query)

    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie with the given ID was not found."
        )

    valid_fields = ["name", "date", "score", "overview", "status", "budget", "revenue"]
    for field, value in movie_data.items():
        if field not in valid_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid field: {field}"
            )
        if field == "score" and (value < 0 or value > 100):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Score must be between 0 and 100."
            )
        if field in ["budget", "revenue"] and value < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field.capitalize()} must be non-negative."
            )
        setattr(movie, field, value)

    db.add(movie)
    await db.commit()

    return {"detail": "Movie updated successfully."}
