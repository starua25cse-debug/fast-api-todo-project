import os
from datetime import UTC, datetime, timedelta
from typing import Annotated

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pwdlib import PasswordHash
from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    model_validator,
)
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from database import db_dependency
from models import Users

# Environment configuration
load_dotenv()

router = APIRouter(prefix="/auth", tags=["Authentication"])

password_hash = PasswordHash.recommended()

SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is missing from environment variables")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

OAuth2_bearer = OAuth2PasswordBearer(tokenUrl="/auth/login")


# =========================
# Pydantic Schemas
# =========================


class CreateUsers(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50)
    firstname: str = Field(min_length=1, max_length=50)
    lastname: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=8)
    phone_number: str | None = Field(default=None, max_length=20)

    model_config = ConfigDict(str_strip_whitespace=True)


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    username: str
    firstname: str
    lastname: str
    phone_number: str | None = None
    is_active: bool
    role: str

    model_config = ConfigDict(from_attributes=True)


class UserProfileUpdate(BaseModel):
    email: EmailStr | None = None
    username: str | None = Field(default=None, min_length=3, max_length=50)
    firstname: str | None = Field(default=None, min_length=1, max_length=50)
    lastname: str | None = Field(default=None, min_length=1, max_length=50)
    phone_number: str | None = Field(default=None, max_length=20)

    model_config = ConfigDict(str_strip_whitespace=True)

    @model_validator(mode="after")
    def validate_update(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided.")

        for field in self.model_fields_set:
            value = getattr(self, field)

            if field != "phone_number" and value is None:
                raise ValueError(f"{field} cannot be null.")

            if isinstance(value, str) and not value:
                raise ValueError(f"{field} cannot be empty.")

        return self


# Password change schema
class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8)
    confirm_new_password: str = Field(min_length=8)

    @model_validator(mode="after")
    def validate_passwords(self):
        if self.new_password != self.confirm_new_password:
            raise ValueError("New passwords do not match.")

        if self.current_password == self.new_password:
            raise ValueError("New password must be different from current password.")

        return self


# =========================
# Authentication Functions
# =========================


def authenticate_user(username: str, password: str, db: Session):
    user = db.query(Users).filter(Users.username == username).first()

    if user is None:
        return False

    if not password_hash.verify(password, user.hash_password):
        return False

    if not user.is_active:
        return False

    return user


def create_access_token(
    username: str, user_id: int, role: str, expires_delta: timedelta
):
    encode = {"sub": username, "id": user_id, "role": role}

    expires = datetime.now(UTC) + expires_delta
    encode.update({"exp": expires})

    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)


# =========================
# Current User Dependency
# =========================


def get_current_user(token: Annotated[str, Depends(OAuth2_bearer)], db: db_dependency):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        user_id = payload.get("id")

        if user_id is None:
            raise credentials_exception

        if not isinstance(user_id, int) or isinstance(user_id, bool):
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    user = db.query(Users).filter(Users.id == user_id).first()

    if user is None or not user.is_active:
        raise credentials_exception

    return {"username": user.username, "id": user.id, "role": user.role}


user_dependency = Annotated[dict, Depends(get_current_user)]


# =========================
# User Registration
# =========================


@router.post(
    "/createuser", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
def create_users(db: db_dependency, new_user: CreateUsers):

    user_model = Users(
        email=new_user.email,
        username=new_user.username,
        firstname=new_user.firstname,
        lastname=new_user.lastname,
        phone_number=new_user.phone_number,
        hash_password=password_hash.hash(new_user.password),
        is_active=True,
        role="user",
    )

    try:
        db.add(user_model)
        db.commit()
        db.refresh(user_model)

        return user_model

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or username already exists",
        )

    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create user",
        )


# =========================
# User Login
# =========================


@router.post("/login")
def login_user(
    db: db_dependency, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
):

    user = authenticate_user(form_data.username, form_data.password, db)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(
        user.username,
        user.id,
        user.role,
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return {"access_token": token, "token_type": "bearer"}


# =========================
# Read Current User
# =========================


@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
def read_current_user(user: user_dependency, db: db_dependency):

    current_user = db.query(Users).filter(Users.id == user["id"]).first()

    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return current_user


# =========================
# Update User Profile
# =========================


@router.patch("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
def update_current_user(
    user: user_dependency, db: db_dependency, updated_data: UserProfileUpdate
):

    current_user = db.query(Users).filter(Users.id == user["id"]).first()

    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    update_data = updated_data.model_dump(exclude_unset=True)

    try:
        for key, value in update_data.items():
            setattr(current_user, key, value)

        db.commit()
        db.refresh(current_user)

        return current_user

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or username already exists",
        )

    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not update user profile",
        )


# =========================
# Change User Password
# =========================


@router.patch("/change-password", status_code=status.HTTP_200_OK)
def change_password(
    user: user_dependency, db: db_dependency, password_data: PasswordChange
):

    current_user = db.query(Users).filter(Users.id == user["id"]).first()

    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Verify current password
    if not password_hash.verify(
        password_data.current_password, current_user.hash_password
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Hash the new password
    new_hashed_password = password_hash.hash(password_data.new_password)

    try:
        current_user.hash_password = new_hashed_password

        db.commit()

        return {"message": "Password changed successfully"}

    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not change password",
        )
