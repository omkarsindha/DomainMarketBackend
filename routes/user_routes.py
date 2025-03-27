from fastapi import APIRouter, Depends

from services.auth_service import AuthService
from services.namecheap_service import NamecheapService
from services.database_service import DatabaseService
from models.api_dto import DomainRegisterUserDetails
from database.connection import get_db
from sqlalchemy.orm import Session

router = APIRouter()
namecheap = NamecheapService()
database_service = DatabaseService()
auth_service = AuthService()

@router.get("/user_details")
def get_user_details(username: str = Depends(auth_service.verify_token), db: Session = Depends(get_db)):
    """Check availability of additional details in user_details model."""

    details = database_service.get_user_details(username, db)
    return details

@router.post("/user_details")
def post_user_details(user_details: DomainRegisterUserDetails, username: str = Depends(auth_service.verify_token)):
    """Additional details before registering for a domain."""
