from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session
from typing import List

from database.connection import get_db
from services.auth_service import AuthService
from services.database_service import DatabaseService
from services.namecheap_management_service import NamecheapManagementService
from models.api_dto import (
    DomainInfoResponse,
    DNSRecordResponse,
    DNSUpdateRequest,
    URLForwardingRequest,
    DomainStatusResponse,
    HostingSetupResponse
)
from models.db_models import Domain, User

router = APIRouter()
auth_service = AuthService()
database_service = DatabaseService()
management_service = NamecheapManagementService()


def verify_domain_ownership(sld: str, tld: str, username: str, db: Session):
    """
    Helper function to verify that the authenticated user owns the domain.

    Args:
        sld: Second-level domain (e.g., 'example' in example.com)
        tld: Top-level domain (e.g., 'com' in example.com)
        username: Username from JWT token
        db: Database session

    Raises:
        HTTPException: If domain not found or user doesn't own it
    """
    domain_name = f"{sld}.{tld}"

    # Get the user
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check if domain exists and belongs to user
    domain = db.query(Domain).filter(
        Domain.domain_name == domain_name,
        Domain.user_id == user.id
    ).first()

    if not domain:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own this domain or it does not exist in your account"
        )

    return domain


@router.get("/manage/{sld}/{tld}/info", response_model=DomainInfoResponse)
def get_domain_info(
        sld: str = Path(..., description="Second-level domain (e.g., 'example' in example.com)"),
        tld: str = Path(..., description="Top-level domain (e.g., 'com' in example.com)"),
        username: str = Depends(auth_service.verify_token),
        db: Session = Depends(get_db)
):
    """
    Get comprehensive information about a domain.

    Returns domain details including:
    - Owner information
    - Registration and expiration dates
    - Lock status
    - Auto-renew status
    - WhoisGuard status
    - Nameservers
    """
    # Verify ownership
    verify_domain_ownership(sld, tld, username, db)

    # Get domain info from Namecheap
    return management_service.get_domain_info(sld, tld, username)


@router.get("/manage/{sld}/{tld}/dns", response_model=List[DNSRecordResponse])
def get_dns_records(
        sld: str = Path(..., description="Second-level domain"),
        tld: str = Path(..., description="Top-level domain"),
        username: str = Depends(auth_service.verify_token),
        db: Session = Depends(get_db)
):
    """
    Get all DNS records for a domain.

    Returns a list of DNS records including:
    - A, AAAA, CNAME, MX, TXT, NS records
    - Hostnames and addresses
    - TTL values
    - MX priorities (for MX records)
    """
    # Verify ownership
    verify_domain_ownership(sld, tld, username, db)

    # Get DNS records from Namecheap
    return management_service.get_dns_records(sld, tld)


@router.post("/manage/{sld}/{tld}/dns/update", response_model=List[DNSRecordResponse])
def update_dns_records(
        request: DNSUpdateRequest,
        sld: str = Path(..., description="Second-level domain"),
        tld: str = Path(..., description="Top-level domain"),
        username: str = Depends(auth_service.verify_token),
        db: Session = Depends(get_db)
):
    """
    Update DNS records for a domain.

    **WARNING:** This replaces ALL existing DNS records with the provided ones.
    Make sure to include all records you want to keep.

    Request body should contain a list of DNS records with:
    - hostname: The subdomain (use '@' for root domain, 'www' for www subdomain)
    - record_type: A, AAAA, CNAME, MX, TXT, NS, SRV, or CAA
    - address: Target IP address or hostname
    - ttl: Time to live (default: 1800 seconds)
    - mx_pref: Priority for MX records (default: 10)

    Example:
    ```json
    {
      "records": [
        {
          "hostname": "@",
          "record_type": "A",
          "address": "192.168.1.1",
          "ttl": 1800
        },
        {
          "hostname": "www",
          "record_type": "CNAME",
          "address": "example.com.",
          "ttl": 1800
        }
      ]
    }
    ```
    """
    # Verify ownership
    verify_domain_ownership(sld, tld, username, db)

    # Update DNS records
    return management_service.update_dns_records(sld, tld, request.records)


@router.post("/manage/{sld}/{tld}/forward")
def set_url_forwarding(
        request: URLForwardingRequest,
        sld: str = Path(..., description="Second-level domain"),
        tld: str = Path(..., description="Top-level domain"),
        username: str = Depends(auth_service.verify_token),
        db: Session = Depends(get_db)
):
    """
    Set up URL forwarding for a domain.

    This will redirect visitors from your domain to another URL.

    Request body:
    - target_url: The URL to forward to (e.g., "https://example.com")
    - forward_type: Either "permanent" (301 redirect) or "temporary" (302 redirect)

    Example:
    ```json
    {
      "target_url": "https://myothersite.com",
      "forward_type": "permanent"
    }
    ```
    """
    # Verify ownership
    verify_domain_ownership(sld, tld, username, db)

    # Set URL forwarding
    return management_service.set_url_forwarding(
        sld, tld, request.target_url, request.forward_type
    )


@router.post("/manage/{sld}/{tld}/host", response_model=HostingSetupResponse)
def setup_hosting(
        sld: str = Path(..., description="Second-level domain"),
        tld: str = Path(..., description="Top-level domain"),
        custom_ip: str = None,
        username: str = Depends(auth_service.verify_token),
        db: Session = Depends(get_db)
):
    """
    Set up basic hosting for a domain.

    This will automatically configure:
    - A record for root domain (@) pointing to your server IP
    - CNAME record for www subdomain pointing to root domain

    Query parameters:
    - custom_ip (optional): Custom IP address to use instead of default

    The default hosting IP is configured in the .env file (DEFAULT_HOSTING_IP).

    Example request:
    ```
    POST /domains/manage/example/com/host?custom_ip=34.56.78.90
    ```
    """
    # Verify ownership
    verify_domain_ownership(sld, tld, username, db)

    # Set up hosting
    result = management_service.set_hosting(sld, tld, custom_ip)

    return HostingSetupResponse(
        success=result["success"],
        message=result["message"],
        dns_records_set=result["dns_records_set"]
    )


@router.get("/manage/{sld}/{tld}/status", response_model=DomainStatusResponse)
def get_domain_status(
        sld: str = Path(..., description="Second-level domain"),
        tld: str = Path(..., description="Top-level domain"),
        username: str = Depends(auth_service.verify_token),
        db: Session = Depends(get_db)
):
    """
    Get comprehensive status of a domain.

    This endpoint combines information from multiple sources to provide:
    - Complete domain information (registration dates, lock status, etc.)
    - All DNS records
    - Hosting status (whether domain is hosted)
    - Forwarding status (whether domain is forwarding)

    This is useful for displaying a complete dashboard view of the domain.
    """
    # Verify ownership
    verify_domain_ownership(sld, tld, username, db)

    # Get comprehensive status
    return management_service.get_domain_status(sld, tld, username)


@router.get("/manage/my-domains")
def list_my_manageable_domains(
        username: str = Depends(auth_service.verify_token),
        db: Session = Depends(get_db)
):
    """
    Get a list of all domains owned by the authenticated user.

    This is a convenience endpoint that returns domains in a format
    ready for the management dashboard, including parsed SLD and TLD.

    Returns:
    ```json
    {
      "domains": [
        {
          "domain_name": "example.com",
          "sld": "example",
          "tld": "com",
          "expiry_date": "2025-12-31T00:00:00",
          "management_url": "/domains/manage/example/com/status"
        }
      ]
    }
    ```
    """
    domains = database_service.get_user_domains(username, db)

    manageable_domains = []
    for domain in domains:
        # Parse domain name into SLD and TLD
        parts = domain.domain_name.split('.')
        if len(parts) >= 2:
            sld = '.'.join(parts[:-1])  # Everything before last dot
            tld = parts[-1]  # Last part

            manageable_domains.append({
                "domain_name": domain.domain_name,
                "sld": sld,
                "tld": tld,
                "expiry_date": domain.expiry_date,
                "management_url": f"/domains/manage/{sld}/{tld}/status"
            })

    return {"domains": manageable_domains}