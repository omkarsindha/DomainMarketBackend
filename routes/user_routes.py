import stripe
from fastapi import APIRouter, Depends

from routes.auction_routes import payment_method_service
from services import auction_service
from services.auth_service import AuthService
from services.namecheap_service import NamecheapService
from services.database_service import DatabaseService
from models.api_dto import DomainRegisterUserDetails, UserDomainResponse, UserTransactionResponse, SavePaymentRequest
from database.connection import get_db
from sqlalchemy.orm import Session
from typing import List

router = APIRouter()
namecheap = NamecheapService()
database_service = DatabaseService()
auth_service = AuthService()


@router.get("/user-details")
def get_user_details(username: str = Depends(auth_service.verify_token), db: Session = Depends(get_db)):
    """Check availability of additional details in user_details model."""
    details = database_service.get_user_details(username, db)
    return details

@router.post("/user-details")
def post_user_details(user_details: DomainRegisterUserDetails, username: str = Depends(auth_service.verify_token),
        db: Session = Depends(get_db)):
    """Save or update additional user details."""
    saved_details = database_service.create_or_update_user_details(username, user_details, db)
    return {"message": "User details saved successfully", "details": saved_details}

@router.get("/my-domains", response_model=List[UserDomainResponse])
def get_my_domains(username: str = Depends(auth_service.verify_token), db: Session = Depends(get_db)):
    """
    Get a list of all domains owned by the user.
    """
    domains = database_service.get_user_domains(username, db)
    return domains

@router.get("/my-transactions", response_model=List[UserTransactionResponse])
def get_my_domains(username: str = Depends(auth_service.verify_token), db: Session = Depends(get_db)):
    """
    Get a list of all transactions owned by the user.
    """
    transactions = database_service.get_user_transactions(username, db)
    return transactions

@router.get("/")
def get_user(username: str = Depends(auth_service.verify_token), db: Session = Depends(get_db)):
    """Check availability of additional details in user_details model."""
    user = database_service.get_user(username, db)
    return user


@router.post("/setup-intent")
def setup_intent(
        username: str,
        db: Session = Depends(get_db)
):
    return payment_method_service.create_setup_intent(username, db)

@router.post("/save-payment-method")
def save_payment_method(request: SavePaymentRequest, db: Session = Depends(get_db)):
    return payment_method_service.save_payment_method(request.username, request.payment_method_id, db)

