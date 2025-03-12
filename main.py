from fastapi import FastAPI, Query
from typing import List, Optional
import json
from NamecheapService import NamecheapService

app = FastAPI()
namecheap = NamecheapService()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/domains/check")
async def check_domains(domains: List[str] = Query(None)):
    """
    Check availability of domains.

    Args:
        domains: List of domains to check

    Returns:
        JSON response with domain availability information
    """
    if not domains:
        return {"error": "No domains provided"}

    return namecheap.check_domains(domains)


@app.get("/domains/trending_tlds")
async def get_trending_tlds():
    """
    Get trending top-level domains (TLDs).

    Returns:
        JSON response with a list of trending TLDs.
    """
    return namecheap.get_trending_tlds()


@app.post("/domains/register")
async def register_domain(domain: str, years: int = 1):
    """
    Register a domain for a user.

    Args:
        domain: The domain name to register.
        years: Number of years to register the domain (default: 1).

    Returns:
        JSON response with registration status.
    """
    return namecheap.register_domain(domain, years)
