from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from database import Base

# -------------------------------
# USERS MODEL
# -------------------------------


class Users(Base):

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    email = Column(String(255), unique=True, nullable=False, index=True)

    username = Column(String(50), unique=True, nullable=False, index=True)

    firstname = Column(String(50), nullable=False)

    lastname = Column(String(50), nullable=False)

    hash_password = Column(String(255), nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)

    role = Column(String(20), default="user", nullable=False)

    phone_number = Column(String(20), nullable=True)

    todos = relationship("Todos", back_populates="owner")


# -------------------------------
# TODOS MODEL
# -------------------------------


class Todos(Base):

    __tablename__ = "todos"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String(100), nullable=False)

    description = Column(String(100), nullable=False)

    priority = Column(Integer, nullable=False)

    completed = Column(Boolean, default=False, nullable=False)

    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    owner = relationship("Users", back_populates="todos")
