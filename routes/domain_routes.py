from http.client import responses

from fastapi import APIRouter, Query, Depends
from typing import List
from database.connection import get_db
from sqlalchemy.orm import Session

from models.api_dto import PaymentRequest
from services import payment_service
from services.namecheap_service import NamecheapService
from services.auth_service import AuthService  # Import the authentication service

router = APIRouter()
namecheap = NamecheapService()
payment = payment_service.PaymentService()
auth_service = AuthService()

@router.get("/check")
def check_domain(domain: str = Query(...), username: str = Depends(auth_service.verify_token)):
    """Check availability of a single domain."""
    if not domain:
        return {"error": "No domain provided"}
    return namecheap.check_domain_availability(domain)

@router.get("/trending_domains")
def trending_domains(username: str = Depends(auth_service.verify_token)):
    """Gets the trending domains"""
    return namecheap.get_trending_available_domains()

@router.get("/trending_tlds")
def get_trending_tlds(username: str = Depends(auth_service.verify_token)):
    """Get trending TLDs."""
    return namecheap.get_trending_tlds()

@router.post("/purchase-domain")
def purchase_domain(
    payment_details: PaymentRequest,
    username: str = Depends(auth_service.verify_token),
    db: Session = Depends(get_db),
):
    domain = payment_details.domain
    years = payment_details.years
    payment_token = payment_details.payment_token
    return payment.purchase_domain(domain, years, payment_token, username, db)


@router.post("/register")
def register_domain(domain: str = Query(...),years: int = Query(...),
                    username: str = Depends(auth_service.verify_token), db: Session = Depends(get_db)):
    """Register a domain using Namecheap for the authenticated user."""
    return namecheap.register_domain(domain, years, username, db)