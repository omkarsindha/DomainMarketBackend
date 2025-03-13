from fastapi import APIRouter, Query, Depends
from typing import List
from services.namecheap_service import NamecheapService
#from services.auth_service import verify_token

router = APIRouter()
namecheap = NamecheapService()

@router.get("/check")
async def check_domains(domains: List[str] = Query(None)):
    """Check availability of domains."""
    if not domains:
        return {"error": "No domains provided"}
    return namecheap.check_domains(domains)

@router.get("/trending_tlds")
async def get_trending_tlds():
    """Get trending TLDs."""
    return namecheap.get_trending_tlds()

@router.post("/register")
async def register_domain(domain: str, years: int = 1):
    """Register a domain."""
    return namecheap.register_domain(domain, years)
