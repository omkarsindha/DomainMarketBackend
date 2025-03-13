from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from models.user_model import User
from fastapi import HTTPException, Depends

# Secret Key & Algorithm
SECRET_KEY = "your_secret_key"
ALGORITHM = "HS256"

# Password Hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    def create_user(self, username: str, password: str, db: Session):
        hashed_password = pwd_context.hash(password)
        user = User(username=username, password_hash=hashed_password)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def authenticate_user(self, username: str, password: str, db: Session):
        user = db.query(User).filter(User.username == username).first()
        if user and pwd_context.verify(password, user.password_hash):
            return user
        return None

    def create_access_token(self, username: str):
        expiration = datetime.utcnow() + timedelta(hours=1)
        token_data = {"sub": username, "exp": expiration}
        return jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)

    def verify_token(self, token: str):
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                raise HTTPException(status_code=401, detail="Invalid token")
            return username
        except Exception:
            raise HTTPException(status_code=401, detail="Could not validate credentials")