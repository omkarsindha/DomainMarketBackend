from fastapi import APIRouter, Depends

from models.db_models import User, Notification
from services.namecheap_service import NamecheapService
from services.notification_service import NotificationService
from services.payment_service import PaymentService
from services.auth_service import AuthService
from services.database_service import DatabaseService
from models.api_dto import DeviceTokenRequest
from models.api_dto import DomainRegisterUserDetails, UserDomainResponse, UserTransactionResponse, SavePaymentRequest, \
    UserMyDetailsResponse
from database.connection import get_db
from sqlalchemy.orm import Session
from typing import List

router = APIRouter()
namecheap = NamecheapService()
database_service = DatabaseService()
auth_service = AuthService()
payment_service = PaymentService()
notification_service = NotificationService()

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
def get_my_transactions(username: str = Depends(auth_service.verify_token), db: Session = Depends(get_db)):
    """
    Get a list of all transactions owned by the user.
    """
    transactions = database_service.get_user_transactions(username, db)
    return transactions

@router.get("/", response_model=UserMyDetailsResponse)
def get_user(username: str = Depends(auth_service.verify_token), db: Session = Depends(get_db)):
    """Gets the current user's details"""
    user = database_service.get_user(username, db)
    return user


@router.post("/setup-intent")
def setup_intent(
        username: str = Depends(auth_service.verify_token),
        db: Session = Depends(get_db)
):
    """Creates a setup intent for the authenticated user to save a payment method."""
    return payment_service.create_setup_intent(username, db)

@router.post("/save-payment-method")
def save_payment_method(
    request: SavePaymentRequest,
    username: str = Depends(auth_service.verify_token),
    db: Session = Depends(get_db)
):
    """Saves a payment method for the authenticated user."""
    return payment_service.save_payment_method(username, request.payment_method_id, db)

@router.get("/payment-info/")
def get_payment_info(
    username: str = Depends(auth_service.verify_token),
    db: Session = Depends(get_db)
):
    """Gets payment information for the authenticated user."""
    return payment_service.get_payment_info(username, db)

@router.delete("/payment-method/")
def remove_payment_method(
    username: str = Depends(auth_service.verify_token),
    db: Session = Depends(get_db)
):
    """Removes the payment method for the authenticated user."""
    return payment_service.remove_payment_method(username, db)

@router.post("/register-device")
def register_device(
    request: DeviceTokenRequest,
    username: str = Depends(auth_service.verify_token),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == username).first()
    notification_service.register_device(user.id, request.token, db)
    return {"message": "Device registered"}

@router.get("/notifications")
def get_notifications(
    username: str = Depends(auth_service.verify_token),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == username).first()
    # Return last 50 notifications
    notifs = db.query(Notification).filter(Notification.user_id == user.id).order_by(Notification.created_at.desc()).limit(50).all()
    return notifs