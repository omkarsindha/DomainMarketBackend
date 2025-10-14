from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime
from decimal import Decimal



class DomainRegisterUserDetails(BaseModel):
    phone_number: str
    first_name: str
    last_name: str
    address: str
    city: str
    state: str
    zip_code: str
    country: str

class DomainRegistrationRequest(BaseModel):
    domain: str
    years: int = 1

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

class DomainsCheckRequest(BaseModel):
    domain: str

class PaymentRequest(BaseModel):
    domain: str
    price: float
    years: int = 1


class AuctionCreateRequest(BaseModel):
    domain_name: str
    start_price: float = Field(..., gt=0, description="The starting price for the auction.")
    duration_days: int = Field(..., gt=0, le=30, description="The duration of the auction in days.")

class BidCreateRequest(BaseModel):
    amount: float = Field(..., gt=0, description="The amount to bid.")

class BidResponse(BaseModel):
    bidder_username: str
    bid_amount: float
    created_at: datetime

    class Config:
        orm_mode = True

class AuctionResponse(BaseModel):
    id: int
    domain_name: str
    seller_username: str
    start_price: float
    current_highest_bid: Optional[float] = 0.0
    end_time: datetime
    status: str
    bids: List[BidResponse] = []
    winner_username: Optional[str] = None

    class Config:
        orm_mode = True


class ListingCreateRequest(BaseModel):
    domain_name: str
    price: float = Field(..., gt=0, description="The fixed price for the domain.")


class ListingResponse(BaseModel):
    id: int
    domain_name: str
    seller_username: str
    price: float
    created_at: datetime
    sold_at: Optional[datetime] = None
    status: str
    buyer_username: Optional[str] = None

    class Config:
        orm_mode = True


class SavePaymentRequest(BaseModel):
    username: str
    payment_method_id: str

class UserDomainResponse(BaseModel):
    id: int
    domain_name: str
    price: Decimal
    bought_date: datetime
    expiry_date: datetime

    class Config:
        orm_mode = True

class UserTransactionResponse(BaseModel):
    id: int
    transaction_type: str
    amount: Decimal
    currency: str
    transaction_date: datetime
    status: str
    description: Optional[str] = None
    domain_name_at_purchase: Optional[str] = None
    years_purchased: Optional[int] = None

    class Config:
        orm_mode = True

class UserMyDetailsResponse(BaseModel):
    username: str
    email: str

    class Config:
        from_attributes = True

#For domain management

class DNSRecordRequest(BaseModel):
    """Request model for a single DNS record."""
    hostname: str = Field(..., description="Hostname (e.g., '@', 'www', 'mail')")
    record_type: str = Field(..., description="Record type (A, AAAA, CNAME, MX, TXT, etc.)")
    address: str = Field(..., description="Target address/value")
    ttl: int = Field(default=1800, description="Time to live in seconds")
    mx_pref: Optional[int] = Field(default=10, description="MX priority (only for MX records)")

    @validator('record_type')
    def validate_record_type(cls, v):
        allowed_types = ['A', 'AAAA', 'CNAME', 'MX', 'TXT', 'NS', 'SRV', 'CAA']
        if v.upper() not in allowed_types:
            raise ValueError(f"Invalid record type. Allowed: {', '.join(allowed_types)}")
        return v.upper()


class DNSRecordResponse(BaseModel):
    """Response model for a single DNS record."""
    host_id: Optional[str] = None
    hostname: str
    record_type: str
    address: str
    ttl: int
    mx_pref: Optional[int] = None
    is_active: bool = True


class DNSUpdateRequest(BaseModel):
    """Request to update all DNS records for a domain."""
    records: List[DNSRecordRequest] = Field(..., description="List of DNS records to set")


class URLForwardingRequest(BaseModel):
    """Request to set up URL forwarding."""
    target_url: str = Field(..., description="URL to forward to (e.g., https://example.com)")
    forward_type: str = Field(default="permanent", description="'permanent' (301) or 'temporary' (302)")

    @validator('forward_type')
    def validate_forward_type(cls, v):
        if v.lower() not in ['permanent', 'temporary']:
            raise ValueError("Forward type must be 'permanent' or 'temporary'")
        return v.lower()


class DomainInfoResponse(BaseModel):
    """Response model for domain information."""
    domain_name: str
    owner_name: str
    is_owner: bool
    status: str
    created_date: Optional[datetime] = None
    expires_date: Optional[datetime] = None
    is_locked: bool
    auto_renew: bool
    whoisguard_enabled: bool
    is_premium: bool
    nameservers: List[str]


class DomainStatusResponse(BaseModel):
    """Comprehensive domain status including info and DNS."""
    domain_info: DomainInfoResponse
    dns_records: List[DNSRecordResponse]
    is_hosted: bool
    is_forwarding: bool


class HostingSetupResponse(BaseModel):
    """Response after setting up hosting."""
    success: bool
    message: str
    dns_records_set: List[DNSRecordResponse]