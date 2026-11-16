from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.exc import SQLAlchemyError

import models
from database import db_dependency, engine
from models import Todos
from router import admin, auth
from router.auth import get_current_user

# -------------------------------
# CREATE DATABASE TABLES
# -------------------------------


models.Base.metadata.create_all(bind=engine)


# -------------------------------
# FASTAPI APPLICATION
# -------------------------------


app = FastAPI(
    title="Todo API",
    description="Todo API with JWT Authentication, User Registration and Admin Authorization",
    version="3.0.0",
)


# -------------------------------
# INCLUDE ROUTERS
# -------------------------------


app.include_router(auth.router)

app.include_router(admin.router)


# -------------------------------
# USER DEPENDENCY
# -------------------------------


user_dependency = Annotated[dict, Depends(get_current_user)]


# -------------------------------
# PYDANTIC SCHEMAS
# -------------------------------


class TodoCreate(BaseModel):

    title: str = Field(min_length=1, max_length=100)

    description: str = Field(min_length=1, max_length=100)

    priority: int = Field(ge=1, le=5)

    completed: bool = False

    model_config = ConfigDict(str_strip_whitespace=True)


class TodoUpdate(BaseModel):

    title: str = Field(min_length=1, max_length=100)

    description: str = Field(min_length=1, max_length=100)

    priority: int = Field(ge=1, le=5)

    completed: bool

    model_config = ConfigDict(str_strip_whitespace=True)


class TodoPatch(BaseModel):

    title: str | None = Field(default=None, min_length=1, max_length=100)

    description: str | None = Field(default=None, min_length=1, max_length=100)

    priority: int | None = Field(default=None, ge=1, le=5)

    completed: bool | None = None

    model_config = ConfigDict(str_strip_whitespace=True)

    @model_validator(mode="after")
    def validate_patch(self):

        if not self.model_fields_set:

            raise ValueError("At least one field must be provided.")

        for field in self.model_fields_set:

            if getattr(self, field) is None:

                raise ValueError(f"{field} cannot be null.")

        return self


class TodoResponse(BaseModel):

    id: int

    title: str

    description: str

    priority: int

    completed: bool

    model_config = ConfigDict(from_attributes=True)


# -------------------------------
# READ ALL USER TODOS
# -------------------------------


@app.get("/", response_model=list[TodoResponse], status_code=status.HTTP_200_OK)
def read_todos(user: user_dependency, db: db_dependency):

    return db.query(Todos).filter(Todos.owner_id == user["id"]).all()


# -------------------------------
# READ SPECIFIC USER TODO
# -------------------------------


@app.get("/todo/{todo_id}", response_model=TodoResponse, status_code=status.HTTP_200_OK)
def read_specific_todos(db: db_dependency, user: user_dependency, todo_id: int):

    todo = (
        db.query(Todos)
        .filter(Todos.id == todo_id, Todos.owner_id == user["id"])
        .first()
    )

    if todo is None:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found"
        )

    return todo


# -------------------------------
# CREATE TODO
# -------------------------------


@app.post("/create/", response_model=TodoResponse, status_code=status.HTTP_201_CREATED)
def create_todos(db: db_dependency, user: user_dependency, new_todo: TodoCreate):

    todo_model = Todos(**new_todo.model_dump(), owner_id=user["id"])

    try:

        db.add(todo_model)

        db.commit()

        db.refresh(todo_model)

        return todo_model

    except SQLAlchemyError:

        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create todo",
        )


# -------------------------------
# UPDATE TODO (PUT)
# -------------------------------


@app.put("/edit/{todo_id}", response_model=TodoResponse, status_code=status.HTTP_200_OK)
def update_todo(
    db: db_dependency, user: user_dependency, todo_id: int, updated_todo: TodoUpdate
):

    todo = (
        db.query(Todos)
        .filter(Todos.id == todo_id, Todos.owner_id == user["id"])
        .first()
    )

    if todo is None:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found"
        )

    update_data = updated_todo.model_dump()

    try:

        for key, value in update_data.items():

            setattr(todo, key, value)

        db.commit()

        db.refresh(todo)

        return todo

    except SQLAlchemyError:

        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not update todo",
        )


# -------------------------------
# PARTIAL UPDATE TODO (PATCH)
# -------------------------------


@app.patch(
    "/edit/{todo_id}", response_model=TodoResponse, status_code=status.HTTP_200_OK
)
def partial_update_todo(
    db: db_dependency, user: user_dependency, todo_id: int, updated_todo: TodoPatch
):

    todo = (
        db.query(Todos)
        .filter(Todos.id == todo_id, Todos.owner_id == user["id"])
        .first()
    )

    if todo is None:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found"
        )

    update_data = updated_todo.model_dump(exclude_unset=True)

    try:

        for key, value in update_data.items():

            setattr(todo, key, value)

        db.commit()

        db.refresh(todo)

        return todo

    except SQLAlchemyError:

        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not update todo",
        )


# -------------------------------
# DELETE TODO
# -------------------------------


@app.delete("/delete/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_todo(db: db_dependency, user: user_dependency, todo_id: int):

    todo = (
        db.query(Todos)
        .filter(Todos.id == todo_id, Todos.owner_id == user["id"])
        .first()
    )

    if todo is None:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found"
        )

    try:

        db.delete(todo)

        db.commit()

        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except SQLAlchemyError:

        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not delete todo",
        )
