from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from database import db_dependency
from models import Todos
from router.auth import get_current_user

router = APIRouter(prefix="/admin", tags=["Admin"])


# -------------------------------
# USER DEPENDENCY
# -------------------------------


user_dependency = Annotated[dict, Depends(get_current_user)]


# -------------------------------
# ADMIN AUTHORIZATION
# -------------------------------


def verify_admin(user: dict):

    if user.get("role") != "admin":

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )


# -------------------------------
# READ ALL USERS' TODOS
# -------------------------------


@router.get("/todo", status_code=status.HTTP_200_OK)
def read_all(user: user_dependency, db: db_dependency):

    verify_admin(user)

    return db.query(Todos).all()


# -------------------------------
# DELETE TODO BY ADMIN
# -------------------------------


@router.delete("/delete/{todo_id}", status_code=status.HTTP_200_OK)
def delete_todos_by_admin(user: user_dependency, db: db_dependency, todo_id: int):

    verify_admin(user)

    todo = db.query(Todos).filter(Todos.id == todo_id).first()

    if todo is None:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found"
        )

    try:

        db.delete(todo)

        db.commit()

        return {"message": "Todo deleted successfully"}

    except SQLAlchemyError:

        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not delete todo",
        )
