from fastapi import APIRouter, Query, Depends
from typing import List
from database.connection import get_db
from sqlalchemy.orm import Session
from services.namecheap_service import NamecheapService
from services.auth_service import AuthService  # Import the authentication service

router = APIRouter()
namecheap = NamecheapService()
auth_service = AuthService()

@router.get("/check")
def check_domain(domain: str = Query(...), username: str = Depends(auth_service.verify_token)):
    """Check availability of a single domain."""
    if not domain:
        return {"error": "No domain provided"}
    return namecheap.check_domain_availability(domain)

@router.get("/trending_domains")
def trending_domains(username: str = Depends(auth_service.verify_token)):
    """"Gets the trending domains"""
    return namecheap.get_trending_available_domains()

@router.get("/trending_tlds")
def get_trending_tlds(username: str = Depends(auth_service.verify_token)):
    """Get trending TLDs."""
    return namecheap.get_trending_tlds()

@router.post("/register")
def register_domain(domain: str = Query(...),years: int = Query(...),
                    username: str = Depends(auth_service.verify_token), db: Session = Depends(get_db)):
    """Register a domain using Namecheap for the authenticated user."""
    return namecheap.register_domain(domain, years, username, db)