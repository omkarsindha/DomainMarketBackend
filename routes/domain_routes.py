from fastapi import APIRouter, Query, Depends, HTTPException, status
from typing import List
from database.connection import get_db
from sqlalchemy.orm import Session
from models.api_dto import PaymentRequest, UserDomainResponse
from models.db_models import User, Domain
from services import payment_service
from services.namecheap_service import NamecheapService
from services.auth_service import AuthService
from services.database_service import DatabaseService

router = APIRouter()
namecheap = NamecheapService()
payment = payment_service.PaymentService()
auth_service = AuthService()
database_service = DatabaseService()

@router.get("/check")
def check_domain(domain: str = Query(...), username: str = Depends(auth_service.verify_token)):
    """Check availability of a single domain."""
    if not domain:
        return {"error": "No domain provided"}
    return namecheap.check_domain_availability(domain)

@router.get("/trending-domains")
def trending_domains(username: str = Depends(auth_service.verify_token)):
    """Gets the trending domains"""
    return namecheap.get_trending_available_domains()

@router.get("/trending-tlds")
def get_trending_tlds(username: str = Depends(auth_service.verify_token)):
    """Get trending TLDs."""
    return namecheap.get_trending_tlds()

@router.post("/purchase-domain")
def purchase_domain(
    payment_details: PaymentRequest,
    username: str = Depends(auth_service.verify_token),
    db: Session = Depends(get_db),
):
    return payment.purchase_domain(payment_details, username, db)


@router.post("/{domain_id}/auto-renew")
def toggle_auto_renew(
        domain_id: int,
        enable: bool,
        username: str = Depends(auth_service.verify_token),
        db: Session = Depends(get_db)
):
    """
    Enables or disables auto-renewal for a domain.
    Requires a saved payment method on the user account.
    """
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    domain = db.query(Domain).filter(Domain.id == domain_id, Domain.user_id == user.id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found or not owned by you")

    if enable:
        if not user.stripe_customer_id or not user.stripe_payment_method_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You must save a credit card in your account settings before enabling auto-renew."
            )

    domain.auto_renew_enabled = enable
    db.commit()

    status_msg = "enabled" if enable else "disabled"
    return {"message": f"Auto-renew {status_msg} for {domain.domain_name}"}

# @router.post("/register")
# def register_domain(domain: str = Query(...),years: int = Query(...),
#                     username: str = Depends(auth_service.verify_token), db: Session = Depends(get_db)):
#     """Register a domain using Namecheap for the authenticated user."""
#     return namecheap.register_domain(domain, years, username, db)





