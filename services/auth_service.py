from datetime import datetime, timedelta
import jwt
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from models.db_models import User, UserDetails
from fastapi import HTTPException, Depends
from dotenv import load_dotenv
import os
import logging

logger = logging.getLogger(__name__)

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class AuthService:
    def create_user(self, username: str, email: str, password: str, db: Session):
        hashed_password = pwd_context.hash(password)
        user = User(username=username, email=email, password_hash=hashed_password)
        db.add(user)
        db.commit()
        db.refresh(user)

        user_details = UserDetails(user_id=user.id, email=email)
        db.add(user_details)
        db.commit()
        return user

    def authenticate_user(self, username: str, password: str, db: Session):
        user = db.query(User).filter(User.username == username).first()
        if user and pwd_context.verify(password, user.password_hash):
            return user
        return None

    def create_access_token(self, username: str):
        expiration = datetime.utcnow() + timedelta(hours=1000)
        token_data = {"sub": username, "exp": expiration}
        return jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)

    def verify_token(self, token: str = Depends(oauth2_scheme)):
        """Verify the JWT token and return the username."""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload.get("sub")  # Extract the username
        except jwt.ExpiredSignatureError:
            logger.warning(f"Authentication failed: Token expired")
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            logger.warning(f"Authentication failed: Invalid token")
            raise HTTPException(status_code=401, detail="Invalid token")