from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

SQLALCHEMY_DATABASE_URL = "postgresql://postgres.mirnwmirqxruxskpzzbj:susmoytarua01312@aws-1-ap-northeast-1.pooler.supabase.com:5432/postgres"


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
