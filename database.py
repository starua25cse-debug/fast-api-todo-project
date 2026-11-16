from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./todos.db"


engine = create_engine(
    SQLALCHEMY_DATABASE_URL
)


SessionLocal = sessionmaker(autoflush=False, autocommit=False, bind=engine)


Base = declarative_base()


# -------------------------------
# DATABASE DEPENDENCY
# -------------------------------


def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
