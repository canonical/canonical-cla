import sqlalchemy
from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio.session import AsyncSession

from app.database import get_session, redis
from app.launchpad.routes import launchpad_router
from app.models import Individual

app = FastAPI()
app.include_router(launchpad_router)


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/healthz")
def health_check():
    return {"status": "OK"}


@app.get("/test-redis")
async def test_redis():
    await redis.set("test-key", "test-value")
    return {"value": await redis.get("test-key")}


# DB testing routes wil be removed after testing


@app.post("/individuals/", response_model=Individual)
async def create_individual(
    individual: Individual, session: AsyncSession = Depends(get_session)
):
    try:
        db_individual = Individual.model_validate(individual)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.errors()
        )
    session.add(db_individual)
    try:
        await session.commit()
        await session.refresh(db_individual)
    except sqlalchemy.exc.IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Conflict")
    return db_individual


@app.get("/individuals", response_model=list[Individual])
async def read_individuals(session: AsyncSession = Depends(get_session)):
    individuals = (await session.execute(select(Individual))).scalars().all()
    return individuals
