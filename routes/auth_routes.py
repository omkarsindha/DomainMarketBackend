from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from services.auth_service import AuthService
from services.database_service import DatabaseService
from database.connection import get_db
from models.api_dto import RegisterRequest
from models.api_dto import LoginRequest

router = APIRouter()
auth_service = AuthService()


@router.post("/register/")
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    user = auth_service.create_user(request.username, request.email, request.password, db)
    return {"message": "User registered successfully", "user": user.username}


@router.post("/login/")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = auth_service.authenticate_user(request.username, request.password, db)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = auth_service.create_access_token(user.username)
    return {"access_token": token, "token_type": "bearer"}
