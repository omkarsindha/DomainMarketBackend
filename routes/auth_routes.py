from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from services.auth_service import AuthService
from database.connection import get_db

router = APIRouter()
auth_service = AuthService()

# Define Pydantic Model for User Registration
class RegisterRequest(BaseModel):
    username: str
    password: str

@router.post("/register/")
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    print("hii")
    user = auth_service.create_user(request.username, request.password, db)
    return {"message": "User registered successfully", "user": user.username}

@router.post("/login/")
def login(request: RegisterRequest, db: Session = Depends(get_db)):
    user = auth_service.authenticate_user(request.username, request.password, db)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = auth_service.create_access_token(user.username)
    return {"access_token": token, "token_type": "bearer"}
